from __future__ import annotations

import sqlite3
from hashlib import sha256
from pathlib import Path

import pytest

from open_brain.core.ports import EventRecord, PutDisposition, RedactionReceipt
from open_brain.events.store import EventStoreError, SqliteEventStore
from open_brain.storage.filesystem import DuplicateConflictError

from ._factories import FIXED_TIME, FixedClock, privacy, raw_capture


def _event(*, event_id: str = "event.synthetic-001", text: str = "redacted value") -> EventRecord:
    payload = {"text": text, "nested": {"safe": True}}
    return EventRecord.create(
        event_id=event_id,
        stream_id=raw_capture().envelope.capture_id,
        event_type="capture.persisted",
        occurred_at=FIXED_TIME,
        privacy_decision=privacy(),
        payload=payload,
        redaction_receipt=RedactionReceipt.create(
            source_digest_sha256=sha256(b"synthetic source").hexdigest(),
            output_digest_sha256=EventRecord.output_digest_sha256(payload),
            policy_version="redaction-v1",
        ),
    )


def test_event_store_preserves_order_privacy_and_idempotent_replay(tmp_path: Path) -> None:
    first = _event()
    second = _event(event_id="event.synthetic-002", text="second redacted value")
    with SqliteEventStore(
        root=tmp_path, database_name="events.sqlite3", clock=FixedClock()
    ) as store:
        created = store.append(first)
        duplicate = store.append(first)
        store.append(second)
        loaded = store.read(first.stream_id)

    assert created.disposition is PutDisposition.CREATED
    assert duplicate.disposition is PutDisposition.DUPLICATE
    assert loaded == (first, second)
    assert loaded[0].privacy_decision == first.privacy_decision


def test_duplicate_event_id_with_different_payload_never_overwrites(
    tmp_path: Path,
) -> None:
    first = _event()
    collision = _event(text="changed redacted value")
    with SqliteEventStore(
        root=tmp_path, database_name="events.sqlite3", clock=FixedClock()
    ) as store:
        store.append(first)
        with pytest.raises(DuplicateConflictError, match="immutable event conflict"):
            store.append(collision)
        assert store.read(first.stream_id) == (first,)


def test_event_read_after_sequence_is_exclusive(tmp_path: Path) -> None:
    first = _event()
    second = _event(event_id="event.synthetic-002")
    with SqliteEventStore(
        root=tmp_path, database_name="events.sqlite3", clock=FixedClock()
    ) as store:
        store.append(first)
        store.append(second)
        assert store.read(first.stream_id, after_sequence=1) == (second,)


def test_event_transaction_failure_rolls_back_and_retry_appends_once(
    tmp_path: Path,
) -> None:
    event = _event()
    database = tmp_path / "events.sqlite3"
    with SqliteEventStore(root=tmp_path, database_name=database.name, clock=FixedClock()) as store:
        injector = sqlite3.connect(database)
        try:
            injector.execute(
                "CREATE TRIGGER synthetic_event_failure "
                "BEFORE INSERT ON events BEGIN "
                "SELECT RAISE(ABORT, 'synthetic event failure'); END"
            )
            injector.commit()
        finally:
            injector.close()

        with pytest.raises(EventStoreError, match="event append failed"):
            store.append(event)
        assert store.read(event.stream_id) == ()

        injector = sqlite3.connect(database)
        try:
            injector.execute("DROP TRIGGER synthetic_event_failure")
            injector.commit()
        finally:
            injector.close()

        result = store.append(event)
        assert result.disposition is PutDisposition.CREATED
        assert store.read(event.stream_id) == (event,)
