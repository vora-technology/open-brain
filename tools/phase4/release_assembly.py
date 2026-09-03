"""Exact artifact assembly helpers for the unpublished P4-W6 candidate."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from collections.abc import Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Final, cast

from open_brain.services.native_artifacts import (
    NATIVE_MANIFEST_NAME,
    NativeArtifactError,
    NativeArtifactManifest,
)
from tools.open_brain_dev.artifact_policy import verify_artifacts
from tools.phase4.native_build import (
    NativeArtifactAudit,
    NativeBuildError,
    audit_native_artifact,
    build_native_artifact,
    exact_source_tree_sha256,
    load_native_build_configuration,
    materialize_exact_source_tree,
    smoke_native_artifact,
    validate_exact_source_binding,
)
from tools.phase4.release_candidate import (
    EXPECTED_RELEASE_ARTIFACT_COORDINATES,
    CleanHostEvidence,
    CommandRunner,
    NotarizationEvidence,
    ReleaseArtifact,
    ReleaseCandidateError,
    build_release_manifest,
    create_deterministic_tar_gz,
    file_sha256,
    notarize_macos_dmg,
    sign_macos_candidate,
    validate_release_manifest,
    write_sha256_file,
)

_FAILURE: Final = "release candidate operation failed"
_SOURCE_SHA = re.compile(r"[0-9a-f]{40}")
_VERSION = "0.1.0"
_CANDIDATE_ID = "candidate_native-p4w6"
_THIRD_PARTY_LICENSES: Final = frozenset({"CPython-LICENSE.txt", "PyInstaller-COPYING.txt"})
_MAXIMUM_COMMAND_OUTPUT: Final = 2 * 1024 * 1024
_DEVELOPER_IDENTITY = re.compile(r'^\s*\d+\)\s+([0-9A-Fa-f]{40})\s+"Developer ID Application:')
_PYTHON_DISTRIBUTION_NAMES: Final = {
    "python.app.sdist": "open_brain-0.1.0.tar.gz",
    "python.app.wheel": "open_brain-0.1.0-py3-none-any.whl",
    "python.connectors.sdist": "open_brain_connectors-0.1.0.tar.gz",
    "python.connectors.wheel": "open_brain_connectors-0.1.0-py3-none-any.whl",
    "python.engine.sdist": "open_brain_engine-0.1.0.tar.gz",
    "python.engine.wheel": "open_brain_engine-0.1.0-py3-none-any.whl",
}
_SENSITIVE_RELEASE_KEYS: Final = (
    "account",
    "credential",
    "identity",
    "keychain",
    "password",
    "profile",
    "subject",
    "team",
)


@dataclass(frozen=True, slots=True)
class LicenseBinding:
    name: str
    license_expression: str
    path: Path

    def __post_init__(self) -> None:
        if (
            not isinstance(self.name, str)
            or not self.name
            or not isinstance(self.license_expression, str)
            or not self.license_expression
            or not isinstance(self.path, Path)
        ):
            raise ReleaseCandidateError(_FAILURE)


def discover_developer_id_identity(
    *,
    runner: CommandRunner | None = None,
) -> str:
    """Select one Developer ID Application certificate without emitting its subject."""
    selected_runner = _run_bounded if runner is None else runner
    try:
        result = selected_runner(
            ("security", "find-identity", "-v", "-p", "codesigning"),
            timeout=30,
        )
        _require_ok(result)
        identities = tuple(
            match.group(1)
            for line in (result.stdout or "").splitlines()
            if (match := _DEVELOPER_IDENTITY.match(line)) is not None
        )
        if len(identities) != 1:
            raise ReleaseCandidateError(_FAILURE)
        return identities[0]
    except ReleaseCandidateError:
        raise
    except Exception as error:
        raise ReleaseCandidateError(_FAILURE) from error


def python_distribution_artifacts(directory: Path) -> dict[str, Path]:
    """Resolve the exact six public Python artifacts and reject residue."""
    try:
        root = directory.resolve(strict=True)
        if directory.is_symlink() or not directory.is_dir():
            raise ReleaseCandidateError(_FAILURE)
        entries = tuple(sorted(root.iterdir(), key=lambda path: path.name))
        if any(path.is_symlink() or not path.is_file() for path in entries) or {
            path.name for path in entries
        } != set(_PYTHON_DISTRIBUTION_NAMES.values()):
            raise ReleaseCandidateError(_FAILURE)
        by_name = {path.name: path for path in entries}
        return {
            coordinate: by_name[name]
            for coordinate, name in sorted(_PYTHON_DISTRIBUTION_NAMES.items())
        }
    except ReleaseCandidateError:
        raise
    except OSError as error:
        raise ReleaseCandidateError(_FAILURE) from error


def bind_native_release_evidence(
    evidence_path: Path,
    *,
    audit: NativeArtifactAudit,
    release: Mapping[str, object],
    source_sha: str,
) -> dict[str, object]:
    """Replace the pre-sign audit with final bytes and bounded release properties."""
    try:
        _regular_file(evidence_path)
        if evidence_path.stat().st_size > _MAXIMUM_COMMAND_OUTPUT:
            raise ReleaseCandidateError(_FAILURE)
        value = json.loads(evidence_path.read_bytes())
        if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
            raise ReleaseCandidateError(_FAILURE)
        evidence = cast(dict[str, object], value)
        if (
            evidence.get("schema_version") != 1
            or evidence.get("wave") != "P4-W6"
            or evidence.get("source_sha") != source_sha
            or _SOURCE_SHA.fullmatch(source_sha) is None
            or evidence.get("runtime") is not None
            and not isinstance(evidence.get("runtime"), dict)
            or not isinstance(audit, NativeArtifactAudit)
            or audit.candidate_id != _CANDIDATE_ID
            or not release
        ):
            raise ReleaseCandidateError(_FAILURE)
        bounded_release = dict(release)
        _reject_sensitive_release_keys(bounded_release)
        if bounded_release.get("status") != "passed":
            raise ReleaseCandidateError(_FAILURE)
        evidence["artifact"] = audit.to_dict()
        evidence["release"] = bounded_release
        _replace_json(evidence_path, evidence)
        return evidence
    except ReleaseCandidateError:
        raise
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise ReleaseCandidateError(_FAILURE) from error


def refresh_native_manifest(candidate: Path) -> NativeArtifactManifest:
    """Rebind the native manifest after signing changes nested artifact bytes."""
    manifest_path = candidate / NATIVE_MANIFEST_NAME
    original_payload: bytes | None = None
    try:
        root = candidate.resolve(strict=True)
        if candidate.is_symlink() or not candidate.is_dir():
            raise ReleaseCandidateError(_FAILURE)
        original_payload = manifest_path.read_bytes()
        if len(original_payload) > 8 * 1024:
            raise ReleaseCandidateError(_FAILURE)
        prior = NativeArtifactManifest.from_dict(json.loads(original_payload))
        if prior.candidate_id != root.name:
            raise ReleaseCandidateError(_FAILURE)
        manifest_path.unlink()
        refreshed = NativeArtifactManifest.create(
            root,
            candidate_id=prior.candidate_id,
            version=prior.version,
            platform_tag=prior.platform_tag,
        )
        refreshed.write(root)
        return refreshed
    except ReleaseCandidateError:
        _restore_manifest(manifest_path, original_payload)
        raise
    except (NativeArtifactError, OSError, UnicodeError, json.JSONDecodeError) as error:
        _restore_manifest(manifest_path, original_payload)
        raise ReleaseCandidateError(_FAILURE) from error


def stage_native_media(
    candidate: Path,
    destination: Path,
    *,
    repository_root: Path,
    third_party_licenses: Mapping[str, Path],
) -> Path:
    """Create the common artifact-only payload used by DMG and tar media."""
    try:
        source = candidate.resolve(strict=True)
        root = repository_root.resolve(strict=True)
        selected_destination = destination.resolve()
        if (
            candidate.is_symlink()
            or not candidate.is_dir()
            or source.name != _CANDIDATE_ID
            or destination.exists()
            or destination.is_symlink()
            or set(third_party_licenses) != _THIRD_PARTY_LICENSES
        ):
            raise ReleaseCandidateError(_FAILURE)
        source_audit = audit_native_artifact(source)
        selected_destination.mkdir(parents=True)
        copied_candidate = selected_destination / _CANDIDATE_ID
        shutil.copytree(source, copied_candidate, symlinks=True)
        for name in ("LICENSE", "NOTICE"):
            source_file = root / name
            _regular_file(source_file)
            shutil.copy2(source_file, selected_destination / name, follow_symlinks=False)
        installer = root / "release/native/install.sh"
        _regular_file(installer)
        shutil.copy2(installer, selected_destination / "install.sh", follow_symlinks=False)
        (selected_destination / "install.sh").chmod(0o755)
        licenses = selected_destination / "licenses"
        licenses.mkdir(mode=0o755)
        for name, path in sorted(third_party_licenses.items()):
            if PurePosixPath(name).name != name:
                raise ReleaseCandidateError(_FAILURE)
            _regular_file(path)
            shutil.copy2(path, licenses / name, follow_symlinks=False)
        copied_audit = audit_native_artifact(copied_candidate)
        if (
            copied_audit.tree_sha256 != source_audit.tree_sha256
            or copied_audit.membership_sha256 != source_audit.membership_sha256
        ):
            raise ReleaseCandidateError(_FAILURE)
        return selected_destination
    except ReleaseCandidateError:
        _remove_created_tree(destination)
        raise
    except (NativeBuildError, OSError, ValueError) as error:
        _remove_created_tree(destination)
        raise ReleaseCandidateError(_FAILURE) from error


def create_macos_dmg(
    payload: Path,
    destination: Path,
    *,
    identity: str,
    runner: CommandRunner | None = None,
) -> dict[str, object]:
    """Create and Developer ID-sign a DMG without returning identity metadata."""
    selected_runner = _run_bounded if runner is None else runner
    temporary: Path | None = None
    try:
        source = payload.resolve(strict=True)
        if payload.is_symlink() or not payload.is_dir():
            raise ReleaseCandidateError(_FAILURE)
        _private_selector(identity)
        output = destination.resolve()
        if output.suffix.casefold() != ".dmg" or output.is_relative_to(source):
            raise ReleaseCandidateError(_FAILURE)
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_name(f".{output.stem}.unsigned.dmg")
        if output.exists() or output.is_symlink() or temporary.exists() or temporary.is_symlink():
            raise ReleaseCandidateError(_FAILURE)
        _require_ok(
            selected_runner(
                (
                    "hdiutil",
                    "create",
                    "-fs",
                    "HFS+",
                    "-format",
                    "UDZO",
                    "-volname",
                    "Open Brain 0.1.0",
                    "-srcfolder",
                    str(source),
                    str(temporary),
                ),
                timeout=900,
            )
        )
        _regular_file(temporary)
        _require_ok(
            selected_runner(
                (
                    "codesign",
                    "--force",
                    "--timestamp",
                    "--sign",
                    identity,
                    str(temporary),
                ),
                timeout=300,
            )
        )
        _require_ok(
            selected_runner(
                ("codesign", "--verify", "--strict", str(temporary)),
                timeout=120,
            )
        )
        temporary.replace(output)
        return {"sha256": file_sha256(output), "signed": True, "status": "built"}
    except ReleaseCandidateError:
        raise
    except Exception as error:
        raise ReleaseCandidateError(_FAILURE) from error
    finally:
        if temporary is not None:
            with suppress(OSError):
                temporary.unlink(missing_ok=True)


def write_license_evidence(
    destination: Path,
    *,
    source_sha: str,
    root: Path,
    bindings: Sequence[LicenseBinding],
) -> dict[str, object]:
    try:
        selected_root = root.resolve(strict=True)
        if _SOURCE_SHA.fullmatch(source_sha) is None or not bindings:
            raise ReleaseCandidateError(_FAILURE)
        records: list[dict[str, object]] = []
        names: set[str] = set()
        for binding in sorted(bindings, key=lambda item: item.name):
            if not isinstance(binding, LicenseBinding) or binding.name in names:
                raise ReleaseCandidateError(_FAILURE)
            names.add(binding.name)
            selected = binding.path.resolve(strict=True)
            _regular_file(binding.path)
            relative = selected.relative_to(selected_root).as_posix()
            if not _safe_relative(relative):
                raise ReleaseCandidateError(_FAILURE)
            records.append(
                {
                    "license_expression": binding.license_expression,
                    "name": binding.name,
                    "path": relative,
                    "sha256": file_sha256(selected),
                }
            )
        evidence: dict[str, object] = {
            "components": records,
            "schema_version": 1,
            "source_sha": source_sha,
            "status": "passed",
        }
        _write_json(destination, evidence)
        return evidence
    except ReleaseCandidateError:
        raise
    except (OSError, ValueError) as error:
        raise ReleaseCandidateError(_FAILURE) from error


def write_spdx_sbom(
    destination: Path,
    *,
    source_sha: str,
    version: str,
    created_at: str,
    artifacts: Sequence[ReleaseArtifact],
    license_evidence: ReleaseArtifact,
) -> dict[str, object]:
    try:
        if (
            _SOURCE_SHA.fullmatch(source_sha) is None
            or version != _VERSION
            or not artifacts
            or license_evidence.coordinate != "evidence.licenses"
        ):
            raise ReleaseCandidateError(_FAILURE)
        parsed_time = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        if (
            parsed_time.tzinfo is None
            or parsed_time.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ") != created_at
        ):
            raise ReleaseCandidateError(_FAILURE)
        all_artifacts = (*artifacts, license_evidence)
        coordinates = tuple(artifact.coordinate for artifact in all_artifacts)
        if len(set(coordinates)) != len(coordinates):
            raise ReleaseCandidateError(_FAILURE)
        files = [
            {
                "SPDXID": _spdx_file_id(artifact.coordinate),
                "checksums": [{"algorithm": "SHA256", "checksumValue": artifact.sha256}],
                "copyrightText": "NOASSERTION",
                "fileName": artifact.path,
                "licenseConcluded": "NOASSERTION",
            }
            for artifact in all_artifacts
        ]
        sbom: dict[str, object] = {
            "SPDXID": "SPDXRef-DOCUMENT",
            "creationInfo": {
                "created": created_at,
                "creators": ["Tool: open-brain-p4w6-release-assembly"],
            },
            "dataLicense": "CC0-1.0",
            "documentNamespace": (
                f"https://open-brain.invalid/spdx/{source_sha}/open-brain-{version}"
            ),
            "files": files,
            "name": f"open-brain-{version}-unpublished-candidate",
            "packages": _spdx_packages(version),
            "relationships": [
                *(
                    {
                        "relatedSpdxElement": package,
                        "relationshipType": "DESCRIBES",
                        "spdxElementId": "SPDXRef-DOCUMENT",
                    }
                    for package in (
                        "SPDXRef-Package-open-brain",
                        "SPDXRef-Package-open-brain-engine",
                        "SPDXRef-Package-open-brain-connectors",
                    )
                ),
                *(
                    {
                        "relatedSpdxElement": _spdx_file_id(artifact.coordinate),
                        "relationshipType": "CONTAINS",
                        "spdxElementId": _spdx_package_id(artifact.coordinate),
                    }
                    for artifact in all_artifacts
                ),
            ],
            "spdxVersion": "SPDX-2.3",
        }
        _write_json(destination, sbom)
        return sbom
    except ReleaseCandidateError:
        raise
    except (OSError, ValueError) as error:
        raise ReleaseCandidateError(_FAILURE) from error


def write_macos14_unavailable_evidence(
    destination: Path,
    *,
    source_sha: str,
    macos_artifact_sha256: str,
) -> CleanHostEvidence:
    """Record the bounded exact-signed-candidate runner limitation."""
    evidence = CleanHostEvidence(
        host="macos-14",
        architecture="arm64",
        artifact_sha256=macos_artifact_sha256,
        source_sha=source_sha,
        setup_seconds=None,
        status="unavailable-runner",
        checks={},
        exact_signed_candidate=True,
        blocker_code="exact-signed-candidate-runner-unavailable",
    )
    _write_json(destination, evidence.to_dict())
    return evidence


def assemble_release_candidate(
    repository_root: Path,
    output_directory: Path,
    *,
    source_sha: str,
    python_directory: Path,
    linux_directory: Path,
    macos_directory: Path,
    clean_host_directory: Path,
) -> dict[str, object]:
    """Assemble and revalidate one exact, unpublished P4-W6 candidate."""
    staging: Path | None = None
    try:
        root = repository_root.resolve(strict=True)
        validate_exact_source_binding(root, source_sha)
        output = output_directory.resolve()
        if output.exists() or output.is_symlink():
            raise ReleaseCandidateError(_FAILURE)
        output.parent.mkdir(parents=True, exist_ok=True)
        staging = output.with_name(f".{output.name}.stage")
        if staging.exists() or staging.is_symlink():
            raise ReleaseCandidateError(_FAILURE)
        staging.mkdir(mode=0o755)

        python_root = _regular_directory(python_directory)
        linux_root = _regular_directory(linux_directory)
        macos_root = _regular_directory(macos_directory)
        clean_host_root = _regular_directory(clean_host_directory)
        artifacts: list[ReleaseArtifact] = []

        python_inputs = python_distribution_artifacts(python_root)
        copied_python: list[Path] = []
        for coordinate, source in sorted(python_inputs.items()):
            destination = staging / "artifacts/python" / source.name
            artifacts.append(_copy_release_artifact(coordinate, source, destination, staging))
            copied_python.append(destination)
        if verify_artifacts(root / "release/v0-artifact-policy.json", tuple(copied_python)):
            raise ReleaseCandidateError(_FAILURE)

        linux_media = linux_root / "artifacts/open-brain-0.1.0-linux-x86_64.tar.gz"
        linux_checksum = linux_media.with_name(linux_media.name + ".sha256")
        macos_media = macos_root / "artifacts/open-brain-0.1.0-macos-arm64.dmg"
        macos_checksum = macos_media.with_name(macos_media.name + ".sha256")
        _validate_checksum(linux_media, linux_checksum)
        _validate_checksum(macos_media, macos_checksum)
        copied_linux_media = staging / "artifacts/native" / linux_media.name
        copied_linux_checksum = staging / "artifacts/native" / linux_checksum.name
        copied_macos_media = staging / "artifacts/native" / macos_media.name
        copied_macos_checksum = staging / "artifacts/native" / macos_checksum.name
        artifacts.extend(
            (
                _copy_release_artifact(
                    "native.linux-x86_64", linux_media, copied_linux_media, staging
                ),
                _copy_release_artifact(
                    "checksums.linux-x86_64",
                    linux_checksum,
                    copied_linux_checksum,
                    staging,
                ),
                _copy_release_artifact(
                    "native.macos-arm64", macos_media, copied_macos_media, staging
                ),
                _copy_release_artifact(
                    "checksums.macos-arm64",
                    macos_checksum,
                    copied_macos_checksum,
                    staging,
                ),
            )
        )

        supervisor_sources = {
            "supervisor.launchd": (
                root / "packages/app/src/open_brain/resources/supervisors/launchd.json"
            ),
            "supervisor.systemd": (
                root / "packages/app/src/open_brain/resources/supervisors/systemd.service"
            ),
        }
        for coordinate, source in sorted(supervisor_sources.items()):
            artifacts.append(
                _copy_release_artifact(
                    coordinate,
                    source,
                    staging / "artifacts/supervisors" / source.name,
                    staging,
                )
            )

        license_sources = {
            "CPython-LICENSE.txt": (
                macos_root / "media-payload/licenses/CPython-LICENSE.txt"
            ),
            "LICENSE": root / "LICENSE",
            "NOTICE": root / "NOTICE",
            "PyInstaller-COPYING.txt": (
                macos_root / "media-payload/licenses/PyInstaller-COPYING.txt"
            ),
        }
        copied_licenses: dict[str, Path] = {}
        for name, source in sorted(license_sources.items()):
            destination = staging / "licenses" / name
            _copy_regular_file(source, destination)
            copied_licenses[name] = destination
        license_evidence_path = staging / "evidence/licenses.json"
        write_license_evidence(
            license_evidence_path,
            source_sha=source_sha,
            root=staging,
            bindings=(
                LicenseBinding(
                    "cpython-runtime",
                    "PSF-2.0",
                    copied_licenses["CPython-LICENSE.txt"],
                ),
                LicenseBinding("open-brain", "Apache-2.0", copied_licenses["LICENSE"]),
                LicenseBinding("open-brain-notice", "Apache-2.0", copied_licenses["NOTICE"]),
                LicenseBinding(
                    "pyinstaller-bootloader",
                    "GPL-2.0-or-later WITH Bootloader-exception",
                    copied_licenses["PyInstaller-COPYING.txt"],
                ),
            ),
        )
        license_artifact = ReleaseArtifact.from_path(
            coordinate="evidence.licenses",
            path=license_evidence_path,
            relative_to=staging,
        )
        artifacts.append(license_artifact)

        notarization_path = macos_root / "evidence/notarization.json"
        notarization = NotarizationEvidence.from_dict(_read_json(notarization_path))
        copied_notarization = staging / "evidence/notarization/macos-arm64.json"
        artifacts.append(
            _copy_release_artifact(
                "evidence.notarization.macos-arm64",
                notarization_path,
                copied_notarization,
                staging,
            )
        )

        linux_build_evidence = linux_root / "native-build/build-evidence.json"
        macos_build_evidence = macos_root / "native-build/build-evidence.json"
        _validate_native_build_evidence(
            linux_build_evidence,
            source_sha=source_sha,
            platform="linux-x86_64",
            media_sha256=file_sha256(linux_media),
            checksum_sha256=file_sha256(linux_checksum),
            notarization=None,
        )
        _validate_native_build_evidence(
            macos_build_evidence,
            source_sha=source_sha,
            platform="macos-arm64",
            media_sha256=file_sha256(macos_media),
            checksum_sha256=file_sha256(macos_checksum),
            notarization=notarization,
        )
        artifacts.extend(
            (
                _copy_release_artifact(
                    "evidence.native-build.linux-x86_64",
                    linux_build_evidence,
                    staging / "evidence/native-build/linux-x86_64.json",
                    staging,
                ),
                _copy_release_artifact(
                    "evidence.native-build.macos-arm64",
                    macos_build_evidence,
                    staging / "evidence/native-build/macos-arm64.json",
                    staging,
                ),
            )
        )

        clean_host_inputs = {
            "evidence.clean-host.debian-13": "debian-13.json",
            "evidence.clean-host.macos-14-source-equivalent": (
                "macos-14-source-equivalent.json"
            ),
            "evidence.clean-host.macos-signed": "macos-signed.json",
            "evidence.clean-host.ubuntu-24.04": "ubuntu-24.04.json",
            "evidence.clean-host.ubuntu-26.04": "ubuntu-26.04.json",
        }
        _require_exact_directory_members(clean_host_root, set(clean_host_inputs.values()))
        clean_hosts: list[CleanHostEvidence] = []
        for coordinate, name in sorted(clean_host_inputs.items()):
            source = clean_host_root / name
            evidence = CleanHostEvidence.from_dict(_read_json(source))
            _validate_clean_host_role(name, evidence)
            clean_hosts.append(evidence)
            artifacts.append(
                _copy_release_artifact(
                    coordinate,
                    source,
                    staging / "evidence/clean-host" / name,
                    staging,
                )
            )
        unavailable_path = staging / "evidence/clean-host/macos-14-unavailable.json"
        unavailable = write_macos14_unavailable_evidence(
            unavailable_path,
            source_sha=source_sha,
            macos_artifact_sha256=file_sha256(macos_media),
        )
        clean_hosts.append(unavailable)
        artifacts.append(
            ReleaseArtifact.from_path(
                coordinate="evidence.clean-host.macos-14-unavailable",
                path=unavailable_path,
                relative_to=staging,
            )
        )

        created_at = datetime.fromtimestamp(
            int(_source_date_epoch(root, source_sha)), tz=UTC
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
        sbom_path = staging / "artifacts/open-brain-0.1.0.spdx.json"
        write_spdx_sbom(
            sbom_path,
            source_sha=source_sha,
            version=_VERSION,
            created_at=created_at,
            artifacts=tuple(
                artifact for artifact in artifacts if artifact.coordinate != "evidence.licenses"
            ),
            license_evidence=license_artifact,
        )
        artifacts.append(
            ReleaseArtifact.from_path(
                coordinate="sbom.spdx",
                path=sbom_path,
                relative_to=staging,
            )
        )
        if {artifact.coordinate for artifact in artifacts} != set(
            EXPECTED_RELEASE_ARTIFACT_COORDINATES
        ):
            raise ReleaseCandidateError(_FAILURE)
        manifest = build_release_manifest(
            source_sha=source_sha,
            version=_VERSION,
            artifacts=tuple(artifacts),
            clean_hosts=tuple(clean_hosts),
            notarization=notarization,
            supported_hosts={
                "linux-x86_64": ["ubuntu-24.04", "ubuntu-26.04", "debian-13"],
                "macos-arm64": ">=14",
            },
            portable_schema={"maximum": 1, "minimum": 1},
        )
        _write_json(staging / "release-candidate.json", manifest)
        validate_release_candidate_directory(staging)
        validate_exact_source_binding(root, source_sha)
        staging.replace(output)
        staging = None
        return manifest
    except ReleaseCandidateError:
        raise
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise ReleaseCandidateError(_FAILURE) from error
    finally:
        if staging is not None:
            _remove_created_tree(staging)


def validate_release_candidate_directory(directory: Path) -> dict[str, object]:
    """Rehash a completed candidate and validate every transitive evidence binding."""
    try:
        root = _regular_directory(directory)
        manifest = _read_json(root / "release-candidate.json")
        validate_release_manifest(manifest)
        raw_artifacts = manifest.get("artifacts")
        if not isinstance(raw_artifacts, list):
            raise ReleaseCandidateError(_FAILURE)
        artifacts = tuple(ReleaseArtifact.from_dict(item) for item in raw_artifacts)
        by_coordinate = {artifact.coordinate: artifact for artifact in artifacts}
        for artifact in artifacts:
            actual = ReleaseArtifact.from_path(
                coordinate=artifact.coordinate,
                path=root / artifact.path,
                relative_to=root,
            )
            if actual != artifact:
                raise ReleaseCandidateError(_FAILURE)

        linux_media = _artifact_path(root, by_coordinate, "native.linux-x86_64")
        linux_checksum = _artifact_path(root, by_coordinate, "checksums.linux-x86_64")
        macos_media = _artifact_path(root, by_coordinate, "native.macos-arm64")
        macos_checksum = _artifact_path(root, by_coordinate, "checksums.macos-arm64")
        _validate_checksum(linux_media, linux_checksum)
        _validate_checksum(macos_media, macos_checksum)

        notarization = NotarizationEvidence.from_dict(
            _read_json(
                _artifact_path(
                    root,
                    by_coordinate,
                    "evidence.notarization.macos-arm64",
                )
            )
        )
        if manifest.get("notarization") != notarization.to_dict():
            raise ReleaseCandidateError(_FAILURE)
        source = manifest.get("source")
        if not isinstance(source, dict) or not isinstance(source.get("git_sha"), str):
            raise ReleaseCandidateError(_FAILURE)
        source_sha = cast(str, source["git_sha"])
        _validate_native_build_evidence(
            _artifact_path(
                root,
                by_coordinate,
                "evidence.native-build.linux-x86_64",
            ),
            source_sha=source_sha,
            platform="linux-x86_64",
            media_sha256=file_sha256(linux_media),
            checksum_sha256=file_sha256(linux_checksum),
            notarization=None,
        )
        _validate_native_build_evidence(
            _artifact_path(
                root,
                by_coordinate,
                "evidence.native-build.macos-arm64",
            ),
            source_sha=source_sha,
            platform="macos-arm64",
            media_sha256=file_sha256(macos_media),
            checksum_sha256=file_sha256(macos_checksum),
            notarization=notarization,
        )
        license_files = _validate_license_evidence(
            root,
            _artifact_path(root, by_coordinate, "evidence.licenses"),
            source_sha=source_sha,
        )
        _validate_spdx(
            _artifact_path(root, by_coordinate, "sbom.spdx"),
            artifacts=artifacts,
        )
        clean_host_coordinates = tuple(
            coordinate
            for coordinate in EXPECTED_RELEASE_ARTIFACT_COORDINATES
            if coordinate.startswith("evidence.clean-host.")
        )
        clean_hosts = tuple(
            CleanHostEvidence.from_dict(
                _read_json(_artifact_path(root, by_coordinate, coordinate))
            )
            for coordinate in clean_host_coordinates
        )
        expected_hosts = sorted(
            (evidence.to_dict() for evidence in clean_hosts),
            key=lambda item: (cast(str, item["host"]), cast(bool, item["exact_signed_candidate"])),
        )
        if manifest.get("clean_hosts") != expected_hosts:
            raise ReleaseCandidateError(_FAILURE)
        expected_files = {
            "release-candidate.json",
            *(artifact.path for artifact in artifacts),
            *license_files,
        }
        if _candidate_files(root) != expected_files:
            raise ReleaseCandidateError(_FAILURE)
        return manifest
    except ReleaseCandidateError:
        raise
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise ReleaseCandidateError(_FAILURE) from error


def build_python_distributions(
    repository_root: Path,
    output_directory: Path,
    *,
    source_sha: str,
) -> dict[str, Path]:
    """Build the six public wheel/sdist files from one immutable Git tree."""
    staging: Path | None = None
    try:
        root = repository_root.resolve(strict=True)
        validate_exact_source_binding(root, source_sha)
        output = output_directory.resolve()
        if output.exists() or output.is_symlink():
            raise ReleaseCandidateError(_FAILURE)
        output.parent.mkdir(parents=True, exist_ok=True)
        staging = output.with_name(f".{output.name}.stage")
        if staging.exists() or staging.is_symlink():
            raise ReleaseCandidateError(_FAILURE)
        staging.mkdir()
        with tempfile.TemporaryDirectory(prefix="ob-p4w6-python-", dir="/tmp") as raw:
            source_root = Path(raw).resolve() / "source"
            source_tree_sha256 = materialize_exact_source_tree(
                root,
                source_sha,
                source_root,
            )
            source_date_epoch = _source_date_epoch(root, source_sha)
            environment = _build_environment(source_date_epoch)
            for project in ("packages/engine", "packages/app", "packages/connectors"):
                _require_ok(
                    _run_build(
                        (
                            "uv",
                            "build",
                            "--no-sources",
                            "--project",
                            project,
                            "--out-dir",
                            str(staging),
                        ),
                        cwd=source_root,
                        environment=environment,
                        timeout=600,
                    )
                )
            if exact_source_tree_sha256(source_root) != source_tree_sha256:
                raise ReleaseCandidateError(_FAILURE)
            inventory = python_distribution_artifacts(staging)
            findings = verify_artifacts(
                source_root / "release/v0-artifact-policy.json",
                tuple(inventory.values()),
            )
            if findings:
                raise ReleaseCandidateError(_FAILURE)
        validate_exact_source_binding(root, source_sha)
        staging.replace(output)
        staging = None
        return python_distribution_artifacts(output)
    except ReleaseCandidateError:
        raise
    except (NativeBuildError, OSError, subprocess.SubprocessError) as error:
        raise ReleaseCandidateError(_FAILURE) from error
    finally:
        if staging is not None:
            with suppress(OSError):
                shutil.rmtree(staging)


def build_linux_release_media(
    repository_root: Path,
    output_directory: Path,
    *,
    source_sha: str,
) -> dict[str, object]:
    """Build, smoke, and package one exact-source Linux x86_64 tarball."""
    try:
        root, output = _release_output(repository_root, output_directory, source_sha)
        configuration = load_native_build_configuration(root)
        candidate, evidence_path, _members = build_native_artifact(
            configuration,
            output / "native-build",
            source_sha=source_sha,
            candidate_id=_CANDIDATE_ID,
            wave="P4-W6",
        )
        audit = audit_native_artifact(candidate, expected_platform="linux-x86_64")
        smoke_native_artifact(
            candidate,
            evidence_path=evidence_path,
            expected_wave="P4-W6",
        )
        payload = stage_native_media(
            candidate,
            output / "media-payload",
            repository_root=root,
            third_party_licenses=_build_license_paths(),
        )
        artifacts = output / "artifacts"
        artifacts.mkdir()
        archive = create_deterministic_tar_gz(
            payload,
            artifacts / "open-brain-0.1.0-linux-x86_64.tar.gz",
            archive_root="open-brain-0.1.0-linux-x86_64",
        )
        checksum = write_sha256_file(archive)
        bind_native_release_evidence(
            evidence_path,
            audit=audit,
            release={
                "archive_sha256": file_sha256(archive),
                "checksum_sha256": file_sha256(checksum),
                "format": "tar.gz",
                "status": "passed",
            },
            source_sha=source_sha,
        )
        return {
            "artifact": archive.name,
            "artifact_sha256": file_sha256(archive),
            "checksum": checksum.name,
            "platform": "linux-x86_64",
            "source_sha": source_sha,
            "status": "built",
        }
    except ReleaseCandidateError:
        raise
    except (NativeBuildError, OSError) as error:
        raise ReleaseCandidateError(_FAILURE) from error


def build_macos_compatibility_media(
    repository_root: Path,
    output_directory: Path,
    *,
    source_sha: str,
) -> dict[str, object]:
    """Build an unsigned source-equivalent tar solely for the macOS 14 runner."""
    try:
        root, output = _release_output(repository_root, output_directory, source_sha)
        configuration = load_native_build_configuration(root)
        candidate, evidence_path, _members = build_native_artifact(
            configuration,
            output / "native-build",
            source_sha=source_sha,
            candidate_id=_CANDIDATE_ID,
            wave="P4-W6",
        )
        audit = audit_native_artifact(candidate, expected_platform="macos-arm64")
        smoke_native_artifact(
            candidate,
            evidence_path=evidence_path,
            expected_wave="P4-W6",
        )
        payload = stage_native_media(
            candidate,
            output / "media-payload",
            repository_root=root,
            third_party_licenses=_build_license_paths(),
        )
        artifacts = output / "artifacts"
        artifacts.mkdir()
        archive = create_deterministic_tar_gz(
            payload,
            artifacts / "open-brain-0.1.0-macos-arm64-compatibility.tar.gz",
            archive_root="open-brain-0.1.0-macos-arm64-compatibility",
        )
        checksum = write_sha256_file(archive)
        bind_native_release_evidence(
            evidence_path,
            audit=audit,
            release={
                "archive_sha256": file_sha256(archive),
                "checksum_sha256": file_sha256(checksum),
                "format": "tar.gz-compatibility-only",
                "signed": False,
                "status": "passed",
            },
            source_sha=source_sha,
        )
        return {
            "artifact": archive.name,
            "artifact_sha256": file_sha256(archive),
            "checksum": checksum.name,
            "platform": "macos-arm64",
            "source_sha": source_sha,
            "status": "built-compatibility-only",
        }
    except ReleaseCandidateError:
        raise
    except (NativeBuildError, OSError) as error:
        raise ReleaseCandidateError(_FAILURE) from error


def build_macos_release_media(
    repository_root: Path,
    output_directory: Path,
    *,
    source_sha: str,
    keychain_profile: str,
    runner: CommandRunner | None = None,
) -> dict[str, object]:
    """Build, sign, notarize, staple, and smoke one macOS ARM64 DMG."""
    selected_runner = _run_bounded if runner is None else runner
    try:
        root, output = _release_output(repository_root, output_directory, source_sha)
        identity = discover_developer_id_identity(runner=selected_runner)
        configuration = load_native_build_configuration(root)
        candidate, evidence_path, _members = build_native_artifact(
            configuration,
            output / "native-build",
            source_sha=source_sha,
            candidate_id=_CANDIDATE_ID,
            wave="P4-W6",
        )
        signing = sign_macos_candidate(
            candidate,
            identity=identity,
            runner=selected_runner,
        )
        refresh_native_manifest(candidate)
        audit = audit_native_artifact(candidate, expected_platform="macos-arm64")
        bind_native_release_evidence(
            evidence_path,
            audit=audit,
            release=signing,
            source_sha=source_sha,
        )
        smoke_native_artifact(
            candidate,
            evidence_path=evidence_path,
            expected_wave="P4-W6",
        )
        payload = stage_native_media(
            candidate,
            output / "media-payload",
            repository_root=root,
            third_party_licenses=_build_license_paths(),
        )
        artifacts = output / "artifacts"
        artifacts.mkdir()
        dmg = artifacts / "open-brain-0.1.0-macos-arm64.dmg"
        create_macos_dmg(
            payload,
            dmg,
            identity=identity,
            runner=selected_runner,
        )
        notarization = notarize_macos_dmg(
            dmg,
            keychain_profile=keychain_profile,
            runner=selected_runner,
        )
        _assess_notarized_dmg(dmg, runner=selected_runner)
        checksum = write_sha256_file(dmg)
        evidence_directory = output / "evidence"
        evidence_directory.mkdir()
        _write_json(evidence_directory / "notarization.json", notarization.to_dict())
        release = {
            **signing,
            "dmg_sha256": file_sha256(dmg),
            "checksum_sha256": file_sha256(checksum),
            "format": "dmg",
            "notarization": notarization.to_dict(),
            "status": "passed",
        }
        bind_native_release_evidence(
            evidence_path,
            audit=audit,
            release=release,
            source_sha=source_sha,
        )
        return {
            "artifact": dmg.name,
            "artifact_sha256": file_sha256(dmg),
            "checksum": checksum.name,
            "notarization": notarization.to_dict(),
            "platform": "macos-arm64",
            "source_sha": source_sha,
            "status": "built",
        }
    except ReleaseCandidateError:
        raise
    except (NativeBuildError, OSError) as error:
        raise ReleaseCandidateError(_FAILURE) from error


def _release_output(
    repository_root: Path,
    output_directory: Path,
    source_sha: str,
) -> tuple[Path, Path]:
    root = repository_root.resolve(strict=True)
    validate_exact_source_binding(root, source_sha)
    output = output_directory.resolve()
    if output.exists() or output.is_symlink():
        raise ReleaseCandidateError(_FAILURE)
    output.mkdir(parents=True)
    return root, output


def _source_date_epoch(root: Path, source_sha: str) -> str:
    result = subprocess.run(
        ("git", "show", "-s", "--format=%ct", source_sha),
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    _require_ok(result)
    value = result.stdout.strip()
    if not value.isascii() or not value.isdigit() or int(value) <= 0:
        raise ReleaseCandidateError(_FAILURE)
    return value


def _build_environment(source_date_epoch: str) -> dict[str, str]:
    environment = dict(os.environ)
    for key in ("PYTHONHOME", "PYTHONPATH", "UV_PROJECT_ENVIRONMENT"):
        environment.pop(key, None)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONNOUSERSITE"] = "1"
    environment["SOURCE_DATE_EPOCH"] = source_date_epoch
    return environment


def _run_build(
    command: tuple[str, ...],
    *,
    cwd: Path,
    environment: Mapping[str, str],
    timeout: int,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        env=dict(environment),
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _build_license_paths() -> dict[str, Path]:
    try:
        if sys.version_info[:2] != (3, 12):
            raise ReleaseCandidateError(_FAILURE)
        python_license = (
            Path(sys.base_prefix)
            / f"lib/python{sys.version_info.major}.{sys.version_info.minor}/LICENSE.txt"
        )
        distribution = importlib.metadata.distribution("pyinstaller")
        if distribution.version != "6.22.2" or distribution.files is None:
            raise ReleaseCandidateError(_FAILURE)
        matches = tuple(
            distribution.locate_file(path)
            for path in distribution.files
            if str(path).endswith(".dist-info/licenses/COPYING.txt")
        )
        if len(matches) != 1:
            raise ReleaseCandidateError(_FAILURE)
        _regular_file(python_license)
        pyinstaller_license = Path(str(matches[0]))
        _regular_file(pyinstaller_license)
        return {
            "CPython-LICENSE.txt": python_license,
            "PyInstaller-COPYING.txt": pyinstaller_license,
        }
    except ReleaseCandidateError:
        raise
    except (ImportError, OSError, importlib.metadata.PackageNotFoundError) as error:
        raise ReleaseCandidateError(_FAILURE) from error


def _assess_notarized_dmg(dmg: Path, *, runner: CommandRunner) -> None:
    _require_ok(
        runner(
            (
                "spctl",
                "--assess",
                "--type",
                "open",
                "--context",
                "context:primary-signature",
                str(dmg.resolve(strict=True)),
            ),
            timeout=120,
        )
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m tools.phase4.release_assembly")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in (
        "build-python",
        "build-linux",
        "build-macos-compatibility",
        "build-macos",
    ):
        command = commands.add_parser(name)
        command.add_argument("--root", type=Path, required=True)
        command.add_argument("--output", type=Path, required=True)
        command.add_argument("--source-sha", required=True)
    assemble = commands.add_parser("assemble")
    assemble.add_argument("--root", type=Path, required=True)
    assemble.add_argument("--output", type=Path, required=True)
    assemble.add_argument("--source-sha", required=True)
    assemble.add_argument("--python-directory", type=Path, required=True)
    assemble.add_argument("--linux-directory", type=Path, required=True)
    assemble.add_argument("--macos-directory", type=Path, required=True)
    assemble.add_argument("--clean-host-directory", type=Path, required=True)
    verify = commands.add_parser("verify")
    verify.add_argument("--candidate", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    namespace = _parser().parse_args(argv)
    try:
        if namespace.command == "build-python":
            artifacts = build_python_distributions(
                namespace.root,
                namespace.output,
                source_sha=namespace.source_sha,
            )
            result: Mapping[str, object] = {
                "artifacts": {
                    coordinate: {
                        "name": path.name,
                        "sha256": file_sha256(path),
                    }
                    for coordinate, path in artifacts.items()
                },
                "source_sha": namespace.source_sha,
                "status": "built",
            }
        elif namespace.command == "build-linux":
            result = build_linux_release_media(
                namespace.root,
                namespace.output,
                source_sha=namespace.source_sha,
            )
        elif namespace.command == "build-macos-compatibility":
            result = build_macos_compatibility_media(
                namespace.root,
                namespace.output,
                source_sha=namespace.source_sha,
            )
        elif namespace.command == "build-macos":
            profile = os.environ.get("OPEN_BRAIN_NOTARY_PROFILE")
            if profile is None:
                raise ReleaseCandidateError(_FAILURE)
            result = build_macos_release_media(
                namespace.root,
                namespace.output,
                source_sha=namespace.source_sha,
                keychain_profile=profile,
            )
        elif namespace.command == "assemble":
            manifest = assemble_release_candidate(
                namespace.root,
                namespace.output,
                source_sha=namespace.source_sha,
                python_directory=namespace.python_directory,
                linux_directory=namespace.linux_directory,
                macos_directory=namespace.macos_directory,
                clean_host_directory=namespace.clean_host_directory,
            )
            result = {
                "artifact_count": len(cast(list[object], manifest["artifacts"])),
                "source_sha": namespace.source_sha,
                "status": "assembled",
            }
        else:
            manifest = validate_release_candidate_directory(namespace.candidate)
            source = cast(dict[str, object], manifest["source"])
            result = {
                "artifact_count": len(cast(list[object], manifest["artifacts"])),
                "source_sha": source["git_sha"],
                "status": "valid",
            }
        exit_code = 0
    except ReleaseCandidateError:
        result = {"status": "failed"}
        exit_code = 1
    print(json.dumps(dict(result), sort_keys=True, separators=(",", ":")))
    return exit_code


def _spdx_packages(version: str) -> list[dict[str, object]]:
    return [
        {
            "SPDXID": "SPDXRef-Package-open-brain",
            "copyrightText": "NOASSERTION",
            "downloadLocation": "NOASSERTION",
            "filesAnalyzed": False,
            "licenseConcluded": "Apache-2.0",
            "licenseDeclared": "Apache-2.0",
            "name": "open-brain",
            "versionInfo": version,
        },
        {
            "SPDXID": "SPDXRef-Package-open-brain-engine",
            "copyrightText": "NOASSERTION",
            "downloadLocation": "NOASSERTION",
            "filesAnalyzed": False,
            "licenseConcluded": "Apache-2.0",
            "licenseDeclared": "Apache-2.0",
            "name": "open-brain-engine",
            "versionInfo": version,
        },
        {
            "SPDXID": "SPDXRef-Package-open-brain-connectors",
            "copyrightText": "NOASSERTION",
            "downloadLocation": "NOASSERTION",
            "filesAnalyzed": False,
            "licenseConcluded": "Apache-2.0",
            "licenseDeclared": "Apache-2.0",
            "name": "open-brain-connectors",
            "versionInfo": version,
        },
    ]


def _spdx_file_id(coordinate: str) -> str:
    normalized = coordinate.replace(".", "-").replace("_", "-")
    if not normalized or any(
        not (character.isalnum() or character in ".-") for character in normalized
    ):
        raise ReleaseCandidateError(_FAILURE)
    return f"SPDXRef-File-{normalized}"


def _spdx_package_id(coordinate: str) -> str:
    if coordinate.startswith("python.engine."):
        return "SPDXRef-Package-open-brain-engine"
    if coordinate.startswith("python.connectors."):
        return "SPDXRef-Package-open-brain-connectors"
    return "SPDXRef-Package-open-brain"


def _copy_release_artifact(
    coordinate: str,
    source: Path,
    destination: Path,
    root: Path,
) -> ReleaseArtifact:
    _copy_regular_file(source, destination)
    return ReleaseArtifact.from_path(
        coordinate=coordinate,
        path=destination,
        relative_to=root,
    )


def _copy_regular_file(source: Path, destination: Path) -> None:
    _regular_file(source)
    if destination.exists() or destination.is_symlink():
        raise ReleaseCandidateError(_FAILURE)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination, follow_symlinks=False)
    _regular_file(destination)


def _regular_directory(path: Path) -> Path:
    try:
        metadata = path.lstat()
        selected = path.resolve(strict=True)
        if not stat.S_ISDIR(metadata.st_mode) or path.is_symlink():
            raise ReleaseCandidateError(_FAILURE)
        return selected
    except ReleaseCandidateError:
        raise
    except OSError as error:
        raise ReleaseCandidateError(_FAILURE) from error


def _require_exact_directory_members(root: Path, expected: set[str]) -> None:
    try:
        entries = tuple(root.iterdir())
        if {path.name for path in entries} != expected:
            raise ReleaseCandidateError(_FAILURE)
        for path in entries:
            _regular_file(path)
    except ReleaseCandidateError:
        raise
    except OSError as error:
        raise ReleaseCandidateError(_FAILURE) from error


def _read_json(path: Path) -> dict[str, object]:
    try:
        _regular_file(path)
        if path.stat().st_size > 8 * 1024 * 1024:
            raise ReleaseCandidateError(_FAILURE)
        value = json.loads(path.read_bytes())
        if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
            raise ReleaseCandidateError(_FAILURE)
        result = cast(dict[str, object], value)
        _reject_sensitive_release_keys(result)
        return result
    except ReleaseCandidateError:
        raise
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as error:
        raise ReleaseCandidateError(_FAILURE) from error


def _validate_checksum(artifact: Path, checksum: Path) -> None:
    try:
        _regular_file(artifact)
        _regular_file(checksum)
        expected = f"{file_sha256(artifact)}  {artifact.name}\n".encode("ascii")
        if checksum.read_bytes() != expected:
            raise ReleaseCandidateError(_FAILURE)
    except ReleaseCandidateError:
        raise
    except (OSError, UnicodeError) as error:
        raise ReleaseCandidateError(_FAILURE) from error


def _validate_native_build_evidence(
    path: Path,
    *,
    source_sha: str,
    platform: str,
    media_sha256: str,
    checksum_sha256: str,
    notarization: NotarizationEvidence | None,
) -> None:
    evidence = _read_json(path)
    if set(evidence) != {
        "artifact",
        "build",
        "release",
        "runtime",
        "schema_version",
        "source_sha",
        "wave",
    }:
        raise ReleaseCandidateError(_FAILURE)
    artifact = evidence.get("artifact")
    build = evidence.get("build")
    release = evidence.get("release")
    runtime = evidence.get("runtime")
    if (
        evidence.get("schema_version") != 1
        or evidence.get("source_sha") != source_sha
        or evidence.get("wave") != "P4-W6"
        or not isinstance(artifact, dict)
        or set(artifact)
        != {
            "candidate_id",
            "member_count",
            "membership_sha256",
            "platform",
            "resource_members",
            "symlink_count",
            "tree_sha256",
            "version",
        }
        or artifact.get("candidate_id") != _CANDIDATE_ID
        or artifact.get("version") != _VERSION
        or artifact.get("platform") != platform
        or type(artifact.get("member_count")) is not int
        or cast(int, artifact["member_count"]) <= 0
        or type(artifact.get("symlink_count")) is not int
        or cast(int, artifact["symlink_count"]) < 0
        or not isinstance(artifact.get("resource_members"), list)
        or any(
            not isinstance(item, str)
            for item in cast(list[object], artifact["resource_members"])
        )
        or re.fullmatch(r"[0-9a-f]{64}", str(artifact.get("membership_sha256"))) is None
        or re.fullmatch(r"[0-9a-f]{64}", str(artifact.get("tree_sha256"))) is None
        or not isinstance(build, dict)
        or set(build)
        != {
            "hooks_version",
            "mode",
            "pyinstaller_version",
            "python_version",
            "source_tree_sha256",
            "spec_sha256",
        }
        or build.get("hooks_version") != "2026.7"
        or build.get("mode") != "onedir"
        or build.get("pyinstaller_version") != "6.22.2"
        or build.get("python_version") != "3.12"
        or re.fullmatch(r"[0-9a-f]{64}", str(build.get("source_tree_sha256"))) is None
        or re.fullmatch(r"[0-9a-f]{64}", str(build.get("spec_sha256"))) is None
        or not isinstance(runtime, dict)
        or runtime.get("status") != "passed"
        or runtime.get("source_checkout_required") is not False
        or runtime.get("system_python_required") is not False
        or not isinstance(release, dict)
        or release.get("status") != "passed"
        or release.get("checksum_sha256") != checksum_sha256
    ):
        raise ReleaseCandidateError(_FAILURE)
    if platform == "linux-x86_64":
        if release != {
            "archive_sha256": media_sha256,
            "checksum_sha256": checksum_sha256,
            "format": "tar.gz",
            "status": "passed",
        }:
            raise ReleaseCandidateError(_FAILURE)
    elif platform == "macos-arm64":
        if (
            notarization is None
            or set(release)
            != {
                "checksum_sha256",
                "dmg_sha256",
                "format",
                "hardened_runtime",
                "notarization",
                "secure_timestamp",
                "signed_code_count",
                "status",
            }
            or release.get("dmg_sha256") != media_sha256
            or release.get("format") != "dmg"
            or release.get("hardened_runtime") is not True
            or release.get("secure_timestamp") is not True
            or type(release.get("signed_code_count")) is not int
            or cast(int, release["signed_code_count"]) <= 0
            or release.get("notarization") != notarization.to_dict()
        ):
            raise ReleaseCandidateError(_FAILURE)
    else:
        raise ReleaseCandidateError(_FAILURE)


def _validate_clean_host_role(name: str, evidence: CleanHostEvidence) -> None:
    linux_names = {f"{host}.json": host for host in ("ubuntu-24.04", "ubuntu-26.04", "debian-13")}
    if name in linux_names:
        if (
            evidence.host != linux_names[name]
            or evidence.architecture != "x86_64"
            or evidence.status != "passed"
            or evidence.exact_signed_candidate
        ):
            raise ReleaseCandidateError(_FAILURE)
    elif name == "macos-signed.json":
        if (
            not evidence.host.startswith("macos-")
            or evidence.architecture != "arm64"
            or evidence.status != "passed"
            or not evidence.exact_signed_candidate
        ):
            raise ReleaseCandidateError(_FAILURE)
    elif name == "macos-14-source-equivalent.json":
        if (
            evidence.host != "macos-14"
            or evidence.architecture != "arm64"
            or evidence.status != "passed"
            or evidence.exact_signed_candidate
        ):
            raise ReleaseCandidateError(_FAILURE)
    else:
        raise ReleaseCandidateError(_FAILURE)


def _artifact_path(
    root: Path,
    artifacts: Mapping[str, ReleaseArtifact],
    coordinate: str,
) -> Path:
    artifact = artifacts.get(coordinate)
    if artifact is None:
        raise ReleaseCandidateError(_FAILURE)
    return root / artifact.path


def _validate_license_evidence(root: Path, path: Path, *, source_sha: str) -> set[str]:
    evidence = _read_json(path)
    components = evidence.get("components")
    if (
        set(evidence) != {"components", "schema_version", "source_sha", "status"}
        or evidence.get("schema_version") != 1
        or evidence.get("source_sha") != source_sha
        or evidence.get("status") != "passed"
        or not isinstance(components, list)
    ):
        raise ReleaseCandidateError(_FAILURE)
    names: set[str] = set()
    paths: set[str] = set()
    for component in components:
        if (
            not isinstance(component, dict)
            or set(component) != {"license_expression", "name", "path", "sha256"}
            or not isinstance(component.get("name"), str)
            or not isinstance(component.get("license_expression"), str)
            or not isinstance(component.get("path"), str)
            or not isinstance(component.get("sha256"), str)
            or cast(str, component["name"]) in names
            or not _safe_relative(cast(str, component["path"]))
            or cast(str, component["path"]) in paths
        ):
            raise ReleaseCandidateError(_FAILURE)
        names.add(cast(str, component["name"]))
        paths.add(cast(str, component["path"]))
        selected = root / cast(str, component["path"])
        if file_sha256(selected) != component["sha256"]:
            raise ReleaseCandidateError(_FAILURE)
    if names != {
        "cpython-runtime",
        "open-brain",
        "open-brain-notice",
        "pyinstaller-bootloader",
    }:
        raise ReleaseCandidateError(_FAILURE)
    return paths


def _candidate_files(root: Path) -> set[str]:
    try:
        files: set[str] = set()
        for path in root.rglob("*"):
            metadata = path.lstat()
            if stat.S_ISDIR(metadata.st_mode):
                continue
            if (
                not stat.S_ISREG(metadata.st_mode)
                or path.is_symlink()
                or metadata.st_nlink != 1
            ):
                raise ReleaseCandidateError(_FAILURE)
            files.add(path.relative_to(root).as_posix())
        return files
    except ReleaseCandidateError:
        raise
    except (OSError, ValueError) as error:
        raise ReleaseCandidateError(_FAILURE) from error


def _validate_spdx(path: Path, *, artifacts: Sequence[ReleaseArtifact]) -> None:
    sbom = _read_json(path)
    files = sbom.get("files")
    if sbom.get("spdxVersion") != "SPDX-2.3" or not isinstance(files, list):
        raise ReleaseCandidateError(_FAILURE)
    expected = {
        _spdx_file_id(artifact.coordinate): {
            "SPDXID": _spdx_file_id(artifact.coordinate),
            "checksums": [{"algorithm": "SHA256", "checksumValue": artifact.sha256}],
            "copyrightText": "NOASSERTION",
            "fileName": artifact.path,
            "licenseConcluded": "NOASSERTION",
        }
        for artifact in artifacts
        if artifact.coordinate != "sbom.spdx"
    }
    actual: dict[str, object] = {}
    for item in files:
        if not isinstance(item, dict) or not isinstance(item.get("SPDXID"), str):
            raise ReleaseCandidateError(_FAILURE)
        identifier = cast(str, item["SPDXID"])
        if identifier in actual:
            raise ReleaseCandidateError(_FAILURE)
        actual[identifier] = item
    if actual != expected:
        raise ReleaseCandidateError(_FAILURE)


def _write_json(path: Path, value: Mapping[str, object]) -> None:
    payload = (json.dumps(dict(value), indent=2, sort_keys=True) + "\n").encode("utf-8")
    if len(payload) > 8 * 1024 * 1024:
        raise ReleaseCandidateError(_FAILURE)
    output = path.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.tmp")
    if output.exists() or output.is_symlink() or temporary.exists() or temporary.is_symlink():
        raise ReleaseCandidateError(_FAILURE)
    try:
        with temporary.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(output)
    finally:
        with suppress(OSError):
            temporary.unlink(missing_ok=True)


def _replace_json(path: Path, value: Mapping[str, object]) -> None:
    payload = (json.dumps(dict(value), indent=2, sort_keys=True) + "\n").encode("utf-8")
    if len(payload) > _MAXIMUM_COMMAND_OUTPUT:
        raise ReleaseCandidateError(_FAILURE)
    output = path.resolve(strict=True)
    _regular_file(output)
    temporary = output.with_name(f".{output.name}.next")
    if temporary.exists() or temporary.is_symlink():
        raise ReleaseCandidateError(_FAILURE)
    try:
        with temporary.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(output)
    finally:
        with suppress(OSError):
            temporary.unlink(missing_ok=True)


def _reject_sensitive_release_keys(value: object) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str) or any(
                term in key.casefold() for term in _SENSITIVE_RELEASE_KEYS
            ):
                raise ReleaseCandidateError(_FAILURE)
            _reject_sensitive_release_keys(item)
    elif isinstance(value, list):
        for item in value:
            _reject_sensitive_release_keys(item)


def _restore_manifest(path: Path, payload: bytes | None) -> None:
    if payload is None or path.exists() or path.is_symlink():
        return
    with suppress(OSError):
        path.write_bytes(payload)


def _remove_created_tree(path: Path) -> None:
    with suppress(OSError):
        if path.exists() and not path.is_symlink():
            shutil.rmtree(path)


def _regular_file(path: Path) -> None:
    metadata = path.lstat()
    if not stat.S_ISREG(metadata.st_mode) or path.is_symlink():
        raise ReleaseCandidateError(_FAILURE)


def _safe_relative(value: str) -> bool:
    if not value or "\\" in value or "\x00" in value:
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and ".." not in path.parts and path.as_posix() == value


def _private_selector(value: str) -> None:
    if (
        not isinstance(value, str)
        or not value
        or value.isspace()
        or any(character in value for character in "\x00\r\n")
    ):
        raise ReleaseCandidateError(_FAILURE)


def _run_bounded(
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
        or len(result.stdout or "") > _MAXIMUM_COMMAND_OUTPUT
        or len(result.stderr or "") > _MAXIMUM_COMMAND_OUTPUT
    ):
        raise ReleaseCandidateError(_FAILURE)


if __name__ == "__main__":
    raise SystemExit(main())
