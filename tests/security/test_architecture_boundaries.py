from pathlib import Path

REPOSITORY_ROOT = Path(__file__).parents[2]
APP_SOURCE_ROOT = REPOSITORY_ROOT / "packages/app/src/open_brain"


def test_core_has_no_concrete_adapter_imports() -> None:
    core = (
        Path(__file__).parents[2]
        / "packages"
        / "engine"
        / "src"
        / "open_brain_engine"
        / "core"
    )
    prohibited = ("filesystem", "socket", "urllib.request", "open_brain.cli", "open_brain.config")
    assert all(token not in path.read_text() for path in core.glob("*.py") for token in prohibited)


def test_core_ports_expose_no_task_capability_or_raw_redaction() -> None:
    source = (
        Path(__file__).parents[2]
        / "packages"
        / "engine"
        / "src"
        / "open_brain_engine"
        / "core"
        / "ports.py"
    ).read_text()
    prohibited = ("create_task", "upsert_task", "enqueue_task", "TaskStore", "task_id")
    assert all(token not in source for token in prohibited)
    raw_store = source.split("class RawStore", maxsplit=1)[1].split(
        "class RedactionFindingCategory", maxsplit=1
    )[0]
    assert "RedactionReceipt" not in raw_store


def test_phase1_cli_and_ui_use_engine_public_surface_not_local_stores() -> None:
    representations = (
        APP_SOURCE_ROOT / "cli" / "phase1.py",
        APP_SOURCE_ROOT / "integrations" / "phase1_ui.py",
    )
    prohibited = (
        "open_brain_engine.engine.local",
        "open_brain_engine.storage",
        "sqlite3",
        "atomic_write",
        "connect_database",
    )
    for path in representations:
        source = path.read_text(encoding="utf-8")
        assert "from open_brain_engine.engine import" in source
        assert all(token not in source for token in prohibited)


def test_phase3_appliance_seams_are_reserved_without_shipping_legacy_control_paths() -> None:
    architecture = (REPOSITORY_ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")
    services = (
        APP_SOURCE_ROOT / "services" / "appliance_daemon.py",
        APP_SOURCE_ROOT / "services" / "appliance_lifecycle.py",
        APP_SOURCE_ROOT / "services" / "phase1_application.py",
        APP_SOURCE_ROOT / "services" / "phase1_entrypoints.py",
        APP_SOURCE_ROOT / "services" / "runtime.py",
    )

    assert "services/appliance_application.py" in architecture
    assert "services/appliance_daemon.py" in architecture
    assert "services/appliance_entrypoints.py" in architecture
    assert "services/appliance_lifecycle.py" in architecture
    assert ".open-brain/run/control.sock" in architecture
    for path in services:
        source = path.read_text(encoding="utf-8")
        assert "open_brain.operations" not in source
        assert "open_brain_legacy.operations" not in source
        assert "open_brain.release" not in source


def test_appliance_application_uses_only_public_engine_surfaces_for_mutations() -> None:
    source = (APP_SOURCE_ROOT / "services" / "appliance_application.py").read_text(
        encoding="utf-8"
    )

    assert "from open_brain_engine.engine import" in source
    prohibited = (
        "open_brain_engine.engine.local",
        "open_brain_engine.storage",
        "FileLease",
        "LockScope",
    )
    assert all(token not in source for token in prohibited)
