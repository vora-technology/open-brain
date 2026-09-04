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
    assert "name: macOS source/wheel (Python 3.14)" in workflow
    assert 'python-version: "3.14"' in workflow
    assert "tests/phase4/test_app_distribution.py" in workflow
    assert "test_appliance_upgrade.py" in workflow
    assert "test_appliance_uninstall.py" in workflow
    assert "test_appliance_supervisors.py" in workflow


def test_macos_install_guide_uses_python_314_and_the_public_daemon_command() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    guide = (ROOT / "docs/install-macos.md").read_text(encoding="utf-8")

    assert "docs/install-macos.md" in readme
    assert "Python 3.14" in guide
    assert "uv tool install --offline --no-python-downloads --python 3.14" in guide
    assert "open_brain_engine-0.1.0-py3-none-any.whl" in guide
    assert "open_brain-0.1.0-py3-none-any.whl" in guide
    assert guide.count("open-brain daemon") == 2
    assert "The DMG is deferred" in guide
    assert "to a later release" in guide


def test_app_sdist_example_config_contains_placeholders_only() -> None:
    text = (ROOT / "examples/config.example.toml").read_text(encoding="utf-8")

    assert "credential" not in text.lower()
    assert "api_key" not in text.lower()


def test_app_builds_and_runs_without_workspace_connector_or_legacy_sources(
    tmp_path: Path,
) -> None:
    assert app_isolation_findings(ROOT, tmp_path) == []
