"""Disposable local search-index generation from materialized Portable records."""

from __future__ import annotations

from dataclasses import dataclass

from open_brain.storage.sqlite import connect_database

from .contracts import LocalEngineContext
from .local_store import _LocalStore


@dataclass(frozen=True, slots=True)
class IndexBuild:
    generation: int
    documents: int


def rebuild_portable_index(profile: LocalEngineContext) -> IndexBuild:
    """Replace the disposable index from current materialized search documents."""
    state = _LocalStore(profile)
    state_connection = state.connect()
    try:
        rows = tuple(
            state_connection.execute(
                """
                SELECT result_id, capture_id, record_type, payload_family, space_id,
                       title, body, trust, provenance_json, canonical_path, updated_at
                FROM search_documents ORDER BY result_id
                """
            )
        )
    finally:
        state_connection.close()
    connection = connect_database(
        root=profile.root,
        database_name=".open-brain/indexes/search.sqlite3",
        expected_root_identity=profile.root_identity,
    )
    try:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS index_metadata (
                singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
                generation INTEGER NOT NULL
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
            """
        )
        previous = connection.execute(
            "SELECT generation FROM index_metadata WHERE singleton = 1"
        ).fetchone()
        generation = (int(previous["generation"]) if previous is not None else 0) + 1
        connection.execute("BEGIN IMMEDIATE")
        try:
            connection.execute("DELETE FROM search_documents")
            connection.executemany(
                """
                INSERT INTO search_documents (
                    result_id, capture_id, record_type, payload_family, space_id,
                    title, body, trust, provenance_json, canonical_path, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [tuple(row) for row in rows],
            )
            connection.execute(
                """
                INSERT INTO index_metadata (singleton, generation) VALUES (1, ?)
                ON CONFLICT(singleton) DO UPDATE SET generation = excluded.generation
                """,
                (generation,),
            )
            connection.execute("COMMIT")
        except BaseException:
            connection.execute("ROLLBACK")
            raise
    finally:
        connection.close()
    return IndexBuild(generation=generation, documents=len(rows))
