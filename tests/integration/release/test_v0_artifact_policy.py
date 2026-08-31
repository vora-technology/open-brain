from __future__ import annotations

import json
import tarfile
import tomllib
import zipfile
from io import BytesIO
from pathlib import Path
from typing import cast

from open_brain.dev.artifact_policy import required_members_for_policy, verify_artifacts

ROOT = Path(__file__).parents[3]
POLICY_PATH = ROOT / "release" / "v0-artifact-policy.json"
DOCUMENTATION_PATH = ROOT / "docs" / "artifact-characterization.md"


def _policy() -> dict[str, object]:
    value = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError("artifact policy must be an object")
    return cast(dict[str, object], value)


def _artifact_config(kind: str) -> dict[str, object]:
    artifacts = _policy()["default_python_artifacts"]
    assert isinstance(artifacts, dict) and isinstance(artifacts[kind], dict)
    return cast(dict[str, object], artifacts[kind])


def _write_wheel(path: Path, members: list[str]) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        for member in members:
            archive.writestr(member, "synthetic")


def _write_sdist(path: Path, members: list[str]) -> None:
    with tarfile.open(path, "w:gz") as archive:
        for member in members:
            data = b"synthetic"
            info = tarfile.TarInfo(f"open_brain-0.1.0/{member}")
            info.size = len(data)
            archive.addfile(info, BytesIO(data))


def test_phase_zero_policy_matches_explicit_hatch_configuration() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    build = pyproject["tool"]["hatch"]["build"]["targets"]
    wheel = _artifact_config("wheel")
    sdist = _artifact_config("sdist")

    assert _policy()["phase"] == "0-explicit-boundary"
    assert build["wheel"]["packages"] == wheel["configured_package_roots"]
    force_includes = [
        {"source": source, "destination": destination}
        for source, destination in build["wheel"]["force-include"].items()
    ]
    assert force_includes == wheel["force_includes"]
    assert build["sdist"]["include"] == sdist["configured_includes"]
    assert wheel["status"] == sdist["status"] == "explicit-current-not-release-ready"


def test_phase_zero_policy_verifies_required_and_forbidden_members(tmp_path: Path) -> None:
    wheel = tmp_path / "open_brain-0.1.0-py3-none-any.whl"
    sdist = tmp_path / "open_brain-0.1.0.tar.gz"
    wheel_members = list(required_members_for_policy(POLICY_PATH, "wheel"))
    sdist_members = list(required_members_for_policy(POLICY_PATH, "sdist"))
    _write_wheel(wheel, wheel_members)
    _write_sdist(sdist, sdist_members)

    assert verify_artifacts(POLICY_PATH, [wheel, sdist]) == []

    _write_wheel(wheel, [*wheel_members, "open_brain/portable/conformance/v1/.open-brain/x"])
    findings = verify_artifacts(POLICY_PATH, [wheel, sdist])
    assert [(finding.member, finding.rule) for finding in findings] == [
        ("open_brain/portable/conformance/v1/.open-brain/x", "forbidden-member")
    ]


def test_phase_zero_policy_requires_every_schema_and_conformance_fixture() -> None:
    wheel_members = set(required_members_for_policy(POLICY_PATH, "wheel"))
    sdist_members = set(required_members_for_policy(POLICY_PATH, "sdist"))
    schema_files = {
        path.relative_to(ROOT / "schemas/portable-brain/v1").as_posix()
        for path in (ROOT / "schemas/portable-brain/v1").rglob("*")
        if path.is_file()
    }
    fixture_files = {
        path.relative_to(ROOT / "tests/fixtures/portable-brain/v1").as_posix()
        for path in (ROOT / "tests/fixtures/portable-brain/v1").rglob("*")
        if path.is_file()
    }

    assert {
        f"open_brain/portable/schemas/v1/{path}" for path in schema_files
    } == {
        path for path in wheel_members if path.startswith("open_brain/portable/schemas/v1/")
    }
    assert {
        f"open_brain/portable/conformance/v1/{path}" for path in fixture_files
    } == {
        path
        for path in wheel_members
        if path.startswith("open_brain/portable/conformance/v1/")
    }
    assert {f"schemas/portable-brain/v1/{path}" for path in schema_files} <= sdist_members
    assert {
        f"tests/fixtures/portable-brain/v1/{path}" for path in fixture_files
    } <= sdist_members


def test_target_boundary_names_legacy_optional_connector_and_cloud_exclusions() -> None:
    exclusions = _policy()["target_release_exclusions"]
    assert isinstance(exclusions, list)
    assert {
        "open_brain/dev/**",
        "open_brain/migrate/**",
        "open_brain/parity/**",
        "open_brain/providers/optional_cloud.py",
        "open_brain/production/media.py",
        "open_brain/production/youtube_bridge.py",
        "open_brain/production/project_commit_bridge.py",
        "open_brain/capture/extractors/social.py",
        "open_brain/capture/extractors/youtube.py",
        "open_brain/integrations/messaging.py",
        "open_brain/integrations/obsidian.py",
        "open_brain/operations/optional_jobs.py",
    } <= set(exclusions)


def test_phase_zero_artifact_policy_has_exact_supported_and_unsupported_hosts() -> None:
    policy = _policy()
    hosts = policy["hosts"]
    assert isinstance(hosts, dict)
    assert hosts["supported"] == [
        {
            "artifact": "macos-arm64",
            "architecture": "arm64",
            "operating_system": "macOS",
            "versions": ">=14",
        },
        {
            "artifact": "linux-x86_64",
            "architecture": "x86_64",
            "operating_system": "Ubuntu",
            "versions": ["24.04 LTS", "26.04 LTS"],
        },
        {
            "artifact": "linux-x86_64",
            "architecture": "x86_64",
            "operating_system": "Debian",
            "versions": ["13"],
        },
    ]
    assert hosts["unsupported"] == ["macos-x86_64", "linux-arm64", "windows"]
    assert policy["native_artifacts"] == {
        "bundler_candidate": "PyInstaller 6 onedir",
        "fallback": "Nuitka standalone",
        "published": [],
        "status": "pending-phase-1-spike",
    }


def test_artifact_characterization_document_marks_phase_one_work_pending() -> None:
    document = DOCUMENTATION_PATH.read_text(encoding="utf-8")

    assert "Phase 1 pending" in document
    assert "does not" in document
    assert "native artifact exists" in document
