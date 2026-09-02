"""Pinned PyInstaller one-folder build, membership audit, and native smoke."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import re
import shlex
import shutil
import socket
import stat
import subprocess
import sys
import time
import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
from typing import Final, cast

from open_brain.services.appliance_lifecycle import ArtifactCandidate
from open_brain.services.native_artifacts import (
    NATIVE_EXECUTABLE_NAME,
    NATIVE_MANIFEST_NAME,
    NativeArtifactError,
    NativeArtifactLifecycleAdapter,
    NativeArtifactManifest,
    native_platform_tag,
)

_FAILURE: Final = "native build operation failed"
_SOURCE_SHA: Final = re.compile(r"[0-9a-f]{40}")
_TOOLCHAIN = Path("release/phase4-toolchain.json")
_SPEC = Path("release/native/open-brain.spec")
_ARTIFACT_POLICY = Path(__file__).resolve().parents[2] / "release/v0-artifact-policy.json"
_RESOURCE_MEMBERS: Final = (
    "_internal/open_brain/resources/supervisors/launchd.json",
    "_internal/open_brain/resources/supervisors/systemd.service",
)
_MAXIMUM_MEMBERS: Final = 20_000
_MAXIMUM_PROCESS_OUTPUT: Final = 128 * 1024


class NativeBuildError(RuntimeError):
    """A native build step failed without exposing raw host output."""


class NativeBuildStageError(NativeBuildError):
    def __init__(self, stage: str) -> None:
        self.stage = stage
        super().__init__(_FAILURE)


class NativeSmokeError(NativeBuildStageError):
    pass


@dataclass(frozen=True, slots=True)
class NativeBuildConfiguration:
    root: Path
    spec_path: Path
    python_executable: str
    python_version: str
    pyinstaller_version: str
    hooks_version: str
    mode: str


@dataclass(frozen=True, slots=True)
class NativeArtifactMember:
    path: str
    kind: str
    size: int | None

    def to_dict(self) -> dict[str, object]:
        value: dict[str, object] = {"kind": self.kind, "path": self.path}
        if self.size is not None:
            value["size"] = self.size
        return value


@dataclass(frozen=True, slots=True)
class NativeArtifactAudit:
    candidate_id: str
    version: str
    platform_tag: str
    tree_sha256: str
    membership_sha256: str
    member_count: int
    symlink_count: int
    resource_members: tuple[str, ...]
    members: tuple[NativeArtifactMember, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "member_count": self.member_count,
            "membership_sha256": self.membership_sha256,
            "platform": self.platform_tag,
            "resource_members": list(self.resource_members),
            "symlink_count": self.symlink_count,
            "tree_sha256": self.tree_sha256,
            "version": self.version,
        }


def load_native_build_configuration(root: Path) -> NativeBuildConfiguration:
    selected_root = root.resolve(strict=True)
    try:
        toolchain = json.loads((selected_root / _TOOLCHAIN).read_text(encoding="utf-8"))
        project = tomllib.loads((selected_root / "pyproject.toml").read_text(encoding="utf-8"))
        native = cast(dict[str, object], toolchain["native"])
        primary = cast(dict[str, object], native["primary"])
        dependency_groups = cast(dict[str, object], project["dependency-groups"])
        group = dependency_groups["native-build"]
        spec_path = selected_root / _SPEC
        if (
            native.get("build_python") != "3.12"
            or primary
            != {
                "hooks_name": "pyinstaller-hooks-contrib",
                "hooks_version": "2026.7",
                "mode": "onedir",
                "name": "PyInstaller",
                "version": "6.22.2",
            }
            or group
            != [
                "pyinstaller==6.22.2",
                "pyinstaller-hooks-contrib==2026.7",
            ]
            or not spec_path.is_file()
        ):
            raise NativeBuildError(_FAILURE)
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise NativeBuildError(_FAILURE) from error
    return NativeBuildConfiguration(
        root=selected_root,
        spec_path=spec_path,
        python_executable=sys.executable,
        python_version="3.12",
        pyinstaller_version="6.22.2",
        hooks_version="2026.7",
        mode="onedir",
    )


def validate_native_build_runtime(configuration: NativeBuildConfiguration) -> str:
    try:
        if sys.version_info[:2] != (3, 12):
            raise NativeBuildError(_FAILURE)
        if (
            importlib.metadata.version("pyinstaller")
            != configuration.pyinstaller_version
            or importlib.metadata.version("pyinstaller-hooks-contrib")
            != configuration.hooks_version
        ):
            raise NativeBuildError(_FAILURE)
        return native_platform_tag()
    except (NativeArtifactError, importlib.metadata.PackageNotFoundError, ValueError) as error:
        raise NativeBuildError(_FAILURE) from error


def pyinstaller_command(
    configuration: NativeBuildConfiguration,
    output_root: Path,
) -> tuple[str, ...]:
    selected_output = output_root.resolve()
    return (
        configuration.python_executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--distpath",
        str(selected_output / "dist"),
        "--workpath",
        str(selected_output / "work"),
        str(configuration.spec_path),
    )


def audit_native_artifact(
    artifact: Path,
    *,
    expected_platform: str | None = None,
) -> NativeArtifactAudit:
    try:
        selected = artifact.resolve(strict=True)
        metadata = artifact.lstat()
        if not stat.S_ISDIR(metadata.st_mode) or artifact.is_symlink():
            raise NativeBuildError(_FAILURE)
        manifest = NativeArtifactManifest.load(selected)
        if expected_platform is not None and manifest.platform_tag != expected_platform:
            raise NativeBuildError(_FAILURE)
        executable = selected / NATIVE_EXECUTABLE_NAME
        executable_metadata = executable.lstat()
        if (
            not stat.S_ISREG(executable_metadata.st_mode)
            or not executable_metadata.st_mode & stat.S_IXUSR
        ):
            raise NativeBuildError(_FAILURE)
        members = _artifact_members(selected)
        member_paths = frozenset(member.path for member in members)
        if (
            not set(_RESOURCE_MEMBERS) <= member_paths
            or any(not _native_member_allowed(member) for member in members)
        ):
            raise NativeBuildError(_FAILURE)
        encoded = json.dumps(
            [member.to_dict() for member in members],
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return NativeArtifactAudit(
            candidate_id=manifest.candidate_id,
            version=manifest.version,
            platform_tag=manifest.platform_tag,
            tree_sha256=manifest.tree_digest_sha256,
            membership_sha256=sha256(encoded).hexdigest(),
            member_count=len(members),
            symlink_count=sum(member.kind == "symlink" for member in members),
            resource_members=_RESOURCE_MEMBERS,
            members=members,
        )
    except NativeBuildError:
        raise
    except (NativeArtifactError, OSError, ValueError) as error:
        raise NativeBuildError(_FAILURE) from error


def build_native_artifact(
    configuration: NativeBuildConfiguration,
    output_root: Path,
    *,
    source_sha: str,
) -> tuple[Path, Path, Path]:
    stage = "runtime"
    try:
        platform_tag = validate_native_build_runtime(configuration)
        stage = "source-binding"
        _validate_source_sha(source_sha)
        _validate_source_binding(configuration.root, source_sha)
        stage = "pyinstaller"
        selected_output = output_root.resolve()
        selected_output.mkdir(parents=True, exist_ok=True)
        _run_checked(
            pyinstaller_command(configuration, selected_output),
            cwd=configuration.root,
            environment=_build_environment(),
            timeout=1_800,
        )
        stage = "manifest"
        produced = selected_output / "dist" / NATIVE_EXECUTABLE_NAME
        artifact = selected_output / "dist" / "candidate_native-p4w5"
        if artifact.exists():
            shutil.rmtree(artifact)
        produced.replace(artifact)
        NativeArtifactManifest.create(
            artifact,
            candidate_id="candidate_native-p4w5",
            version="0.1.0",
            platform_tag=platform_tag,
        ).write(artifact)
        stage = "artifact-audit"
        audit = audit_native_artifact(artifact, expected_platform=platform_tag)
        stage = "evidence"
        members_path = selected_output / "artifact-members.json"
        evidence_path = selected_output / "build-evidence.json"
        _write_json(
            members_path,
            {
                "artifact": audit.candidate_id,
                "members": [member.to_dict() for member in audit.members],
                "schema_version": 1,
            },
        )
        _write_json(
            evidence_path,
            {
                "artifact": audit.to_dict(),
                "build": {
                    "hooks_version": configuration.hooks_version,
                    "mode": configuration.mode,
                    "pyinstaller_version": configuration.pyinstaller_version,
                    "python_version": configuration.python_version,
                    "spec_sha256": _file_sha256(configuration.spec_path),
                },
                "runtime": None,
                "schema_version": 1,
                "source_sha": source_sha,
                "wave": "P4-W5",
            },
        )
        return artifact, evidence_path, members_path
    except NativeBuildStageError:
        raise
    except Exception as error:
        raise NativeBuildStageError(stage) from error


def smoke_native_artifact(artifact: Path, *, evidence_path: Path) -> dict[str, object]:
    stage = "artifact-audit"
    try:
        audit = audit_native_artifact(artifact, expected_platform=native_platform_tag())
        with TemporaryDirectory(prefix="ob-p4w5-", dir=_temporary_parent()) as raw:
            stage = "isolated-copy"
            smoke_root = Path(raw).resolve()
            install_root = smoke_root / "install"
            candidates = install_root / "candidates"
            candidates.mkdir(parents=True)
            prior_id = "candidate_native-p4w5-prior"
            failed_id = "candidate_native-p4w5-failed"
            isolated_artifact = _copy_native_candidate(
                artifact,
                candidates / audit.candidate_id,
                candidate_id=audit.candidate_id,
                version=audit.version,
                platform_tag=audit.platform_tag,
            )
            _copy_native_candidate(
                artifact,
                candidates / prior_id,
                candidate_id=prior_id,
                version=audit.version,
                platform_tag=audit.platform_tag,
            )
            failed_artifact = _copy_native_candidate(
                artifact,
                candidates / failed_id,
                candidate_id=failed_id,
                version=audit.version,
                platform_tag=audit.platform_tag,
            )
            stage = "isolated-audit"
            isolated_audit = audit_native_artifact(
                isolated_artifact,
                expected_platform=audit.platform_tag,
            )
            if isolated_audit.tree_sha256 != audit.tree_sha256:
                raise NativeBuildError(_FAILURE)
            stage = "artifact-activation"
            adapter = NativeArtifactLifecycleAdapter(
                install_root=install_root,
                current_version=audit.version,
            )
            candidate = ArtifactCandidate(
                candidate_id=audit.candidate_id,
                version=audit.version,
                artifact_kind="native-onedir",
            )
            prior_candidate = ArtifactCandidate(
                candidate_id=prior_id,
                version=audit.version,
                artifact_kind="native-onedir",
            )
            compatibility = adapter.compatibility_preflight(candidate)
            activation = adapter.activate(prior_candidate)
            if (
                compatibility.status != "compatible"
                or activation.status != "activated"
                or adapter.active_candidate_id != prior_id
            ):
                raise NativeBuildError(_FAILURE)
            executable = install_root / "current" / NATIVE_EXECUTABLE_NAME
            brain_root = smoke_root / "brain"
            environment = _runtime_environment(
                smoke_root,
                executable=executable,
                brain_root=brain_root,
            )
            stage = "version"
            version = _run_checked(
                (str(executable), "--version"),
                cwd=smoke_root,
                environment=environment,
                timeout=30,
            )
            if version.stdout != f"open-brain {audit.version}\n":
                raise NativeBuildError(_FAILURE)
            stage = "self-check"
            self_check = _run_checked(
                (str(executable), "__native-self-check"),
                cwd=smoke_root,
                environment=environment,
                timeout=30,
            )
            self_check_value = _json_object(self_check.stdout)
            if (
                self_check_value.get("status") != "ok"
                or self_check_value.get("frozen") is not True
                or self_check_value.get("platform") != audit.platform_tag
                or self_check_value.get("package_resources") != "available"
            ):
                raise NativeBuildError(_FAILURE)
            stage = "connector-child"
            connector = _run_checked(
                (str(executable), "__connector-worker"),
                cwd=smoke_root,
                environment={},
                timeout=30,
                input_text="{}\n",
            )
            connector_value = _json_object(connector.stdout)
            if (
                connector_value.get("schema_version") != 1
                or connector_value.get("failure_code") != "process_failed"
            ):
                raise NativeBuildError(_FAILURE)
            appliance_environment = {
                **environment,
                "OPEN_BRAIN_ROOT": str(brain_root),
                "OPEN_BRAIN_UI_PORT": str(_available_port()),
            }
            stage = "init"
            initialized = _run_checked(
                (str(executable), "init", "--starter-space=Personal", "--json"),
                cwd=smoke_root,
                environment=appliance_environment,
                timeout=30,
            )
            if _json_object(initialized.stdout).get("status") != "initialized":
                raise NativeBuildError(_FAILURE)
            stage = "supervisor-install"
            installed = _run_checked(
                (str(executable), "supervisor", "install", "--json"),
                cwd=smoke_root,
                environment=appliance_environment,
                timeout=30,
            )
            if _json_object(installed.stdout).get("status") != "ok":
                raise NativeBuildError(_FAILURE)
            stage = "daemon-start"
            _run_daemon_cycle(executable, brain_root, smoke_root, appliance_environment)
            stage = "daemon-restart"
            _run_daemon_cycle(executable, brain_root, smoke_root, appliance_environment)
            stage = "portable-round-trip"
            portable = _run_checked(
                (
                    str(executable),
                    "__native-portable-self-check",
                    str(smoke_root / "portable-export"),
                    str(smoke_root / "portable-import"),
                ),
                cwd=smoke_root,
                environment=appliance_environment,
                timeout=60,
            )
            portable_value = _json_object(portable.stdout)
            if (
                portable_value.get("status") != "passed"
                or portable_value.get("portable_export") != "exported"
                or portable_value.get("portable_import") != "imported"
            ):
                raise NativeBuildError(_FAILURE)
            stage = "artifact-rollback"
            rollback = _run_checked(
                (
                    str(executable),
                    "__native-rollback-self-check",
                    failed_id,
                    prior_id,
                ),
                cwd=smoke_root,
                environment=appliance_environment,
                timeout=30,
            )
            if _json_object(rollback.stdout).get("status") != "rolled_back":
                raise NativeBuildError(_FAILURE)
            shutil.rmtree(failed_artifact)
            stage = "artifact-upgrade"
            disposable_root = smoke_root / "upgrade-preflight"
            disposable_root.mkdir(mode=0o700)
            upgraded = _run_checked(
                (
                    str(executable),
                    "upgrade",
                    f"--candidate-id={candidate.candidate_id}",
                    f"--version={candidate.version}",
                    "--artifact-kind=native-onedir",
                    f"--backup-destination={smoke_root / 'upgrade-backup'}",
                    f"--disposable-root={disposable_root}",
                    "--request-id=upgrade_123e4567-e89b-42d3-a456-4266141745a3",
                    "--requested-at=2026-09-02T12:00:00Z",
                    "--confirm-owner",
                    "--json",
                ),
                cwd=smoke_root,
                environment=appliance_environment,
                timeout=90,
            )
            if _json_object(upgraded.stdout).get("status") != "upgraded":
                raise NativeBuildError(_FAILURE)
            stage = "artifact-uninstall"
            uninstalled = _run_checked(
                (
                    str(executable),
                    "uninstall",
                    "--request-id=uninstall_123e4567-e89b-42d3-a456-4266141745a4",
                    "--requested-at=2026-09-02T12:01:00Z",
                    "--confirm-owner",
                    "--json",
                ),
                cwd=smoke_root,
                environment=appliance_environment,
                timeout=60,
            )
            if (
                _json_object(uninstalled.stdout).get("status") != "uninstalled"
                or (install_root / "current").exists()
                or tuple(candidates.iterdir())
                or not brain_root.is_dir()
            ):
                raise NativeBuildError(_FAILURE)
        runtime: dict[str, object] = {
            "artifact_activation": "activated",
            "artifact_rollback": "rolled_back",
            "artifact_uninstall": "clean",
            "artifact_upgrade": "upgraded",
            "backup_restore": "passed",
            "child_environment": "sanitized",
            "connector_child": "bounded",
            "daemon_restart_count": 2,
            "init_status": "initialized",
            "package_resources": "available",
            "portable_round_trip": "passed",
            "source_checkout_required": False,
            "status": "passed",
            "supervisor_lifecycle": "isolated-shim",
            "system_python_required": False,
        }
        stage = "evidence"
        _merge_runtime_evidence(evidence_path, audit, runtime)
        return runtime
    except NativeSmokeError:
        raise
    except Exception as error:
        raise NativeSmokeError(stage) from error


def _copy_native_candidate(
    source: Path,
    destination: Path,
    *,
    candidate_id: str,
    version: str,
    platform_tag: str,
) -> Path:
    shutil.copytree(source, destination, symlinks=True)
    (destination / NATIVE_MANIFEST_NAME).unlink()
    NativeArtifactManifest.create(
        destination,
        candidate_id=candidate_id,
        version=version,
        platform_tag=platform_tag,
    ).write(destination)
    return destination


def _artifact_members(root: Path) -> tuple[NativeArtifactMember, ...]:
    members: list[NativeArtifactMember] = []

    def visit(directory: Path) -> None:
        with os.scandir(directory) as scanner:
            entries = sorted(scanner, key=lambda entry: entry.name)
        for entry in entries:
            path = Path(entry.path)
            relative = path.relative_to(root).as_posix()
            if relative == NATIVE_MANIFEST_NAME:
                continue
            metadata = entry.stat(follow_symlinks=False)
            if stat.S_ISLNK(metadata.st_mode):
                kind = "symlink"
                size = None
            elif stat.S_ISDIR(metadata.st_mode):
                kind = "directory"
                size = None
            elif stat.S_ISREG(metadata.st_mode):
                kind = "file"
                size = metadata.st_size
            else:
                raise NativeBuildError(_FAILURE)
            members.append(NativeArtifactMember(path=relative, kind=kind, size=size))
            if kind == "directory":
                visit(path)
            if len(members) > _MAXIMUM_MEMBERS:
                raise NativeBuildError(_FAILURE)

    visit(root)
    return tuple(members)


def _native_member_allowed(member: NativeArtifactMember) -> bool:
    try:
        policy = json.loads(_ARTIFACT_POLICY.read_text(encoding="utf-8"))["native_artifacts"][
            "member_policy"
        ]
        if not isinstance(policy, dict):
            raise NativeBuildError(_FAILURE)
        allowed_exact = _policy_strings(policy, "allowed_exact")
        allowed_trees = _policy_strings(policy, "allowed_trees")
        forbidden_components = frozenset(
            component.casefold()
            for component in _policy_strings(policy, "forbidden_components")
        )
        forbidden_suffixes = _policy_strings(policy, "forbidden_suffixes")
        library_pattern = policy.get("allowed_internal_library_pattern")
        if not isinstance(library_pattern, str):
            raise NativeBuildError(_FAILURE)
        compiled_library = re.compile(library_pattern)
    except (KeyError, OSError, TypeError, json.JSONDecodeError, re.error) as error:
        raise NativeBuildError(_FAILURE) from error

    path = PurePosixPath(member.path)
    components = tuple(component.casefold() for component in path.parts)
    if (
        path.is_absolute()
        or not components
        or any(
            component in forbidden_components
            or PurePosixPath(component).stem in forbidden_components
            for component in components
        )
        or member.path.endswith(forbidden_suffixes)
    ):
        return False
    if member.path in allowed_exact:
        return True
    if compiled_library.fullmatch(member.path) is not None:
        return member.kind in {"file", "symlink"}
    return any(
        member.path == tree
        or member.path.startswith(tree + "/")
        or tree.startswith(member.path + "/")
        for tree in allowed_trees
    )


def _policy_strings(policy: Mapping[str, object], key: str) -> tuple[str, ...]:
    value = policy.get(key)
    if (
        not isinstance(value, list)
        or not value
        or any(not isinstance(item, str) or not item for item in value)
    ):
        raise NativeBuildError(_FAILURE)
    return tuple(cast(list[str], value))


def _run_daemon_cycle(
    executable: Path,
    brain_root: Path,
    cwd: Path,
    environment: Mapping[str, str],
) -> None:
    process = subprocess.Popen(
        (str(executable), "__appliance-daemon", "--root", str(brain_root)),
        cwd=cwd,
        env=dict(environment),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        start_new_session=True,
    )
    try:
        socket_path = brain_root / ".open-brain/run/control.sock"
        deadline = time.monotonic() + 15
        status_receipt: subprocess.CompletedProcess[str] | None = None
        while status_receipt is None:
            if process.poll() is not None or time.monotonic() >= deadline:
                raise NativeBuildError(_FAILURE)
            if socket_path.exists():
                try:
                    candidate = _run_checked(
                        (str(executable), "status", "--json"),
                        cwd=cwd,
                        environment=environment,
                        timeout=5,
                    )
                except NativeBuildError:
                    pass
                else:
                    if _json_object(candidate.stdout).get("status") == "ok":
                        status_receipt = candidate
            time.sleep(0.05)
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def _run_checked(
    command: Sequence[str],
    *,
    cwd: Path,
    environment: Mapping[str, str],
    timeout: int,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            tuple(command),
            cwd=cwd,
            env=dict(environment),
            input=input_text,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise NativeBuildError(_FAILURE) from error
    if (
        result.returncode != 0
        or len(result.stdout.encode("utf-8")) > _MAXIMUM_PROCESS_OUTPUT
        or len(result.stderr.encode("utf-8")) > _MAXIMUM_PROCESS_OUTPUT
    ):
        raise NativeBuildError(_FAILURE)
    return result


def _build_environment() -> dict[str, str]:
    environment = dict(os.environ)
    for key in ("PYTHONPATH", "PYTHONHOME", "UV_PROJECT_ENVIRONMENT"):
        environment.pop(key, None)
    environment["PYTHONNOUSERSITE"] = "1"
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return environment


def _runtime_environment(
    root: Path,
    *,
    executable: Path,
    brain_root: Path,
) -> dict[str, str]:
    home = root / "home"
    temporary = root / "tmp"
    host_tools = root / "host-tools"
    home.mkdir()
    temporary.mkdir()
    host_tools.mkdir()
    supervisor_name = "launchctl" if sys.platform == "darwin" else "systemctl"
    supervisor = host_tools / supervisor_name
    pidfile = root / "supervised-daemon.pid"
    supervisor.write_text(
        _supervisor_shim(
            executable=executable,
            brain_root=brain_root,
            pidfile=pidfile,
        ),
        encoding="utf-8",
    )
    supervisor.chmod(0o755)
    return {
        "HOME": str(home),
        "PATH": str(host_tools),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "TMPDIR": str(temporary),
    }


def _supervisor_shim(*, executable: Path, brain_root: Path, pidfile: Path) -> str:
    return f"""#!/bin/sh
pidfile={shlex.quote(str(pidfile))}
executable={shlex.quote(str(executable))}
brain_root={shlex.quote(str(brain_root))}

stop_daemon() {{
    if [ -f "$pidfile" ]; then
        pid=$(/bin/cat "$pidfile")
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true
            count=0
            while kill -0 "$pid" 2>/dev/null && [ "$count" -lt 200 ]; do
                /bin/sleep 0.05
                count=$((count + 1))
            done
            if kill -0 "$pid" 2>/dev/null; then
                kill -KILL "$pid" 2>/dev/null || true
            fi
        fi
        /bin/rm -f "$pidfile"
    fi
}}

start_daemon() {{
    "$executable" __appliance-daemon --root "$brain_root" >/dev/null 2>&1 &
    echo "$!" > "$pidfile"
}}

status_daemon() {{
    if [ -f "$pidfile" ]; then
        pid=$(/bin/cat "$pidfile")
        if kill -0 "$pid" 2>/dev/null; then
            printf 'active\\n'
            exit 0
        fi
    fi
    exit 1
}}

case " $* " in
    *" kickstart "*|*" restart "*) stop_daemon; start_daemon ;;
    *" start "*) start_daemon ;;
    *" kill "*|*" stop "*|*" bootout "*|*" disable "*) stop_daemon ;;
    *" print "*|*" status "*) status_daemon ;;
    *) exit 0 ;;
esac
"""


def _available_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return cast(int, listener.getsockname()[1])


def _temporary_parent() -> str | None:
    return "/tmp" if Path("/tmp").is_dir() else None


def _json_object(payload: str) -> dict[str, object]:
    try:
        value = json.loads(payload)
    except (TypeError, json.JSONDecodeError) as error:
        raise NativeBuildError(_FAILURE) from error
    if type(value) is not dict:
        raise NativeBuildError(_FAILURE)
    return cast(dict[str, object], value)


def _merge_runtime_evidence(
    evidence_path: Path,
    audit: NativeArtifactAudit,
    runtime: Mapping[str, object],
) -> None:
    try:
        evidence = _json_object(evidence_path.read_text(encoding="utf-8"))
        artifact = evidence.get("artifact")
        if (
            evidence.get("schema_version") != 1
            or evidence.get("wave") != "P4-W5"
            or type(artifact) is not dict
            or cast(dict[str, object], artifact).get("tree_sha256")
            != audit.tree_sha256
            or evidence.get("runtime") is not None
        ):
            raise NativeBuildError(_FAILURE)
        evidence["runtime"] = dict(runtime)
        _write_json(evidence_path, evidence)
    except OSError as error:
        raise NativeBuildError(_FAILURE) from error


def _write_json(path: Path, value: Mapping[str, object]) -> None:
    payload = json.dumps(dict(value), sort_keys=True, indent=2) + "\n"
    if len(payload.encode("utf-8")) > 2 * 1024 * 1024:
        raise NativeBuildError(_FAILURE)
    path.write_text(payload, encoding="utf-8")


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_source_sha(value: str) -> None:
    if not isinstance(value, str) or _SOURCE_SHA.fullmatch(value) is None:
        raise NativeBuildError(_FAILURE)


def _validate_source_binding(root: Path, source_sha: str) -> None:
    try:
        head = subprocess.run(
            ("git", "rev-parse", "HEAD"),
            cwd=root,
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        ).stdout.strip()
        status = subprocess.run(
            ("git", "status", "--porcelain=v1", "--untracked-files=all"),
            cwd=root,
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        ).stdout
    except (OSError, subprocess.SubprocessError) as error:
        raise NativeBuildError(_FAILURE) from error
    if head != source_sha or status:
        raise NativeBuildError(_FAILURE)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m tools.phase4.native_build")
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate-config")
    validate.add_argument("--root", type=Path, required=True)
    build = commands.add_parser("build")
    build.add_argument("--root", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--source-sha", required=True)
    smoke = commands.add_parser("smoke")
    smoke.add_argument("--artifact", type=Path, required=True)
    smoke.add_argument("--evidence", type=Path, required=True)
    audit = commands.add_parser("audit")
    audit.add_argument("--artifact", type=Path, required=True)
    audit.add_argument("--expected-platform")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    namespace = _parser().parse_args(argv)
    try:
        if namespace.command == "validate-config":
            configuration = load_native_build_configuration(namespace.root)
            validate_native_build_runtime(configuration)
            result: Mapping[str, object] = {"status": "valid"}
        elif namespace.command == "build":
            artifact, evidence, members = build_native_artifact(
                load_native_build_configuration(namespace.root),
                namespace.output,
                source_sha=namespace.source_sha,
            )
            audit = audit_native_artifact(artifact)
            result = {
                "artifact": audit.to_dict(),
                "evidence": evidence.name,
                "members": members.name,
                "source_sha": namespace.source_sha,
                "status": "built",
            }
        elif namespace.command == "smoke":
            runtime = smoke_native_artifact(
                namespace.artifact,
                evidence_path=namespace.evidence,
            )
            result = {"runtime": runtime, "status": "passed"}
        else:
            result = audit_native_artifact(
                namespace.artifact,
                expected_platform=namespace.expected_platform,
            ).to_dict()
    except NativeSmokeError as error:
        result = {"failure_stage": error.stage, "status": "failed"}
        exit_code = 1
    except NativeBuildStageError as error:
        result = {"failure_stage": error.stage, "status": "failed"}
        exit_code = 1
    except NativeBuildError:
        result = {"status": "failed"}
        exit_code = 1
    else:
        exit_code = 0
    sys.stdout.write(json.dumps(dict(result), sort_keys=True, separators=(",", ":")) + "\n")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
