from __future__ import annotations

import sqlite3
import stat
from hashlib import sha256
from pathlib import Path

import pytest
from open_brain_engine.storage.filesystem import RootConfinementError
from open_brain_engine.storage.sqlite import (
    MIGRATIONS,
    SCHEMA_VERSION,
    Migration,
    MigrationChecksumError,
    NewerSchemaError,
    SchemaError,
    connect_database,
    connect_database_read_only,
    inspect_event_schema,
    migrate,
)

from tests.unit.storage._factories import FixedClock


def _custom_migration(version: int, name: str, statements: tuple[str, ...]) -> Migration:
    from open_brain_engine.core.ids import canonical_json_bytes

    checksum = sha256(
        canonical_json_bytes(
            {"version": version, "name": name, "statements": list(statements)}
        )
    ).hexdigest()
    return Migration(
        version=version,
        name=name,
        checksum=checksum,
        statements=statements,
    )


def test_fresh_sqlite_has_required_pragmas_and_current_migration(tmp_path: Path) -> None:
    connection = connect_database(root=tmp_path, database_name="events.sqlite3")
    try:
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert connection.execute("PRAGMA busy_timeout").fetchone()[0] == 5000
        assert connection.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        assert connection.execute("PRAGMA synchronous").fetchone()[0] == 2
        assert migrate(connection, clock=FixedClock()) == SCHEMA_VERSION
        assert migrate(connection, clock=FixedClock()) == SCHEMA_VERSION
        assert connection.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
        rows = connection.execute(
            "SELECT version, name, checksum FROM schema_migrations"
        ).fetchall()
        assert [tuple(row) for row in rows] == [(1, MIGRATIONS[0].name, MIGRATIONS[0].checksum)]
    finally:
        connection.close()


def test_custom_migrations_are_independent_from_event_schema(tmp_path: Path) -> None:
    migrations = (
        _custom_migration(1, "runs", ("CREATE TABLE runs (run_id TEXT PRIMARY KEY)",)),
        _custom_migration(
            2,
            "receipts",
            ("CREATE TABLE receipts (run_id TEXT PRIMARY KEY, digest TEXT NOT NULL)",),
        ),
    )
    connection = connect_database(root=tmp_path, database_name="replay.sqlite3")
    try:
        assert (
            migrate(
                connection,
                clock=FixedClock(),
                migrations=migrations,
                schema_version=2,
            )
            == 2
        )
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 2
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        assert {"runs", "receipts", "schema_migrations"} <= tables
        assert "events" not in tables
    finally:
        connection.close()


@pytest.mark.parametrize(
    ("migrations", "schema_version"),
    (
        ((_custom_migration(1, "one", ("CREATE TABLE one (id INTEGER)",)),), 2),
        ((_custom_migration(2, "two", ("CREATE TABLE two (id INTEGER)",)),), 1),
        (
            (
                Migration(
                    version=1,
                    name="forged",
                    checksum="0" * 64,
                    statements=("CREATE TABLE forged (id INTEGER)",),
                ),
            ),
            1,
        ),
    ),
)
def test_invalid_custom_migration_set_is_rejected_before_mutation(
    tmp_path: Path,
    migrations: tuple[Migration, ...],
    schema_version: int,
) -> None:
    connection = connect_database(root=tmp_path, database_name="replay.sqlite3")
    try:
        with pytest.raises(SchemaError, match="invalid migration set"):
            migrate(
                connection,
                clock=FixedClock(),
                migrations=migrations,
                schema_version=schema_version,
            )
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 0
        assert (
            connection.execute(
                "SELECT 1 FROM sqlite_master WHERE name = 'schema_migrations'"
            ).fetchone()
            is None
        )
    finally:
        connection.close()


def test_migration_checksum_drift_is_rejected(tmp_path: Path) -> None:
    connection = connect_database(root=tmp_path, database_name="events.sqlite3")
    try:
        migrate(connection, clock=FixedClock())
        connection.execute(
            "UPDATE schema_migrations SET checksum = ? WHERE version = 1", ("0" * 64,)
        )
        with pytest.raises(MigrationChecksumError):
            migrate(connection, clock=FixedClock())
    finally:
        connection.close()


def test_newer_schema_is_rejected_without_mutation(tmp_path: Path) -> None:
    connection = connect_database(root=tmp_path, database_name="events.sqlite3")
    try:
        connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION + 1}")
        with pytest.raises(NewerSchemaError):
            migrate(connection, clock=FixedClock())
        assert connection.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION + 1
    finally:
        connection.close()


def test_database_symlink_is_rejected(tmp_path: Path) -> None:
    target = tmp_path / "target.sqlite3"
    sqlite3.connect(target).close()
    linked = tmp_path / "linked.sqlite3"
    linked.symlink_to(target)

    with pytest.raises(RootConfinementError, match="unsafe database path"):
        connect_database(root=tmp_path, database_name="linked.sqlite3")


def test_database_symlink_root_is_rejected(tmp_path: Path) -> None:
    actual = tmp_path / "actual"
    actual.mkdir()
    linked_root = tmp_path / "linked-root"
    linked_root.symlink_to(actual, target_is_directory=True)

    with pytest.raises(RootConfinementError, match="unsafe storage root"):
        connect_database(root=linked_root, database_name="events.sqlite3")


@pytest.mark.parametrize("database_name", ("../events.sqlite3", "/events.sqlite3", "bad\\name"))
def test_database_name_must_be_safe_and_relative(tmp_path: Path, database_name: str) -> None:
    with pytest.raises(RootConfinementError, match="unsafe relative path"):
        connect_database(root=tmp_path, database_name=database_name)


def test_database_intermediate_symlink_escape_is_rejected(tmp_path: Path) -> None:
    approved = tmp_path / "approved"
    approved.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (approved / "linked").symlink_to(outside, target_is_directory=True)

    with pytest.raises(RootConfinementError, match="unsafe storage path"):
        connect_database(root=approved, database_name="linked/events.sqlite3")

    assert not (outside / "events.sqlite3").exists()


def test_database_parent_replacement_does_not_escape_approved_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    approved = tmp_path / "approved"
    nested = approved / "nested"
    nested.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    displaced = approved / "displaced"
    real_connect = sqlite3.connect

    def replace_parent(
        database: str, *, timeout: float, isolation_level: None
    ) -> sqlite3.Connection:
        nested.rename(displaced)
        nested.symlink_to(outside, target_is_directory=True)
        return real_connect(database, timeout=timeout, isolation_level=isolation_level)

    monkeypatch.setattr("open_brain_engine.storage.sqlite.sqlite3.connect", replace_parent)
    connection = connect_database(root=approved, database_name="nested/events.sqlite3")
    connection.close()

    assert not (outside / "events.sqlite3").exists()
    assert (displaced / "events.sqlite3").exists()


def test_database_and_wal_artifacts_are_owner_only(tmp_path: Path) -> None:
    database = tmp_path / "events.sqlite3"
    connection = connect_database(root=tmp_path, database_name="events.sqlite3")
    try:
        connection.execute("CREATE TABLE synthetic (value INTEGER)")
        connection.execute("INSERT INTO synthetic(value) VALUES (1)")
        assert stat.S_IMODE(database.stat().st_mode) == 0o600
        assert stat.S_IMODE((tmp_path / "events.sqlite3-wal").stat().st_mode) == 0o600
        assert stat.S_IMODE((tmp_path / "events.sqlite3-shm").stat().st_mode) == 0o600
    finally:
        connection.close()


def test_read_only_connection_reads_without_allowing_writes(tmp_path: Path) -> None:
    writable = connect_database(root=tmp_path, database_name="events.sqlite3")
    try:
        writable.execute("CREATE TABLE synthetic (value INTEGER)")
        writable.execute("INSERT INTO synthetic(value) VALUES (1)")
    finally:
        writable.close()

    read_only = connect_database_read_only(root=tmp_path, database_name="events.sqlite3")
    try:
        assert read_only.execute("SELECT value FROM synthetic").fetchone()[0] == 1
        with pytest.raises(sqlite3.OperationalError):
            read_only.execute("INSERT INTO synthetic(value) VALUES (2)")
    finally:
        read_only.close()


def test_read_only_connection_never_creates_an_absent_database(tmp_path: Path) -> None:
    database = tmp_path / "missing.sqlite3"

    with pytest.raises(SchemaError, match="database unavailable"):
        connect_database_read_only(root=tmp_path, database_name=database.name)

    assert not database.exists()


def test_event_schema_inspection_is_read_only_and_detects_checksum_drift(
    tmp_path: Path,
) -> None:
    connection = connect_database(root=tmp_path, database_name="events.sqlite3")
    try:
        migrate(connection, clock=FixedClock())
    finally:
        connection.close()

    healthy = inspect_event_schema(root=tmp_path, database_name="events.sqlite3")
    writable = sqlite3.connect(tmp_path / "events.sqlite3")
    try:
        writable.execute("UPDATE schema_migrations SET checksum = ?", ("0" * 64,))
        writable.commit()
    finally:
        writable.close()
    drifted = inspect_event_schema(root=tmp_path, database_name="events.sqlite3")

    assert healthy.version == SCHEMA_VERSION
    assert healthy.valid is True
    assert drifted.version == SCHEMA_VERSION
    assert drifted.valid is False
