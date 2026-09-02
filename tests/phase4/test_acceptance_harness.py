from __future__ import annotations

import json
import subprocess
import warnings
import zipfile
from pathlib import Path
from typing import Any

from tools.phase4.acceptance_harness import (
    CONTRACTS,
    ArtifactContract,
    ImportProbe,
    artifact_findings,
    build_command,
    create_environment_command,
    engine_test_command,
    export_test_requirements_command,
    import_probe_findings,
    install_command,
    run_checked,
    sanitized_environment,
)

ROOT = Path(__file__).parents[2]
WORKSTREAM = (
    ROOT / "docs/ai/workstreams/"
    "20260901-open-brain-public-execute-goal-63-through-phase-4-p4a-p4b-and-p4c-"
    "with-independently-reviewed-pack-8a3f9b"
)
EXPECTED_RED = WORKSTREAM / "P4-W0-EXPECTED-RED.json"


def _codes(path: Path, contract: ArtifactContract) -> set[str]:
    return {finding.code for finding in artifact_findings(path, contract)}


def _wheel(path: Path, members: dict[str, bytes], *, duplicate: str | None = None) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        for name, payload in members.items():
            archive.writestr(name, payload)
        if duplicate is not None:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                archive.writestr(duplicate, b"duplicate")


def test_all_six_acceptance_contracts_are_independently_named() -> None:
    assert [contract.contract_id for contract in CONTRACTS] == [
        "engine-isolation",
        "app-isolation",
        "connector-isolation",
        "artifact-membership",
        "identity-compatibility",
        "clean-host-lifecycle",
    ]
    app = next(contract for contract in CONTRACTS if contract.contract_id == "app-isolation")
    assert "v0-gate-07-sibling-approve-reject-safe-edit-cli-ui" in app.behaviors
    assert "v0-gate-13-space-create-rename-later-route-scoped-all-retrieval" in app.behaviors


def test_build_and_install_commands_enforce_no_sources_and_python_312(tmp_path: Path) -> None:
    assert "--no-sources" in build_command(tmp_path / "project", tmp_path / "dist")
    assert create_environment_command(tmp_path / "venv")[:4] == (
        "uv",
        "venv",
        "--python",
        "3.12",
    )
    command = install_command(tmp_path / "venv/bin/python", [tmp_path / "app.whl"])
    assert command[5:7] == ("--link-mode", "copy")
    assert "--no-index" in command
    assert "app.whl" in command[-1]
    export = export_test_requirements_command()
    assert "--locked" in export
    assert "--no-emit-workspace" in export
    assert "open-brain-engine" not in export
    assert engine_test_command(
        tmp_path / "venv/bin/python",
        tmp_path / "engine_test_runner.py",
        tmp_path / "tests",
        tmp_path / "venv/lib/python3.12/site-packages",
    ) == (
        str(tmp_path / "venv/bin/python"),
        "-I",
        str(tmp_path / "engine_test_runner.py"),
        str(tmp_path / "tests"),
        str(tmp_path / "venv/lib/python3.12/site-packages"),
    )


def test_isolated_environment_removes_source_masking_inputs() -> None:
    environment = sanitized_environment(
        {
            "PATH": "/bin",
            "PYTHONPATH": "/repo/src",
            "PYTHONHOME": "/repo/python",
            "VIRTUAL_ENV": "/repo/.venv",
            "UV_PROJECT_ENVIRONMENT": "/repo/.venv",
        }
    )

    assert environment == {
        "PATH": "/bin",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
    }


def test_run_checked_uses_isolated_cwd_environment_and_timeout(tmp_path: Path) -> None:
    observed: dict[str, Any] = {}

    def runner(command: tuple[str, ...], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        observed.update({"command": command, **kwargs})
        return subprocess.CompletedProcess(command, 0, "ok", "")

    result = run_checked(("python", "-V"), cwd=tmp_path, runner=runner)

    assert result.returncode == 0
    assert observed["cwd"] == tmp_path
    assert observed["timeout"] == 1800
    assert "PYTHONPATH" not in observed["env"]


def test_harness_detects_missing_leaked_and_mismatched_artifacts(tmp_path: Path) -> None:
    contract = ArtifactContract(
        subject="app-wheel",
        required_members=("open_brain/__init__.py",),
        forbidden_patterns=("open_brain_legacy/**",),
        expected_name="open-brain",
        expected_version="0.1.0",
    )
    assert _codes(tmp_path / "missing.whl", contract) == {"P4H001"}

    leaked = tmp_path / "leaked.whl"
    _wheel(
        leaked,
        {
            "open_brain/__init__.py": b"",
            "open_brain_legacy/writer.py": b"",
            "open_brain-0.1.0.dist-info/METADATA": b"Name: open-brain\nVersion: 0.1.0\n",
        },
    )
    assert "P4H002" in _codes(leaked, contract)

    mismatched = tmp_path / "mismatched.whl"
    _wheel(
        mismatched,
        {
            "open_brain/__init__.py": b"",
            "wrong-9.9.9.dist-info/METADATA": b"Name: wrong\nVersion: 9.9.9\n",
        },
    )
    assert "P4H003" in _codes(mismatched, contract)


def test_harness_detects_unsafe_duplicate_and_source_path_masked_cases(
    tmp_path: Path,
) -> None:
    wheel = tmp_path / "unsafe.whl"
    metadata = b"Name: open-brain\nVersion: 0.1.0\n"
    _wheel(
        wheel,
        {
            "open_brain/__init__.py": b"",
            "../escape.py": b"",
            "open_brain-0.1.0.dist-info/METADATA": metadata,
        },
        duplicate="open_brain/__init__.py",
    )
    contract = ArtifactContract(
        subject="app-wheel",
        required_members=("open_brain/__init__.py",),
        forbidden_patterns=(),
        expected_name="open-brain",
        expected_version="0.1.0",
    )

    assert {"P4H005", "P4H006"} <= _codes(wheel, contract)
    probe = ImportProbe(module_paths=(str(ROOT / "src/open_brain/__init__.py"),), sys_path=())
    assert [finding.code for finding in import_probe_findings(probe, ROOT)] == ["P4H004"]


def test_expected_red_report_is_bounded_metadata_only() -> None:
    payload = json.loads(EXPECTED_RED.read_text(encoding="utf-8"))

    assert payload["schema_version"] == 1
    assert payload["baseline"] == "current-monolith"
    assert len(payload["findings"]) == 11
    assert {finding["code"] for finding in payload["findings"]} == {
        "P4E001",
        "P4E002",
        "P4E003",
        "P4E004",
        "P4E005",
    }
    assert "/" + "Users/" not in EXPECTED_RED.read_text(encoding="utf-8")
