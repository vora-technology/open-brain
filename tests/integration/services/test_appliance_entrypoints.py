from __future__ import annotations

import json
from pathlib import Path

import pytest

from open_brain.profile import compile_single_user_local
from open_brain.services.appliance_entrypoints import run_cli, run_mcp
from open_brain.services.appliance_init import initialize_appliance


def test_appliance_cli_help_and_version_are_root_free(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert run_cli(("--help",), environment={}) == 0
    assert "init" in capsys.readouterr().out
    assert run_cli(("--version",), environment={}) == 0
    assert capsys.readouterr().out == "open-brain 0.1.0\n"


def test_appliance_status_reports_bounded_maintenance_without_leaking_root(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = tmp_path / "brain"
    initialize_appliance(root, starter_spaces=("Personal",))

    exit_code = run_cli(("status", "--json"), environment={"OPEN_BRAIN_ROOT": str(root)})
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["status"] == "ok"
    assert payload["maintenance"]["schema"]["state"] == "current"
    assert str(root) not in json.dumps(payload, sort_keys=True)


def test_appliance_mcp_rejects_absent_schema_without_mutating_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "brain"
    compile_single_user_local(root)
    environment = {
        "OPEN_BRAIN_ROOT": str(root),
        "OPEN_BRAIN_MCP_ALLOWED_SPACE_IDS": "[]",
    }

    monkeypatch.setattr("open_brain.services.appliance_entrypoints.os.environ", environment)

    assert run_mcp() == 78
    assert not (root / ".open-brain" / "state" / "phase1.sqlite3").exists()
    assert not (root / ".open-brain" / ".open-brain-locks").exists()

