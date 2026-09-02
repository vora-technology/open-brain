from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from open_brain.services.native_artifacts import NativeArtifactManifest, native_platform_tag
from tools.phase4.native_build import (
    NativeBuildError,
    audit_native_artifact,
    load_native_build_configuration,
    pyinstaller_command,
    smoke_native_artifact,
)

ROOT = Path(__file__).resolve().parents[2]


def test_native_build_configuration_is_pinned_and_uses_one_deterministic_spec() -> None:
    configuration = load_native_build_configuration(ROOT)
    command = pyinstaller_command(configuration, ROOT / "build/p4w5-test")
    spec = configuration.spec_path.read_text(encoding="utf-8")

    assert configuration.python_version == "3.12"
    assert configuration.pyinstaller_version == "6.22.2"
    assert configuration.hooks_version == "2026.7"
    assert configuration.mode == "onedir"
    assert command == (
        configuration.python_executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--distpath",
        str(ROOT / "build/p4w5-test/dist"),
        "--workpath",
        str(ROOT / "build/p4w5-test/work"),
        str(ROOT / "release/native/open-brain.spec"),
    )
    assert "native_entrypoint.py" in spec
    assert "collect_submodules(\"open_brain\")" in spec
    assert "collect_submodules(\"open_brain_engine\")" in spec
    assert "name=\"open-brain\"" in spec


def test_native_artifact_audit_requires_executable_resources_and_safe_symlinks(
    tmp_path: Path,
) -> None:
    artifact = (tmp_path / "candidate_native-p4w5").resolve()
    resources = artifact / "_internal/open_brain/resources/supervisors"
    resources.mkdir(parents=True)
    executable = artifact / "open-brain"
    executable.write_bytes(b"native executable")
    executable.chmod(0o755)
    (resources / "launchd.json").write_text("{}\n", encoding="utf-8")
    (resources / "systemd.service").write_text("[Service]\n", encoding="utf-8")
    (resources / "launchd-link.json").symlink_to("launchd.json")
    NativeArtifactManifest.create(
        artifact,
        candidate_id="candidate_native-p4w5",
        version="0.1.0",
        platform_tag=native_platform_tag(),
    ).write(artifact)

    audit = audit_native_artifact(artifact, expected_platform=native_platform_tag())

    assert audit.candidate_id == "candidate_native-p4w5"
    assert audit.version == "0.1.0"
    assert audit.member_count == 8
    assert audit.symlink_count == 1
    assert audit.resource_members == (
        "_internal/open_brain/resources/supervisors/launchd.json",
        "_internal/open_brain/resources/supervisors/systemd.service",
    )
    assert len(audit.tree_sha256) == 64


def test_native_artifact_audit_rejects_private_residue(tmp_path: Path) -> None:
    artifact = (tmp_path / "candidate_native-p4w5").resolve()
    resources = artifact / "_internal/open_brain/resources/supervisors"
    resources.mkdir(parents=True)
    executable = artifact / "open-brain"
    executable.write_bytes(b"native executable")
    executable.chmod(0o755)
    (resources / "launchd.json").write_text("{}\n", encoding="utf-8")
    (resources / "systemd.service").write_text("[Service]\n", encoding="utf-8")
    private = artifact / "_internal/credentials"
    private.mkdir()
    (private / "private.txt").write_text("private", encoding="utf-8")
    NativeArtifactManifest.create(
        artifact,
        candidate_id="candidate_native-p4w5",
        version="0.1.0",
        platform_tag=native_platform_tag(),
    ).write(artifact)

    with pytest.raises(NativeBuildError, match="native build operation failed"):
        audit_native_artifact(artifact, expected_platform=native_platform_tag())


def test_native_artifact_audit_rejects_mixed_case_source_suffixes(tmp_path: Path) -> None:
    artifact = (tmp_path / "candidate_native-p4w5").resolve()
    resources = artifact / "_internal/open_brain/resources/supervisors"
    resources.mkdir(parents=True)
    executable = artifact / "open-brain"
    executable.write_bytes(b"native executable")
    executable.chmod(0o755)
    (resources / "launchd.json").write_text("{}\n", encoding="utf-8")
    (resources / "systemd.service").write_text("[Service]\n", encoding="utf-8")
    (resources / "unexpected.PY").write_text("private source\n", encoding="utf-8")
    NativeArtifactManifest.create(
        artifact,
        candidate_id="candidate_native-p4w5",
        version="0.1.0",
        platform_tag=native_platform_tag(),
    ).write(artifact)

    with pytest.raises(NativeBuildError, match="native build operation failed"):
        audit_native_artifact(artifact, expected_platform=native_platform_tag())


def test_native_smoke_uses_public_recovery_upgrade_rollback_and_uninstall() -> None:
    source = inspect.getsource(smoke_native_artifact)

    for command in ('"portable-export"', '"portable-import"', '"upgrade"', '"uninstall"'):
        assert command in source
    assert "__native-portable-self-check" not in source
    assert "__native-rollback-self-check" not in source
    assert "shutil.rmtree(failed_artifact)" not in source
    assert "adapter.remove" not in source
