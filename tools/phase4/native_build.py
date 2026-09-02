"""Pinned PyInstaller one-folder build, membership audit, and native smoke."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import re
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
from pathlib import Path
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
            or any(member.path.endswith((".py", ".pyc")) for member in members)
            or any(member.path.startswith(("packages/", "tests/")) for member in members)
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
            isolated_artifact = candidates / artifact.name
            shutil.copytree(artifact, isolated_artifact, symlinks=True)
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
            compatibility = adapter.compatibility_preflight(candidate)
            activation = adapter.activate(candidate)
            if (
                compatibility.status != "compatible"
                or activation.status != "activated"
                or adapter.active_candidate_id != audit.candidate_id
            ):
                raise NativeBuildError(_FAILURE)
            executable = install_root / "current" / NATIVE_EXECUTABLE_NAME
            environment = _runtime_environment(smoke_root)
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
            brain_root = smoke_root / "brain"
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
            stage = "daemon-start"
            _run_daemon_cycle(executable, brain_root, smoke_root, appliance_environment)
            stage = "daemon-restart"
            _run_daemon_cycle(executable, brain_root, smoke_root, appliance_environment)
            stage = "artifact-uninstall"
            removal = adapter.remove(current_candidate_id=audit.candidate_id)
            if (
                removal.status != "removed"
                or adapter.active_candidate_id is not None
                or (install_root / "current").exists()
                or tuple(candidates.iterdir())
            ):
                raise NativeBuildError(_FAILURE)
        runtime: dict[str, object] = {
            "artifact_activation": "activated",
            "artifact_uninstall": "clean",
            "child_environment": "sanitized",
            "connector_child": "bounded",
            "daemon_restart_count": 2,
            "init_status": "initialized",
            "package_resources": "available",
            "source_checkout_required": False,
            "status": "passed",
            "system_python_required": False,
        }
        stage = "evidence"
        _merge_runtime_evidence(evidence_path, audit, runtime)
        return runtime
    except NativeSmokeError:
        raise
    except Exception as error:
        raise NativeSmokeError(stage) from error


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


def _runtime_environment(root: Path) -> dict[str, str]:
    home = root / "home"
    temporary = root / "tmp"
    host_tools = root / "host-tools"
    home.mkdir()
    temporary.mkdir()
    host_tools.mkdir()
    supervisor_name = "launchctl" if sys.platform == "darwin" else "systemctl"
    supervisor = shutil.which(supervisor_name, path=os.defpath)
    if supervisor is None:
        raise NativeBuildError(_FAILURE)
    (host_tools / supervisor_name).symlink_to(supervisor)
    return {
        "HOME": str(home),
        "PATH": str(host_tools),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "TMPDIR": str(temporary),
    }


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
