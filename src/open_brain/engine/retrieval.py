"""Public-safe lexical retrieval and caller-scoped capability enforcement."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping
from typing import TYPE_CHECKING, cast

from open_brain.core.ids import portable_canonical_json_bytes
from open_brain.core.models import ContentOrigin
from open_brain.storage.filesystem import read_confined
from open_brain.storage.markdown import MarkdownFormatError, parse_markdown

from .contracts import (
    PublicProvenance,
    RetrievalResult,
    RetrievalTask,
    _LocalEngineOperations,
    project_public_result_text,
)
from .normalization import _TERM, _excerpt, _portable_id, _text

if TYPE_CHECKING:
    from .local import BrainEngine


class RetrievalOperations(_LocalEngineOperations):
    def _upsert_source_search(self, connection: sqlite3.Connection, capture: sqlite3.Row) -> None:
        provenance = {
            "capture_id": capture["capture_id"],
            "source_ref": capture["source_reference"],
        }
        self._upsert_search(
            connection,
            result_id=cast(str, capture["capture_id"]),
            capture_id=cast(str, capture["capture_id"]),
            record_type="source",
            payload_family=cast(str, capture["payload_family"]),
            space_id=cast(str | None, capture["space_id"]),
            title=f"{capture['payload_family']} source",
            body=cast(str, capture["search_text"]),
            trust=("third_party" if capture["source_origin"] == "third_party" else "owner"),
            provenance=provenance,
            canonical_path=None,
            updated_at=cast(str, capture["accepted_at"]),
        )

    def _upsert_canonical_search(
        self,
        connection: sqlite3.Connection,
        *,
        result_id: str,
        capture_id: str,
        payload_family: str,
        space_id: str,
        title: str,
        body: str,
        trust: str,
        canonical_path: str,
        updated_at: str,
    ) -> None:
        self._upsert_search(
            connection,
            result_id=result_id,
            capture_id=capture_id,
            record_type="canonical",
            payload_family=payload_family,
            space_id=space_id,
            title=title,
            body=body,
            trust=trust,
            provenance={"capture_id": capture_id, "source_ref": f"capture:{capture_id}"},
            canonical_path=canonical_path,
            updated_at=updated_at,
        )

    def _upsert_search(
        self,
        connection: sqlite3.Connection,
        *,
        result_id: str,
        capture_id: str,
        record_type: str,
        payload_family: str,
        space_id: str | None,
        title: str,
        body: str,
        trust: str,
        provenance: Mapping[str, str],
        canonical_path: str | None,
        updated_at: str,
    ) -> None:
        connection.execute(
            """
            INSERT INTO search_documents (
                result_id, capture_id, record_type, payload_family, space_id,
                title, body, trust, provenance_json, canonical_path, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(result_id) DO UPDATE SET
                space_id = excluded.space_id,
                title = excluded.title,
                body = excluded.body,
                trust = excluded.trust,
                provenance_json = excluded.provenance_json,
                canonical_path = excluded.canonical_path,
                updated_at = excluded.updated_at
            """,
            (
                result_id,
                capture_id,
                record_type,
                payload_family,
                space_id,
                title,
                body,
                trust,
                portable_canonical_json_bytes(dict(provenance)).decode("utf-8"),
                canonical_path,
                updated_at,
            ),
        )

    def _search(
        self,
        query: str,
        *,
        space_id: str | None,
        payload_family: str | None,
        record_type: str | None,
        limit: int,
        allowed_space_ids: frozenset[str] | None = None,
    ) -> tuple[RetrievalResult, ...]:
        query = _text(query, field="query", maximum=500)
        if space_id is not None:
            _portable_id(space_id, "space")
        if payload_family is not None and payload_family not in {
            "text",
            "reference_or_file",
            "event",
            "measurement",
        }:
            raise ValueError("invalid payload-family filter")
        if record_type is not None and record_type not in {"source", "canonical"}:
            raise ValueError("invalid record-type filter")
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("invalid result limit")
        if allowed_space_ids is not None:
            if not allowed_space_ids:
                return ()
            if any(
                _portable_id(identifier, "space") != identifier for identifier in allowed_space_ids
            ):
                raise ValueError("invalid allowed space")
            if space_id is not None and space_id not in allowed_space_ids:
                return ()
        clauses: list[str] = []
        parameters: list[object] = []
        if space_id is not None:
            clauses.append("space_id = ?")
            parameters.append(space_id)
        elif allowed_space_ids is not None:
            space_ids = tuple(sorted(allowed_space_ids))
            clauses.append("space_id IN (" + ", ".join("?" for _ in space_ids) + ")")
            parameters.extend(space_ids)
        if payload_family is not None:
            clauses.append("payload_family = ?")
            parameters.append(payload_family)
        if record_type is not None:
            clauses.append("record_type = ?")
            parameters.append(record_type)
        sql = "SELECT * FROM search_documents"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        connection = self._store.connect()
        try:
            rows = tuple(connection.execute(sql, parameters))
        finally:
            connection.close()
        terms = tuple(term.casefold() for term in _TERM.findall(query))
        ranked: list[tuple[int, RetrievalResult]] = []
        for row in rows:
            candidate = self._retrieval_result(row, query=query, terms=terms)
            if candidate is not None:
                ranked.append(candidate)
        ranked.sort(
            key=lambda item: (
                -item[0],
                0 if item[1].record_type == "canonical" else 1,
                item[1].title.casefold(),
                item[1].result_id,
            )
        )
        return tuple(result for _, result in ranked[:limit])

    def _fetch(
        self, result_id: str, *, allowed_space_ids: frozenset[str] | None = None
    ) -> RetrievalResult | None:
        if allowed_space_ids is not None:
            if not allowed_space_ids:
                return None
            if any(
                _portable_id(identifier, "space") != identifier for identifier in allowed_space_ids
            ):
                raise ValueError("invalid allowed space")
            space_ids = tuple(sorted(allowed_space_ids))
            sql = (
                "SELECT * FROM search_documents WHERE result_id = ? AND space_id IN ("
                + ", ".join("?" for _ in space_ids)
                + ")"
            )
            parameters: tuple[object, ...] = (result_id, *space_ids)
        else:
            sql = "SELECT * FROM search_documents WHERE result_id = ?"
            parameters = (result_id,)
        connection = self._store.connect()
        try:
            row = connection.execute(sql, parameters).fetchone()
        finally:
            connection.close()
        if row is None:
            return None
        result = self._retrieval_result(row, query="", terms=())
        return None if result is None else result[1]

    def _retrieval_result(
        self, row: sqlite3.Row, *, query: str, terms: tuple[str, ...]
    ) -> tuple[int, RetrievalResult] | None:
        title = cast(str, row["title"])
        body = cast(str, row["body"])
        canonical_path = cast(str | None, row["canonical_path"])
        if canonical_path is not None:
            payload = read_confined(
                root=self.profile.root,
                relative=canonical_path,
                expected_root_identity=self.profile.root_identity,
            )
            if payload is None:
                return None
            try:
                parsed = parse_markdown(payload)
                title = cast(str, parsed.fields["title"])
                body = parsed.body
            except (KeyError, MarkdownFormatError, TypeError):
                return None
        haystack = f"{title}\n{body}".casefold()
        phrase = query.casefold()
        if terms and not all(term in haystack for term in terms):
            return None
        score = sum(haystack.count(term) for term in terms)
        if phrase and phrase in haystack:
            score += 20
        if cast(str, row["record_type"]) == "canonical":
            score += 2
        if not terms:
            score = 1
        explanation = (
            "fetched by result identifier"
            if not terms
            else ("exact phrase match" if phrase in haystack else "lexical match")
        )
        provenance_value = json.loads(cast(str, row["provenance_json"]))
        if not isinstance(provenance_value, dict) or any(
            not isinstance(key, str) or not isinstance(value, str)
            for key, value in provenance_value.items()
        ):
            return None
        capture_id = cast(str, row["capture_id"])
        connection = self._store.connect()
        try:
            capture = connection.execute(
                "SELECT source_origin, source_reference, provenance_json "
                "FROM captures WHERE capture_id = ?",
                (capture_id,),
            ).fetchone()
        finally:
            connection.close()
        if capture is None:
            return None
        protected_literals = (cast(str, capture["source_reference"]),)
        public_title = project_public_result_text(title, protected_literals=protected_literals)
        public_body = project_public_result_text(body, protected_literals=protected_literals)
        public_explanation = project_public_result_text(
            explanation,
            protected_literals=protected_literals,
        )
        excerpt = _excerpt(public_body, terms)
        return (
            score,
            RetrievalResult(
                result_id=cast(str, row["result_id"]),
                capture_id=capture_id,
                record_type=cast(str, row["record_type"]),
                payload_family=cast(str, row["payload_family"]),
                space_id=cast(str | None, row["space_id"]),
                title=public_title,
                excerpt=excerpt,
                trust=cast(str, row["trust"]),
                provenance=PublicProvenance(
                    capture_id=capture_id,
                    source_origin=_public_source_origin(capture),
                ),
                explanation=public_explanation,
            ),
        )


def _public_source_origin(capture: sqlite3.Row) -> str:
    raw_provenance = capture["provenance_json"]
    if isinstance(raw_provenance, str):
        try:
            provenance = json.loads(raw_provenance)
        except json.JSONDecodeError:
            provenance = None
        if isinstance(provenance, dict):
            value = provenance.get("content_origin")
            if isinstance(value, str):
                try:
                    return ContentOrigin(value).value
                except ValueError:
                    pass
    return (
        ContentOrigin.OWNER_AUTHORED.value
        if capture["source_origin"] == "owner"
        else ContentOrigin.THIRD_PARTY.value
    )


class RetrievalTasks:
    def __init__(self, engine: BrainEngine) -> None:
        self._engine = engine

    def search(
        self,
        query: str,
        *,
        space_id: str | None = None,
        payload_family: str | None = None,
        record_type: str | None = None,
        limit: int = 10,
    ) -> tuple[RetrievalResult, ...]:
        return self._engine._search(
            query,
            space_id=space_id,
            payload_family=payload_family,
            record_type=record_type,
            limit=limit,
        )

    def fetch(self, result_id: str) -> RetrievalResult | None:
        return self._engine._fetch(result_id)

    def scoped(self, *, allowed_space_ids: frozenset[str]) -> ScopedRetrieval:
        return ScopedRetrieval(self, allowed_space_ids=allowed_space_ids)


class ScopedRetrieval:
    """Read-only retrieval restricted to a caller's explicit space allow-list."""

    def __init__(self, retrieval: RetrievalTask, *, allowed_space_ids: frozenset[str]) -> None:
        if not isinstance(allowed_space_ids, frozenset):
            raise ValueError("invalid allowed spaces")
        for space_id in allowed_space_ids:
            _portable_id(space_id, "space")
        self._retrieval = cast(RetrievalTasks, retrieval)
        self._allowed_space_ids = allowed_space_ids

    def search(
        self,
        query: str,
        *,
        space_id: str | None = None,
        payload_family: str | None = None,
        record_type: str | None = None,
        limit: int = 10,
    ) -> tuple[RetrievalResult, ...]:
        return self._retrieval._engine._search(
            query,
            space_id=space_id,
            payload_family=payload_family,
            record_type=record_type,
            limit=limit,
            allowed_space_ids=self._allowed_space_ids,
        )

    def fetch(self, result_id: str) -> RetrievalResult | None:
        return self._retrieval._engine._fetch(
            result_id,
            allowed_space_ids=self._allowed_space_ids,
        )
