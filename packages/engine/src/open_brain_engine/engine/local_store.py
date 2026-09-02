"""SQLite storage boundary for the local engine."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager, suppress

from open_brain_engine.storage.sqlite import connect_database

from .contracts import LocalEngineContext

_SCHEMA = """
CREATE TABLE IF NOT EXISTS captures (
    delivery_id TEXT PRIMARY KEY,
    request_sha256 TEXT NOT NULL,
    capture_id TEXT NOT NULL UNIQUE,
    accepted_receipt_id TEXT NOT NULL UNIQUE,
    payload_family TEXT NOT NULL,
    payload_json BLOB NOT NULL,
    search_text TEXT NOT NULL,
    file_bytes BLOB,
    source_origin TEXT NOT NULL,
    source_reference TEXT NOT NULL,
    space_id TEXT,
    intent TEXT,
    capture_why TEXT,
    action TEXT NOT NULL,
    title TEXT,
    accepted_at TEXT NOT NULL,
    stage INTEGER NOT NULL DEFAULT 0,
    source_path TEXT,
    canonical_path TEXT,
    auto_proposal_id TEXT UNIQUE,
    auto_proposal_receipt_id TEXT UNIQUE,
    auto_decision_id TEXT UNIQUE,
    auto_decision_receipt_id TEXT UNIQUE,
    page_id TEXT UNIQUE,
    publication_id TEXT UNIQUE,
    publication_path TEXT,
    enrichment_state TEXT NOT NULL DEFAULT 'pending_enrichment',
    actor_id TEXT,
    role_claim_json TEXT,
    privacy_json TEXT,
    provenance_json TEXT,
    submission_path TEXT
);
CREATE TABLE IF NOT EXISTS spaces (
    space_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS space_operations (
    delivery_id TEXT PRIMARY KEY,
    request_sha256 TEXT NOT NULL,
    operation TEXT NOT NULL,
    space_id TEXT NOT NULL,
    name TEXT NOT NULL,
    receipt_id TEXT NOT NULL UNIQUE,
    recorded_at TEXT NOT NULL,
    stage INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS route_operations (
    delivery_id TEXT PRIMARY KEY,
    request_sha256 TEXT NOT NULL,
    route_id TEXT NOT NULL UNIQUE,
    supersedes_route_id TEXT,
    capture_id TEXT NOT NULL,
    space_id TEXT NOT NULL,
    receipt_id TEXT NOT NULL UNIQUE,
    recorded_at TEXT NOT NULL,
    stage INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS proposal_sets (
    delivery_id TEXT PRIMARY KEY,
    request_sha256 TEXT NOT NULL,
    capture_id TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    stage INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS proposals (
    proposal_id TEXT PRIMARY KEY,
    set_delivery_id TEXT NOT NULL,
    capture_id TEXT NOT NULL,
    proposed_kind TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    proposed_bytes BLOB NOT NULL,
    supplied_reason TEXT,
    space_id TEXT,
    receipt_id TEXT NOT NULL UNIQUE,
    page_id TEXT,
    canonical_path TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    terminal_decision_id TEXT UNIQUE
);
CREATE TABLE IF NOT EXISTS decisions (
    delivery_id TEXT PRIMARY KEY,
    request_sha256 TEXT NOT NULL,
    decision_id TEXT NOT NULL UNIQUE,
    decision_receipt_id TEXT NOT NULL UNIQUE,
    proposal_id TEXT NOT NULL UNIQUE,
    outcome TEXT NOT NULL,
    effective_bytes BLOB,
    recorded_at TEXT NOT NULL,
    page_id TEXT,
    publication_id TEXT UNIQUE,
    canonical_path TEXT,
    publication_path TEXT,
    stage INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS search_documents (
    result_id TEXT PRIMARY KEY,
    capture_id TEXT NOT NULL,
    record_type TEXT NOT NULL,
    payload_family TEXT NOT NULL,
    space_id TEXT,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    trust TEXT NOT NULL,
    provenance_json TEXT NOT NULL,
    canonical_path TEXT,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS search_capture_idx ON search_documents (capture_id);
"""


class _LocalStore:
    def __init__(self, profile: LocalEngineContext) -> None:
        self.profile = profile
        self.root = profile.root
        connection = self.connect()
        try:
            connection.executescript(_SCHEMA)
            _add_capture_submission_columns(connection)
            _add_route_operation_columns(connection)
        finally:
            connection.close()

    def connect(self) -> sqlite3.Connection:
        return connect_database(
            root=self.root,
            database_name=".open-brain/state/phase1.sqlite3",
            expected_root_identity=self.profile.root_identity,
        )

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self.connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.execute("COMMIT")
        except BaseException:
            with suppress(sqlite3.Error):
                connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()


def _add_capture_submission_columns(connection: sqlite3.Connection) -> None:
    existing = {str(row["name"]) for row in connection.execute("PRAGMA table_info(captures)")}
    for name, declaration in (
        ("actor_id", "TEXT"),
        ("role_claim_json", "TEXT"),
        ("privacy_json", "TEXT"),
        ("provenance_json", "TEXT"),
        ("submission_path", "TEXT"),
    ):
        if name not in existing:
            connection.execute(f"ALTER TABLE captures ADD COLUMN {name} {declaration}")


def _add_route_operation_columns(connection: sqlite3.Connection) -> None:
    existing = {
        str(row["name"]) for row in connection.execute("PRAGMA table_info(route_operations)")
    }
    if "route_id" not in existing:
        connection.execute("ALTER TABLE route_operations ADD COLUMN route_id TEXT")
    if "supersedes_route_id" not in existing:
        connection.execute("ALTER TABLE route_operations ADD COLUMN supersedes_route_id TEXT")
    latest_by_capture: dict[str, str] = {}
    rows = tuple(
        connection.execute(
            "SELECT rowid, * FROM route_operations ORDER BY capture_id, recorded_at, rowid"
        )
    )
    for row in rows:
        capture_id = str(row["capture_id"])
        route_id = row["route_id"]
        if route_id is None:
            receipt_id = str(row["receipt_id"])
            route_id = "route_" + receipt_id.removeprefix("receipt_")
            connection.execute(
                """
                UPDATE route_operations
                SET route_id = ?, supersedes_route_id = ?, stage = 0
                WHERE rowid = ?
                """,
                (route_id, latest_by_capture.get(capture_id), row["rowid"]),
            )
        latest_by_capture[capture_id] = str(route_id)
    connection.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS route_identity_idx ON route_operations (route_id)"
    )
