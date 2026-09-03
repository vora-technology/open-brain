from __future__ import annotations

import inspect
import json
import subprocess
import tarfile
from pathlib import Path

import pytest

import tools.phase4.native_build as native_build
from tools.phase4.native_build import NativeArtifactAudit
from tools.phase4.release_candidate import (
    EXPECTED_RELEASE_ARTIFACT_COORDINATES,
    CleanHostEvidence,
    NotarizationEvidence,
    ReleaseArtifact,
    ReleaseCandidateError,
    build_release_manifest,
    collect_macos_signing_targets,
    create_deterministic_tar_gz,
    file_sha256,
    notarize_macos_dmg,
    sign_macos_candidate,
    validate_clean_host_matrix,
    validate_release_manifest,
    write_sha256_file,
)

_MACHO_64 = b"\xcf\xfa\xed\xfe"
_SOURCE_SHA = "a" * 40
_ROOT = Path(__file__).resolve().parents[2]


def _write_macho(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_MACHO_64 + b"synthetic Mach-O")
    path.chmod(0o755)


def _passed_host(
    host: str,
    *,
    artifact_sha256: str = "b" * 64,
    signed: bool = False,
) -> CleanHostEvidence:
    return CleanHostEvidence(
        host=host,
        architecture="arm64" if host.startswith("macos-") else "x86_64",
        artifact_sha256=artifact_sha256,
        source_sha=_SOURCE_SHA,
        setup_seconds=12.5,
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
        exact_signed_candidate=signed,
    )


def _release_artifacts(root: Path) -> tuple[ReleaseArtifact, ...]:
    artifacts: list[ReleaseArtifact] = []
    for index, coordinate in enumerate(EXPECTED_RELEASE_ARTIFACT_COORDINATES):
        suffix = ".json" if coordinate in {"sbom.spdx", "evidence.licenses"} else ".bin"
        path = root / "artifacts" / f"{index:02d}-{coordinate.replace('.', '-')}{suffix}"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(f"{coordinate}\n".encode())
        artifacts.append(
            ReleaseArtifact.from_path(
                coordinate=coordinate,
                path=path,
                relative_to=root,
            )
        )
    return tuple(artifacts)


def _write_synthetic_candidate(path: Path) -> None:
    path.mkdir(parents=True)
    executable = path / "open-brain"
    executable.write_text(
        '#!/bin/sh\n[ "${1:-}" = __native-self-check ] || exit 1\nexit 0\n',
        encoding="utf-8",
    )
    executable.chmod(0o755)
    (path / "open-brain-native.json").write_text("{}\n", encoding="utf-8")


def test_p4w6_parameterization_preserves_p4w5_native_defaults(tmp_path: Path) -> None:
    build_signature = inspect.signature(native_build.build_native_artifact)
    smoke_signature = inspect.signature(native_build.smoke_native_artifact)
    assert build_signature.parameters["candidate_id"].default == "candidate_native-p4w5"
    assert build_signature.parameters["wave"].default == "P4-W5"
    assert smoke_signature.parameters["expected_wave"].default == "P4-W5"

    evidence_path = tmp_path / "build-evidence.json"
    evidence_path.write_text(
        json.dumps(
            {
                "artifact": {"tree_sha256": "b" * 64},
                "runtime": None,
                "schema_version": 1,
                "wave": "P4-W6",
            }
        ),
        encoding="utf-8",
    )
    audit = NativeArtifactAudit(
        candidate_id="candidate_native-p4w6",
        version="0.1.0",
        platform_tag="macos-arm64",
        tree_sha256="b" * 64,
        membership_sha256="c" * 64,
        member_count=0,
        symlink_count=0,
        resource_members=(),
        members=(),
    )

    native_build._merge_runtime_evidence(
        evidence_path,
        audit,
        {"status": "passed"},
        expected_wave="P4-W6",
    )

    assert json.loads(evidence_path.read_text(encoding="utf-8"))["runtime"] == {"status": "passed"}


def test_native_media_installer_is_artifact_only_and_leaves_one_relative_activation_link(
    tmp_path: Path,
) -> None:
    media = tmp_path / "media"
    _write_synthetic_candidate(media / "candidate_native-p4w6")
    installer = media / "install.sh"
    installer.write_bytes((_ROOT / "release/native/install.sh").read_bytes())
    installer.chmod(0o755)
    install_root = tmp_path / "installed"
    result = subprocess.run(
        (str(installer),),
        check=False,
        capture_output=True,
        text=True,
        env={
            "HOME": str(tmp_path / "home"),
            "OPEN_BRAIN_INSTALL_ROOT": str(install_root),
            "PATH": "/usr/bin:/bin",
            "PYTHONHOME": str(tmp_path / "python-home-canary"),
            "PYTHONPATH": str(tmp_path / "source-canary"),
        },
        timeout=10,
    )

    assert result.returncode == 0
    assert result.stdout == '{"status":"installed"}\n'
    assert result.stderr == ""
    assert (install_root / "current").readlink() == Path("candidates/candidate_native-p4w6")
    assert (install_root / "current/open-brain").is_file()
    assert not tuple((install_root / "candidates").glob(".candidate_native-p4w6.*"))


def test_native_media_installer_rejects_symlink_install_root_without_residue(
    tmp_path: Path,
) -> None:
    media = tmp_path / "media"
    _write_synthetic_candidate(media / "candidate_native-p4w6")
    installer = media / "install.sh"
    installer.write_bytes((_ROOT / "release/native/install.sh").read_bytes())
    installer.chmod(0o755)
    outside = tmp_path / "outside"
    outside.mkdir()
    install_root = tmp_path / "installed"
    install_root.symlink_to(outside, target_is_directory=True)

    result = subprocess.run(
        (str(installer),),
        check=False,
        capture_output=True,
        text=True,
        env={
            "HOME": str(tmp_path / "home"),
            "OPEN_BRAIN_INSTALL_ROOT": str(install_root),
            "PATH": "/usr/bin:/bin",
        },
        timeout=10,
    )

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr == '{"status":"failed"}\n'
    assert not tuple(outside.iterdir())


def test_macos_signing_targets_are_confined_inside_out_and_main_executable_last(
    tmp_path: Path,
) -> None:
    candidate = tmp_path / "candidate_native-p4w6"
    nested = candidate / "_internal/Python.framework/Versions/3.12/Python"
    extension = candidate / "_internal/lib-dynload/_sqlite3.cpython-312-darwin.so"
    main = candidate / "open-brain"
    _write_macho(nested)
    _write_macho(extension)
    _write_macho(main)
    (candidate / "_internal/Python.framework/Versions/Current").symlink_to("3.12")
    (candidate / "README.txt").write_text("not executable code\n", encoding="utf-8")

    targets = collect_macos_signing_targets(candidate)

    assert [target.relative_to(candidate).as_posix() for target in targets] == [
        "_internal/Python.framework/Versions/3.12/Python",
        "_internal/lib-dynload/_sqlite3.cpython-312-darwin.so",
        "_internal/Python.framework",
        "open-brain",
    ]


def test_macos_signing_requires_hardened_runtime_timestamp_and_bounded_evidence(
    tmp_path: Path,
) -> None:
    candidate = tmp_path / "candidate_native-p4w6"
    _write_macho(candidate / "_internal/libexample.dylib")
    _write_macho(candidate / "open-brain")
    calls: list[tuple[str, ...]] = []

    def runner(command: tuple[str, ...], *, timeout: int) -> subprocess.CompletedProcess[str]:
        assert timeout > 0
        calls.append(command)
        if "--display" in command:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout="",
                stderr="Executable=private\nflags=0x10000(runtime)\nTimestamp=Sep 2, 2026\n",
            )
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    evidence = sign_macos_candidate(
        candidate,
        identity="private signing identity",
        runner=runner,
    )

    signing_calls = [command for command in calls if "--sign" in command]
    verification_calls = [command for command in calls if "--verify" in command]
    assert signing_calls
    assert all("--options" in command and "runtime" in command for command in signing_calls)
    assert all("--timestamp" in command for command in signing_calls)
    assert signing_calls[-1][-1] == str(candidate / "open-brain")
    assert [command[-1] for command in verification_calls] == [
        command[-1] for command in signing_calls
    ]
    assert evidence == {
        "hardened_runtime": True,
        "secure_timestamp": True,
        "signed_code_count": 2,
        "status": "passed",
    }
    assert "identity" not in json.dumps(evidence).casefold()


def test_notarization_acceptance_is_stapled_validated_and_secret_safe(tmp_path: Path) -> None:
    dmg = tmp_path / "open-brain-0.1.0-macos-arm64.dmg"
    dmg.write_bytes(b"synthetic dmg")
    submission_id = "123e4567-e89b-42d3-a456-426614174000"
    calls: list[tuple[str, ...]] = []

    def runner(command: tuple[str, ...], *, timeout: int) -> subprocess.CompletedProcess[str]:
        assert timeout > 0
        calls.append(command)
        output: dict[str, object]
        if "submit" in command:
            output = {"id": submission_id, "message": "uploaded", "status": "Accepted"}
        elif "log" in command:
            output = {
                "issues": [],
                "jobId": submission_id,
                "status": "Accepted",
                "statusSummary": "Ready for distribution",
            }
        else:
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps(output), stderr="")

    result = notarize_macos_dmg(
        dmg,
        keychain_profile="private profile selector",
        runner=runner,
    )

    assert result.status == "accepted"
    assert result.issue_count == 0
    assert result.stapled is True
    assert result.validated is True
    assert result.receipt.startswith("rct_v1_")
    rendered = json.dumps(result.to_dict(), sort_keys=True)
    assert submission_id not in rendered
    assert "profile" not in rendered.casefold()
    assert any("submit" in command for command in calls)
    assert any("log" in command for command in calls)
    assert any("staple" in command for command in calls)
    assert any("validate" in command for command in calls)


def test_notarization_failure_never_exposes_raw_output_or_selector(tmp_path: Path) -> None:
    dmg = tmp_path / "candidate.dmg"
    dmg.write_bytes(b"synthetic dmg")
    private_selector = "private-selector-canary"
    raw_canary = "private-account-and-path-canary"

    def runner(command: tuple[str, ...], *, timeout: int) -> subprocess.CompletedProcess[str]:
        del timeout
        return subprocess.CompletedProcess(command, 1, stdout=raw_canary, stderr=raw_canary)

    with pytest.raises(ReleaseCandidateError) as raised:
        notarize_macos_dmg(dmg, keychain_profile=private_selector, runner=runner)

    assert str(raised.value) == "release candidate operation failed"
    assert private_selector not in str(raised.value)
    assert raw_canary not in str(raised.value)


def test_linux_archive_and_checksum_are_deterministic_and_safe(tmp_path: Path) -> None:
    payload = tmp_path / "payload"
    executable = payload / "candidate_native-p4w6/open-brain"
    executable.parent.mkdir(parents=True)
    executable.write_bytes(b"native executable\n")
    executable.chmod(0o755)
    (payload / "candidate_native-p4w6/current-library").symlink_to("library.so")
    (payload / "candidate_native-p4w6/library.so").write_bytes(b"library\n")
    (payload / "install.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    (payload / "install.sh").chmod(0o755)
    (payload / "LICENSE").write_text("license\n", encoding="utf-8")
    first = tmp_path / "first.tar.gz"
    second = tmp_path / "second.tar.gz"

    create_deterministic_tar_gz(
        payload,
        first,
        archive_root="open-brain-0.1.0-linux-x86_64",
    )
    create_deterministic_tar_gz(
        payload,
        second,
        archive_root="open-brain-0.1.0-linux-x86_64",
    )

    assert first.read_bytes() == second.read_bytes()
    with tarfile.open(first, "r:gz") as archive:
        members = archive.getmembers()
    assert [member.name for member in members] == sorted(member.name for member in members)
    assert all(member.mtime == 0 and member.uid == 0 and member.gid == 0 for member in members)
    assert all(
        not Path(member.name).is_absolute() and ".." not in Path(member.name).parts
        for member in members
    )
    archived_link = next(member for member in members if member.name.endswith("/current-library"))
    assert (
        archived_link.mode
        == (payload / "candidate_native-p4w6/current-library").lstat().st_mode & 0o777
    )
    checksum = write_sha256_file(first)
    assert checksum.read_text(encoding="ascii") == f"{file_sha256(first)}  {first.name}\n"

    (payload / "escape").symlink_to("../../outside")
    with pytest.raises(ReleaseCandidateError, match="release candidate operation failed"):
        create_deterministic_tar_gz(
            payload,
            tmp_path / "unsafe.tar.gz",
            archive_root="open-brain-0.1.0-linux-x86_64",
        )


def test_clean_host_matrix_requires_every_lifecycle_gate_and_bounded_macos_blocker() -> None:
    linux_digest = "b" * 64
    macos_digest = "c" * 64
    results = (
        _passed_host("ubuntu-24.04", artifact_sha256=linux_digest),
        _passed_host("ubuntu-26.04", artifact_sha256=linux_digest),
        _passed_host("debian-13", artifact_sha256=linux_digest),
        _passed_host("macos-26", artifact_sha256=macos_digest, signed=True),
        CleanHostEvidence(
            host="macos-14",
            architecture="arm64",
            artifact_sha256=macos_digest,
            source_sha=_SOURCE_SHA,
            setup_seconds=None,
            status="unavailable-runner",
            checks={},
            exact_signed_candidate=True,
            blocker_code="exact-signed-candidate-runner-unavailable",
        ),
        _passed_host("macos-14", artifact_sha256="d" * 64, signed=False),
    )

    validate_clean_host_matrix(
        results,
        source_sha=_SOURCE_SHA,
        linux_artifact_sha256=linux_digest,
        macos_artifact_sha256=macos_digest,
    )

    missing_gate = _passed_host("ubuntu-24.04", artifact_sha256=linux_digest)
    missing_gate.checks.pop("v0_gate_13")
    with pytest.raises(ReleaseCandidateError, match="release candidate operation failed"):
        validate_clean_host_matrix(
            (missing_gate, *results[1:]),
            source_sha=_SOURCE_SHA,
            linux_artifact_sha256=linux_digest,
            macos_artifact_sha256=macos_digest,
        )


def test_release_manifest_closes_every_required_coordinate_and_omits_private_metadata(
    tmp_path: Path,
) -> None:
    artifacts = _release_artifacts(tmp_path)
    notarization = NotarizationEvidence(
        status="accepted",
        issue_count=0,
        receipt="rct_v1_" + "d" * 64,
        stapled=True,
        validated=True,
    )
    artifacts_by_coordinate = {artifact.coordinate: artifact for artifact in artifacts}
    linux_digest = artifacts_by_coordinate["native.linux-x86_64"].sha256
    macos_digest = artifacts_by_coordinate["native.macos-arm64"].sha256
    hosts = (
        _passed_host("ubuntu-24.04", artifact_sha256=linux_digest),
        _passed_host("ubuntu-26.04", artifact_sha256=linux_digest),
        _passed_host("debian-13", artifact_sha256=linux_digest),
        _passed_host("macos-14", artifact_sha256=macos_digest, signed=True),
        _passed_host("macos-14", artifact_sha256="e" * 64, signed=False),
    )

    manifest = build_release_manifest(
        source_sha=_SOURCE_SHA,
        version="0.1.0",
        artifacts=artifacts,
        clean_hosts=hosts,
        notarization=notarization,
        supported_hosts={
            "linux-x86_64": ["ubuntu-24.04", "ubuntu-26.04", "debian-13"],
            "macos-arm64": ">=14",
        },
        portable_schema={"minimum": 1, "maximum": 1},
    )

    validate_release_manifest(manifest)
    rendered = json.dumps(manifest, sort_keys=True)
    raw_artifacts = manifest["artifacts"]
    assert isinstance(raw_artifacts, list)
    coordinates: set[str] = set()
    for item in raw_artifacts:
        assert isinstance(item, dict)
        coordinate = item.get("coordinate")
        assert isinstance(coordinate, str)
        coordinates.add(coordinate)
    assert coordinates == set(EXPECTED_RELEASE_ARTIFACT_COORDINATES)
    assert manifest["publication"] == {
        "packages": [],
        "releases": [],
        "status": "unpublished",
        "tags": [],
    }
    assert manifest["candidate_id"] == "candidate_native-p4w6"
    assert str(tmp_path) not in rendered
    assert "profile" not in rendered.casefold()
    assert "identity" not in rendered.casefold()
    assert "account" not in rendered.casefold()

    incomplete = dict(manifest)
    incomplete["artifacts"] = raw_artifacts[:-1]
    with pytest.raises(ReleaseCandidateError, match="release candidate operation failed"):
        validate_release_manifest(incomplete)
