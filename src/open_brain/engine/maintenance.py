"""Read-only engine maintenance evidence for appliance status and MCP gating."""

from __future__ import annotations

import json
import re
import sqlite3
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from open_brain.core.ids import canonical_json_bytes, validate_identifier
from open_brain.storage.filesystem import DurabilityError, read_confined
from open_brain.storage.locks import inspect_file_leases
from open_brain.storage.sqlite import SchemaError, connect_database_read_only

from .contracts import LocalEngineContext

PHASE1_STATE_DATABASE = ".open-brain/state/phase1.sqlite3"
PHASE1_STATE_SCHEMA_VERSION = 1
SEARCH_INDEX_DATABASE = ".open-brain/indexes/search.sqlite3"
APPLIANCE_BACKUP_EVIDENCE = Path(".open-brain/state/appliance-backup-evidence.json")
APPLIANCE_EXPORT_EVIDENCE = Path(".open-brain/state/appliance-export-evidence.json")
_STATE_TABLES = frozenset(
    {
        "captures",
        "spaces",
        "space_operations",
        "route_operations",
        "proposal_sets",
        "proposals",
        "decisions",
        "search_documents",
    }
)
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class SchemaState:
    state: str
    version: int | None

    def to_dict(self) -> dict[str, object]:
        return {"state": self.state, "version": self.version}


@dataclass(frozen=True, slots=True)
class IndexState:
    state: str
    generation: int | None
    document_count: int

    def to_dict(self) -> dict[str, object]:
        return {
            "state": self.state,
            "generation": self.generation,
            "document_count": self.document_count,
        }


@dataclass(frozen=True, slots=True)
class WriterState:
    held_count: int
    malformed_count: int
    held_leases: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "held_count": self.held_count,
            "malformed_count": self.malformed_count,
            "held_leases": list(self.held_leases),
        }


@dataclass(frozen=True, slots=True)
class EvidenceState:
    state: str
    operation_id: str | None
    recorded_at: str | None
    manifest_digest_sha256: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "state": self.state,
            "operation_id": self.operation_id,
            "recorded_at": self.recorded_at,
            "manifest_digest_sha256": self.manifest_digest_sha256,
        }


@dataclass(frozen=True, slots=True)
class QueueState:
    state: str
    pending_count: int
    malformed_count: int
    oldest_captured_at: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "state": self.state,
            "pending_count": self.pending_count,
            "malformed_count": self.malformed_count,
            "oldest_captured_at": self.oldest_captured_at,
        }


@dataclass(frozen=True, slots=True)
class MaintenanceSnapshot:
    schema: SchemaState
    index: IndexState
    writer: WriterState
    backup: EvidenceState
    export: EvidenceState
    queue: QueueState

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema.to_dict(),
            "index": self.index.to_dict(),
            "writer": self.writer.to_dict(),
            "backup": self.backup.to_dict(),
            "export": self.export.to_dict(),
            "queue": self.queue.to_dict(),
        }


def inspect_phase1_state(profile: LocalEngineContext) -> SchemaState:
    """Inspect the app-owned engine state database without creating or migrating it."""
    if not isinstance(profile, LocalEngineContext):
        raise ValueError("invalid local profile")
    try:
        connection = connect_database_read_only(
            root=profile.root,
            database_name=PHASE1_STATE_DATABASE,
            expected_root_identity=profile.root_identity,
        )
    except SchemaError:
        database = profile.root / PHASE1_STATE_DATABASE
        try:
            database.lstat()
        except FileNotFoundError:
            return SchemaState(state="absent", version=None)
        except OSError:
            pass
        return SchemaState(state="invalid", version=None)
    try:
        version = int(connection.execute("PRAGMA user_version").fetchone()[0])
        tables = {
            cast(str, row["name"])
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
    except (TypeError, ValueError, sqlite3.Error):
        return SchemaState(state="invalid", version=None)
    finally:
        connection.close()
    if version > PHASE1_STATE_SCHEMA_VERSION:
        return SchemaState(state="newer", version=version)
    if version == 0 and tables >= _STATE_TABLES:
        return SchemaState(state="legacy", version=version)
    if version == PHASE1_STATE_SCHEMA_VERSION and tables >= _STATE_TABLES:
        return SchemaState(state="current", version=version)
    return SchemaState(state="invalid", version=version)


def read_maintenance_snapshot(profile: LocalEngineContext) -> MaintenanceSnapshot:
    """Read bounded schema, index, writer, backup, export, and queue evidence."""
    if not isinstance(profile, LocalEngineContext):
        raise ValueError("invalid local profile")
    return MaintenanceSnapshot(
        schema=inspect_phase1_state(profile),
        index=_inspect_index(profile),
        writer=_inspect_writer(profile),
        backup=_read_evidence(profile, APPLIANCE_BACKUP_EVIDENCE, prefix="backup_"),
        export=_read_evidence(profile, APPLIANCE_EXPORT_EVIDENCE, prefix="export_"),
        queue=QueueState(
            state="unavailable",
            pending_count=0,
            malformed_count=0,
            oldest_captured_at=None,
        ),
    )


def _inspect_index(profile: LocalEngineContext) -> IndexState:
    try:
        connection = connect_database_read_only(
            root=profile.root,
            database_name=SEARCH_INDEX_DATABASE,
            expected_root_identity=profile.root_identity,
        )
    except SchemaError:
        database = profile.root / SEARCH_INDEX_DATABASE
        try:
            database.lstat()
        except FileNotFoundError:
            return IndexState(state="absent", generation=None, document_count=0)
        except OSError:
            pass
        return IndexState(state="invalid", generation=None, document_count=0)
    try:
        row = connection.execute(
            "SELECT generation FROM index_metadata WHERE singleton = 1"
        ).fetchone()
        document_count = int(
            connection.execute("SELECT count(*) FROM search_documents").fetchone()[0]
        )
    except (TypeError, ValueError, sqlite3.Error):
        return IndexState(state="invalid", generation=None, document_count=0)
    finally:
        with suppress(Exception):
            connection.close()
    generation = None if row is None else cast(int, row["generation"])
    if generation is None:
        return IndexState(state="invalid", generation=None, document_count=document_count)
    return IndexState(state="current", generation=generation, document_count=document_count)


def _inspect_writer(profile: LocalEngineContext) -> WriterState:
    try:
        snapshot = inspect_file_leases(profile.root / ".open-brain")
    except DurabilityError:
        return WriterState(held_count=0, malformed_count=1, held_leases=())
    return WriterState(
        held_count=snapshot.held_count,
        malformed_count=snapshot.malformed_count,
        held_leases=tuple(lease.discriminator for lease in snapshot.held_leases),
    )


def _read_evidence(profile: LocalEngineContext, relative: Path, *, prefix: str) -> EvidenceState:
    payload = read_confined(
        root=profile.root,
        relative=relative.as_posix(),
        expected_root_identity=profile.root_identity,
    )
    if payload is None:
        return EvidenceState(
            state="absent",
            operation_id=None,
            recorded_at=None,
            manifest_digest_sha256=None,
        )
    try:
        decoded = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return EvidenceState("invalid", None, None, None)
    if (
        not isinstance(decoded, dict)
        or decoded.get("schema_version") != 1
        or canonical_json_bytes(decoded) != payload
    ):
        return EvidenceState("invalid", None, None, None)
    operation_key = "backup_id" if prefix == "backup_" else "export_id"
    operation_id = decoded.get(operation_key)
    recorded_at = decoded.get("created_at")
    digest = decoded.get("manifest_digest_sha256")
    if not isinstance(operation_id, str) or not isinstance(recorded_at, str) or not isinstance(
        digest, str
    ):
        return EvidenceState("invalid", None, None, None)
    try:
        validate_identifier(operation_id, prefix=prefix)
        _parse_timestamp(recorded_at)
    except ValueError:
        return EvidenceState("invalid", None, None, None)
    if _HEX64.fullmatch(digest) is None:
        return EvidenceState("invalid", None, None, None)
    return EvidenceState(
        state="present",
        operation_id=operation_id,
        recorded_at=recorded_at,
        manifest_digest_sha256=digest,
    )


def _parse_timestamp(value: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("invalid timestamp")
    return datetime.fromisoformat(value[:-1] + "+00:00").astimezone(UTC)
