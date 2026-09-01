from __future__ import annotations

import os
import sqlite3
import stat
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path, PurePosixPath
from urllib.parse import quote

from open_brain.core.ids import canonical_json_bytes
from open_brain.core.ports import Clock

from .filesystem import (
    RootConfinementError,
    RootIdentity,
    StorageError,
    StorageUnsupportedPlatformError,
    _open_parent,
    _open_root,
    _validated_parts,
)

SCHEMA_VERSION = 1
_SQLITE_OPEN_LOCK = threading.Lock()


class SchemaError(StorageError):
    """The SQLite schema is unavailable or inconsistent."""


class NewerSchemaError(SchemaError):
    """The database schema is newer than this application."""


class MigrationChecksumError(SchemaError):
    """An applied migration differs from the in-code migration."""


@dataclass(frozen=True, slots=True)
class Migration:
    version: int
    name: str
    checksum: str
    statements: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SchemaInspection:
    version: int
    valid: bool

    def __post_init__(self) -> None:
        if (
            type(self.version) is not int
            or self.version < 0
            or type(self.valid) is not bool
        ):
            raise SchemaError("invalid schema inspection")


_SCHEMA_MIGRATIONS_SQL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY CHECK (version > 0),
    name TEXT NOT NULL,
    checksum TEXT NOT NULL,
    applied_at TEXT NOT NULL
)
""".strip()

_EVENT_STATEMENTS = (
    """
CREATE TABLE events (
    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL UNIQUE,
    capture_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    privacy_tier TEXT NOT NULL,
    privacy_reason TEXT NOT NULL,
    privacy_policy_version TEXT NOT NULL,
    privacy_confirmation_ref TEXT,
    cloud_allowed INTEGER NOT NULL CHECK (cloud_allowed IN (0, 1)),
    egress_allowed INTEGER NOT NULL CHECK (egress_allowed IN (0, 1)),
    redaction_policy_version TEXT NOT NULL,
    redaction_source_sha256 TEXT NOT NULL CHECK (length(redaction_source_sha256) = 64),
    redaction_output_sha256 TEXT NOT NULL CHECK (length(redaction_output_sha256) = 64),
    redaction_findings_json TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    payload_sha256 TEXT NOT NULL CHECK (length(payload_sha256) = 64),
    created_at TEXT NOT NULL,
    CHECK (length(event_id) > 0),
    CHECK (length(capture_id) > 0),
    CHECK (length(event_type) > 0)
)
""".strip(),
    "CREATE INDEX events_capture_sequence_idx ON events (capture_id, sequence)",
)


def _migration_checksum(version: int, name: str, statements: tuple[str, ...]) -> str:
    return sha256(
        canonical_json_bytes({"version": version, "name": name, "statements": list(statements)})
    ).hexdigest()


def _migration(version: int, name: str, statements: tuple[str, ...]) -> Migration:
    return Migration(
        version=version,
        name=name,
        checksum=_migration_checksum(version, name, statements),
        statements=statements,
    )


MIGRATIONS = (_migration(1, "events", _EVENT_STATEMENTS),)


def _open_database_file(parent_fd: int, name: str) -> None:
    try:
        database_fd = os.open(
            name,
            os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW,
            0o600,
            dir_fd=parent_fd,
        )
    except OSError:
        raise RootConfinementError("unsafe database path") from None
    try:
        if not stat.S_ISREG(os.fstat(database_fd).st_mode):
            raise RootConfinementError("unsafe database path")
        os.fchmod(database_fd, 0o600)
    finally:
        os.close(database_fd)


def _restrict_existing_file(parent_fd: int, name: str) -> None:
    try:
        file_fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent_fd)
    except FileNotFoundError:
        return
    except OSError:
        raise RootConfinementError("unsafe database path") from None
    try:
        if not stat.S_ISREG(os.fstat(file_fd).st_mode):
            raise RootConfinementError("unsafe database path")
        os.fchmod(file_fd, 0o600)
    finally:
        os.close(file_fd)


def _require_private_directory(directory_fd: int) -> None:
    if stat.S_IMODE(os.fstat(directory_fd).st_mode) & 0o022:
        raise RootConfinementError("unsafe database path")


def _connect_from_parent(parent_fd: int, name: str) -> sqlite3.Connection:
    if not hasattr(os, "fchdir"):
        raise StorageUnsupportedPlatformError("storage platform unsupported")
    original_directory_fd = os.open(".", os.O_RDONLY | os.O_DIRECTORY)
    try:
        with _SQLITE_OPEN_LOCK:
            os.fchdir(parent_fd)
            try:
                return sqlite3.connect(name, timeout=5.0, isolation_level=None)
            finally:
                os.fchdir(original_directory_fd)
    finally:
        os.close(original_directory_fd)


def connect_database(
    *,
    root: Path,
    database_name: str | PurePosixPath,
    expected_root_identity: RootIdentity | None = None,
) -> sqlite3.Connection:
    raw_database_name = str(database_name)
    if "%" in raw_database_name:
        raise RootConfinementError("unsafe database path")
    parts = _validated_parts(raw_database_name)
    root_fd = _open_root(root, expected_root_identity)
    parent_fd = -1
    try:
        _require_private_directory(root_fd)
        for depth in range(1, len(parts)):
            component_fd = _open_parent(root_fd, parts[:depth], create=True)
            try:
                _require_private_directory(component_fd)
            finally:
                os.close(component_fd)
        parent_fd = _open_parent(root_fd, parts[:-1], create=True)
        _open_database_file(parent_fd, parts[-1])
        old_umask = os.umask(0o077)
        try:
            connection = _connect_from_parent(parent_fd, parts[-1])
        finally:
            os.umask(old_umask)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        journal_mode = connection.execute("PRAGMA journal_mode = WAL").fetchone()[0]
        connection.execute("PRAGMA synchronous = FULL")
        settings = (
            connection.execute("PRAGMA foreign_keys").fetchone()[0],
            connection.execute("PRAGMA busy_timeout").fetchone()[0],
            connection.execute("PRAGMA synchronous").fetchone()[0],
        )
        if str(journal_mode).lower() != "wal" or settings != (1, 5000, 2):
            connection.close()
            raise SchemaError("required database settings unavailable")
        for suffix in ("-wal", "-shm"):
            _restrict_existing_file(parent_fd, parts[-1] + suffix)
        return connection
    except (RootConfinementError, SchemaError):
        raise
    except (OSError, sqlite3.Error):
        raise SchemaError("database connection failed") from None
    finally:
        if parent_fd >= 0:
            os.close(parent_fd)
        os.close(root_fd)


def connect_database_read_only(
    *,
    root: Path,
    database_name: str | PurePosixPath,
    expected_root_identity: RootIdentity | None = None,
) -> sqlite3.Connection:
    """Open an existing root-confined SQLite database without creating or migrating it."""
    parts = _validated_parts(str(database_name))
    root_fd = _open_root(root, expected_root_identity)
    parent_fd = -1
    database_fd = -1
    try:
        _require_private_directory(root_fd)
        try:
            parent_fd = _open_parent(root_fd, parts[:-1], create=False)
            _require_private_directory(parent_fd)
            database_fd = os.open(
                parts[-1],
                os.O_RDONLY | os.O_NOFOLLOW,
                dir_fd=parent_fd,
            )
        except FileNotFoundError:
            raise SchemaError("database unavailable") from None
        metadata = os.fstat(database_fd)
        if not stat.S_ISREG(metadata.st_mode):
            raise RootConfinementError("unsafe database path")
        original_directory_fd = os.open(".", os.O_RDONLY | os.O_DIRECTORY)
        try:
            with _SQLITE_OPEN_LOCK:
                os.fchdir(parent_fd)
                try:
                    uri = f"file:{quote(parts[-1], safe='')}?mode=ro"
                    connection = sqlite3.connect(
                        uri,
                        uri=True,
                        timeout=5.0,
                        isolation_level=None,
                    )
                finally:
                    os.fchdir(original_directory_fd)
        finally:
            os.close(original_directory_fd)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection
    except (RootConfinementError, SchemaError):
        raise
    except (OSError, sqlite3.Error):
        raise SchemaError("database read-only connection failed") from None
    finally:
        if database_fd >= 0:
            os.close(database_fd)
        if parent_fd >= 0:
            os.close(parent_fd)
        os.close(root_fd)


def inspect_event_schema(
    *,
    root: Path,
    database_name: str | PurePosixPath,
) -> SchemaInspection:
    """Inspect the event schema and migration checksums without running migrations."""
    connection = connect_database_read_only(root=root, database_name=database_name)
    try:
        version = int(connection.execute("PRAGMA user_version").fetchone()[0])
        try:
            rows = connection.execute(
                "SELECT version, name, checksum FROM schema_migrations ORDER BY version"
            ).fetchall()
        except sqlite3.Error:
            return SchemaInspection(version=version, valid=False)
        valid = (
            version == SCHEMA_VERSION
            and len(rows) == len(MIGRATIONS)
            and all(
                int(row["version"]) == migration.version
                and row["name"] == migration.name
                and row["checksum"] == migration.checksum
                for row, migration in zip(rows, MIGRATIONS, strict=True)
            )
        )
        return SchemaInspection(version=version, valid=valid)
    except (TypeError, ValueError, sqlite3.Error):
        raise SchemaError("event schema inspection failed") from None
    finally:
        connection.close()


def _format_timestamp(value: datetime) -> str:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise SchemaError("migration clock returned invalid timestamp")
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _validate_migration_set(
    migrations: tuple[Migration, ...], schema_version: int
) -> None:
    if (
        type(schema_version) is not int
        or schema_version < 1
        or not isinstance(migrations, tuple)
        or len(migrations) != schema_version
    ):
        raise SchemaError("invalid migration set")
    for expected_version, migration in enumerate(migrations, start=1):
        if (
            not isinstance(migration, Migration)
            or migration.version != expected_version
            or not migration.name
            or not isinstance(migration.statements, tuple)
            or not migration.statements
            or any(
                not isinstance(statement, str) or not statement
                for statement in migration.statements
            )
            or migration.checksum
            != _migration_checksum(migration.version, migration.name, migration.statements)
        ):
            raise SchemaError("invalid migration set")


def migrate(
    connection: sqlite3.Connection,
    *,
    clock: Clock,
    migrations: tuple[Migration, ...] = MIGRATIONS,
    schema_version: int = SCHEMA_VERSION,
) -> int:
    _validate_migration_set(migrations, schema_version)
    try:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(_SCHEMA_MIGRATIONS_SQL)
        rows = connection.execute(
            "SELECT version, name, checksum FROM schema_migrations ORDER BY version"
        ).fetchall()
        versions = [int(row["version"]) for row in rows]
        if versions != list(range(1, len(versions) + 1)):
            raise SchemaError("database migration versions are not contiguous")
        user_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
        if user_version > schema_version or versions and versions[-1] > schema_version:
            raise NewerSchemaError("database schema is newer than supported")
        for row in rows:
            migration = migrations[int(row["version"]) - 1]
            if row["name"] != migration.name or row["checksum"] != migration.checksum:
                raise MigrationChecksumError("database migration checksum mismatch")
        for migration in migrations[len(rows) :]:
            for statement in migration.statements:
                connection.execute(statement)
            connection.execute(
                "INSERT INTO schema_migrations(version, name, checksum, applied_at) "
                "VALUES (?, ?, ?, ?)",
                (
                    migration.version,
                    migration.name,
                    migration.checksum,
                    _format_timestamp(clock.now()),
                ),
            )
        connection.execute(f"PRAGMA user_version = {schema_version}")
        connection.commit()
        return schema_version
    except SchemaError:
        if connection.in_transaction:
            connection.rollback()
        raise
    except (IndexError, KeyError, TypeError, ValueError, sqlite3.Error):
        if connection.in_transaction:
            connection.rollback()
        raise SchemaError("database migration failed") from None
