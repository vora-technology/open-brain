"""Pinned PyInstaller one-folder build, membership audit, and native smoke."""

from __future__ import annotations

import argparse
import hashlib
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
import tarfile
import time
import tomllib
from collections.abc import Mapping, Sequence
from contextlib import suppress
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
_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_ARTIFACT_POLICY = _REPOSITORY_ROOT / "release/v0-artifact-policy.json"
_RESOURCE_SOURCE_TREES: Final = (
    (
        PurePosixPath("packages/app/src/open_brain/resources/supervisors"),
        PurePosixPath("_internal/open_brain/resources/supervisors"),
    ),
    (
        PurePosixPath("packages/engine/src/open_brain_engine/portable"),
        PurePosixPath("_internal/open_brain_engine/portable"),
    ),
)
_MAXIMUM_MEMBERS: Final = 20_000
_MAXIMUM_SOURCE_MEMBERS: Final = 10_000
_MAXIMUM_SOURCE_MANIFEST_BYTES: Final = 2 * 1024 * 1024
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


@dataclass(frozen=True, slots=True)
class _GitTreeMember:
    mode: str
    object_id: str
    path: str


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
            importlib.metadata.version("pyinstaller") != configuration.pyinstaller_version
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


def native_resource_members(root: Path) -> tuple[str, ...]:
    """Return the exact tracked package resources admitted to a native artifact."""
    try:
        selected_root = root.resolve(strict=True)
        result = subprocess.run(
            (
                "git",
                "ls-files",
                "-z",
                "--",
                *(source.as_posix() for source, _destination in _RESOURCE_SOURCE_TREES),
            ),
            cwd=selected_root,
            capture_output=True,
            timeout=10,
            check=False,
        )
        if (
            result.returncode != 0
            or len(result.stdout) > _MAXIMUM_PROCESS_OUTPUT
            or len(result.stderr) > _MAXIMUM_PROCESS_OUTPUT
        ):
            raise NativeBuildError(_FAILURE)
        tracked = tuple(
            PurePosixPath(value.decode("utf-8")) for value in result.stdout.split(b"\0") if value
        )
        members: set[str] = set()
        for source_root, destination_root in _RESOURCE_SOURCE_TREES:
            source_members = tuple(
                path
                for path in tracked
                if path.is_relative_to(source_root)
                and path.suffix.casefold() not in {".py", ".pyi"}
            )
            if not source_members:
                raise NativeBuildError(_FAILURE)
            for source_member in source_members:
                source_path = selected_root.joinpath(*source_member.parts)
                metadata = source_path.lstat()
                if not stat.S_ISREG(metadata.st_mode):
                    raise NativeBuildError(_FAILURE)
                relative = source_member.relative_to(source_root)
                members.add((destination_root / relative).as_posix())
        return tuple(sorted(members))
    except NativeBuildError:
        raise
    except (OSError, UnicodeError, ValueError, subprocess.SubprocessError) as error:
        raise NativeBuildError(_FAILURE) from error


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
        resource_members = native_resource_members(_REPOSITORY_ROOT)
        if not set(resource_members) <= member_paths or any(
            not _native_member_allowed(member, resource_members=resource_members)
            for member in members
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
            resource_members=resource_members,
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
    candidate_id: str = "candidate_native-p4w5",
    wave: str = "P4-W5",
) -> tuple[Path, Path, Path]:
    stage = "runtime"
    try:
        ArtifactCandidate(
            candidate_id=candidate_id,
            version="0.1.0",
            artifact_kind="native-onedir",
        )
        if wave not in {"P4-W5", "P4-W6"}:
            raise NativeBuildError(_FAILURE)
        platform_tag = validate_native_build_runtime(configuration)
        stage = "source-binding"
        _validate_source_sha(source_sha)
        _validate_source_binding(configuration.root, source_sha)
        selected_output = output_root.resolve()
        selected_output.mkdir(parents=True, exist_ok=True)
        stage = "source-materialization"
        with TemporaryDirectory(prefix="ob-p4w5-source-", dir=_temporary_parent()) as raw:
            source_root = Path(raw).resolve() / "source"
            source_tree_sha256 = _materialize_source_tree(
                configuration.root,
                source_sha,
                source_root,
            )
            staged_configuration = NativeBuildConfiguration(
                root=source_root,
                spec_path=source_root / _SPEC,
                python_executable=configuration.python_executable,
                python_version=configuration.python_version,
                pyinstaller_version=configuration.pyinstaller_version,
                hooks_version=configuration.hooks_version,
                mode=configuration.mode,
            )
            stage = "pyinstaller"
            _run_checked(
                pyinstaller_command(staged_configuration, selected_output),
                cwd=source_root,
                environment=_build_environment(source_root=source_root),
                timeout=1_800,
            )
            if _source_tree_sha256(source_root) != source_tree_sha256:
                raise NativeBuildError(_FAILURE)
        stage = "source-revalidation"
        _validate_source_binding(configuration.root, source_sha)
        stage = "manifest"
        produced = selected_output / "dist" / NATIVE_EXECUTABLE_NAME
        artifact = selected_output / "dist" / candidate_id
        if artifact.exists():
            shutil.rmtree(artifact)
        produced.replace(artifact)
        NativeArtifactManifest.create(
            artifact,
            candidate_id=candidate_id,
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
                    "source_tree_sha256": source_tree_sha256,
                    "spec_sha256": _file_sha256(configuration.spec_path),
                },
                "runtime": None,
                "schema_version": 1,
                "source_sha": source_sha,
                "wave": wave,
            },
        )
        return artifact, evidence_path, members_path
    except NativeBuildStageError:
        raise
    except Exception as error:
        raise NativeBuildStageError(stage) from error


def smoke_native_artifact(
    artifact: Path,
    *,
    evidence_path: Path,
    expected_wave: str = "P4-W5",
) -> dict[str, object]:
    stage = "artifact-audit"
    try:
        if expected_wave not in {"P4-W5", "P4-W6"}:
            raise NativeBuildError(_FAILURE)
        audit = audit_native_artifact(artifact, expected_platform=native_platform_tag())
        with TemporaryDirectory(prefix="ob-p4w5-", dir=_temporary_parent()) as raw:
            stage = "isolated-copy"
            smoke_root = Path(raw).resolve()
            install_root = smoke_root / "install"
            candidates = install_root / "candidates"
            candidates.mkdir(parents=True)
            prior_id = f"{audit.candidate_id}-prior"
            failed_id = f"{audit.candidate_id}-failed"
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
            corruption_marker = smoke_root / "corrupt-next-stop"
            environment = _runtime_environment(
                smoke_root,
                executable=executable,
                brain_root=brain_root,
                corruption_marker=corruption_marker,
                corruption_target=(
                    failed_artifact / "_internal/open_brain/resources/supervisors/launchd.json"
                ),
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
            _run_supervisor_action(
                executable,
                "start",
                brain_root,
                smoke_root,
                appliance_environment,
            )
            stage = "daemon-restart"
            _run_supervisor_action(
                executable,
                "restart",
                brain_root,
                smoke_root,
                appliance_environment,
            )
            stage = "portable-round-trip"
            portable_export = smoke_root / "portable-export"
            portable_import = smoke_root / "portable-import"
            exported = _request_recovery_control(
                brain_root,
                operation="portable-export",
                request_id="export_123e4567-e89b-42d3-a456-4266141745a1",
                destination=portable_export,
            )
            if exported.get("operation") != "portable-export" or exported.get("status") not in {
                "scheduled",
                "completed",
            }:
                raise NativeBuildError(_FAILURE)
            _wait_for_path(portable_export / "portable-manifest.json")
            imported = _request_recovery_control(
                brain_root,
                operation="portable-import",
                request_id="import_123e4567-e89b-42d3-a456-4266141745a2",
                source=portable_export,
                destination=portable_import,
            )
            if imported.get("operation") != "portable-import" or imported.get("status") not in {
                "scheduled",
                "completed",
            }:
                raise NativeBuildError(_FAILURE)
            _wait_for_path(portable_import / ".open-brain/state/appliance-owner-credential")
            stage = "artifact-rollback"
            corruption_marker.write_text("corrupt once\n", encoding="utf-8")
            failed_disposable_root = smoke_root / "failed-upgrade-preflight"
            failed_disposable_root.mkdir(mode=0o700)
            rollback = _run_bounded(
                (
                    str(executable),
                    "upgrade",
                    f"--candidate-id={failed_id}",
                    f"--version={audit.version}",
                    "--artifact-kind=native-onedir",
                    f"--backup-destination={smoke_root / 'failed-upgrade-backup'}",
                    f"--disposable-root={failed_disposable_root}",
                    "--request-id=upgrade_123e4567-e89b-42d3-a456-4266141745a3",
                    "--requested-at=2026-09-02T12:00:00Z",
                    "--confirm-owner",
                    "--json",
                ),
                cwd=smoke_root,
                environment=appliance_environment,
                timeout=90,
            )
            rollback_value = _json_object(rollback.stdout)
            if (
                rollback.returncode == 0
                or rollback_value.get("failure_stage") != "activate"
                or rollback_value.get("rollback_state") != "rolled_back"
                or rollback_value.get("daemon_restore_state") != "restored"
                or (install_root / "current").readlink() != Path("candidates") / prior_id
            ):
                raise NativeBuildError(_FAILURE)
            _wait_for_daemon(executable, brain_root, smoke_root, appliance_environment)
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
                    "--request-id=upgrade_123e4567-e89b-42d3-a456-4266141745a4",
                    "--requested-at=2026-09-02T12:01:00Z",
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
                    "--request-id=uninstall_123e4567-e89b-42d3-a456-4266141745a5",
                    "--requested-at=2026-09-02T12:02:00Z",
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
        _merge_runtime_evidence(
            evidence_path,
            audit,
            runtime,
            expected_wave=expected_wave,
        )
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


def _native_member_allowed(
    member: NativeArtifactMember,
    *,
    resource_members: tuple[str, ...],
) -> bool:
    try:
        policy = json.loads(_ARTIFACT_POLICY.read_text(encoding="utf-8"))["native_artifacts"][
            "member_policy"
        ]
        if not isinstance(policy, dict):
            raise NativeBuildError(_FAILURE)
        allowed_exact = _policy_strings(policy, "allowed_exact")
        allowed_resource_roots = _policy_strings(policy, "allowed_resource_roots")
        allowed_trees = _policy_strings(policy, "allowed_trees")
        forbidden_components = frozenset(
            component.casefold() for component in _policy_strings(policy, "forbidden_components")
        )
        forbidden_suffixes = tuple(
            suffix.casefold() for suffix in _policy_strings(policy, "forbidden_suffixes")
        )
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
            or component.startswith(".env")
            for component in components
        )
        or member.path.casefold().endswith(forbidden_suffixes)
    ):
        return False
    expected_resource_roots = tuple(
        destination.as_posix() for _source, destination in _RESOURCE_SOURCE_TREES
    )
    if allowed_resource_roots != expected_resource_roots:
        raise NativeBuildError(_FAILURE)
    if member.path in resource_members:
        return member.kind == "file"
    if any(resource.startswith(member.path + "/") for resource in resource_members):
        return member.kind == "directory"
    if any(
        member.path == root or member.path.startswith(root + "/") for root in allowed_resource_roots
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


def _run_supervisor_action(
    executable: Path,
    action: str,
    brain_root: Path,
    cwd: Path,
    environment: Mapping[str, str],
) -> None:
    result = _run_checked(
        (str(executable), "supervisor", action, "--json"),
        cwd=cwd,
        environment=environment,
        timeout=30,
    )
    if _json_object(result.stdout).get("status") != "ok":
        raise NativeBuildError(_FAILURE)
    _wait_for_daemon(executable, brain_root, cwd, environment)


def _wait_for_daemon(
    executable: Path,
    brain_root: Path,
    cwd: Path,
    environment: Mapping[str, str],
) -> None:
    socket_path = brain_root / ".open-brain/run/control.sock"
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if socket_path.exists():
            try:
                status = _run_checked(
                    (str(executable), "status", "--json"),
                    cwd=cwd,
                    environment=environment,
                    timeout=5,
                )
            except NativeBuildError:
                pass
            else:
                if _json_object(status.stdout).get("status") == "ok":
                    return
        time.sleep(0.05)
    raise NativeBuildError(_FAILURE)


def _request_recovery_control(
    root: Path,
    *,
    operation: str,
    request_id: str,
    destination: Path,
    source: Path | None = None,
) -> dict[str, object]:
    payload = json.dumps(
        {
            "action": "recovery.request",
            "destination": str(destination),
            "operation": operation,
            "request_id": request_id,
            "schema_version": 1,
            "source": None if source is None else str(source),
        },
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client.settimeout(5)
    try:
        client.connect(str(root / ".open-brain/run/control.sock"))
        client.sendall(payload)
        client.shutdown(socket.SHUT_WR)
        chunks = bytearray()
        while len(chunks) <= 4_096:
            chunk = client.recv(4_097 - len(chunks))
            if not chunk:
                break
            chunks.extend(chunk)
    except OSError as error:
        raise NativeBuildError(_FAILURE) from error
    finally:
        client.close()
    if len(chunks) > 4_096:
        raise NativeBuildError(_FAILURE)
    try:
        value = json.loads(bytes(chunks).decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise NativeBuildError(_FAILURE) from error
    if (
        not isinstance(value, dict)
        or value.get("action") != "recovery.request"
        or value.get("request_id") != request_id
        or value.get("schema_version") != 1
    ):
        raise NativeBuildError(_FAILURE)
    return cast(dict[str, object], value)


def _wait_for_path(path: Path) -> None:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if path.is_file():
            return
        time.sleep(0.05)
    raise NativeBuildError(_FAILURE)


def _run_checked(
    command: Sequence[str],
    *,
    cwd: Path,
    environment: Mapping[str, str],
    timeout: int,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    result = _run_bounded(
        command,
        cwd=cwd,
        environment=environment,
        timeout=timeout,
        input_text=input_text,
    )
    if result.returncode != 0:
        raise NativeBuildError(_FAILURE)
    return result


def _run_bounded(
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
        len(result.stdout.encode("utf-8")) > _MAXIMUM_PROCESS_OUTPUT
        or len(result.stderr.encode("utf-8")) > _MAXIMUM_PROCESS_OUTPUT
    ):
        raise NativeBuildError(_FAILURE)
    return result


def _build_environment(*, source_root: Path) -> dict[str, str]:
    environment = dict(os.environ)
    for key in ("PYTHONPATH", "PYTHONHOME", "UV_PROJECT_ENVIRONMENT"):
        environment.pop(key, None)
    environment["PYTHONNOUSERSITE"] = "1"
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONPATH"] = os.pathsep.join(
        str(source_root / relative) for relative in ("packages/app/src", "packages/engine/src")
    )
    return environment


def _runtime_environment(
    root: Path,
    *,
    executable: Path,
    brain_root: Path,
    corruption_marker: Path,
    corruption_target: Path,
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
    loadedfile = root / "supervisor-loaded"
    supervisor.write_text(
        _supervisor_shim(
            executable=executable,
            brain_root=brain_root,
            pidfile=pidfile,
            loadedfile=loadedfile,
            corruption_marker=corruption_marker,
            corruption_target=corruption_target,
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


def _supervisor_shim(
    *,
    executable: Path,
    brain_root: Path,
    pidfile: Path,
    loadedfile: Path,
    corruption_marker: Path,
    corruption_target: Path,
) -> str:
    return f"""#!/bin/sh
pidfile={shlex.quote(str(pidfile))}
loadedfile={shlex.quote(str(loadedfile))}
executable={shlex.quote(str(executable))}
brain_root={shlex.quote(str(brain_root))}
corruption_marker={shlex.quote(str(corruption_marker))}
corruption_target={shlex.quote(str(corruption_target))}

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
    if [ -f "$corruption_marker" ]; then
        /bin/rm -f "$corruption_marker"
        printf '\n' >> "$corruption_target"
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
    *" bootstrap "*|*" enable "*) : > "$loadedfile" ;;
    *" kickstart "*) [ -f "$loadedfile" ] || exit 1; stop_daemon; start_daemon ;;
    *" restart "*) stop_daemon; start_daemon ;;
    *" start "*) start_daemon ;;
    *" kill "*) stop_daemon; [ ! -f "$loadedfile" ] || start_daemon ;;
    *" stop "*) stop_daemon ;;
    *" bootout "*|*" disable "*) /bin/rm -f "$loadedfile"; stop_daemon ;;
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
    *,
    expected_wave: str = "P4-W5",
) -> None:
    try:
        evidence = _json_object(evidence_path.read_text(encoding="utf-8"))
        artifact = evidence.get("artifact")
        if (
            evidence.get("schema_version") != 1
            or evidence.get("wave") != expected_wave
            or type(artifact) is not dict
            or cast(dict[str, object], artifact).get("tree_sha256") != audit.tree_sha256
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


def _materialize_source_tree(root: Path, source_sha: str, destination: Path) -> str:
    """Extract exactly one named Git tree and return its deterministic digest."""
    _validate_source_sha(source_sha)
    archive: Path | None = None
    try:
        selected_root = root.resolve(strict=True)
        _validate_repository_git_inputs(selected_root)
        object_format, raw_manifest = _raw_git_tree_manifest(
            selected_root,
            source_sha,
        )
        destination_parent = destination.parent.resolve(strict=True)
        selected_destination = destination_parent / destination.name
        if selected_destination.exists() or selected_destination.is_symlink():
            raise NativeBuildError(_FAILURE)
        archive = destination_parent / f".{destination.name}.tar"
        with archive.open("xb") as stream:
            result = subprocess.run(
                _git_command("archive", "--format=tar", source_sha),
                cwd=selected_root,
                stdout=stream,
                stderr=subprocess.PIPE,
                env=_hermetic_git_environment(),
                timeout=30,
                check=False,
            )
        if result.returncode != 0 or len(result.stderr) > _MAXIMUM_PROCESS_OUTPUT:
            raise NativeBuildError(_FAILURE)
        selected_destination.mkdir(mode=0o700)
        with tarfile.open(archive, mode="r:") as bundle:
            if len(bundle.getmembers()) > _MAXIMUM_SOURCE_MEMBERS:
                raise NativeBuildError(_FAILURE)
            bundle.extractall(selected_destination, filter="data")
        if _extracted_git_tree_manifest(selected_destination, object_format) != raw_manifest:
            raise NativeBuildError(_FAILURE)
        return _source_tree_sha256(selected_destination)
    except NativeBuildError:
        raise
    except (OSError, tarfile.TarError, subprocess.SubprocessError) as error:
        raise NativeBuildError(_FAILURE) from error
    finally:
        if archive is not None:
            with suppress(OSError):
                archive.unlink()


def materialize_exact_source_tree(root: Path, source_sha: str, destination: Path) -> str:
    """Expose the accepted D-051 exact-source materialization to P4-W6."""
    return _materialize_source_tree(root, source_sha, destination)


def _source_tree_sha256(root: Path) -> str:
    try:
        selected_root = root.resolve(strict=True)
        if not stat.S_ISDIR(selected_root.lstat().st_mode) or root.is_symlink():
            raise NativeBuildError(_FAILURE)
        entries: list[dict[str, object]] = []

        def visit(directory: Path) -> None:
            with os.scandir(directory) as scanner:
                children = sorted(scanner, key=lambda entry: entry.name)
            for entry in children:
                path = Path(entry.path)
                metadata = entry.stat(follow_symlinks=False)
                relative = path.relative_to(selected_root).as_posix()
                if stat.S_ISDIR(metadata.st_mode):
                    entries.append({"kind": "directory", "path": relative})
                    visit(path)
                elif stat.S_ISREG(metadata.st_mode):
                    entries.append(
                        {
                            "executable": bool(metadata.st_mode & 0o111),
                            "kind": "file",
                            "path": relative,
                            "sha256": _file_sha256(path),
                        }
                    )
                elif stat.S_ISLNK(metadata.st_mode):
                    entries.append(
                        {
                            "kind": "symlink",
                            "path": relative,
                            "target": os.readlink(path),
                        }
                    )
                else:
                    raise NativeBuildError(_FAILURE)
                if len(entries) > _MAXIMUM_SOURCE_MEMBERS:
                    raise NativeBuildError(_FAILURE)

        visit(selected_root)
        encoded = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return sha256(encoded).hexdigest()
    except NativeBuildError:
        raise
    except (OSError, UnicodeError, ValueError) as error:
        raise NativeBuildError(_FAILURE) from error


def exact_source_tree_sha256(root: Path) -> str:
    """Return the deterministic D-051 digest for a materialized source tree."""
    return _source_tree_sha256(root)


def _git_command(*arguments: str) -> tuple[str, ...]:
    return (
        "git",
        "--no-replace-objects",
        "-c",
        f"core.attributesFile={os.devnull}",
        *arguments,
    )


def _hermetic_git_environment() -> dict[str, str]:
    environment = dict(os.environ)
    for key in (
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_COMMON_DIR",
        "GIT_CONFIG_COUNT",
        "GIT_CONFIG_KEY_0",
        "GIT_CONFIG_VALUE_0",
        "GIT_DIR",
        "GIT_INDEX_FILE",
        "GIT_OBJECT_DIRECTORY",
        "GIT_REPLACE_REF_BASE",
        "GIT_WORK_TREE",
    ):
        environment.pop(key, None)
    environment.update(
        {
            "GIT_ATTR_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_OPTIONAL_LOCKS": "0",
        }
    )
    return environment


def _run_git(root: Path, *arguments: str) -> bytes:
    try:
        result = subprocess.run(
            _git_command(*arguments),
            cwd=root,
            capture_output=True,
            env=_hermetic_git_environment(),
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise NativeBuildError(_FAILURE) from error
    if (
        result.returncode != 0
        or len(result.stdout) > _MAXIMUM_SOURCE_MANIFEST_BYTES
        or len(result.stderr) > _MAXIMUM_PROCESS_OUTPUT
    ):
        raise NativeBuildError(_FAILURE)
    return result.stdout


def _validate_repository_git_inputs(root: Path) -> None:
    replacements = _run_git(
        root,
        "for-each-ref",
        "--format=%(refname)",
        "refs/replace/",
    )
    if replacements:
        raise NativeBuildError(_FAILURE)
    try:
        attributes_value = (
            _run_git(
                root,
                "rev-parse",
                "--path-format=absolute",
                "--git-path",
                "info/attributes",
            )
            .decode("utf-8")
            .strip()
        )
        attributes = Path(attributes_value)
        try:
            metadata = attributes.lstat()
        except FileNotFoundError:
            return
        if not stat.S_ISREG(metadata.st_mode) or attributes.read_bytes().strip():
            raise NativeBuildError(_FAILURE)
    except NativeBuildError:
        raise
    except (OSError, UnicodeError, ValueError) as error:
        raise NativeBuildError(_FAILURE) from error


def _raw_git_tree_manifest(
    root: Path,
    source_sha: str,
) -> tuple[str, tuple[_GitTreeMember, ...]]:
    try:
        object_format = _run_git(root, "rev-parse", "--show-object-format").decode("ascii").strip()
        if object_format not in {"sha1", "sha256"}:
            raise NativeBuildError(_FAILURE)
        output = _run_git(root, "ls-tree", "-rz", "--full-tree", source_sha)
        members: list[_GitTreeMember] = []
        for record in output.split(b"\0"):
            if not record:
                continue
            header, raw_path = record.split(b"\t", maxsplit=1)
            raw_mode, raw_kind, raw_object_id = header.split(b" ", maxsplit=2)
            mode = raw_mode.decode("ascii")
            kind = raw_kind.decode("ascii")
            object_id = raw_object_id.decode("ascii")
            path = raw_path.decode("utf-8")
            parsed_path = PurePosixPath(path)
            if (
                kind != "blob"
                or mode not in {"100644", "100755", "120000"}
                or len(object_id) != hashlib.new(object_format).digest_size * 2
                or any(character not in "0123456789abcdef" for character in object_id)
                or parsed_path.is_absolute()
                or not parsed_path.parts
                or any(part in {"", ".", ".."} for part in parsed_path.parts)
            ):
                raise NativeBuildError(_FAILURE)
            members.append(_GitTreeMember(mode, object_id, path))
            if len(members) > _MAXIMUM_SOURCE_MEMBERS:
                raise NativeBuildError(_FAILURE)
        if not members:
            raise NativeBuildError(_FAILURE)
        return object_format, tuple(members)
    except NativeBuildError:
        raise
    except (UnicodeError, ValueError) as error:
        raise NativeBuildError(_FAILURE) from error


def _extracted_git_tree_manifest(
    root: Path,
    object_format: str,
) -> tuple[_GitTreeMember, ...]:
    try:
        selected_root = root.resolve(strict=True)
        members: list[_GitTreeMember] = []

        def visit(directory: Path) -> None:
            with os.scandir(directory) as scanner:
                children = sorted(scanner, key=lambda entry: os.fsencode(entry.name))
            for entry in children:
                path = Path(entry.path)
                metadata = entry.stat(follow_symlinks=False)
                relative = path.relative_to(selected_root).as_posix()
                if stat.S_ISDIR(metadata.st_mode):
                    visit(path)
                    continue
                if stat.S_ISREG(metadata.st_mode):
                    mode = "100755" if metadata.st_mode & 0o111 else "100644"
                    payload = path.read_bytes()
                elif stat.S_ISLNK(metadata.st_mode):
                    mode = "120000"
                    payload = os.fsencode(os.readlink(path))
                else:
                    raise NativeBuildError(_FAILURE)
                members.append(
                    _GitTreeMember(
                        mode,
                        _git_blob_object_id(payload, object_format),
                        relative,
                    )
                )
                if len(members) > _MAXIMUM_SOURCE_MEMBERS:
                    raise NativeBuildError(_FAILURE)

        visit(selected_root)
        return tuple(sorted(members, key=lambda member: member.path.encode("utf-8")))
    except NativeBuildError:
        raise
    except (OSError, UnicodeError, ValueError) as error:
        raise NativeBuildError(_FAILURE) from error


def _git_blob_object_id(payload: bytes, object_format: str) -> str:
    try:
        digest = hashlib.new(object_format)
    except ValueError as error:
        raise NativeBuildError(_FAILURE) from error
    digest.update(f"blob {len(payload)}\0".encode("ascii"))
    digest.update(payload)
    return digest.hexdigest()


def _validate_source_binding(root: Path, source_sha: str) -> None:
    try:
        _validate_repository_git_inputs(root)
        head = subprocess.run(
            _git_command("rev-parse", "HEAD"),
            cwd=root,
            capture_output=True,
            text=True,
            env=_hermetic_git_environment(),
            timeout=10,
            check=True,
        ).stdout.strip()
        status = subprocess.run(
            _git_command("status", "--porcelain=v1", "--untracked-files=all"),
            cwd=root,
            capture_output=True,
            text=True,
            env=_hermetic_git_environment(),
            timeout=10,
            check=True,
        ).stdout
    except (OSError, subprocess.SubprocessError) as error:
        raise NativeBuildError(_FAILURE) from error
    if head != source_sha or status:
        raise NativeBuildError(_FAILURE)


def validate_exact_source_binding(root: Path, source_sha: str) -> None:
    """Require one clean exact HEAD without changing the P4-W5 default path."""
    _validate_source_binding(root, source_sha)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m tools.phase4.native_build")
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate-config")
    validate.add_argument("--root", type=Path, required=True)
    build = commands.add_parser("build")
    build.add_argument("--root", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--source-sha", required=True)
    build.add_argument("--candidate-id", default="candidate_native-p4w5")
    build.add_argument("--wave", choices=("P4-W5", "P4-W6"), default="P4-W5")
    smoke = commands.add_parser("smoke")
    smoke.add_argument("--artifact", type=Path, required=True)
    smoke.add_argument("--evidence", type=Path, required=True)
    smoke.add_argument(
        "--expected-wave",
        choices=("P4-W5", "P4-W6"),
        default="P4-W5",
    )
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
                candidate_id=namespace.candidate_id,
                wave=namespace.wave,
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
                expected_wave=namespace.expected_wave,
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
