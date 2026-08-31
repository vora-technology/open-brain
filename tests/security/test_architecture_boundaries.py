from pathlib import Path


def test_core_has_no_concrete_adapter_imports() -> None:
    core = Path(__file__).parents[2] / "src" / "open_brain" / "core"
    prohibited = ("filesystem", "socket", "urllib.request", "open_brain.cli", "open_brain.config")
    assert all(token not in path.read_text() for path in core.glob("*.py") for token in prohibited)


def test_core_ports_expose_no_task_capability_or_raw_redaction() -> None:
    source = (Path(__file__).parents[2] / "src" / "open_brain" / "core" / "ports.py").read_text()
    prohibited = ("create_task", "upsert_task", "enqueue_task", "TaskStore", "task_id")
    assert all(token not in source for token in prohibited)
    raw_store = source.split("class RawStore", maxsplit=1)[1].split(
        "class RedactionFindingCategory", maxsplit=1
    )[0]
    assert "RedactionReceipt" not in raw_store


def test_phase1_cli_and_ui_use_engine_public_surface_not_local_stores() -> None:
    source_root = Path(__file__).parents[2] / "src" / "open_brain"
    representations = (
        source_root / "cli" / "phase1.py",
        source_root / "integrations" / "phase1_ui.py",
    )
    prohibited = (
        "open_brain.engine.local",
        "open_brain.storage",
        "sqlite3",
        "atomic_write",
        "connect_database",
    )
    for path in representations:
        source = path.read_text(encoding="utf-8")
        assert "from open_brain.engine import" in source
        assert all(token not in source for token in prohibited)
