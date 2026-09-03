"""P4-W6 release media, signing, notarization, and manifest contracts."""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import re
import stat
import subprocess
import tarfile
import uuid
from collections.abc import Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Final, Protocol, Self, cast

_FAILURE: Final = "release candidate operation failed"
_DIGEST = re.compile(r"[0-9a-f]{64}")
_SOURCE_SHA = re.compile(r"[0-9a-f]{40}")
_RECEIPT = re.compile(r"rct_v1_[0-9a-f]{64}")
_ARCHIVE_ROOT = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
_MACHO_MAGICS: Final = frozenset(
    {
        b"\xfe\xed\xfa\xce",
        b"\xce\xfa\xed\xfe",
        b"\xfe\xed\xfa\xcf",
        b"\xcf\xfa\xed\xfe",
        b"\xca\xfe\xba\xbe",
        b"\xbe\xba\xfe\xca",
        b"\xca\xfe\xba\xbf",
        b"\xbf\xba\xfe\xca",
    }
)
_MAXIMUM_PRIVATE_OUTPUT: Final = 2 * 1024 * 1024
_REQUIRED_CLEAN_HOST_CHECKS: Final = frozenset(
    {
        "artifact_install",
        "backup_disposable_restore_exact_bytes",
        "doctor",
        "portable_round_trip",
        "prior_schema_upgrade",
        "residue",
        "rollback",
        "source_checkout_required",
        "system_python_required",
        "uninstall",
        "v0_gate_07",
        "v0_gate_13",
    }
)
_LINUX_HOSTS: Final = ("ubuntu-24.04", "ubuntu-26.04", "debian-13")
_MACOS_HOST = re.compile(r"macos-(?:1[4-9]|[2-9][0-9]|[1-9][0-9]{2,})")
_MACOS_BLOCKER = "exact-signed-candidate-runner-unavailable"
_SENSITIVE_KEYS: Final = (
    "account",
    "apple_id",
    "certificate_subject",
    "credential",
    "identity",
    "keychain",
    "password",
    "profile",
    "team_id",
)

EXPECTED_RELEASE_ARTIFACT_COORDINATES: Final = (
    "python.app.sdist",
    "python.app.wheel",
    "python.connectors.sdist",
    "python.connectors.wheel",
    "python.engine.sdist",
    "python.engine.wheel",
    "native.linux-x86_64",
    "native.macos-arm64",
    "checksums.linux-x86_64",
    "checksums.macos-arm64",
    "supervisor.launchd",
    "supervisor.systemd",
    "sbom.spdx",
    "evidence.licenses",
    "evidence.native-build.linux-x86_64",
    "evidence.native-build.macos-arm64",
    "evidence.notarization.macos-arm64",
    "evidence.clean-host.ubuntu-24.04",
    "evidence.clean-host.ubuntu-26.04",
    "evidence.clean-host.debian-13",
    "evidence.clean-host.macos-signed",
    "evidence.clean-host.macos-14-unavailable",
    "evidence.clean-host.macos-14-source-equivalent",
)


class ReleaseCandidateError(RuntimeError):
    """A release operation failed without exposing host or credential output."""


class CommandRunner(Protocol):
    def __call__(
        self,
        command: tuple[str, ...],
        *,
        timeout: int,
    ) -> subprocess.CompletedProcess[str]: ...


@dataclass(frozen=True, slots=True)
class NotarizationEvidence:
    status: str
    issue_count: int
    receipt: str
    stapled: bool
    validated: bool

    def __post_init__(self) -> None:
        if (
            self.status != "accepted"
            or type(self.issue_count) is not int
            or self.issue_count != 0
            or _RECEIPT.fullmatch(self.receipt) is None
            or self.stapled is not True
            or self.validated is not True
        ):
            raise ReleaseCandidateError(_FAILURE)

    def to_dict(self) -> dict[str, object]:
        return {
            "issue_count": self.issue_count,
            "receipt": self.receipt,
            "stapled": self.stapled,
            "status": self.status,
            "validated": self.validated,
        }

    @classmethod
    def from_dict(cls, value: object) -> Self:
        record = _object(value)
        if set(record) != {"issue_count", "receipt", "stapled", "status", "validated"}:
            raise ReleaseCandidateError(_FAILURE)
        return cls(
            status=_string(record, "status"),
            issue_count=_integer(record, "issue_count"),
            receipt=_string(record, "receipt"),
            stapled=_boolean(record, "stapled"),
            validated=_boolean(record, "validated"),
        )


@dataclass(frozen=True, slots=True)
class ReleaseArtifact:
    coordinate: str
    path: str
    sha256: str
    size: int

    def __post_init__(self) -> None:
        if (
            self.coordinate not in EXPECTED_RELEASE_ARTIFACT_COORDINATES
            or not _safe_relative_path(self.path)
            or _DIGEST.fullmatch(self.sha256) is None
            or type(self.size) is not int
            or self.size < 0
        ):
            raise ReleaseCandidateError(_FAILURE)

    @classmethod
    def from_path(
        cls,
        *,
        coordinate: str,
        path: Path,
        relative_to: Path,
    ) -> Self:
        try:
            root = relative_to.resolve(strict=True)
            selected = path.resolve(strict=True)
            metadata = path.lstat()
            if not stat.S_ISREG(metadata.st_mode) or path.is_symlink():
                raise ReleaseCandidateError(_FAILURE)
            relative = selected.relative_to(root).as_posix()
            return cls(
                coordinate=coordinate,
                path=relative,
                sha256=file_sha256(selected),
                size=metadata.st_size,
            )
        except ReleaseCandidateError:
            raise
        except (OSError, ValueError) as error:
            raise ReleaseCandidateError(_FAILURE) from error

    @classmethod
    def from_dict(cls, value: object) -> Self:
        record = _object(value)
        if set(record) != {"coordinate", "path", "sha256", "size"}:
            raise ReleaseCandidateError(_FAILURE)
        return cls(
            coordinate=_string(record, "coordinate"),
            path=_string(record, "path"),
            sha256=_string(record, "sha256"),
            size=_integer(record, "size"),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "coordinate": self.coordinate,
            "path": self.path,
            "sha256": self.sha256,
            "size": self.size,
        }


@dataclass(frozen=True, slots=True)
class CleanHostEvidence:
    host: str
    architecture: str
    artifact_sha256: str
    source_sha: str
    setup_seconds: float | None
    status: str
    checks: dict[str, object]
    exact_signed_candidate: bool
    blocker_code: str | None = None

    def __post_init__(self) -> None:
        if (
            not isinstance(self.host, str)
            or not self.host
            or self.host not in _LINUX_HOSTS
            and _MACOS_HOST.fullmatch(self.host) is None
            or not isinstance(self.architecture, str)
            or self.architecture not in {"arm64", "x86_64"}
            or _DIGEST.fullmatch(self.artifact_sha256) is None
            or _SOURCE_SHA.fullmatch(self.source_sha) is None
            or self.status not in {"passed", "unavailable-runner"}
            or not isinstance(self.checks, dict)
            or type(self.exact_signed_candidate) is not bool
            or self.blocker_code is not None
            and not isinstance(self.blocker_code, str)
        ):
            raise ReleaseCandidateError(_FAILURE)
        if self.setup_seconds is not None and (
            isinstance(self.setup_seconds, bool)
            or not isinstance(self.setup_seconds, (int, float))
            or not 0 <= float(self.setup_seconds) <= 86_400
        ):
            raise ReleaseCandidateError(_FAILURE)

    @classmethod
    def from_dict(cls, value: object) -> Self:
        record = _object(value)
        if set(record) != {
            "architecture",
            "artifact_sha256",
            "blocker_code",
            "checks",
            "exact_signed_candidate",
            "host",
            "setup_seconds",
            "source_sha",
            "status",
        }:
            raise ReleaseCandidateError(_FAILURE)
        raw_setup = record["setup_seconds"]
        setup: float | None
        if raw_setup is None:
            setup = None
        elif isinstance(raw_setup, bool) or not isinstance(raw_setup, (int, float)):
            raise ReleaseCandidateError(_FAILURE)
        else:
            setup = float(raw_setup)
        raw_blocker = record["blocker_code"]
        if raw_blocker is not None and not isinstance(raw_blocker, str):
            raise ReleaseCandidateError(_FAILURE)
        raw_checks = record["checks"]
        if not isinstance(raw_checks, dict) or any(not isinstance(key, str) for key in raw_checks):
            raise ReleaseCandidateError(_FAILURE)
        return cls(
            host=_string(record, "host"),
            architecture=_string(record, "architecture"),
            artifact_sha256=_string(record, "artifact_sha256"),
            source_sha=_string(record, "source_sha"),
            setup_seconds=setup,
            status=_string(record, "status"),
            checks=cast(dict[str, object], raw_checks),
            exact_signed_candidate=_boolean(record, "exact_signed_candidate"),
            blocker_code=raw_blocker,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "architecture": self.architecture,
            "artifact_sha256": self.artifact_sha256,
            "blocker_code": self.blocker_code,
            "checks": dict(sorted(self.checks.items())),
            "exact_signed_candidate": self.exact_signed_candidate,
            "host": self.host,
            "setup_seconds": self.setup_seconds,
            "source_sha": self.source_sha,
            "status": self.status,
        }


def file_sha256(path: Path) -> str:
    try:
        metadata = path.lstat()
        if not stat.S_ISREG(metadata.st_mode) or path.is_symlink():
            raise ReleaseCandidateError(_FAILURE)
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                digest.update(chunk)
        return digest.hexdigest()
    except ReleaseCandidateError:
        raise
    except OSError as error:
        raise ReleaseCandidateError(_FAILURE) from error


def collect_macos_signing_targets(candidate: Path) -> tuple[Path, ...]:
    """Return confined Mach-O files, framework bundles, and the main binary in sign order."""
    try:
        root = candidate.resolve(strict=True)
        metadata = candidate.lstat()
        if not stat.S_ISDIR(metadata.st_mode) or candidate.is_symlink():
            raise ReleaseCandidateError(_FAILURE)
        macho_files: list[Path] = []
        frameworks: list[Path] = []
        for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
            item_metadata = path.lstat()
            if stat.S_ISLNK(item_metadata.st_mode):
                resolved = path.resolve(strict=True)
                if not resolved.is_relative_to(root):
                    raise ReleaseCandidateError(_FAILURE)
                continue
            if stat.S_ISDIR(item_metadata.st_mode):
                if path.name.endswith(".framework"):
                    frameworks.append(path)
                continue
            if not stat.S_ISREG(item_metadata.st_mode):
                raise ReleaseCandidateError(_FAILURE)
            with path.open("rb") as stream:
                if stream.read(4) in _MACHO_MAGICS:
                    macho_files.append(path)
        main = root / "open-brain"
        if main not in macho_files:
            raise ReleaseCandidateError(_FAILURE)
        nested = sorted(
            (path for path in macho_files if path != main),
            key=lambda path: (
                -len(path.relative_to(root).parts),
                path.relative_to(root).as_posix(),
            ),
        )
        bundles = sorted(
            frameworks,
            key=lambda path: (
                -len(path.relative_to(root).parts),
                path.relative_to(root).as_posix(),
            ),
        )
        return (*nested, *bundles, main)
    except ReleaseCandidateError:
        raise
    except OSError as error:
        raise ReleaseCandidateError(_FAILURE) from error


def sign_macos_candidate(
    candidate: Path,
    *,
    identity: str,
    runner: CommandRunner | None = None,
) -> dict[str, object]:
    selected_runner = _run_private if runner is None else runner
    try:
        _private_selector(identity)
        targets = collect_macos_signing_targets(candidate)
        for target in targets:
            _require_ok(
                selected_runner(
                    (
                        "codesign",
                        "--force",
                        "--options",
                        "runtime",
                        "--timestamp",
                        "--sign",
                        identity,
                        str(target),
                    ),
                    timeout=120,
                )
            )
        hardened_runtime = True
        secure_timestamp = True
        for target in targets:
            _require_ok(
                selected_runner(
                    ("codesign", "--verify", "--strict", str(target)),
                    timeout=60,
                )
            )
            display = selected_runner(
                ("codesign", "--display", "--verbose=4", str(target)),
                timeout=60,
            )
            _require_ok(display)
            details = f"{display.stdout or ''}\n{display.stderr or ''}"
            hardened_runtime = hardened_runtime and "runtime" in details.casefold()
            secure_timestamp = secure_timestamp and "timestamp=" in details.casefold()
        if not hardened_runtime or not secure_timestamp:
            raise ReleaseCandidateError(_FAILURE)
        return {
            "hardened_runtime": True,
            "secure_timestamp": True,
            "signed_code_count": len(targets),
            "status": "passed",
        }
    except ReleaseCandidateError:
        raise
    except Exception as error:
        raise ReleaseCandidateError(_FAILURE) from error


def notarize_macos_dmg(
    dmg: Path,
    *,
    keychain_profile: str,
    runner: CommandRunner | None = None,
) -> NotarizationEvidence:
    selected_runner = _run_private if runner is None else runner
    try:
        path = dmg.resolve(strict=True)
        metadata = dmg.lstat()
        _private_selector(keychain_profile)
        if (
            dmg.suffix.casefold() != ".dmg"
            or not stat.S_ISREG(metadata.st_mode)
            or dmg.is_symlink()
        ):
            raise ReleaseCandidateError(_FAILURE)
        submission = selected_runner(
            (
                "xcrun",
                "notarytool",
                "submit",
                str(path),
                "--keychain-profile",
                keychain_profile,
                "--wait",
                "--output-format",
                "json",
            ),
            timeout=1_800,
        )
        _require_ok(submission)
        submitted = _json_object(submission.stdout)
        submission_id = _string(submitted, "id")
        uuid.UUID(submission_id)
        if _string(submitted, "status").casefold() != "accepted":
            raise ReleaseCandidateError(_FAILURE)
        log_result = selected_runner(
            (
                "xcrun",
                "notarytool",
                "log",
                submission_id,
                "--keychain-profile",
                keychain_profile,
                "--output-format",
                "json",
            ),
            timeout=300,
        )
        _require_ok(log_result)
        log = _json_object(log_result.stdout)
        issues = log.get("issues")
        if (
            log.get("jobId") != submission_id
            or log.get("status") != "Accepted"
            or not isinstance(issues, list)
            or issues
        ):
            raise ReleaseCandidateError(_FAILURE)
        _require_ok(selected_runner(("xcrun", "stapler", "staple", str(path)), timeout=300))
        _require_ok(selected_runner(("xcrun", "stapler", "validate", str(path)), timeout=120))
        receipt = (
            "rct_v1_"
            + hashlib.sha256(
                f"notary:{submission_id}:{file_sha256(path)}".encode("ascii")
            ).hexdigest()
        )
        return NotarizationEvidence(
            status="accepted",
            issue_count=0,
            receipt=receipt,
            stapled=True,
            validated=True,
        )
    except ReleaseCandidateError:
        raise
    except Exception as error:
        raise ReleaseCandidateError(_FAILURE) from error


def create_deterministic_tar_gz(
    source: Path,
    destination: Path,
    *,
    archive_root: str,
) -> Path:
    """Write a normalized tar.gz while preserving only safe relative symlinks."""
    temporary: Path | None = None
    try:
        root = source.resolve(strict=True)
        metadata = source.lstat()
        if (
            not stat.S_ISDIR(metadata.st_mode)
            or source.is_symlink()
            or _ARCHIVE_ROOT.fullmatch(archive_root) is None
        ):
            raise ReleaseCandidateError(_FAILURE)
        selected_destination = destination.resolve()
        if selected_destination.is_relative_to(root):
            raise ReleaseCandidateError(_FAILURE)
        selected_destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = selected_destination.with_name(f".{selected_destination.name}.tmp")
        if temporary.exists() or temporary.is_symlink():
            raise ReleaseCandidateError(_FAILURE)
        entries = _archive_entries(root)
        with temporary.open("xb") as raw_stream:
            with (
                gzip.GzipFile(
                    filename="",
                    mode="wb",
                    compresslevel=9,
                    fileobj=raw_stream,
                    mtime=0,
                ) as gzip_stream,
                tarfile.open(
                    fileobj=gzip_stream,
                    mode="w",
                    format=tarfile.PAX_FORMAT,
                ) as archive,
            ):
                _add_tar_directory(archive, archive_root)
                for path in entries:
                    relative = path.relative_to(root).as_posix()
                    _add_tar_member(
                        archive,
                        path,
                        PurePosixPath(archive_root, relative).as_posix(),
                        root=root,
                    )
            raw_stream.flush()
            os.fsync(raw_stream.fileno())
        temporary.replace(selected_destination)
        return selected_destination
    except ReleaseCandidateError:
        raise
    except (OSError, ValueError, tarfile.TarError) as error:
        raise ReleaseCandidateError(_FAILURE) from error
    finally:
        if temporary is not None:
            with suppress(OSError):
                temporary.unlink(missing_ok=True)


def write_sha256_file(artifact: Path) -> Path:
    try:
        selected = artifact.resolve(strict=True)
        if any(character in artifact.name for character in "\r\n"):
            raise ReleaseCandidateError(_FAILURE)
        checksum = selected.with_name(selected.name + ".sha256")
        temporary = checksum.with_name(f".{checksum.name}.tmp")
        if temporary.exists() or temporary.is_symlink():
            raise ReleaseCandidateError(_FAILURE)
        payload = f"{file_sha256(selected)}  {selected.name}\n".encode("ascii")
        with temporary.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(checksum)
        return checksum
    except ReleaseCandidateError:
        raise
    except OSError as error:
        raise ReleaseCandidateError(_FAILURE) from error


def validate_clean_host_matrix(
    results: Sequence[CleanHostEvidence],
    *,
    source_sha: str,
    linux_artifact_sha256: str,
    macos_artifact_sha256: str,
) -> None:
    try:
        if (
            _SOURCE_SHA.fullmatch(source_sha) is None
            or _DIGEST.fullmatch(linux_artifact_sha256) is None
            or _DIGEST.fullmatch(macos_artifact_sha256) is None
            or not results
        ):
            raise ReleaseCandidateError(_FAILURE)
        by_host_and_candidate: dict[tuple[str, bool], CleanHostEvidence] = {}
        for result in results:
            if not isinstance(result, CleanHostEvidence):
                raise ReleaseCandidateError(_FAILURE)
            evidence_key = (result.host, result.exact_signed_candidate)
            if evidence_key in by_host_and_candidate or result.source_sha != source_sha:
                raise ReleaseCandidateError(_FAILURE)
            by_host_and_candidate[evidence_key] = result
            if result.host in _LINUX_HOSTS:
                if (
                    result.architecture != "x86_64"
                    or result.exact_signed_candidate
                    or result.artifact_sha256 != linux_artifact_sha256
                    or result.status != "passed"
                ):
                    raise ReleaseCandidateError(_FAILURE)
                _validate_passed_host(result)
            elif not result.host.startswith("macos-") or result.architecture != "arm64":
                raise ReleaseCandidateError(_FAILURE)
            elif result.exact_signed_candidate:
                if result.artifact_sha256 != macos_artifact_sha256:
                    raise ReleaseCandidateError(_FAILURE)
                if result.status == "passed":
                    _validate_passed_host(result)
                elif (
                    result.host != "macos-14"
                    or result.setup_seconds is not None
                    or result.checks
                    or result.blocker_code != _MACOS_BLOCKER
                ):
                    raise ReleaseCandidateError(_FAILURE)
            elif result.host != "macos-14" or result.status != "passed":
                raise ReleaseCandidateError(_FAILURE)
            else:
                _validate_passed_host(result)
        for host in _LINUX_HOSTS:
            if by_host_and_candidate.get((host, False)) is None:
                raise ReleaseCandidateError(_FAILURE)
        minimum_macos = by_host_and_candidate.get(("macos-14", True))
        source_equivalent = by_host_and_candidate.get(("macos-14", False))
        signed_macos_runs = tuple(
            result
            for result in results
            if result.host.startswith("macos-")
            and result.status == "passed"
            and result.exact_signed_candidate
        )
        if minimum_macos is None or source_equivalent is None or (
            minimum_macos.status == "passed"
            and not minimum_macos.exact_signed_candidate
            or minimum_macos.status == "unavailable-runner"
            and not signed_macos_runs
        ):
            raise ReleaseCandidateError(_FAILURE)
    except ReleaseCandidateError:
        raise
    except Exception as error:
        raise ReleaseCandidateError(_FAILURE) from error


def build_release_manifest(
    *,
    source_sha: str,
    version: str,
    artifacts: Sequence[ReleaseArtifact],
    clean_hosts: Sequence[CleanHostEvidence],
    notarization: NotarizationEvidence,
    supported_hosts: Mapping[str, object],
    portable_schema: Mapping[str, object],
) -> dict[str, object]:
    try:
        manifest: dict[str, object] = {
            "artifacts": [
                artifact.to_dict()
                for artifact in sorted(artifacts, key=lambda item: item.coordinate)
            ],
            "clean_hosts": [
                result.to_dict()
                for result in sorted(
                    clean_hosts,
                    key=lambda item: (item.host, item.exact_signed_candidate),
                )
            ],
            "candidate_id": "candidate_native-p4w6",
            "notarization": notarization.to_dict(),
            "portable_schema": dict(portable_schema),
            "publication": {
                "packages": [],
                "releases": [],
                "status": "unpublished",
                "tags": [],
            },
            "schema_version": 1,
            "source": {"git_sha": source_sha},
            "supported_hosts": dict(supported_hosts),
            "version": version,
        }
        validate_release_manifest(manifest)
        return manifest
    except ReleaseCandidateError:
        raise
    except Exception as error:
        raise ReleaseCandidateError(_FAILURE) from error


def validate_release_manifest(value: object) -> None:
    try:
        manifest = _object(value)
        _reject_sensitive_keys(manifest)
        if (
            set(manifest)
            != {
                "artifacts",
                "candidate_id",
                "clean_hosts",
                "notarization",
                "portable_schema",
                "publication",
                "schema_version",
                "source",
                "supported_hosts",
                "version",
            }
            or manifest.get("schema_version") != 1
            or manifest.get("candidate_id") != "candidate_native-p4w6"
        ):
            raise ReleaseCandidateError(_FAILURE)
        version = manifest.get("version")
        if version != "0.1.0":
            raise ReleaseCandidateError(_FAILURE)
        source = _object(manifest.get("source"))
        if set(source) != {"git_sha"}:
            raise ReleaseCandidateError(_FAILURE)
        source_sha = _string(source, "git_sha")
        if _SOURCE_SHA.fullmatch(source_sha) is None:
            raise ReleaseCandidateError(_FAILURE)
        raw_artifacts = manifest.get("artifacts")
        if not isinstance(raw_artifacts, list):
            raise ReleaseCandidateError(_FAILURE)
        artifacts = tuple(ReleaseArtifact.from_dict(item) for item in raw_artifacts)
        coordinates = tuple(artifact.coordinate for artifact in artifacts)
        paths = tuple(artifact.path for artifact in artifacts)
        if (
            coordinates != tuple(sorted(coordinates))
            or len(set(coordinates)) != len(coordinates)
            or len(set(paths)) != len(paths)
            or set(coordinates) != set(EXPECTED_RELEASE_ARTIFACT_COORDINATES)
        ):
            raise ReleaseCandidateError(_FAILURE)
        raw_hosts = manifest.get("clean_hosts")
        if not isinstance(raw_hosts, list):
            raise ReleaseCandidateError(_FAILURE)
        clean_hosts = tuple(CleanHostEvidence.from_dict(item) for item in raw_hosts)
        if tuple((result.host, result.exact_signed_candidate) for result in clean_hosts) != tuple(
            sorted((result.host, result.exact_signed_candidate) for result in clean_hosts)
        ):
            raise ReleaseCandidateError(_FAILURE)
        artifact_by_coordinate = {artifact.coordinate: artifact for artifact in artifacts}
        validate_clean_host_matrix(
            clean_hosts,
            source_sha=source_sha,
            linux_artifact_sha256=artifact_by_coordinate["native.linux-x86_64"].sha256,
            macos_artifact_sha256=artifact_by_coordinate["native.macos-arm64"].sha256,
        )
        NotarizationEvidence.from_dict(manifest.get("notarization"))
        if manifest.get("portable_schema") != {"maximum": 1, "minimum": 1}:
            raise ReleaseCandidateError(_FAILURE)
        if manifest.get("supported_hosts") != {
            "linux-x86_64": ["ubuntu-24.04", "ubuntu-26.04", "debian-13"],
            "macos-arm64": ">=14",
        }:
            raise ReleaseCandidateError(_FAILURE)
        if manifest.get("publication") != {
            "packages": [],
            "releases": [],
            "status": "unpublished",
            "tags": [],
        }:
            raise ReleaseCandidateError(_FAILURE)
    except ReleaseCandidateError:
        raise
    except Exception as error:
        raise ReleaseCandidateError(_FAILURE) from error


def _validate_passed_host(result: CleanHostEvidence) -> None:
    if (
        result.setup_seconds is None
        or result.setup_seconds > 900
        or result.blocker_code is not None
        or set(result.checks) != _REQUIRED_CLEAN_HOST_CHECKS
        or result.checks.get("source_checkout_required") is not False
        or result.checks.get("system_python_required") is not False
        or any(
            result.checks.get(name) != "passed"
            for name in _REQUIRED_CLEAN_HOST_CHECKS
            if name not in {"source_checkout_required", "system_python_required"}
        )
    ):
        raise ReleaseCandidateError(_FAILURE)


def _archive_entries(root: Path) -> tuple[Path, ...]:
    entries: list[Path] = []

    def visit(directory: Path) -> None:
        with os.scandir(directory) as scanner:
            children = sorted(scanner, key=lambda entry: entry.name)
        for child in children:
            path = Path(child.path)
            metadata = child.stat(follow_symlinks=False)
            if stat.S_ISLNK(metadata.st_mode):
                target = os.readlink(path)
                if "\x00" in target or Path(target).is_absolute():
                    raise ReleaseCandidateError(_FAILURE)
                resolved = (path.parent / target).resolve(strict=True)
                if not resolved.is_relative_to(root):
                    raise ReleaseCandidateError(_FAILURE)
            elif stat.S_ISDIR(metadata.st_mode):
                pass
            elif stat.S_ISREG(metadata.st_mode):
                if metadata.st_nlink != 1:
                    raise ReleaseCandidateError(_FAILURE)
            else:
                raise ReleaseCandidateError(_FAILURE)
            entries.append(path)
            if stat.S_ISDIR(metadata.st_mode):
                visit(path)

    visit(root)
    return tuple(sorted(entries, key=lambda path: path.relative_to(root).as_posix()))


def _normalized_tar_info(name: str, *, mode: int) -> tarfile.TarInfo:
    info = tarfile.TarInfo(name)
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    info.mtime = 0
    info.mode = mode
    return info


def _add_tar_directory(archive: tarfile.TarFile, name: str, *, mode: int = 0o755) -> None:
    info = _normalized_tar_info(name, mode=mode)
    info.type = tarfile.DIRTYPE
    archive.addfile(info)


def _add_tar_member(archive: tarfile.TarFile, path: Path, name: str, *, root: Path) -> None:
    metadata = path.lstat()
    mode = stat.S_IMODE(metadata.st_mode)
    if mode & 0o7000 or mode & 0o400 == 0:
        raise ReleaseCandidateError(_FAILURE)
    if stat.S_ISDIR(metadata.st_mode):
        _add_tar_directory(archive, name, mode=mode)
        return
    if stat.S_ISLNK(metadata.st_mode):
        target = os.readlink(path)
        resolved = (path.parent / target).resolve(strict=True)
        if Path(target).is_absolute() or not resolved.is_relative_to(root):
            raise ReleaseCandidateError(_FAILURE)
        info = _normalized_tar_info(name, mode=mode)
        info.type = tarfile.SYMTYPE
        info.linkname = target
        archive.addfile(info)
        return
    if not stat.S_ISREG(metadata.st_mode):
        raise ReleaseCandidateError(_FAILURE)
    info = _normalized_tar_info(name, mode=mode)
    info.type = tarfile.REGTYPE
    info.size = metadata.st_size
    with path.open("rb") as stream:
        archive.addfile(info, stream)


def _run_private(
    command: tuple[str, ...],
    *,
    timeout: int,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _require_ok(result: subprocess.CompletedProcess[str]) -> None:
    if (
        not isinstance(result, subprocess.CompletedProcess)
        or result.returncode != 0
        or len(result.stdout or "") > _MAXIMUM_PRIVATE_OUTPUT
        or len(result.stderr or "") > _MAXIMUM_PRIVATE_OUTPUT
    ):
        raise ReleaseCandidateError(_FAILURE)


def _private_selector(value: str) -> None:
    if (
        not isinstance(value, str)
        or not value
        or value.isspace()
        or "\x00" in value
        or "\n" in value
        or "\r" in value
    ):
        raise ReleaseCandidateError(_FAILURE)


def _json_object(payload: str | None) -> dict[str, object]:
    try:
        if not isinstance(payload, str) or len(payload) > _MAXIMUM_PRIVATE_OUTPUT:
            raise ReleaseCandidateError(_FAILURE)
        value = json.loads(payload)
        return _object(value)
    except ReleaseCandidateError:
        raise
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        raise ReleaseCandidateError(_FAILURE) from error


def _object(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise ReleaseCandidateError(_FAILURE)
    return cast(dict[str, object], value)


def _string(value: Mapping[str, object], key: str) -> str:
    item = value.get(key)
    if not isinstance(item, str):
        raise ReleaseCandidateError(_FAILURE)
    return item


def _integer(value: Mapping[str, object], key: str) -> int:
    item = value.get(key)
    if type(item) is not int:
        raise ReleaseCandidateError(_FAILURE)
    return item


def _boolean(value: Mapping[str, object], key: str) -> bool:
    item = value.get(key)
    if type(item) is not bool:
        raise ReleaseCandidateError(_FAILURE)
    return item


def _safe_relative_path(value: str) -> bool:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and ".." not in path.parts and path.as_posix() == value


def _reject_sensitive_keys(value: object) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str) or any(term in key.casefold() for term in _SENSITIVE_KEYS):
                raise ReleaseCandidateError(_FAILURE)
            _reject_sensitive_keys(item)
    elif isinstance(value, list):
        for item in value:
            _reject_sensitive_keys(item)
