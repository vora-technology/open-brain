from __future__ import annotations

import json
from pathlib import Path

from tools.phase4.acceptance_harness import connector_isolation_findings

ROOT = Path(__file__).parents[2]


def test_connector_builds_and_runs_only_through_the_isolated_worker(tmp_path: Path) -> None:
    assert connector_isolation_findings(ROOT, tmp_path) == []


def test_connector_compatibility_remains_provisional_until_all_proofs_exist() -> None:
    compatibility = json.loads(
        (ROOT / "release/phase4-compatibility.json").read_text(encoding="utf-8")
    )
    connector = compatibility["distributions"]["connectors"]

    assert connector["interface_status"] == "provisional"
    assert connector["worker_protocol"] == 1
    assert connector["stability_prerequisites"] == [
        "event-conformance",
        "measurement-conformance",
        "reference-conformance",
    ]


def test_connector_isolation_runs_on_every_supported_python_in_ci() -> None:
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "connector-isolation:" in workflow
    assert 'python-version: ["3.12", "3.13", "3.14"]' in workflow
    assert "pytest -q tests/phase4/test_connector_distribution.py" in workflow
