from __future__ import annotations

import inspect
import subprocess
from pathlib import Path

import pytest

import tools.phase4.native_build as native_build
from open_brain.services.native_artifacts import NativeArtifactManifest, native_platform_tag
from tools.phase4.native_build import (
    NativeBuildError,
    audit_native_artifact,
    load_native_build_configuration,
    native_resource_members,
    pyinstaller_command,
    smoke_native_artifact,
)

ROOT = Path(__file__).resolve().parents[2]


def _write_declared_native_resources(artifact: Path) -> None:
    for member in native_resource_members(ROOT):
        target = artifact / member
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"declared native resource\n")


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
    _write_declared_native_resources(artifact)
    framework_versions = artifact / "_internal/Python.framework/Versions"
    (framework_versions / "3.12").mkdir(parents=True)
    (framework_versions / "Current").symlink_to("3.12", target_is_directory=True)
    NativeArtifactManifest.create(
        artifact,
        candidate_id="candidate_native-p4w5",
        version="0.1.0",
        platform_tag=native_platform_tag(),
    ).write(artifact)

    audit = audit_native_artifact(artifact, expected_platform=native_platform_tag())

    assert audit.candidate_id == "candidate_native-p4w5"
    assert audit.version == "0.1.0"
    assert audit.member_count == len(audit.members)
    assert audit.symlink_count == 1
    assert audit.resource_members == native_resource_members(ROOT)
    assert len(audit.tree_sha256) == 64


def test_native_artifact_audit_rejects_private_residue(tmp_path: Path) -> None:
    artifact = (tmp_path / "candidate_native-p4w5").resolve()
    resources = artifact / "_internal/open_brain/resources/supervisors"
    resources.mkdir(parents=True)
    executable = artifact / "open-brain"
    executable.write_bytes(b"native executable")
    executable.chmod(0o755)
    _write_declared_native_resources(artifact)
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
    _write_declared_native_resources(artifact)
    (resources / "unexpected.PY").write_text("private source\n", encoding="utf-8")
    NativeArtifactManifest.create(
        artifact,
        candidate_id="candidate_native-p4w5",
        version="0.1.0",
        platform_tag=native_platform_tag(),
    ).write(artifact)

    with pytest.raises(NativeBuildError, match="native build operation failed"):
        audit_native_artifact(artifact, expected_platform=native_platform_tag())


def test_native_artifact_audit_rejects_undeclared_credential_resource(
    tmp_path: Path,
) -> None:
    artifact = (tmp_path / "candidate_native-p4w5").resolve()
    resources = artifact / "_internal/open_brain/resources/supervisors"
    resources.mkdir(parents=True)
    executable = artifact / "open-brain"
    executable.write_bytes(b"native executable")
    executable.chmod(0o755)
    _write_declared_native_resources(artifact)
    (resources / "api.token").write_text("private canary\n", encoding="utf-8")
    NativeArtifactManifest.create(
        artifact,
        candidate_id="candidate_native-p4w5",
        version="0.1.0",
        platform_tag=native_platform_tag(),
    ).write(artifact)

    with pytest.raises(NativeBuildError, match="native build operation failed"):
        audit_native_artifact(artifact, expected_platform=native_platform_tag())


def test_native_build_materializes_only_the_named_git_tree(tmp_path: Path) -> None:
    repository = (tmp_path / "repository").resolve()
    package = repository / "packages/app/src/open_brain"
    package.mkdir(parents=True)
    (repository / ".gitignore").write_text("*.token\n", encoding="utf-8")
    (package / "tracked.py").write_text("VALUE = 1\n", encoding="utf-8")
    (package / "ignored.token").write_text("private canary\n", encoding="utf-8")
    subprocess.run(("git", "init", "-q"), cwd=repository, check=True)
    subprocess.run(("git", "add", "."), cwd=repository, check=True)
    subprocess.run(
        (
            "git",
            "-c",
            "user.name=Open Brain Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-qm",
            "fixture",
        ),
        cwd=repository,
        check=True,
    )
    source_sha = subprocess.run(
        ("git", "rev-parse", "HEAD"),
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    destination = (tmp_path / "source").resolve()

    assert hasattr(native_build, "_materialize_source_tree")
    native_build._materialize_source_tree(repository, source_sha, destination)

    assert (destination / "packages/app/src/open_brain/tracked.py").is_file()
    assert not (destination / "packages/app/src/open_brain/ignored.token").exists()
    assert not (destination / ".git").exists()


def test_native_smoke_uses_public_recovery_upgrade_rollback_and_uninstall() -> None:
    source = inspect.getsource(smoke_native_artifact)

    for command in ('"portable-export"', '"portable-import"', '"upgrade"', '"uninstall"'):
        assert command in source
    assert "__native-portable-self-check" not in source
    assert "__native-rollback-self-check" not in source
    assert "shutil.rmtree(failed_artifact)" not in source
    assert "adapter.remove" not in source
