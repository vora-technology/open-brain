from __future__ import annotations

import json
import socket
import subprocess
import tempfile
import threading
from collections.abc import Iterator
from pathlib import Path
from typing import cast

import pytest

import tools.phase4.release_assembly as release_assembly
from open_brain.services.native_artifacts import NativeArtifactManifest, native_platform_tag
from tools.phase4.clean_host_fixture import create_clean_host_fixture
from tools.phase4.native_build import audit_native_artifact, native_resource_members
from tools.phase4.release_assembly import (
    LicenseBinding,
    assemble_release_candidate,
    bind_native_release_evidence,
    create_macos_dmg,
    discover_developer_id_identity,
    python_distribution_artifacts,
    refresh_native_manifest,
    stage_native_media,
    validate_release_candidate_directory,
    write_license_evidence,
    write_macos14_unavailable_evidence,
    write_spdx_sbom,
)
from tools.phase4.release_candidate import (
    EXPECTED_RELEASE_ARTIFACT_COORDINATES,
    CleanHostEvidence,
    NotarizationEvidence,
    ReleaseArtifact,
    ReleaseCandidateError,
    file_sha256,
)

ROOT = Path(__file__).resolve().parents[2]
SOURCE_SHA = "a" * 40
_ORIGINAL_SOCKET_BIND = socket.socket.bind
_ORIGINAL_SOCKET_LISTEN = socket.socket.listen


@pytest.fixture
def short_socket_root() -> Iterator[Path]:
    with tempfile.TemporaryDirectory(prefix="ob-p4w6-sock-", dir="/tmp") as raw:
        yield Path(raw).resolve()


def _native_candidate(path: Path) -> Path:
    path.mkdir(parents=True)
    executable = path / "open-brain"
    executable.write_bytes(b"synthetic native executable\n")
    executable.chmod(0o755)
    for relative in native_resource_members(ROOT):
        resource = path / relative
        resource.parent.mkdir(parents=True, exist_ok=True)
        resource.write_bytes(b"declared resource\n")
    NativeArtifactManifest.create(
        path,
        candidate_id="candidate_native-p4w6",
        version="0.1.0",
        platform_tag=native_platform_tag(),
    ).write(path)
    return path


def test_clean_host_fixture_has_six_pending_siblings_and_no_operational_state(
    tmp_path: Path,
) -> None:
    output = tmp_path / "fixture"

    evidence = create_clean_host_fixture(output)

    portable = output / "portable-root"
    runtime = output / "runtime-root"
    controller = output / "controller.json"
    control = json.loads(controller.read_text(encoding="utf-8"))
    assert evidence == {
        "capture_count": 1,
        "proposal_count": 6,
        "schema_version": 1,
        "status": "created",
    }
    assert controller.stat().st_mode & 0o777 == 0o600
    assert len(control["proposal_ids"]) == 6
    assert len(set(control["proposal_ids"])) == 6
    proposals = tuple((portable / "history/proposals").rglob("*.json"))
    assert len(proposals) == 6
    assert all(json.loads(path.read_bytes())["status"] == "pending" for path in proposals)
    assert not (portable / ".open-brain").exists()
    assert (portable / "portable-manifest.json").is_file()
    assert (runtime / ".open-brain/state/phase1.sqlite3").is_file()
    assert not (runtime / ".open-brain/state/appliance-owner-credential").exists()
    assert "seed" not in json.dumps(evidence).casefold()
    assert "credential" not in json.dumps(evidence).casefold()


def test_unix_request_helper_half_closes_and_returns_one_bounded_receipt(
    short_socket_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(socket.socket, "bind", _ORIGINAL_SOCKET_BIND)
    monkeypatch.setattr(socket.socket, "listen", _ORIGINAL_SOCKET_LISTEN)
    socket_path = short_socket_root / "control.sock"
    received: list[bytes] = []

    def serve() -> None:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
            listener.bind(str(socket_path))
            listener.listen(1)
            connection, _address = listener.accept()
            with connection:
                chunks: list[bytes] = []
                while chunk := connection.recv(1024):
                    chunks.append(chunk)
                received.append(b"".join(chunks))
                connection.sendall(b'{"status":"completed"}\n')

    thread = threading.Thread(target=serve)
    thread.start()
    for _attempt in range(100):
        if socket_path.exists():
            break
        thread.join(timeout=0.01)
    helper = ROOT / "tools/phase4/unix_request.pl"
    result = subprocess.run(
        (str(helper), str(socket_path)),
        input='{"action":"status.read"}\n',
        check=False,
        capture_output=True,
        text=True,
        timeout=5,
    )
    thread.join(timeout=5)

    assert not thread.is_alive()
    assert received == [b'{"action":"status.read"}']
    assert result.returncode == 0
    assert result.stdout == '{"status":"completed"}\n'
    assert result.stderr == ""


def test_clean_host_harness_uses_only_artifact_surfaces_and_covers_full_lifecycle() -> None:
    harness = (ROOT / "tools/phase4/clean_host_lifecycle.sh").read_text(encoding="utf-8")
    installer = (ROOT / "release/native/install.sh").read_text(encoding="utf-8")

    assert "python -m" not in harness.casefold()
    assert "uv run" not in harness.casefold()
    assert "packages/app" not in harness
    assert "source_checkout_required:false" in harness
    assert "system_python_required:false" in harness
    for contract in (
        "backup_disposable_restore_exact_bytes",
        "doctor",
        "portable_round_trip",
        "prior_schema_upgrade",
        "residue",
        "rollback",
        "uninstall",
        "v0_gate_07",
        "v0_gate_13",
    ):
        assert f'{contract}:"passed"' in harness
    assert "__native-self-check" in installer
    assert "python" not in installer.casefold()


def test_refresh_native_manifest_rebinds_post_signing_tree(tmp_path: Path) -> None:
    candidate = _native_candidate(tmp_path / "candidate_native-p4w6")
    original = NativeArtifactManifest.load(candidate)
    signature = candidate / "_internal/Python.framework/_CodeSignature/CodeResources"
    signature.parent.mkdir(parents=True)
    signature.write_bytes(b"synthetic code signature\n")

    refreshed = refresh_native_manifest(candidate)

    assert refreshed.candidate_id == original.candidate_id
    assert refreshed.platform_tag == original.platform_tag
    assert refreshed.tree_digest_sha256 != original.tree_digest_sha256
    assert NativeArtifactManifest.load(candidate) == refreshed
    assert audit_native_artifact(candidate).tree_sha256 == refreshed.tree_digest_sha256


def test_stage_native_media_binds_installer_notices_and_third_party_licenses(
    tmp_path: Path,
) -> None:
    candidate = _native_candidate(tmp_path / "candidate_native-p4w6")
    python_license = tmp_path / "Python-LICENSE.txt"
    pyinstaller_license = tmp_path / "PyInstaller-COPYING.txt"
    python_license.write_text("Python license\n", encoding="utf-8")
    pyinstaller_license.write_text("PyInstaller license\n", encoding="utf-8")
    output = tmp_path / "media"

    staged = stage_native_media(
        candidate,
        output,
        repository_root=ROOT,
        third_party_licenses={
            "CPython-LICENSE.txt": python_license,
            "PyInstaller-COPYING.txt": pyinstaller_license,
        },
    )

    assert staged == output.resolve()
    assert (staged / "install.sh").stat().st_mode & 0o111
    assert (staged / "LICENSE").read_bytes() == (ROOT / "LICENSE").read_bytes()
    assert (staged / "NOTICE").read_bytes() == (ROOT / "NOTICE").read_bytes()
    assert (staged / "licenses/CPython-LICENSE.txt").read_bytes() == b"Python license\n"
    copied = staged / "candidate_native-p4w6"
    assert NativeArtifactManifest.load(copied) == NativeArtifactManifest.load(candidate)


def test_macos_dmg_creation_signs_media_without_persisting_identity(tmp_path: Path) -> None:
    payload = tmp_path / "payload"
    payload.mkdir()
    (payload / "README.txt").write_text("payload\n", encoding="utf-8")
    destination = tmp_path / "open-brain-0.1.0-macos-arm64.dmg"
    identity = "private identity canary"
    calls: list[tuple[str, ...]] = []

    def runner(command: tuple[str, ...], *, timeout: int) -> subprocess.CompletedProcess[str]:
        assert timeout > 0
        calls.append(command)
        if command[0] == "hdiutil":
            Path(command[-1]).write_bytes(b"synthetic signed dmg")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    evidence = create_macos_dmg(
        payload,
        destination,
        identity=identity,
        runner=runner,
    )

    assert destination.is_file()
    assert evidence == {
        "sha256": file_sha256(destination),
        "signed": True,
        "status": "built",
    }
    assert calls[0][:2] == ("hdiutil", "create")
    assert "-srcfolder" in calls[0]
    assert calls[1][:3] == ("codesign", "--force", "--timestamp")
    assert calls[2][:3] == ("codesign", "--verify", "--strict")
    assert identity not in json.dumps(evidence)


def test_developer_id_discovery_requires_one_application_identity_without_exposing_subject() -> (
    None
):
    certificate_hash = "A" * 40

    def runner(command: tuple[str, ...], *, timeout: int) -> subprocess.CompletedProcess[str]:
        assert command == ("security", "find-identity", "-v", "-p", "codesigning")
        assert timeout == 30
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=(
                f'  1) {certificate_hash} "Developer ID Application: Private Subject"\n'
                "     1 valid identities found\n"
            ),
            stderr="",
        )

    assert discover_developer_id_identity(runner=runner) == certificate_hash

    def ambiguous(command: tuple[str, ...], *, timeout: int) -> subprocess.CompletedProcess[str]:
        del timeout
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=(
                f'1) {certificate_hash} "Developer ID Application: First"\n'
                f'2) {"B" * 40} "Developer ID Application: Second"\n'
            ),
            stderr="private subject canary",
        )

    with pytest.raises(ReleaseCandidateError) as raised:
        discover_developer_id_identity(runner=ambiguous)
    assert str(raised.value) == "release candidate operation failed"
    assert "subject" not in str(raised.value).casefold()


def test_python_distribution_inventory_requires_exact_six_coordinates(tmp_path: Path) -> None:
    names = {
        "python.app.wheel": "open_brain-0.1.0-py3-none-any.whl",
        "python.app.sdist": "open_brain-0.1.0.tar.gz",
        "python.connectors.wheel": "open_brain_connectors-0.1.0-py3-none-any.whl",
        "python.connectors.sdist": "open_brain_connectors-0.1.0.tar.gz",
        "python.engine.wheel": "open_brain_engine-0.1.0-py3-none-any.whl",
        "python.engine.sdist": "open_brain_engine-0.1.0.tar.gz",
    }
    for name in names.values():
        (tmp_path / name).write_bytes(name.encode())

    inventory = python_distribution_artifacts(tmp_path)

    assert {coordinate: path.name for coordinate, path in inventory.items()} == names
    (tmp_path / "unexpected.whl").write_bytes(b"unexpected")
    with pytest.raises(ReleaseCandidateError, match="release candidate operation failed"):
        python_distribution_artifacts(tmp_path)


def test_uv_build_ignore_cleanup_accepts_only_the_exact_generated_marker(tmp_path: Path) -> None:
    marker = tmp_path / ".gitignore"
    marker.write_bytes(b"*")

    release_assembly._remove_uv_build_ignore(tmp_path)

    assert not marker.exists()
    marker.write_bytes(b"*\n")
    with pytest.raises(ReleaseCandidateError, match="release candidate operation failed"):
        release_assembly._remove_uv_build_ignore(tmp_path)


def test_native_build_evidence_rebinds_signed_tree_without_private_metadata(
    tmp_path: Path,
) -> None:
    evidence_path = tmp_path / "build-evidence.json"
    evidence_path.write_text(
        json.dumps(
            {
                "artifact": {"tree_sha256": "0" * 64},
                "build": {"source_tree_sha256": "1" * 64},
                "runtime": None,
                "schema_version": 1,
                "source_sha": SOURCE_SHA,
                "wave": "P4-W6",
            }
        ),
        encoding="utf-8",
    )
    audit = audit_native_artifact(_native_candidate(tmp_path / "candidate_native-p4w6"))

    rebound = bind_native_release_evidence(
        evidence_path,
        audit=audit,
        release={
            "hardened_runtime": True,
            "secure_timestamp": True,
            "signed_code_count": 53,
            "status": "passed",
        },
        source_sha=SOURCE_SHA,
    )

    assert rebound["artifact"] == audit.to_dict()
    assert rebound["release"] == {
        "hardened_runtime": True,
        "secure_timestamp": True,
        "signed_code_count": 53,
        "status": "passed",
    }
    rendered = evidence_path.read_text(encoding="utf-8")
    assert "identity" not in rendered.casefold()
    assert "profile" not in rendered.casefold()


def test_spdx_and_license_evidence_bind_exact_relative_artifacts(tmp_path: Path) -> None:
    artifact_path = tmp_path / "artifacts/open-brain-0.1.0-linux-x86_64.tar.gz"
    artifact_path.parent.mkdir(parents=True)
    artifact_path.write_bytes(b"native archive\n")
    artifact = ReleaseArtifact.from_path(
        coordinate="native.linux-x86_64",
        path=artifact_path,
        relative_to=tmp_path,
    )
    license_path = tmp_path / "LICENSE"
    notice_path = tmp_path / "NOTICE"
    license_path.write_text("Apache license\n", encoding="utf-8")
    notice_path.write_text("Notice\n", encoding="utf-8")
    license_output = tmp_path / "evidence/licenses.json"

    license_evidence = write_license_evidence(
        license_output,
        source_sha=SOURCE_SHA,
        root=tmp_path,
        bindings=(
            LicenseBinding("open-brain", "Apache-2.0", license_path),
            LicenseBinding("open-brain-notice", "Apache-2.0", notice_path),
        ),
    )
    sbom_path = tmp_path / "artifacts/open-brain-0.1.0.spdx.json"
    sbom = write_spdx_sbom(
        sbom_path,
        source_sha=SOURCE_SHA,
        version="0.1.0",
        created_at="2026-09-02T12:00:00Z",
        artifacts=(artifact,),
        license_evidence=ReleaseArtifact.from_path(
            coordinate="evidence.licenses",
            path=license_output,
            relative_to=tmp_path,
        ),
    )

    assert license_evidence["source_sha"] == SOURCE_SHA
    license_rows = cast(list[dict[str, object]], license_evidence["components"])
    assert {row["name"] for row in license_rows} == {
        "open-brain",
        "open-brain-notice",
    }
    assert sbom["spdxVersion"] == "SPDX-2.3"
    assert sbom["dataLicense"] == "CC0-1.0"
    files = cast(list[dict[str, object]], sbom["files"])
    assert files == [
        {
            "SPDXID": "SPDXRef-File-native-linux-x86-64",
            "checksums": [{"algorithm": "SHA256", "checksumValue": artifact.sha256}],
            "copyrightText": "NOASSERTION",
            "fileName": artifact.path,
            "licenseConcluded": "NOASSERTION",
        },
        {
            "SPDXID": "SPDXRef-File-evidence-licenses",
            "checksums": [
                {
                    "algorithm": "SHA256",
                    "checksumValue": file_sha256(license_output),
                }
            ],
            "copyrightText": "NOASSERTION",
            "fileName": "evidence/licenses.json",
            "licenseConcluded": "NOASSERTION",
        },
    ]
    assert str(tmp_path) not in json.dumps(sbom, sort_keys=True)


def _passed_host(
    host: str,
    *,
    artifact_sha256: str,
    exact_signed_candidate: bool,
) -> CleanHostEvidence:
    return CleanHostEvidence(
        host=host,
        architecture="arm64" if host.startswith("macos-") else "x86_64",
        artifact_sha256=artifact_sha256,
        source_sha=SOURCE_SHA,
        setup_seconds=7.0,
        status="passed",
        checks={
            "artifact_install": "passed",
            "backup_disposable_restore_exact_bytes": "passed",
            "doctor": "passed",
            "portable_round_trip": "passed",
            "prior_schema_upgrade": "passed",
            "residue": "passed",
            "rollback": "passed",
            "source_checkout_required": False,
            "system_python_required": False,
            "uninstall": "passed",
            "v0_gate_07": "passed",
            "v0_gate_13": "passed",
        },
        exact_signed_candidate=exact_signed_candidate,
    )


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")


def _write_build_evidence(
    path: Path,
    *,
    platform: str,
    release: dict[str, object],
) -> None:
    _write_json(
        path,
        {
            "artifact": {
                "candidate_id": "candidate_native-p4w6",
                "member_count": 1,
                "membership_sha256": "b" * 64,
                "platform": platform,
                "resource_members": [],
                "symlink_count": 0,
                "tree_sha256": "c" * 64,
                "version": "0.1.0",
            },
            "build": {
                "hooks_version": "2026.7",
                "mode": "onedir",
                "pyinstaller_version": "6.22.2",
                "python_version": "3.12",
                "source_tree_sha256": "d" * 64,
                "spec_sha256": "e" * 64,
            },
            "release": release,
            "runtime": {
                "source_checkout_required": False,
                "status": "passed",
                "system_python_required": False,
            },
            "schema_version": 1,
            "source_sha": SOURCE_SHA,
            "wave": "P4-W6",
        },
    )


def test_macos14_unavailable_evidence_is_exact_and_bounded(tmp_path: Path) -> None:
    destination = tmp_path / "macos-14-unavailable.json"

    evidence = write_macos14_unavailable_evidence(
        destination,
        source_sha=SOURCE_SHA,
        macos_artifact_sha256="e" * 64,
    )

    assert CleanHostEvidence.from_dict(json.loads(destination.read_bytes())) == evidence
    assert evidence.to_dict() == {
        "architecture": "arm64",
        "artifact_sha256": "e" * 64,
        "blocker_code": "exact-signed-candidate-runner-unavailable",
        "checks": {},
        "exact_signed_candidate": True,
        "host": "macos-14",
        "setup_seconds": None,
        "source_sha": SOURCE_SHA,
        "status": "unavailable-runner",
    }


def test_final_assembler_closes_and_revalidates_all_release_coordinates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    python = tmp_path / "python"
    python.mkdir()
    for name in (
        "open_brain-0.1.0-py3-none-any.whl",
        "open_brain-0.1.0.tar.gz",
        "open_brain_connectors-0.1.0-py3-none-any.whl",
        "open_brain_connectors-0.1.0.tar.gz",
        "open_brain_engine-0.1.0-py3-none-any.whl",
        "open_brain_engine-0.1.0.tar.gz",
    ):
        (python / name).write_bytes(name.encode())

    linux = tmp_path / "linux"
    linux_artifact = linux / "artifacts/open-brain-0.1.0-linux-x86_64.tar.gz"
    linux_artifact.parent.mkdir(parents=True)
    linux_artifact.write_bytes(b"linux native\n")
    linux_checksum = linux_artifact.with_name(linux_artifact.name + ".sha256")
    linux_checksum.write_text(
        f"{file_sha256(linux_artifact)}  {linux_artifact.name}\n",
        encoding="ascii",
    )
    _write_build_evidence(
        linux / "native-build/build-evidence.json",
        platform="linux-x86_64",
        release={
            "archive_sha256": file_sha256(linux_artifact),
            "checksum_sha256": file_sha256(linux_checksum),
            "format": "tar.gz",
            "status": "passed",
        },
    )

    macos = tmp_path / "macos"
    macos_artifact = macos / "artifacts/open-brain-0.1.0-macos-arm64.dmg"
    macos_artifact.parent.mkdir(parents=True)
    macos_artifact.write_bytes(b"macos native\n")
    macos_checksum = macos_artifact.with_name(macos_artifact.name + ".sha256")
    macos_checksum.write_text(
        f"{file_sha256(macos_artifact)}  {macos_artifact.name}\n",
        encoding="ascii",
    )
    notarization = NotarizationEvidence(
        status="accepted",
        issue_count=0,
        receipt="rct_v1_" + "f" * 64,
        stapled=True,
        validated=True,
    )
    _write_json(macos / "evidence/notarization.json", notarization.to_dict())
    _write_build_evidence(
        macos / "native-build/build-evidence.json",
        platform="macos-arm64",
        release={
            "checksum_sha256": file_sha256(macos_checksum),
            "dmg_sha256": file_sha256(macos_artifact),
            "format": "dmg",
            "hardened_runtime": True,
            "notarization": notarization.to_dict(),
            "secure_timestamp": True,
            "signed_code_count": 2,
            "status": "passed",
        },
    )
    licenses = macos / "media-payload/licenses"
    licenses.mkdir(parents=True)
    (licenses / "CPython-LICENSE.txt").write_text("Python license\n", encoding="utf-8")
    (licenses / "PyInstaller-COPYING.txt").write_text(
        "PyInstaller license\n", encoding="utf-8"
    )

    clean_hosts = tmp_path / "clean-hosts"
    linux_digest = file_sha256(linux_artifact)
    for host in ("ubuntu-24.04", "ubuntu-26.04", "debian-13"):
        _write_json(
            clean_hosts / f"{host}.json",
            _passed_host(
                host,
                artifact_sha256=linux_digest,
                exact_signed_candidate=False,
            ).to_dict(),
        )
    _write_json(
        clean_hosts / "macos-signed.json",
        _passed_host(
            "macos-26",
            artifact_sha256=file_sha256(macos_artifact),
            exact_signed_candidate=True,
        ).to_dict(),
    )
    _write_json(
        clean_hosts / "macos-14-source-equivalent.json",
        _passed_host(
            "macos-14",
            artifact_sha256="9" * 64,
            exact_signed_candidate=False,
        ).to_dict(),
    )

    monkeypatch.setattr(release_assembly, "validate_exact_source_binding", lambda *_: None)
    monkeypatch.setattr(release_assembly, "verify_artifacts", lambda *_: [])
    monkeypatch.setattr(release_assembly, "_source_date_epoch", lambda *_: "1788350400")
    output = tmp_path / "release-candidate"

    manifest = assemble_release_candidate(
        ROOT,
        output,
        source_sha=SOURCE_SHA,
        python_directory=python,
        linux_directory=linux,
        macos_directory=macos,
        clean_host_directory=clean_hosts,
    )
    validated = validate_release_candidate_directory(output)

    artifacts = cast(list[dict[str, object]], manifest["artifacts"])
    assert validated == manifest
    assert manifest["candidate_id"] == "candidate_native-p4w6"
    assert {item["coordinate"] for item in artifacts} == set(
        EXPECTED_RELEASE_ARTIFACT_COORDINATES
    )
    assert (output / "release-candidate.json").is_file()
    unavailable = json.loads(
        (output / "evidence/clean-host/macos-14-unavailable.json").read_bytes()
    )
    assert unavailable["status"] == "unavailable-runner"
    assert unavailable["artifact_sha256"] == file_sha256(macos_artifact)
    assert str(tmp_path) not in json.dumps(manifest, sort_keys=True)
