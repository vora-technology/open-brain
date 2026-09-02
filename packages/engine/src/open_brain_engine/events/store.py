from __future__ import annotations

import json
import sqlite3
from datetime import UTC
from hashlib import sha256
from pathlib import Path

from open_brain_engine.core.ids import CaptureId, canonical_json_bytes, validate_identifier
from open_brain_engine.core.models import (
    PrivacyDecision,
    PrivacyReason,
    PrivacyTier,
    ValidationError,
)
from open_brain_engine.core.ports import (
    Clock,
    EventRecord,
    PutDisposition,
    PutResult,
)
from open_brain_engine.storage.filesystem import DuplicateConflictError, StorageError
from open_brain_engine.storage.sqlite import connect_database, migrate


class EventStoreError(StorageError):
    """An event operation failed without exposing event content."""


def _allows_work_tier_persistence(decision: PrivacyDecision) -> bool:
    return (
        (
            decision.tier is PrivacyTier.PUBLIC
            and decision.reason is PrivacyReason.POLICY_PUBLIC
            and decision.confirmation_ref is None
        )
        or (
            decision.tier is PrivacyTier.WORK
            and decision.reason is PrivacyReason.POLICY_WORK
            and decision.confirmation_ref is None
        )
        or (
            decision.tier is PrivacyTier.PERSONAL
            and decision.reason is PrivacyReason.PERSONAL_CONFIRMED
            and decision.confirmation_ref is not None
        )
    )


_INSERT_SQL = """
INSERT INTO events (
    event_id, capture_id, event_type, occurred_at,
    privacy_tier, privacy_reason, privacy_policy_version, privacy_confirmation_ref,
    cloud_allowed, egress_allowed,
    redaction_policy_version, redaction_source_sha256, redaction_output_sha256,
    redaction_findings_json, payload_json, payload_sha256, created_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(event_id) DO NOTHING
"""

_IMMUTABLE_COLUMNS = """
event_id, capture_id, event_type, occurred_at,
privacy_tier, privacy_reason, privacy_policy_version, privacy_confirmation_ref,
cloud_allowed, egress_allowed,
redaction_policy_version, redaction_source_sha256, redaction_output_sha256,
redaction_findings_json, payload_json, payload_sha256
"""


def _timestamp(record: EventRecord) -> str:
    return record.occurred_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _created_at(clock: Clock) -> str:
    value = clock.now()
    if value.tzinfo is None or value.utcoffset() is None:
        raise EventStoreError("event clock returned invalid timestamp")
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _serialized_values(record: EventRecord) -> tuple[object, ...]:
    value = record.to_dict()
    payload = value["payload"]
    receipt = record.redaction_receipt
    payload_bytes = canonical_json_bytes(payload)
    findings_bytes = canonical_json_bytes([finding.to_dict() for finding in receipt.findings])
    privacy = record.privacy_decision
    return (
        record.event_id,
        str(record.stream_id),
        record.event_type,
        _timestamp(record),
        privacy.tier.value,
        privacy.reason.value,
        privacy.policy_version,
        privacy.confirmation_ref,
        int(privacy.authority.cloud),
        int(privacy.authority.external_egress),
        receipt.policy_version,
        receipt.source_digest_sha256,
        receipt.output_digest_sha256,
        findings_bytes.decode("utf-8"),
        payload_bytes.decode("utf-8"),
        sha256(payload_bytes).hexdigest(),
    )


def _decode_row(row: sqlite3.Row) -> EventRecord:
    try:
        payload_text = str(row["payload_json"])
        payload_bytes = payload_text.encode("utf-8")
        if sha256(payload_bytes).hexdigest() != row["payload_sha256"]:
            raise ValueError
        payload = json.loads(payload_text)
        findings = json.loads(str(row["redaction_findings_json"]))
        value = {
            "event_id": row["event_id"],
            "stream_id": row["capture_id"],
            "event_type": row["event_type"],
            "occurred_at": row["occurred_at"],
            "privacy_decision": {
                "tier": row["privacy_tier"],
                "reason": row["privacy_reason"],
                "policy_version": row["privacy_policy_version"],
                "authority": {
                    "cloud": bool(row["cloud_allowed"]),
                    "external_egress": bool(row["egress_allowed"]),
                },
                "confirmation_ref": row["privacy_confirmation_ref"],
            },
            "payload": payload,
            "redaction_receipt": {
                "source_digest_sha256": row["redaction_source_sha256"],
                "output_digest_sha256": row["redaction_output_sha256"],
                "policy_version": row["redaction_policy_version"],
                "findings": findings,
            },
        }
        record = EventRecord.from_dict(value)
        if _serialized_values(record) != tuple(
            row[column.strip()] for column in _IMMUTABLE_COLUMNS.split(",")
        ):
            raise ValueError
        return record
    except (KeyError, TypeError, ValueError, ValidationError):
        raise EventStoreError("invalid stored event") from None


class SqliteEventStore:
    def __init__(self, *, root: Path, database_name: str, clock: Clock) -> None:
        self._clock = clock
        self._connection = connect_database(root=root, database_name=database_name)
        migrate(self._connection, clock=clock)

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> SqliteEventStore:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def append(self, record: EventRecord) -> PutResult:
        if not isinstance(record, EventRecord):
            raise EventStoreError("invalid event record")
        if not _allows_work_tier_persistence(record.privacy_decision):
            raise EventStoreError("work-tier privacy decision rejected")
        try:
            verified = EventRecord.from_canonical_bytes(record.canonical_bytes())
        except (TypeError, ValueError):
            raise EventStoreError("invalid event record") from None
        immutable_values = _serialized_values(verified)
        try:
            self._connection.execute("BEGIN IMMEDIATE")
            cursor = self._connection.execute(
                _INSERT_SQL, immutable_values + (_created_at(self._clock),)
            )
            if cursor.rowcount == 1:
                self._connection.commit()
                disposition = PutDisposition.CREATED
            else:
                row = self._connection.execute(
                    f"SELECT {_IMMUTABLE_COLUMNS} FROM events WHERE event_id = ?",
                    (verified.event_id,),
                ).fetchone()
                if row is None or tuple(row) != immutable_values:
                    self._connection.rollback()
                    raise DuplicateConflictError("immutable event conflict")
                self._connection.commit()
                disposition = PutDisposition.DUPLICATE
            return PutResult(
                disposition=disposition,
                record_id=verified.event_id,
                digest_sha256=verified.redaction_receipt.output_digest_sha256,
            )
        except DuplicateConflictError:
            raise
        except (EventStoreError, sqlite3.Error):
            if self._connection.in_transaction:
                self._connection.rollback()
            raise EventStoreError("event append failed") from None

    def read(self, stream_id: CaptureId, *, after_sequence: int = 0) -> tuple[EventRecord, ...]:
        try:
            validated_stream_id = validate_identifier(str(stream_id), prefix="cap_")
        except ValueError:
            raise EventStoreError("invalid event stream identifier") from None
        if (
            not isinstance(after_sequence, int)
            or isinstance(after_sequence, bool)
            or after_sequence < 0
        ):
            raise EventStoreError("invalid event sequence")
        try:
            rows = self._connection.execute(
                f"SELECT sequence, {_IMMUTABLE_COLUMNS} FROM events "
                "WHERE capture_id = ? AND sequence > ? ORDER BY sequence",
                (validated_stream_id, after_sequence),
            ).fetchall()
            return tuple(_decode_row(row) for row in rows)
        except EventStoreError:
            raise
        except sqlite3.Error:
            raise EventStoreError("event read failed") from None
