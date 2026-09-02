from __future__ import annotations

from pathlib import Path

from tools.phase4.acceptance_harness import engine_isolation_findings

ROOT = Path(__file__).parents[2]


def test_engine_builds_and_runs_without_workspace_sources(tmp_path: Path) -> None:
    assert engine_isolation_findings(ROOT, tmp_path) == []
