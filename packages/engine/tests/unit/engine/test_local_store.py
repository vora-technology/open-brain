from __future__ import annotations

import sqlite3

from open_brain_engine.engine.local_store import _add_route_operation_columns


def test_legacy_route_operations_gain_stable_append_only_route_chain_ids() -> None:
    connection = sqlite3.connect(":memory:", isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute(
        """
        CREATE TABLE route_operations (
            delivery_id TEXT PRIMARY KEY,
            request_sha256 TEXT NOT NULL,
            capture_id TEXT NOT NULL,
            space_id TEXT NOT NULL,
            receipt_id TEXT NOT NULL UNIQUE,
            recorded_at TEXT NOT NULL,
            stage INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    capture_id = "capture_123e4567-e89b-42d3-a456-426614174100"
    rows = (
        (
            "delivery.first",
            "1" * 64,
            capture_id,
            "space_123e4567-e89b-42d3-a456-426614174004",
            "receipt_123e4567-e89b-42d3-a456-426614174120",
            "2026-08-30T12:00:00Z",
            1,
        ),
        (
            "delivery.second",
            "2" * 64,
            capture_id,
            "space_123e4567-e89b-42d3-a456-426614174014",
            "receipt_123e4567-e89b-42d3-a456-426614174121",
            "2026-08-30T12:01:00Z",
            1,
        ),
    )
    connection.executemany(
        """
        INSERT INTO route_operations (
            delivery_id, request_sha256, capture_id, space_id,
            receipt_id, recorded_at, stage
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )

    _add_route_operation_columns(connection)
    migrated = tuple(connection.execute("SELECT * FROM route_operations ORDER BY rowid"))

    assert [row["route_id"] for row in migrated] == [
        "route_123e4567-e89b-42d3-a456-426614174120",
        "route_123e4567-e89b-42d3-a456-426614174121",
    ]
    assert migrated[0]["supersedes_route_id"] is None
    assert migrated[1]["supersedes_route_id"] == migrated[0]["route_id"]
    assert [row["stage"] for row in migrated] == [0, 0]
    connection.close()
