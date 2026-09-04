from __future__ import annotations

from pathlib import Path

from tools.phase4.acceptance_harness import app_isolation_findings

ROOT = Path(__file__).parents[2]


def test_app_source_and_wheel_contract_declares_cross_platform_coverage() -> None:
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "runs-on: ubuntu-latest" in workflow
    assert "uv run pytest -q" in workflow
    assert "uv run mypy" in workflow
    assert "runs-on: macos-14" in workflow
    assert 'python-version: ["3.12", "3.13", "3.14"]' in workflow
    assert "tests/phase4/test_app_distribution.py" in workflow
    assert "test_appliance_upgrade.py" in workflow
    assert "test_appliance_uninstall.py" in workflow
    assert "test_appliance_supervisors.py" in workflow


def test_app_sdist_example_config_contains_placeholders_only() -> None:
    text = (ROOT / "examples/config.example.toml").read_text(encoding="utf-8")

    assert "credential" not in text.lower()
    assert "api_key" not in text.lower()


def test_app_builds_and_runs_without_workspace_connector_or_legacy_sources(
    tmp_path: Path,
) -> None:
    assert app_isolation_findings(ROOT, tmp_path) == []
