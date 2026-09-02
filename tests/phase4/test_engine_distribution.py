from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path

import pytest

from tools.phase4.acceptance_harness import build_command, engine_isolation_findings

ROOT = Path(__file__).parents[2]


def test_engine_builds_and_runs_without_workspace_sources(tmp_path: Path) -> None:
    assert engine_isolation_findings(ROOT, tmp_path) == []


@pytest.mark.parametrize("distribution", ("connectors", "legacy"))
def test_future_distribution_skeletons_cannot_build_wheels(
    tmp_path: Path,
    distribution: str,
) -> None:
    project = ROOT / "packages" / distribution
    metadata = tomllib.loads((project / "pyproject.toml").read_text(encoding="utf-8"))
    output = tmp_path / distribution

    completed = subprocess.run(
        build_command(project, output),
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
        timeout=1800,
    )

    assert metadata["tool"]["uv"]["package"] is False
    assert completed.returncode != 0
    assert not tuple(output.glob("*.whl"))
