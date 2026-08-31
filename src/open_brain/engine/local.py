"""Portable, no-model task facades over one local Brain root."""

from __future__ import annotations

import base64
import json
import re
import sqlite3
import unicodedata
import uuid
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from hashlib import sha256
from pathlib import Path
from types import MappingProxyType
from typing import Protocol, cast

from open_brain.core.ids import canonicalize_source_url, portable_canonical_json_bytes
from open_brain.providers.base import EnrichmentState, ProviderMode
from open_brain.storage.filesystem import atomic_replace, atomic_write_new, read_confined
from open_brain.storage.locks import FileLease
from open_brain.storage.markdown import MarkdownFormatError, parse_markdown, render_markdown
from open_brain.storage.sqlite import connect_database

_MAX_TEXT = 65_536
_MAX_FILE_BYTES = 1_048_576
_MAX_NAME = 120
_MAX_REASON = 1_000
_DELIVERY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,199}$")
_EVENT_TYPE = re.compile(r"^[a-z][a-z0-9_.-]{0,63}$")
_MEDIA_TYPE = re.compile(r"^[a-z0-9.+-]+/[a-z0-9.+-]+$")
_UNIT = re.compile(r"^[a-zA-Z][a-zA-Z0-9_./-]{0,63}$")
_DECIMAL = re.compile(
    r"^(?=.{1,130}$)(?=(?:[^0-9]*[0-9]){1,128}$)"
    r"(?:0|-?(?:(?:[1-9][0-9]*)(?:\.[0-9]*[1-9])?|0\.[0-9]*[1-9]))$"
)
_TERM = re.compile(r"[A-Za-z0-9]+")


class CaptureAction(StrEnum):
    QUICK = "quick"
    CANONICAL_NOTE = "canonical_note"


class DecisionOutcome(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"
    EDITED = "edited"


class CaptureFault(StrEnum):
    AFTER_CAPTURE_RESERVATION = "after_capture_reservation"
    AFTER_BLOB_WRITE = "after_blob_write"
    AFTER_SOURCE_WRITE = "after_source_write"
    AFTER_AUTOMATIC_PROPOSAL_WRITE = "after_automatic_proposal_write"
    AFTER_AUTOMATIC_DECISION_WRITE = "after_automatic_decision_write"
    AFTER_CANONICAL_PAGE_WRITE = "after_canonical_page_write"
    AFTER_PUBLICATION_WRITE = "after_publication_write"
    AFTER_INDEX_UPDATE = "after_index_update"
    AFTER_SPACE_RESERVATION = "after_space_reservation"
    AFTER_SPACE_WRITE = "after_space_write"
    AFTER_ROUTE_RESERVATION = "after_route_reservation"
    AFTER_ROUTE_SOURCE_WRITE = "after_route_source_write"
    AFTER_PROPOSAL_RESERVATION = "after_proposal_reservation"
    AFTER_PROPOSAL_WRITE = "after_proposal_write"
    AFTER_DECISION_RESERVATION = "after_decision_reservation"
    AFTER_DECISION_WRITE = "after_decision_write"
    AFTER_REVIEW_PAGE_WRITE = "after_review_page_write"
    AFTER_REVIEW_PUBLICATION_WRITE = "after_review_publication_write"


class InjectedFault(RuntimeError):
    """Synthetic process interruption at one named durable boundary."""

    def __init__(self, point: CaptureFault) -> None:
        self.point = point
        super().__init__(point.value)


class Payload(Protocol):
    @property
    def family(self) -> str: ...

    def to_dict(self) -> dict[str, object]: ...

    def search_text(self) -> str: ...


@dataclass(frozen=True, slots=True)
class TextPayload:
    text: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "text", _text(self.text, field="text", maximum=_MAX_TEXT))

    @property
    def family(self) -> str:
        return "text"

    def to_dict(self) -> dict[str, object]:
        return {"family": self.family, "text": self.text}

    def search_text(self) -> str:
        return self.text


@dataclass(frozen=True, slots=True)
class ReferencePayload:
    url: str
    supplied_text: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "url", canonicalize_source_url(self.url))
        if self.supplied_text is not None:
            object.__setattr__(
                self,
                "supplied_text",
                _text(self.supplied_text, field="supplied text", maximum=_MAX_TEXT),
            )

    @property
    def family(self) -> str:
        return "reference_or_file"

    def to_dict(self) -> dict[str, object]:
        value: dict[str, object] = {"family": self.family, "kind": "reference", "url": self.url}
        if self.supplied_text is not None:
            value["supplied_text"] = self.supplied_text
        return value

    def search_text(self) -> str:
        return " ".join(part for part in (self.url, self.supplied_text) if part)


@dataclass(frozen=True, slots=True)
class FilePayload:
    file_name: str
    media_type: str
    data: bytes

    def __post_init__(self) -> None:
        name = _text(self.file_name, field="file name", maximum=255)
        if "/" in name or "\\" in name or name in {".", ".."}:
            raise ValueError("invalid file name")
        if not isinstance(self.media_type, str) or _MEDIA_TYPE.fullmatch(self.media_type) is None:
            raise ValueError("invalid media type")
        if not isinstance(self.data, bytes) or not self.data or len(self.data) > _MAX_FILE_BYTES:
            raise ValueError("invalid file payload")
        object.__setattr__(self, "file_name", name)

    @property
    def family(self) -> str:
        return "reference_or_file"

    @property
    def digest(self) -> str:
        return sha256(self.data).hexdigest()

    def to_dict(self) -> dict[str, object]:
        return {
            "blob_sha256": self.digest,
            "family": self.family,
            "file_name": self.file_name,
            "kind": "file",
            "media_type": self.media_type,
        }

    def search_text(self) -> str:
        try:
            decoded = self.data.decode("utf-8") if self.media_type.startswith("text/") else ""
        except UnicodeDecodeError:
            decoded = ""
        return f"{self.file_name} {self.media_type} {decoded}"


@dataclass(frozen=True, slots=True)
class EventPayload:
    event_type: str
    occurrence_at: str | None
    attributes: Mapping[str, str]

    def __post_init__(self) -> None:
        if not isinstance(self.event_type, str) or _EVENT_TYPE.fullmatch(self.event_type) is None:
            raise ValueError("invalid event type")
        object.__setattr__(self, "occurrence_at", _optional_timestamp(self.occurrence_at))
        object.__setattr__(self, "attributes", _attributes(self.attributes))

    @property
    def family(self) -> str:
        return "event"

    def to_dict(self) -> dict[str, object]:
        return {
            "attributes": _attribute_list(self.attributes),
            "event_type": self.event_type,
            "family": self.family,
            "occurrence_at": self.occurrence_at,
        }

    def search_text(self) -> str:
        return " ".join(
            (self.event_type, self.occurrence_at or "", *(_pairs(self.attributes)))
        )


@dataclass(frozen=True, slots=True)
class MeasurementPayload:
    value: str
    unit: str
    occurrence_at: str | None
    dimensions: Mapping[str, str]

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or _DECIMAL.fullmatch(self.value) is None:
            raise ValueError("invalid measurement value")
        if not isinstance(self.unit, str) or _UNIT.fullmatch(self.unit) is None:
            raise ValueError("invalid measurement unit")
        object.__setattr__(self, "occurrence_at", _optional_timestamp(self.occurrence_at))
        object.__setattr__(self, "dimensions", _attributes(self.dimensions))

    @property
    def family(self) -> str:
        return "measurement"

    def to_dict(self) -> dict[str, object]:
        return {
            "dimensions": _attribute_list(self.dimensions),
            "family": self.family,
            "occurrence_at": self.occurrence_at,
            "unit": self.unit,
            "value": self.value,
        }

    def search_text(self) -> str:
        return " ".join(
            (self.value, self.unit, self.occurrence_at or "", *(_pairs(self.dimensions)))
        )


@dataclass(frozen=True, slots=True)
class CaptureReceipt:
    capture_id: str
    payload_family: str
    state: str
    enrichment_state: str
    space_id: str | None
    canonical_path: str | None
    duplicate: bool = False


@dataclass(frozen=True, slots=True)
class InboxItem:
    capture_id: str
    payload_family: str
    state: str
    space_id: str | None
    intent: str | None
    capture_why: str | None


@dataclass(frozen=True, slots=True)
class SpaceRecord:
    space_id: str
    name: str
    slug: str


@dataclass(frozen=True, slots=True)
class RoutedCapture:
    capture_id: str
    space_id: str


@dataclass(frozen=True, slots=True)
class ProposalDraft:
    title: str
    markdown: str
    proposed_kind: str = "page_update"
    supplied_reason: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "title", _text(self.title, field="proposal title", maximum=200))
        object.__setattr__(
            self,
            "markdown",
            _text(self.markdown, field="proposal markdown", maximum=_MAX_TEXT),
        )
        if self.proposed_kind not in {"page_update", "event", "measurement", "action"}:
            raise ValueError("invalid proposal kind")
        if self.supplied_reason is not None:
            object.__setattr__(
                self,
                "supplied_reason",
                _text(self.supplied_reason, field="proposal reason", maximum=_MAX_REASON),
            )


@dataclass(frozen=True, slots=True)
class EnrichmentRequest:
    capture_id: str
    payload_family: str
    source_text: str

    def __post_init__(self) -> None:
        _portable_id(self.capture_id, "capture")
        if self.payload_family not in {
            "text",
            "reference_or_file",
            "event",
            "measurement",
        }:
            raise ValueError("invalid enrichment payload family")
        object.__setattr__(
            self,
            "source_text",
            _text(self.source_text, field="enrichment source", maximum=_MAX_TEXT + 512),
        )


class EnrichmentProvider(Protocol):
    def enrich(self, request: EnrichmentRequest) -> Sequence[ProposalDraft]: ...


class EnrichmentUnavailable(RuntimeError):
    """The selected enrichment provider is unavailable without changing capture state."""


@dataclass(frozen=True, slots=True)
class ProposalRecord:
    proposal_id: str
    capture_id: str
    proposed_kind: str
    status: str
    space_id: str | None
    sibling_proposal_ids: tuple[str, ...]
    terminal_decision_id: str | None


@dataclass(frozen=True, slots=True)
class DecisionRecord:
    decision_id: str
    proposal_id: str
    outcome: DecisionOutcome
    page_id: str | None
    publication_id: str | None
    duplicate: bool = False


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    result_id: str
    capture_id: str
    record_type: str
    payload_family: str
    space_id: str | None
    title: str
    excerpt: str
    trust: str
    provenance: Mapping[str, str]
    explanation: str


@dataclass(frozen=True, slots=True)
class LocalEngineContext:
    """Engine-owned values supplied by a deployment profile compiler."""

    root: Path
    tenant_id: str
    owner_actor_id: str
    owner_role_claim: Mapping[str, object]
    provider_mode: ProviderMode
    starter_spaces: tuple[str, ...]


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
    enrichment_state TEXT NOT NULL DEFAULT 'pending_enrichment'
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
        finally:
            connection.close()

    def connect(self) -> sqlite3.Connection:
        return connect_database(
            root=self.root,
            database_name=".open-brain/state/phase1.sqlite3",
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


class BrainEngine:
    """Concrete Phase 1 engine with task-shaped facades."""

    def __init__(
        self,
        profile: LocalEngineContext,
        *,
        faults: set[CaptureFault],
        clock: Callable[[], datetime],
        enrichment_provider: EnrichmentProvider | None,
    ) -> None:
        if profile.provider_mode is ProviderMode.CLOUD:
            raise ValueError("Phase 1 local engine does not enable cloud enrichment")
        if profile.provider_mode is ProviderMode.NONE and enrichment_provider is not None:
            raise ValueError("provider-none mode cannot construct an enrichment provider")
        if enrichment_provider is not None and not callable(
            getattr(enrichment_provider, "enrich", None)
        ):
            raise ValueError("invalid enrichment provider")
        self.profile = profile
        self._faults = set(faults)
        self._clock = clock
        self._enrichment_provider = enrichment_provider
        lease_identity = "engine-" + sha256(profile.owner_actor_id.encode("utf-8")).hexdigest()[:32]
        self._writer_lease = FileLease(profile.root / ".open-brain", lease_identity, clock=clock)
        with self._writer_lease.acquire_shared_writer():
            self._store = _LocalStore(profile)
        self.capture = CaptureTasks(self)
        self.inbox = InboxSpaceTasks(self)
        self.review = ReviewTasks(self)
        self.retrieval = RetrievalTasks(self)

    @classmethod
    def open(
        cls,
        profile: LocalEngineContext,
        *,
        faults: set[CaptureFault] | None = None,
        clock: Callable[[], datetime] | None = None,
        enrichment_provider: EnrichmentProvider | None = None,
    ) -> BrainEngine:
        if not isinstance(profile, LocalEngineContext):
            raise ValueError("invalid local profile")
        engine = cls(
            profile,
            faults=faults or set(),
            clock=clock or _utc_now,
            enrichment_provider=enrichment_provider,
        )
        with engine._writer_lease.acquire_shared_writer():
            engine._recover()
            for name in profile.starter_spaces:
                key = sha256(name.encode("utf-8")).hexdigest()
                engine._space_operation("create", None, name, f"starter.{key}")
        return engine

    def recover(self) -> int:
        with self._writer_lease.acquire_shared_writer():
            return self._recover()

    def _recover(self) -> int:
        recovered = 0
        for table, processor in (
            ("space_operations", self._process_space_operation),
            ("captures", self._process_capture),
            ("route_operations", self._process_route),
            ("proposal_sets", self._process_proposal_set),
            ("decisions", self._process_decision),
        ):
            connection = self._store.connect()
            try:
                rows = tuple(
                    connection.execute(
                        f"SELECT * FROM {table} WHERE stage < ?", (_done(table),)
                    )
                )
            finally:
                connection.close()
            for row in rows:
                processor(row)
                recovered += 1
        return recovered

    def _fault(self, point: CaptureFault) -> None:
        if point in self._faults:
            self._faults.remove(point)
            raise InjectedFault(point)

    def _accept_capture(
        self,
        payload: Payload,
        *,
        delivery_id: str,
        action: CaptureAction,
        space_id: str | None,
        intent: str | None,
        capture_why: str | None,
        title: str | None,
    ) -> CaptureReceipt:
        _delivery_id(delivery_id)
        if not isinstance(
            payload,
            TextPayload | ReferencePayload | FilePayload | EventPayload | MeasurementPayload,
        ):
            raise ValueError("invalid capture payload")
        action = CaptureAction(action)
        intent = _optional_text(intent, field="intent", maximum=120)
        capture_why = _optional_text(
            capture_why, field="capture reason", maximum=_MAX_REASON
        )
        title = _optional_text(title, field="title", maximum=200)
        if space_id is not None:
            _portable_id(space_id, "space")
        if action is CaptureAction.CANONICAL_NOTE and not isinstance(payload, TextPayload):
            raise ValueError("canonical note requires owner text")
        payload_bytes = portable_canonical_json_bytes(payload.to_dict())
        source_origin = "third_party" if isinstance(payload, ReferencePayload) else "owner"
        source_reference = (
            payload.url
            if isinstance(payload, ReferencePayload)
            else "urn:open-brain:local:" + sha256(payload_bytes).hexdigest()
        )
        request = {
            "action": action.value,
            "capture_why": capture_why,
            "intent": intent,
            "payload": payload.to_dict(),
            "source_origin": source_origin,
            "space_id": space_id,
            "title": title,
        }
        request_sha = sha256(portable_canonical_json_bytes(request)).hexdigest()
        duplicate = False
        conflict: tuple[str, str] | None = None
        with self._store.transaction() as connection:
            existing = connection.execute(
                "SELECT * FROM captures WHERE delivery_id = ?", (delivery_id,)
            ).fetchone()
            if existing is not None:
                if cast(str, existing["request_sha256"]) != request_sha:
                    conflict = (cast(str, existing["request_sha256"]), request_sha)
                else:
                    duplicate = True
                    capture_id = cast(str, existing["capture_id"])
            else:
                if space_id is not None and _space_row(connection, space_id) is None:
                    raise ValueError("unknown space")
                if action is CaptureAction.CANONICAL_NOTE and space_id is None:
                    raise ValueError("canonical note requires a space")
                capture_id = _new_id("capture")
                accepted_at = _timestamp(self._clock())
                canonical = action is CaptureAction.CANONICAL_NOTE
                connection.execute(
                    """
                    INSERT INTO captures (
                        delivery_id, request_sha256, capture_id, accepted_receipt_id,
                        payload_family, payload_json, search_text, file_bytes,
                        source_origin, source_reference, space_id, intent, capture_why,
                        action, title, accepted_at, auto_proposal_id,
                        auto_proposal_receipt_id, auto_decision_id,
                        auto_decision_receipt_id, page_id, publication_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        delivery_id,
                        request_sha,
                        capture_id,
                        _new_id("receipt"),
                        payload.family,
                        payload_bytes,
                        payload.search_text(),
                        payload.data if isinstance(payload, FilePayload) else None,
                        source_origin,
                        source_reference,
                        space_id,
                        intent,
                        capture_why,
                        action.value,
                        title,
                        accepted_at,
                        _new_id("proposal") if canonical else None,
                        _new_id("receipt") if canonical else None,
                        _new_id("decision") if canonical else None,
                        _new_id("receipt") if canonical else None,
                        _new_id("page") if canonical else None,
                        _new_id("publication") if canonical else None,
                    ),
                )
        if conflict is not None:
            self._quarantine(delivery_id, expected=conflict[0], actual=conflict[1])
            raise ValueError("conflicting delivery")
        if not duplicate:
            self._fault(CaptureFault.AFTER_CAPTURE_RESERVATION)
        row = self._capture_row(capture_id)
        self._process_capture(row)
        receipt = self._capture_receipt(capture_id)
        if receipt is None:
            raise RuntimeError("capture state unavailable")
        return CaptureReceipt(
            capture_id=receipt.capture_id,
            payload_family=receipt.payload_family,
            state=receipt.state,
            enrichment_state=receipt.enrichment_state,
            space_id=receipt.space_id,
            canonical_path=receipt.canonical_path,
            duplicate=duplicate,
        )

    def _capture_row(self, capture_id: str) -> sqlite3.Row:
        _portable_id(capture_id, "capture")
        connection = self._store.connect()
        try:
            row = connection.execute(
                "SELECT * FROM captures WHERE capture_id = ?", (capture_id,)
            ).fetchone()
        finally:
            connection.close()
        if row is None:
            raise ValueError("unknown capture")
        return cast(sqlite3.Row, row)

    def _process_capture(self, supplied_row: sqlite3.Row) -> None:
        row = self._capture_row(cast(str, supplied_row["capture_id"]))
        stage = cast(int, row["stage"])
        if stage < 1:
            payload = _payload_dict(row)
            if cast(bytes | None, row["file_bytes"]) is not None:
                digest = cast(str, payload["blob_sha256"])
                atomic_write_new(
                    root=self.profile.root,
                    relative=f"sources/blobs/sha256/{digest[:2]}/{digest}",
                    data=cast(bytes, row["file_bytes"]),
                )
                self._fault(CaptureFault.AFTER_BLOB_WRITE)
            source_path = _dated_path(
                "sources/captures", cast(str, row["accepted_at"]), cast(str, row["capture_id"])
            )
            atomic_write_new(
                root=self.profile.root,
                relative=source_path,
                data=portable_canonical_json_bytes(self._capture_record(row)),
            )
            self._fault(CaptureFault.AFTER_SOURCE_WRITE)
            with self._store.transaction() as connection:
                connection.execute(
                    "UPDATE captures SET source_path = ?, stage = 1 WHERE capture_id = ?",
                    (source_path, row["capture_id"]),
                )
            row = self._capture_row(cast(str, row["capture_id"]))
            stage = 1
        if stage < 2:
            if cast(str, row["action"]) == CaptureAction.CANONICAL_NOTE.value:
                proposal_path, decision_path, canonical_path, publication_path = (
                    self._write_automatic_publication(row)
                )
                del proposal_path, decision_path
                with self._store.transaction() as connection:
                    connection.execute(
                        """
                        UPDATE captures
                        SET canonical_path = ?, publication_path = ?, stage = 2
                        WHERE capture_id = ?
                        """,
                        (canonical_path, publication_path, row["capture_id"]),
                    )
            else:
                with self._store.transaction() as connection:
                    connection.execute(
                        "UPDATE captures SET stage = 2 WHERE capture_id = ?",
                        (row["capture_id"],),
                    )
            row = self._capture_row(cast(str, row["capture_id"]))
            stage = 2
        if stage < 3:
            with self._store.transaction() as connection:
                self._upsert_source_search(connection, row)
                if cast(str | None, row["canonical_path"]) is not None:
                    self._upsert_canonical_search(
                        connection,
                        result_id=cast(str, row["page_id"]),
                        capture_id=cast(str, row["capture_id"]),
                        payload_family=cast(str, row["payload_family"]),
                        space_id=cast(str, row["space_id"]),
                        title=self._capture_title(row),
                        body=cast(str, row["search_text"]),
                        trust="owner",
                        canonical_path=cast(str, row["canonical_path"]),
                        updated_at=cast(str, row["accepted_at"]),
                    )
                connection.execute(
                    "UPDATE captures SET stage = 3 WHERE capture_id = ?", (row["capture_id"],)
                )
            self._fault(CaptureFault.AFTER_INDEX_UPDATE)

    def _capture_record(self, row: sqlite3.Row) -> dict[str, object]:
        payload = _payload_dict(row)
        payload_bytes = portable_canonical_json_bytes(payload)
        capture_id = cast(str, row["capture_id"])
        original: dict[str, object]
        if cast(bytes | None, row["file_bytes"]) is not None:
            original = {"blob_sha256": cast(str, payload["blob_sha256"]), "kind": "blob"}
            original_digest = cast(str, payload["blob_sha256"])
        else:
            original_digest = sha256(payload_bytes).hexdigest()
            original = {
                "bytes_base64": base64.b64encode(payload_bytes).decode("ascii"),
                "kind": "inline",
                "sha256": original_digest,
            }
        accepted_payload = {
            "capture_id": capture_id,
            "original_payload_sha256": original_digest,
            "payload_sha256": sha256(payload_bytes).hexdigest(),
        }
        receipts = [
            _receipt(
                "capture_accepted",
                cast(str, row["accepted_receipt_id"]),
                capture_id,
                cast(str, row["accepted_at"]),
                accepted_payload,
            )
        ]
        connection = self._store.connect()
        try:
            routes = tuple(
                connection.execute(
                    "SELECT * FROM route_operations WHERE capture_id = ? "
                    "ORDER BY recorded_at, delivery_id",
                    (capture_id,),
                )
            )
        finally:
            connection.close()
        receipts.extend(
            _receipt(
                "routing",
                cast(str, route["receipt_id"]),
                capture_id,
                cast(str, route["recorded_at"]),
                {"capture_id": capture_id, "space_id": cast(str, route["space_id"])},
            )
            for route in routes
        )
        origin = cast(str, row["source_origin"])
        return {
            "accepted_at": row["accepted_at"],
            "actor_id": self.profile.owner_actor_id,
            "capture_id": capture_id,
            "capture_why": row["capture_why"],
            "intent": row["intent"],
            "original_payload": original,
            "payload": payload,
            "payload_binding": {
                "kind": "inline",
                "payload_sha256": sha256(payload_bytes).hexdigest(),
            },
            "payload_schema_version": 1,
            "privacy": _privacy(),
            "provenance": {
                "content_origin": "third_party" if origin == "third_party" else "owner_authored",
                "owner_context": (
                    "automation_absent" if origin == "third_party" else "owner_authored"
                ),
                "source_ref": row["source_reference"],
                "transformation_receipts": [],
            },
            "receipt_refs": receipts,
            "role_claim": _role_claim(self.profile),
            "schema_version": 1,
            "source": {"origin": origin, "reference": row["source_reference"]},
            "space_id": row["space_id"],
            "tenant_id": self.profile.tenant_id,
            "trust": _trust(
                self.profile,
                cast(str, row["accepted_at"]),
                "third_party" if origin == "third_party" else "owner",
                "captured source material" if origin == "third_party" else "owner supplied capture",
            ),
        }

    def _write_automatic_publication(
        self, row: sqlite3.Row
    ) -> tuple[str, str, str, str]:
        page_bytes = self._canonical_page_bytes(row, trust="owner")
        proposal = self._proposal_record(
            row,
            proposal_id=cast(str, row["auto_proposal_id"]),
            receipt_id=cast(str, row["auto_proposal_receipt_id"]),
            proposed_bytes=page_bytes,
            proposed_kind="page_update",
            sibling_ids=(cast(str, row["auto_proposal_id"]),),
            supplied_reason="explicit canonical-note action",
            recorded_at=cast(str, row["accepted_at"]),
        )
        proposal_path = _dated_path(
            "history/proposals",
            cast(str, row["accepted_at"]),
            cast(str, row["auto_proposal_id"]),
        )
        atomic_write_new(
            root=self.profile.root,
            relative=proposal_path,
            data=portable_canonical_json_bytes(proposal),
        )
        self._fault(CaptureFault.AFTER_AUTOMATIC_PROPOSAL_WRITE)
        decision = _decision_record(
            profile=self.profile,
            proposal=proposal,
            decision_id=cast(str, row["auto_decision_id"]),
            outcome=DecisionOutcome.APPROVED,
            edited_bytes=None,
            recorded_at=cast(str, row["accepted_at"]),
        )
        decision_path = _dated_path(
            "history/decisions",
            cast(str, row["accepted_at"]),
            cast(str, row["auto_decision_id"]),
        )
        atomic_write_new(
            root=self.profile.root,
            relative=decision_path,
            data=portable_canonical_json_bytes(decision),
        )
        self._fault(CaptureFault.AFTER_AUTOMATIC_DECISION_WRITE)
        canonical_path = self._canonical_path(
            cast(str, row["space_id"]), cast(str, row["page_id"])
        )
        atomic_write_new(root=self.profile.root, relative=canonical_path, data=page_bytes)
        self._fault(CaptureFault.AFTER_CANONICAL_PAGE_WRITE)
        publication = _publication_record(
            profile=self.profile,
            decision_id=cast(str, row["auto_decision_id"]),
            page_id=cast(str, row["page_id"]),
            publication_id=cast(str, row["publication_id"]),
            published_path=canonical_path,
            published_bytes=page_bytes,
            recorded_at=cast(str, row["accepted_at"]),
        )
        publication_path = _dated_path(
            "history/publications",
            cast(str, row["accepted_at"]),
            cast(str, row["publication_id"]),
        )
        atomic_write_new(
            root=self.profile.root,
            relative=publication_path,
            data=portable_canonical_json_bytes(publication),
        )
        self._fault(CaptureFault.AFTER_PUBLICATION_WRITE)
        return proposal_path, decision_path, canonical_path, publication_path

    def _capture_title(self, row: sqlite3.Row) -> str:
        supplied = cast(str | None, row["title"])
        if supplied is not None:
            return supplied
        first = next(
            (
                line.strip().lstrip("#").strip()
                for line in cast(str, row["search_text"]).splitlines()
                if line.strip()
            ),
            "Untitled note",
        )
        return first[:200]

    def _canonical_page_bytes(self, row: sqlite3.Row, *, trust: str) -> bytes:
        body = cast(str, row["search_text"])
        rendered = render_markdown(
            fields={
                "actor_id": self.profile.owner_actor_id,
                "modified_at": row["accepted_at"],
                "page_id": row["page_id"],
                "privacy": _privacy(),
                "provenance": [row["capture_id"]],
                "role_claim": _role_claim(self.profile),
                "schema_version": 1,
                "space_id": row["space_id"],
                "status": "active",
                "tenant_id": self.profile.tenant_id,
                "title": self._capture_title(row),
                "trust": trust,
            },
            body=body if body.endswith("\n") else body + "\n",
        )
        return rendered.encode("utf-8")

    def _capture_receipt(self, capture_id: str) -> CaptureReceipt | None:
        connection = self._store.connect()
        try:
            row = connection.execute(
                "SELECT * FROM captures WHERE capture_id = ?", (capture_id,)
            ).fetchone()
        finally:
            connection.close()
        if row is None:
            return None
        return CaptureReceipt(
            capture_id=cast(str, row["capture_id"]),
            payload_family=cast(str, row["payload_family"]),
            state=(
                "published"
                if cast(str | None, row["canonical_path"]) is not None
                else "inbox"
            ),
            enrichment_state=cast(str, row["enrichment_state"]),
            space_id=cast(str | None, row["space_id"]),
            canonical_path=cast(str | None, row["canonical_path"]),
        )

    def _list_inbox(self, *, unassigned_only: bool) -> tuple[InboxItem, ...]:
        sql = "SELECT * FROM captures WHERE action = ?"
        parameters: list[object] = [CaptureAction.QUICK.value]
        if unassigned_only:
            sql += " AND space_id IS NULL"
        sql += " ORDER BY accepted_at, capture_id"
        connection = self._store.connect()
        try:
            rows = tuple(connection.execute(sql, parameters))
        finally:
            connection.close()
        return tuple(
            InboxItem(
                capture_id=cast(str, row["capture_id"]),
                payload_family=cast(str, row["payload_family"]),
                state="inbox",
                space_id=cast(str | None, row["space_id"]),
                intent=cast(str | None, row["intent"]),
                capture_why=cast(str | None, row["capture_why"]),
            )
            for row in rows
        )

    def _space_operation(
        self, operation: str, space_id: str | None, name: str, delivery_id: str
    ) -> SpaceRecord:
        _delivery_id(delivery_id)
        name = _text(name, field="space name", maximum=_MAX_NAME)
        if operation not in {"create", "rename"}:
            raise ValueError("invalid space operation")
        if space_id is not None:
            _portable_id(space_id, "space")
        request_sha = sha256(
            portable_canonical_json_bytes(
                {"name": name, "operation": operation, "space_id": space_id}
            )
        ).hexdigest()
        conflict: tuple[str, str] | None = None
        created = False
        with self._store.transaction() as connection:
            existing = connection.execute(
                "SELECT * FROM space_operations WHERE delivery_id = ?", (delivery_id,)
            ).fetchone()
            if existing is not None:
                if cast(str, existing["request_sha256"]) != request_sha:
                    conflict = (cast(str, existing["request_sha256"]), request_sha)
                target_id = cast(str, existing["space_id"])
            else:
                now = _timestamp(self._clock())
                if operation == "create":
                    target_id = _new_id("space")
                    slug = _slug(name, target_id)
                    connection.execute(
                        "INSERT INTO spaces (space_id, name, slug, updated_at) VALUES (?, ?, ?, ?)",
                        (target_id, name, slug, now),
                    )
                else:
                    if space_id is None or _space_row(connection, space_id) is None:
                        raise ValueError("unknown space")
                    target_id = space_id
                    connection.execute(
                        "UPDATE spaces SET name = ?, updated_at = ? WHERE space_id = ?",
                        (name, now, target_id),
                    )
                connection.execute(
                    """
                    INSERT INTO space_operations (
                        delivery_id, request_sha256, operation, space_id, name,
                        receipt_id, recorded_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (delivery_id, request_sha, operation, target_id, name, _new_id("receipt"), now),
                )
                created = True
        if conflict is not None:
            self._quarantine(delivery_id, expected=conflict[0], actual=conflict[1])
            raise ValueError("conflicting delivery")
        if created:
            self._fault(CaptureFault.AFTER_SPACE_RESERVATION)
        self._process_space_operation(self._space_operation_row(delivery_id))
        return self._space(target_id)

    def _space_operation_row(self, delivery_id: str) -> sqlite3.Row:
        connection = self._store.connect()
        try:
            row = connection.execute(
                "SELECT * FROM space_operations WHERE delivery_id = ?", (delivery_id,)
            ).fetchone()
        finally:
            connection.close()
        if row is None:
            raise ValueError("unknown space operation")
        return cast(sqlite3.Row, row)

    def _process_space_operation(self, supplied_row: sqlite3.Row) -> None:
        row = self._space_operation_row(cast(str, supplied_row["delivery_id"]))
        if cast(int, row["stage"]) >= 1:
            return
        space = self._space(cast(str, row["space_id"]))
        relative = f"content/spaces/{space.slug}/_space.md"
        payload = render_markdown(
            fields={
                "actor_id": self.profile.owner_actor_id,
                "name": space.name,
                "role_claim": _role_claim(self.profile),
                "schema_version": 1,
                "slug": space.slug,
                "space_id": space.space_id,
                "tenant_id": self.profile.tenant_id,
            },
            body="",
        ).encode("utf-8")
        if cast(str, row["operation"]) == "create":
            atomic_write_new(root=self.profile.root, relative=relative, data=payload)
        else:
            atomic_replace(root=self.profile.root, relative=relative, data=payload)
        self._fault(CaptureFault.AFTER_SPACE_WRITE)
        with self._store.transaction() as connection:
            connection.execute(
                "UPDATE space_operations SET stage = 1 WHERE delivery_id = ?",
                (row["delivery_id"],),
            )

    def _space(self, space_id: str) -> SpaceRecord:
        connection = self._store.connect()
        try:
            row = _space_row(connection, space_id)
        finally:
            connection.close()
        if row is None:
            raise ValueError("unknown space")
        return SpaceRecord(
            space_id=cast(str, row["space_id"]),
            name=cast(str, row["name"]),
            slug=cast(str, row["slug"]),
        )

    def _list_spaces(self) -> tuple[SpaceRecord, ...]:
        connection = self._store.connect()
        try:
            rows = tuple(connection.execute("SELECT * FROM spaces ORDER BY name, space_id"))
        finally:
            connection.close()
        return tuple(
            SpaceRecord(
                space_id=cast(str, row["space_id"]),
                name=cast(str, row["name"]),
                slug=cast(str, row["slug"]),
            )
            for row in rows
        )

    def _canonical_path(self, space_id: str, page_id: str) -> str:
        space = self._space(space_id)
        return f"content/spaces/{space.slug}/notes/{page_id}.md"

    def _route_capture(
        self, capture_id: str, space_id: str, delivery_id: str
    ) -> RoutedCapture:
        _portable_id(capture_id, "capture")
        _portable_id(space_id, "space")
        _delivery_id(delivery_id)
        request_sha = sha256(
            portable_canonical_json_bytes({"capture_id": capture_id, "space_id": space_id})
        ).hexdigest()
        conflict: tuple[str, str] | None = None
        created = False
        with self._store.transaction() as connection:
            existing = connection.execute(
                "SELECT * FROM route_operations WHERE delivery_id = ?", (delivery_id,)
            ).fetchone()
            if existing is not None:
                if cast(str, existing["request_sha256"]) != request_sha:
                    conflict = (cast(str, existing["request_sha256"]), request_sha)
            else:
                capture = connection.execute(
                    "SELECT * FROM captures WHERE capture_id = ?", (capture_id,)
                ).fetchone()
                if capture is None or _space_row(connection, space_id) is None:
                    raise ValueError("unknown route target")
                if cast(str, capture["action"]) == CaptureAction.CANONICAL_NOTE.value:
                    raise ValueError("published capture cannot be rerouted")
                now = _timestamp(self._clock())
                connection.execute(
                    """
                    INSERT INTO route_operations (
                        delivery_id, request_sha256, capture_id, space_id, receipt_id, recorded_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (delivery_id, request_sha, capture_id, space_id, _new_id("receipt"), now),
                )
                connection.execute(
                    "UPDATE captures SET space_id = ? WHERE capture_id = ?", (space_id, capture_id)
                )
                created = True
        if conflict is not None:
            self._quarantine(delivery_id, expected=conflict[0], actual=conflict[1])
            raise ValueError("conflicting delivery")
        if created:
            self._fault(CaptureFault.AFTER_ROUTE_RESERVATION)
        self._process_route(self._route_row(delivery_id))
        return RoutedCapture(capture_id=capture_id, space_id=space_id)

    def _route_row(self, delivery_id: str) -> sqlite3.Row:
        connection = self._store.connect()
        try:
            row = connection.execute(
                "SELECT * FROM route_operations WHERE delivery_id = ?", (delivery_id,)
            ).fetchone()
        finally:
            connection.close()
        if row is None:
            raise ValueError("unknown route")
        return cast(sqlite3.Row, row)

    def _process_route(self, supplied_row: sqlite3.Row) -> None:
        row = self._route_row(cast(str, supplied_row["delivery_id"]))
        if cast(int, row["stage"]) >= 1:
            return
        capture = self._capture_row(cast(str, row["capture_id"]))
        source_path = cast(str | None, capture["source_path"])
        if source_path is None:
            self._process_capture(capture)
            capture = self._capture_row(cast(str, row["capture_id"]))
            source_path = cast(str, capture["source_path"])
        atomic_replace(
            root=self.profile.root,
            relative=source_path,
            data=portable_canonical_json_bytes(self._capture_record(capture)),
        )
        self._fault(CaptureFault.AFTER_ROUTE_SOURCE_WRITE)
        with self._store.transaction() as connection:
            connection.execute(
                "UPDATE search_documents SET space_id = ?, updated_at = ? WHERE capture_id = ?",
                (row["space_id"], row["recorded_at"], row["capture_id"]),
            )
            connection.execute(
                "UPDATE route_operations SET stage = 1 WHERE delivery_id = ?",
                (row["delivery_id"],),
            )

    def _quarantine(self, delivery_id: str, *, expected: str, actual: str) -> None:
        marker = sha256(delivery_id.encode("utf-8")).hexdigest()
        payload = {
            "actual_sha256": actual,
            "delivery_id_sha256": marker,
            "expected_sha256": expected,
            "recorded_at": _timestamp(self._clock()),
            "schema_version": 1,
        }
        atomic_write_new(
            root=self.profile.root,
            relative=f".open-brain/quarantine/{marker}-{uuid.uuid4()}.json",
            data=portable_canonical_json_bytes(payload),
        )

    def _propose(
        self, capture_id: str, drafts: Sequence[ProposalDraft], delivery_id: str
    ) -> tuple[ProposalRecord, ...]:
        _portable_id(capture_id, "capture")
        _delivery_id(delivery_id)
        if (
            isinstance(drafts, str)
            or not isinstance(drafts, Sequence)
            or not 1 <= len(drafts) <= 8
            or any(not isinstance(draft, ProposalDraft) for draft in drafts)
        ):
            raise ValueError("invalid proposal set")
        request_value = {
            "capture_id": capture_id,
            "drafts": [
                {
                    "markdown": draft.markdown,
                    "proposed_kind": draft.proposed_kind,
                    "supplied_reason": draft.supplied_reason,
                    "title": draft.title,
                }
                for draft in drafts
            ],
        }
        request_sha = sha256(portable_canonical_json_bytes(request_value)).hexdigest()
        conflict: tuple[str, str] | None = None
        created = False
        with self._store.transaction() as connection:
            existing = connection.execute(
                "SELECT * FROM proposal_sets WHERE delivery_id = ?", (delivery_id,)
            ).fetchone()
            if existing is not None:
                if cast(str, existing["request_sha256"]) != request_sha:
                    conflict = (cast(str, existing["request_sha256"]), request_sha)
            else:
                capture = connection.execute(
                    "SELECT * FROM captures WHERE capture_id = ?", (capture_id,)
                ).fetchone()
                if capture is None:
                    raise ValueError("unknown capture")
                if any(
                    draft.proposed_kind == "page_update" for draft in drafts
                ) and capture["space_id"] is None:
                    raise ValueError("page proposal requires routed capture")
                now = _timestamp(self._clock())
                proposal_ids = tuple(_new_id("proposal") for _ in drafts)
                connection.execute(
                    """
                    INSERT INTO proposal_sets (
                        delivery_id, request_sha256, capture_id, recorded_at
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (delivery_id, request_sha, capture_id, now),
                )
                for proposal_id, draft in zip(proposal_ids, drafts, strict=True):
                    page_id = _new_id("page") if draft.proposed_kind == "page_update" else None
                    proposed_bytes = (
                        self._proposal_page_bytes(
                            capture,
                            page_id=page_id,
                            title=draft.title,
                            body=draft.markdown,
                            modified_at=now,
                        )
                        if page_id is not None
                        else portable_canonical_json_bytes(
                            {"kind": draft.proposed_kind, "text": draft.markdown}
                        )
                    )
                    canonical_path = (
                        self._canonical_path(
                            cast(str, capture["space_id"]), page_id
                        )
                        if page_id is not None
                        else None
                    )
                    connection.execute(
                        """
                        INSERT INTO proposals (
                            proposal_id, set_delivery_id, capture_id, proposed_kind,
                            title, body, proposed_bytes, supplied_reason, space_id,
                            receipt_id, page_id, canonical_path
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            proposal_id,
                            delivery_id,
                            capture_id,
                            draft.proposed_kind,
                            draft.title,
                            draft.markdown,
                            proposed_bytes,
                            draft.supplied_reason,
                            capture["space_id"],
                            _new_id("receipt"),
                            page_id,
                            canonical_path,
                        ),
                    )
                created = True
        if conflict is not None:
            self._quarantine(delivery_id, expected=conflict[0], actual=conflict[1])
            raise ValueError("conflicting delivery")
        if created:
            self._fault(CaptureFault.AFTER_PROPOSAL_RESERVATION)
        self._process_proposal_set(self._proposal_set_row(delivery_id))
        return self._list_proposals(capture_id=capture_id, status=None, set_delivery_id=delivery_id)

    def _proposal_page_bytes(
        self,
        capture: sqlite3.Row,
        *,
        page_id: str,
        title: str,
        body: str,
        modified_at: str,
    ) -> bytes:
        return render_markdown(
            fields={
                "actor_id": self.profile.owner_actor_id,
                "modified_at": modified_at,
                "page_id": page_id,
                "privacy": _privacy(),
                "provenance": [capture["capture_id"]],
                "role_claim": _role_claim(self.profile),
                "schema_version": 1,
                "space_id": capture["space_id"],
                "status": "active",
                "tenant_id": self.profile.tenant_id,
                "title": title,
                "trust": "reviewed",
            },
            body=body if body.endswith("\n") else body + "\n",
        ).encode("utf-8")

    def _proposal_set_row(self, delivery_id: str) -> sqlite3.Row:
        connection = self._store.connect()
        try:
            row = connection.execute(
                "SELECT * FROM proposal_sets WHERE delivery_id = ?", (delivery_id,)
            ).fetchone()
        finally:
            connection.close()
        if row is None:
            raise ValueError("unknown proposal set")
        return cast(sqlite3.Row, row)

    def _proposal_rows(self, delivery_id: str) -> tuple[sqlite3.Row, ...]:
        connection = self._store.connect()
        try:
            return tuple(
                connection.execute(
                    "SELECT * FROM proposals WHERE set_delivery_id = ? ORDER BY proposal_id",
                    (delivery_id,),
                )
            )
        finally:
            connection.close()

    def _process_proposal_set(self, supplied_row: sqlite3.Row) -> None:
        row = self._proposal_set_row(cast(str, supplied_row["delivery_id"]))
        if cast(int, row["stage"]) >= 1:
            return
        proposals = self._proposal_rows(cast(str, row["delivery_id"]))
        siblings = tuple(cast(str, proposal["proposal_id"]) for proposal in proposals)
        capture = self._capture_row(cast(str, row["capture_id"]))
        for proposal in proposals:
            record = self._proposal_record(
                capture,
                proposal_id=cast(str, proposal["proposal_id"]),
                receipt_id=cast(str, proposal["receipt_id"]),
                proposed_bytes=cast(bytes, proposal["proposed_bytes"]),
                proposed_kind=cast(str, proposal["proposed_kind"]),
                sibling_ids=siblings,
                supplied_reason=cast(str | None, proposal["supplied_reason"]),
                recorded_at=cast(str, row["recorded_at"]),
            )
            path = _dated_path(
                "history/proposals",
                cast(str, row["recorded_at"]),
                cast(str, proposal["proposal_id"]),
            )
            atomic_write_new(
                root=self.profile.root,
                relative=path,
                data=portable_canonical_json_bytes(record),
            )
        self._fault(CaptureFault.AFTER_PROPOSAL_WRITE)
        with self._store.transaction() as connection:
            connection.execute(
                "UPDATE proposal_sets SET stage = 1 WHERE delivery_id = ?",
                (row["delivery_id"],),
            )

    def _proposal_record(
        self,
        capture: sqlite3.Row,
        *,
        proposal_id: str,
        receipt_id: str,
        proposed_bytes: bytes,
        proposed_kind: str,
        sibling_ids: tuple[str, ...],
        supplied_reason: str | None,
        recorded_at: str,
    ) -> dict[str, object]:
        excerpt = cast(str, capture["search_text"]).strip()[:512] or cast(
            str, capture["payload_family"]
        )
        receipt_payload = {
            "proposal_id": proposal_id,
            "proposed_content_sha256": sha256(proposed_bytes).hexdigest(),
        }
        return {
            "actor_id": self.profile.owner_actor_id,
            "capture_ids": [capture["capture_id"]],
            "evidence": [
                {
                    "capture_id": capture["capture_id"],
                    "excerpt": excerpt,
                    "sha256": sha256(excerpt.encode("utf-8")).hexdigest(),
                }
            ],
            "expected_receipt": _receipt(
                "proposal_created", receipt_id, proposal_id, recorded_at, receipt_payload
            ),
            "privacy": _privacy(),
            "proposal_id": proposal_id,
            "proposed_content": {
                "bytes_base64": base64.b64encode(proposed_bytes).decode("ascii"),
                "media_type": (
                    "text/markdown" if proposed_kind == "page_update" else "application/json"
                ),
                "sha256": sha256(proposed_bytes).hexdigest(),
            },
            "proposed_kind": proposed_kind,
            "recorded_at": recorded_at,
            "role_claim": _role_claim(self.profile),
            "schema_version": 1,
            "sibling_context": {"proposal_ids": list(sibling_ids)},
            "space_id": capture["space_id"],
            "status": "pending",
            "supplied_reason": supplied_reason,
            "tenant_id": self.profile.tenant_id,
            "trust": _trust(
                self.profile,
                recorded_at,
                "third_party" if capture["source_origin"] == "third_party" else "owner",
                "proposal retains capture trust",
            ),
        }

    def _list_proposals(
        self,
        *,
        capture_id: str | None,
        status: str | None,
        set_delivery_id: str | None = None,
    ) -> tuple[ProposalRecord, ...]:
        if capture_id is not None:
            _portable_id(capture_id, "capture")
        if status is not None and status not in {
            "pending",
            DecisionOutcome.APPROVED.value,
            DecisionOutcome.REJECTED.value,
            DecisionOutcome.EDITED.value,
        }:
            raise ValueError("invalid proposal status")
        clauses: list[str] = []
        parameters: list[object] = []
        if capture_id is not None:
            clauses.append("capture_id = ?")
            parameters.append(capture_id)
        if status is not None:
            clauses.append("status = ?")
            parameters.append(status)
        if set_delivery_id is not None:
            clauses.append("set_delivery_id = ?")
            parameters.append(set_delivery_id)
        sql = "SELECT * FROM proposals"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY proposal_id"
        connection = self._store.connect()
        try:
            rows = tuple(connection.execute(sql, parameters))
            sibling_rows = tuple(
                connection.execute(
                    "SELECT set_delivery_id, proposal_id FROM proposals ORDER BY proposal_id"
                )
            )
        finally:
            connection.close()
        siblings: dict[str, list[str]] = {}
        for sibling in sibling_rows:
            siblings.setdefault(cast(str, sibling["set_delivery_id"]), []).append(
                cast(str, sibling["proposal_id"])
            )
        return tuple(
            ProposalRecord(
                proposal_id=cast(str, row["proposal_id"]),
                capture_id=cast(str, row["capture_id"]),
                proposed_kind=cast(str, row["proposed_kind"]),
                status=cast(str, row["status"]),
                space_id=cast(str | None, row["space_id"]),
                sibling_proposal_ids=tuple(siblings[cast(str, row["set_delivery_id"])]),
                terminal_decision_id=cast(str | None, row["terminal_decision_id"]),
            )
            for row in rows
        )

    def _proposal_row(self, proposal_id: str) -> sqlite3.Row:
        _portable_id(proposal_id, "proposal")
        connection = self._store.connect()
        try:
            row = connection.execute(
                "SELECT * FROM proposals WHERE proposal_id = ?", (proposal_id,)
            ).fetchone()
        finally:
            connection.close()
        if row is None:
            raise ValueError("unknown proposal")
        return cast(sqlite3.Row, row)

    def _decide(
        self,
        proposal_id: str,
        outcome: DecisionOutcome,
        *,
        delivery_id: str,
        edited_markdown: str | None,
    ) -> DecisionRecord:
        _portable_id(proposal_id, "proposal")
        _delivery_id(delivery_id)
        outcome = DecisionOutcome(outcome)
        edited_markdown = _optional_text(
            edited_markdown, field="edited markdown", maximum=_MAX_TEXT
        )
        if (outcome is DecisionOutcome.EDITED) != (edited_markdown is not None):
            raise ValueError("edited outcome requires edited content")
        request_sha = sha256(
            portable_canonical_json_bytes(
                {
                    "edited_markdown": edited_markdown,
                    "outcome": outcome.value,
                    "proposal_id": proposal_id,
                }
            )
        ).hexdigest()
        conflict: tuple[str, str] | None = None
        created = False
        duplicate = False
        with self._store.transaction() as connection:
            delivery = connection.execute(
                "SELECT * FROM decisions WHERE delivery_id = ?", (delivery_id,)
            ).fetchone()
            proposal = connection.execute(
                "SELECT * FROM proposals WHERE proposal_id = ?", (proposal_id,)
            ).fetchone()
            if proposal is None:
                raise ValueError("unknown proposal")
            existing = connection.execute(
                "SELECT * FROM decisions WHERE proposal_id = ?", (proposal_id,)
            ).fetchone()
            if delivery is not None and cast(str, delivery["request_sha256"]) != request_sha:
                conflict = (cast(str, delivery["request_sha256"]), request_sha)
            elif existing is not None:
                existing_outcome = DecisionOutcome(cast(str, existing["outcome"]))
                if existing_outcome is not outcome:
                    raise ValueError("proposal already has a terminal decision")
                if outcome is DecisionOutcome.EDITED:
                    current = cast(bytes, existing["effective_bytes"])
                    capture = connection.execute(
                        "SELECT * FROM captures WHERE capture_id = ?", (proposal["capture_id"],)
                    ).fetchone()
                    assert capture is not None
                    expected = self._proposal_page_bytes(
                        capture,
                        page_id=cast(str, proposal["page_id"]),
                        title=cast(str, proposal["title"]),
                        body=cast(str, edited_markdown),
                        modified_at=cast(str, existing["recorded_at"]),
                    )
                    if current != expected:
                        raise ValueError("proposal already has a terminal decision")
                duplicate = True
                decision_id = cast(str, existing["decision_id"])
            else:
                if cast(str, proposal["proposed_kind"]) == "page_update" and proposal[
                    "space_id"
                ] is None:
                    raise ValueError("page proposal requires routed capture")
                now = _timestamp(self._clock())
                capture = connection.execute(
                    "SELECT * FROM captures WHERE capture_id = ?", (proposal["capture_id"],)
                ).fetchone()
                assert capture is not None
                if outcome is DecisionOutcome.REJECTED:
                    effective_bytes = None
                elif outcome is DecisionOutcome.EDITED:
                    effective_bytes = self._proposal_page_bytes(
                        capture,
                        page_id=cast(str, proposal["page_id"]),
                        title=cast(str, proposal["title"]),
                        body=cast(str, edited_markdown),
                        modified_at=now,
                    )
                else:
                    effective_bytes = cast(bytes, proposal["proposed_bytes"])
                decision_id = _new_id("decision")
                publishable = (
                    cast(str, proposal["proposed_kind"]) == "page_update"
                    and effective_bytes is not None
                )
                connection.execute(
                    """
                    INSERT INTO decisions (
                        delivery_id, request_sha256, decision_id, decision_receipt_id,
                        proposal_id, outcome, effective_bytes, recorded_at, page_id,
                        publication_id, canonical_path
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        delivery_id,
                        request_sha,
                        decision_id,
                        _new_id("receipt"),
                        proposal_id,
                        outcome.value,
                        effective_bytes,
                        now,
                        proposal["page_id"] if publishable else None,
                        _new_id("publication") if publishable else None,
                        proposal["canonical_path"] if publishable else None,
                    ),
                )
                connection.execute(
                    "UPDATE proposals SET status = ?, terminal_decision_id = ? "
                    "WHERE proposal_id = ?",
                    (outcome.value, decision_id, proposal_id),
                )
                created = True
        if conflict is not None:
            self._quarantine(delivery_id, expected=conflict[0], actual=conflict[1])
            raise ValueError("conflicting delivery")
        if created:
            self._fault(CaptureFault.AFTER_DECISION_RESERVATION)
        row = self._decision_row(decision_id)
        self._process_decision(row)
        return self._decision_public(self._decision_row(decision_id), duplicate=duplicate)

    def _decision_row(self, decision_id: str) -> sqlite3.Row:
        connection = self._store.connect()
        try:
            row = connection.execute(
                "SELECT * FROM decisions WHERE decision_id = ?", (decision_id,)
            ).fetchone()
        finally:
            connection.close()
        if row is None:
            raise ValueError("unknown decision")
        return cast(sqlite3.Row, row)

    def _process_decision(self, supplied_row: sqlite3.Row) -> None:
        row = self._decision_row(cast(str, supplied_row["decision_id"]))
        proposal = self._proposal_row(cast(str, row["proposal_id"]))
        set_row = self._proposal_set_row(cast(str, proposal["set_delivery_id"]))
        siblings = tuple(
            cast(str, item["proposal_id"])
            for item in self._proposal_rows(cast(str, proposal["set_delivery_id"]))
        )
        capture = self._capture_row(cast(str, proposal["capture_id"]))
        proposal_record = self._proposal_record(
            capture,
            proposal_id=cast(str, proposal["proposal_id"]),
            receipt_id=cast(str, proposal["receipt_id"]),
            proposed_bytes=cast(bytes, proposal["proposed_bytes"]),
            proposed_kind=cast(str, proposal["proposed_kind"]),
            sibling_ids=siblings,
            supplied_reason=cast(str | None, proposal["supplied_reason"]),
            recorded_at=cast(str, set_row["recorded_at"]),
        )
        if cast(int, row["stage"]) < 1:
            edited_bytes = (
                cast(bytes, row["effective_bytes"])
                if cast(str, row["outcome"]) == DecisionOutcome.EDITED.value
                else None
            )
            record = _decision_record(
                profile=self.profile,
                proposal=proposal_record,
                decision_id=cast(str, row["decision_id"]),
                outcome=DecisionOutcome(cast(str, row["outcome"])),
                edited_bytes=edited_bytes,
                recorded_at=cast(str, row["recorded_at"]),
            )
            decision_path = _dated_path(
                "history/decisions",
                cast(str, row["recorded_at"]),
                cast(str, row["decision_id"]),
            )
            atomic_write_new(
                root=self.profile.root,
                relative=decision_path,
                data=portable_canonical_json_bytes(record),
            )
            self._fault(CaptureFault.AFTER_DECISION_WRITE)
            with self._store.transaction() as connection:
                connection.execute(
                    "UPDATE decisions SET stage = 1 WHERE decision_id = ?",
                    (row["decision_id"],),
                )
            row = self._decision_row(cast(str, row["decision_id"]))
        if cast(int, row["stage"]) < 2:
            effective = cast(bytes | None, row["effective_bytes"])
            canonical_path = cast(str | None, row["canonical_path"])
            publication_path: str | None = None
            if effective is not None and canonical_path is not None:
                atomic_write_new(root=self.profile.root, relative=canonical_path, data=effective)
                self._fault(CaptureFault.AFTER_REVIEW_PAGE_WRITE)
                publication = _publication_record(
                    profile=self.profile,
                    decision_id=cast(str, row["decision_id"]),
                    page_id=cast(str, row["page_id"]),
                    publication_id=cast(str, row["publication_id"]),
                    published_path=canonical_path,
                    published_bytes=effective,
                    recorded_at=cast(str, row["recorded_at"]),
                )
                publication_path = _dated_path(
                    "history/publications",
                    cast(str, row["recorded_at"]),
                    cast(str, row["publication_id"]),
                )
                atomic_write_new(
                    root=self.profile.root,
                    relative=publication_path,
                    data=portable_canonical_json_bytes(publication),
                )
                self._fault(CaptureFault.AFTER_REVIEW_PUBLICATION_WRITE)
            with self._store.transaction() as connection:
                connection.execute(
                    "UPDATE decisions SET publication_path = ?, stage = 2 WHERE decision_id = ?",
                    (publication_path, row["decision_id"]),
                )
            row = self._decision_row(cast(str, row["decision_id"]))
        if cast(int, row["stage"]) < 3:
            effective = cast(bytes | None, row["effective_bytes"])
            canonical_path = cast(str | None, row["canonical_path"])
            with self._store.transaction() as connection:
                if effective is not None and canonical_path is not None:
                    parsed = parse_markdown(effective)
                    self._upsert_canonical_search(
                        connection,
                        result_id=cast(str, row["page_id"]),
                        capture_id=cast(str, proposal["capture_id"]),
                        payload_family=cast(str, capture["payload_family"]),
                        space_id=cast(str, proposal["space_id"]),
                        title=cast(str, parsed.fields["title"]),
                        body=parsed.body,
                        trust="reviewed",
                        canonical_path=canonical_path,
                        updated_at=cast(str, row["recorded_at"]),
                    )
                connection.execute(
                    "UPDATE decisions SET stage = 3 WHERE decision_id = ?",
                    (row["decision_id"],),
                )

    def _decision_public(self, row: sqlite3.Row, *, duplicate: bool) -> DecisionRecord:
        return DecisionRecord(
            decision_id=cast(str, row["decision_id"]),
            proposal_id=cast(str, row["proposal_id"]),
            outcome=DecisionOutcome(cast(str, row["outcome"])),
            page_id=cast(str | None, row["page_id"]),
            publication_id=cast(str | None, row["publication_id"]),
            duplicate=duplicate,
        )

    def _upsert_source_search(
        self, connection: sqlite3.Connection, capture: sqlite3.Row
    ) -> None:
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
            trust=(
                "third_party" if capture["source_origin"] == "third_party" else "owner"
            ),
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
        clauses: list[str] = []
        parameters: list[object] = []
        if space_id is not None:
            clauses.append("space_id = ?")
            parameters.append(space_id)
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

    def _fetch(self, result_id: str) -> RetrievalResult | None:
        connection = self._store.connect()
        try:
            row = connection.execute(
                "SELECT * FROM search_documents WHERE result_id = ?", (result_id,)
            ).fetchone()
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
            payload = read_confined(root=self.profile.root, relative=canonical_path)
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
        matched = tuple(term for term in terms if term in haystack)
        explanation = (
            "fetched by result identifier"
            if not terms
            else (
                "exact phrase and lexical terms: " if phrase in haystack else "lexical terms: "
            )
            + ", ".join(matched)
        )
        provenance_value = json.loads(cast(str, row["provenance_json"]))
        if not isinstance(provenance_value, dict) or any(
            not isinstance(key, str) or not isinstance(value, str)
            for key, value in provenance_value.items()
        ):
            return None
        excerpt = _excerpt(body, terms)
        return (
            score,
            RetrievalResult(
                result_id=cast(str, row["result_id"]),
                capture_id=cast(str, row["capture_id"]),
                record_type=cast(str, row["record_type"]),
                payload_family=cast(str, row["payload_family"]),
                space_id=cast(str | None, row["space_id"]),
                title=title,
                excerpt=excerpt,
                trust=cast(str, row["trust"]),
                provenance=MappingProxyType(cast(dict[str, str], provenance_value)),
                explanation=explanation,
            ),
        )


class CaptureTasks:
    def __init__(self, engine: BrainEngine) -> None:
        self._engine = engine

    def accept(
        self,
        payload: Payload,
        *,
        delivery_id: str,
        action: CaptureAction = CaptureAction.QUICK,
        space_id: str | None = None,
        intent: str | None = None,
        capture_why: str | None = None,
        title: str | None = None,
    ) -> CaptureReceipt:
        with self._engine._writer_lease.acquire_shared_writer():
            return self._engine._accept_capture(
                payload,
                delivery_id=delivery_id,
                action=action,
                space_id=space_id,
                intent=intent,
                capture_why=capture_why,
                title=title,
            )

    def get(self, capture_id: str) -> CaptureReceipt | None:
        return self._engine._capture_receipt(capture_id)

    def retry_enrichment(
        self,
        capture_id: str,
        *,
        delivery_id: str,
    ) -> tuple[ProposalRecord, ...]:
        with self._engine._writer_lease.acquire_shared_writer():
            row = self._engine._capture_row(capture_id)
            if cast(str, row["enrichment_state"]) == EnrichmentState.ENRICHED.value:
                proposal_set = self._engine._proposal_set_row(delivery_id)
                if cast(str, proposal_set["capture_id"]) != capture_id:
                    raise ValueError("conflicting enrichment delivery")
                return self._engine._list_proposals(
                    capture_id=capture_id,
                    status=None,
                    set_delivery_id=delivery_id,
                )
            provider = self._engine._enrichment_provider
            if provider is None:
                raise EnrichmentUnavailable("enrichment provider unavailable")
            request = EnrichmentRequest(
                capture_id=capture_id,
                payload_family=cast(str, row["payload_family"]),
                source_text=cast(str, row["search_text"]),
            )
            try:
                drafts = tuple(provider.enrich(request))
            except EnrichmentUnavailable:
                raise
            except Exception:
                raise EnrichmentUnavailable("enrichment provider unavailable") from None
            proposals = self._engine._propose(capture_id, drafts, delivery_id)
            with self._engine._store.transaction() as connection:
                connection.execute(
                    "UPDATE captures SET enrichment_state = ? WHERE capture_id = ?",
                    (EnrichmentState.ENRICHED.value, capture_id),
                )
            return proposals


class InboxSpaceTasks:
    def __init__(self, engine: BrainEngine) -> None:
        self._engine = engine

    def list(self, *, unassigned_only: bool = False) -> tuple[InboxItem, ...]:
        return self._engine._list_inbox(unassigned_only=unassigned_only)

    def spaces(self) -> tuple[SpaceRecord, ...]:
        return self._engine._list_spaces()

    def create_space(self, name: str, *, delivery_id: str) -> SpaceRecord:
        with self._engine._writer_lease.acquire_shared_writer():
            return self._engine._space_operation("create", None, name, delivery_id)

    def rename_space(self, space_id: str, name: str, *, delivery_id: str) -> SpaceRecord:
        with self._engine._writer_lease.acquire_shared_writer():
            return self._engine._space_operation("rename", space_id, name, delivery_id)

    def route(self, capture_id: str, space_id: str, *, delivery_id: str) -> RoutedCapture:
        with self._engine._writer_lease.acquire_shared_writer():
            return self._engine._route_capture(capture_id, space_id, delivery_id)


class ReviewTasks:
    def __init__(self, engine: BrainEngine) -> None:
        self._engine = engine

    def propose(
        self,
        capture_id: str,
        drafts: Sequence[ProposalDraft],
        *,
        delivery_id: str,
    ) -> tuple[ProposalRecord, ...]:
        with self._engine._writer_lease.acquire_shared_writer():
            return self._engine._propose(capture_id, drafts, delivery_id)

    def list(
        self, *, capture_id: str | None = None, status: str | None = None
    ) -> tuple[ProposalRecord, ...]:
        return self._engine._list_proposals(capture_id=capture_id, status=status)

    def decide(
        self,
        proposal_id: str,
        outcome: DecisionOutcome,
        *,
        delivery_id: str,
        edited_markdown: str | None = None,
    ) -> DecisionRecord:
        with self._engine._writer_lease.acquire_shared_writer():
            return self._engine._decide(
                proposal_id,
                outcome,
                delivery_id=delivery_id,
                edited_markdown=edited_markdown,
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


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _text(value: object, *, field: str, maximum: int) -> str:
    if not isinstance(value, str):
        raise ValueError(f"invalid {field}")
    normalized = unicodedata.normalize("NFC", value).replace("\r\n", "\n").replace("\r", "\n")
    if not normalized.strip() or "\x00" in normalized or len(normalized) > maximum:
        raise ValueError(f"invalid {field}")
    return normalized


def _optional_text(value: object, *, field: str, maximum: int) -> str | None:
    if value is None:
        return None
    return _text(value, field=field, maximum=maximum)


def _timestamp(value: datetime) -> str:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError("invalid timestamp")
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _optional_timestamp(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("invalid occurrence timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("invalid occurrence timestamp") from error
    if parsed.tzinfo is None:
        raise ValueError("invalid occurrence timestamp")
    return _timestamp(parsed)


def _attributes(value: Mapping[str, str]) -> Mapping[str, str]:
    if not isinstance(value, Mapping):
        raise ValueError("invalid attributes")
    normalized: dict[str, str] = {}
    for key, item in value.items():
        name = _text(key, field="attribute name", maximum=120)
        text = _text(item, field="attribute value", maximum=1_000)
        if name in normalized:
            raise ValueError("duplicate attribute")
        normalized[name] = text
    return MappingProxyType(dict(sorted(normalized.items())))


def _attribute_list(value: Mapping[str, str]) -> list[dict[str, str]]:
    return [{"name": name, "value": item} for name, item in value.items()]


def _pairs(value: Mapping[str, str]) -> tuple[str, ...]:
    return tuple(f"{name} {item}" for name, item in value.items())


def _delivery_id(value: str) -> str:
    if not isinstance(value, str) or _DELIVERY.fullmatch(value) is None:
        raise ValueError("invalid delivery identity")
    return value


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4()}"


def _portable_id(value: str, prefix: str) -> str:
    marker = prefix + "_"
    if not isinstance(value, str) or not value.startswith(marker):
        raise ValueError("invalid portable identifier")
    try:
        identifier = uuid.UUID(value.removeprefix(marker))
    except ValueError as error:
        raise ValueError("invalid portable identifier") from error
    if identifier.version != 4 or value != f"{prefix}_{identifier}":
        raise ValueError("invalid portable identifier")
    return value


def _role_claim(profile: LocalEngineContext) -> dict[str, object]:
    result = dict(profile.owner_role_claim)
    capabilities = result.get("capabilities")
    if isinstance(capabilities, tuple | list):
        result["capabilities"] = list(capabilities)
    return result


def _privacy() -> dict[str, object]:
    return {
        "authority": {"cloud": False, "external_egress": False},
        "confirmation_ref": None,
        "policy_version": "privacy-v1",
        "reason": "personal_local_only",
        "tier": "personal",
    }


def _trust(
    profile: LocalEngineContext,
    assessed_at: str,
    label: str,
    reason: str,
) -> dict[str, object]:
    return {
        "assessed_at": assessed_at,
        "assessor_actor_id": profile.owner_actor_id,
        "label": label,
        "reason": reason,
    }


def _receipt(
    kind: str,
    receipt_id: str,
    subject_id: str,
    recorded_at: str,
    payload: Mapping[str, object],
) -> dict[str, object]:
    thawed = dict(payload)
    return {
        "kind": kind,
        "payload": thawed,
        "receipt_id": receipt_id,
        "recorded_at": recorded_at,
        "sha256": sha256(portable_canonical_json_bytes(thawed)).hexdigest(),
        "subject_id": subject_id,
    }


def _dated_path(root: str, timestamp: str, identifier: str) -> str:
    parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).astimezone(UTC)
    return f"{root}/{parsed:%Y/%m}/{identifier}.json"


def _payload_dict(row: sqlite3.Row) -> dict[str, object]:
    raw = cast(bytes, row["payload_json"])
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError("invalid stored payload")
    return cast(dict[str, object], value)


def _space_row(connection: sqlite3.Connection, space_id: str) -> sqlite3.Row | None:
    return cast(
        sqlite3.Row | None,
        connection.execute("SELECT * FROM spaces WHERE space_id = ?", (space_id,)).fetchone(),
    )


def _slug(name: str, space_id: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.casefold()).strip("-") or "space"
    suffix = space_id.removeprefix("space_").replace("-", "")[:8]
    return f"{base[:80].strip('-') or 'space'}-{suffix}"


def _decision_record(
    *,
    profile: LocalEngineContext,
    proposal: Mapping[str, object],
    decision_id: str,
    outcome: DecisionOutcome,
    edited_bytes: bytes | None,
    recorded_at: str,
) -> dict[str, object]:
    proposal_id = cast(str, proposal["proposal_id"])
    edited = (
        {
            "bytes_base64": base64.b64encode(edited_bytes).decode("ascii"),
            "sha256": sha256(edited_bytes).hexdigest(),
        }
        if edited_bytes is not None
        else None
    )
    expected_state_digest = sha256(portable_canonical_json_bytes(dict(proposal))).hexdigest()
    terminal_payload = {
        "decision_id": decision_id,
        "edited_content_sha256": (
            sha256(edited_bytes).hexdigest() if edited_bytes is not None else None
        ),
        "expected_state_digest": expected_state_digest,
        "outcome": outcome.value,
        "proposal_id": proposal_id,
    }
    return {
        "actor_id": profile.owner_actor_id,
        "decision_id": decision_id,
        "edited_content": edited,
        "expected_receipt": proposal["expected_receipt"],
        "expected_state_digest": expected_state_digest,
        "outcome": outcome.value,
        "proposal_id": proposal_id,
        "recorded_at": recorded_at,
        "role_claim": _role_claim(profile),
        "schema_version": 1,
        "tenant_id": profile.tenant_id,
        "terminal_digest": sha256(portable_canonical_json_bytes(terminal_payload)).hexdigest(),
    }


def _publication_record(
    *,
    profile: LocalEngineContext,
    decision_id: str,
    page_id: str,
    publication_id: str,
    published_path: str,
    published_bytes: bytes,
    recorded_at: str,
) -> dict[str, object]:
    return {
        "actor_id": profile.owner_actor_id,
        "decision_id": decision_id,
        "page_id": page_id,
        "publication_id": publication_id,
        "published_bytes_base64": base64.b64encode(published_bytes).decode("ascii"),
        "published_path": published_path,
        "published_sha256": sha256(published_bytes).hexdigest(),
        "recorded_at": recorded_at,
        "role_claim": _role_claim(profile),
        "schema_version": 1,
        "tenant_id": profile.tenant_id,
    }


def _excerpt(body: str, terms: tuple[str, ...]) -> str:
    collapsed = " ".join(body.split())
    if not collapsed:
        return "(empty)"
    if not terms:
        return collapsed[:512]
    lower = collapsed.casefold()
    offsets = [lower.find(term) for term in terms if lower.find(term) >= 0]
    start = max(0, min(offsets, default=0) - 80)
    return collapsed[start : start + 512]


def _done(table: str) -> int:
    return {
        "captures": 3,
        "decisions": 3,
        "proposal_sets": 1,
        "route_operations": 1,
        "space_operations": 1,
    }[table]
