from __future__ import annotations

import logging
import sqlite3
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

import pytest

from open_brain.core.ids import CaptureId
from open_brain.core.models import (
    Authority,
    PrivacyDecision,
    PrivacyReason,
    PrivacyTier,
)
from open_brain.core.ports import (
    EventRecord,
    RedactedMarkdownDocument,
    RedactionFinding,
    RedactionFindingCategory,
    RedactionReceipt,
)
from open_brain.events.store import SqliteEventStore
from open_brain.storage.filesystem import DuplicateConflictError
from open_brain.storage.frontmatter import AtomicMarkdownSink, markdown_relative_path

FIXED_TIME = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
STREAM_ID = CaptureId("cap_" + "a" * 64)


class FixedClock:
    def now(self) -> datetime:
        return FIXED_TIME


def privacy() -> PrivacyDecision:
    return PrivacyDecision.create(
        tier=PrivacyTier.WORK,
        reason=PrivacyReason.POLICY_WORK,
        policy_version="privacy-v1",
        authority=Authority(cloud=False, external_egress=False),
    )


def _disallowed_privacy_decisions() -> tuple[PrivacyDecision, ...]:
    return (
        PrivacyDecision.create(
            tier=PrivacyTier.SECRET,
            reason=PrivacyReason.SECRET_DETECTED,
            policy_version="privacy-v1",
            authority=Authority(cloud=False, external_egress=False),
        ),
        PrivacyDecision.create(
            tier=PrivacyTier.UNKNOWN,
            reason=PrivacyReason.CLASSIFICATION_MISSING,
            policy_version="privacy-v1",
            authority=Authority(cloud=False, external_egress=False),
        ),
        PrivacyDecision.create(
            tier=PrivacyTier.UNKNOWN,
            reason=PrivacyReason.CLASSIFICATION_INVALID,
            policy_version="privacy-v1",
            authority=Authority(cloud=False, external_egress=False),
        ),
        PrivacyDecision.create(
            tier=PrivacyTier.PERSONAL,
            reason=PrivacyReason.EXPLICIT_LOCAL_ONLY,
            policy_version="privacy-v1",
            authority=Authority(cloud=False, external_egress=False),
        ),
        PrivacyDecision.create(
            tier=PrivacyTier.PERSONAL,
            reason=PrivacyReason.PERSONAL_LOCAL_ONLY,
            policy_version="privacy-v1",
            authority=Authority(cloud=False, external_egress=False),
        ),
    )


def _allowed_privacy_decisions() -> tuple[PrivacyDecision, ...]:
    return (
        PrivacyDecision.create(
            tier=PrivacyTier.PUBLIC,
            reason=PrivacyReason.POLICY_PUBLIC,
            policy_version="privacy-v1",
            authority=Authority(cloud=False, external_egress=False),
        ),
        privacy(),
        PrivacyDecision.create(
            tier=PrivacyTier.PERSONAL,
            reason=PrivacyReason.PERSONAL_CONFIRMED,
            policy_version="privacy-v1",
            authority=Authority(cloud=False, external_egress=False),
            confirmation_ref="review.synthetic-001",
        ),
    )


def _runtime_canary() -> str:
    return "cred" + "ential" + "-synthetic-value"


def _receipt(output_digest: str, source: str) -> RedactionReceipt:
    return RedactionReceipt.create(
        source_digest_sha256=sha256(source.encode()).hexdigest(),
        output_digest_sha256=output_digest,
        policy_version="redaction-v1",
        findings=(
            RedactionFinding.create(
                category=RedactionFindingCategory.CREDENTIAL,
                count=1,
            ),
        ),
    )


def test_work_tier_persistence_contains_redacted_output_and_receipt_only(
    tmp_path: Path,
) -> None:
    canary = _runtime_canary()
    replacement = "[removed]"
    event_payload = {"text": replacement}
    event = EventRecord.create(
        event_id="event.redacted-001",
        stream_id=STREAM_ID,
        event_type="capture.redacted",
        occurred_at=FIXED_TIME,
        privacy_decision=privacy(),
        payload=event_payload,
        redaction_receipt=_receipt(EventRecord.output_digest_sha256(event_payload), canary),
    )
    document_fields = {"summary": replacement}
    document_body = replacement
    document = RedactedMarkdownDocument.create(
        document_id="note.redacted-001",
        logical_key="capture.redacted-001",
        privacy_decision=privacy(),
        frontmatter=document_fields,
        body=document_body,
        redaction_receipt=_receipt(
            RedactedMarkdownDocument.output_digest_sha256(document_fields, document_body),
            canary,
        ),
    )

    database = tmp_path / "events.sqlite3"
    with SqliteEventStore(
        root=tmp_path, database_name="events.sqlite3", clock=FixedClock()
    ) as store:
        store.append(event)
    AtomicMarkdownSink(root=tmp_path).write_if_absent(document)

    connection = sqlite3.connect(database)
    try:
        persisted_event = " ".join(
            str(value)
            for value in connection.execute(
                "SELECT payload_json, redaction_findings_json, redaction_policy_version FROM events"
            ).fetchone()
        )
    finally:
        connection.close()
    persisted_markdown = (tmp_path / markdown_relative_path(document.document_id)).read_text()
    assert canary not in persisted_event
    assert canary not in persisted_markdown
    assert replacement in persisted_event
    assert replacement in persisted_markdown


def test_collision_errors_and_logs_never_contain_raw_content(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    canary = _runtime_canary()
    first_payload = {"text": "[removed]"}
    changed_payload = {"text": canary}
    first = EventRecord.create(
        event_id="event.collision-001",
        stream_id=STREAM_ID,
        event_type="capture.redacted",
        occurred_at=FIXED_TIME,
        privacy_decision=privacy(),
        payload=first_payload,
        redaction_receipt=_receipt(EventRecord.output_digest_sha256(first_payload), canary),
    )
    collision = EventRecord.create(
        event_id=first.event_id,
        stream_id=first.stream_id,
        event_type=first.event_type,
        occurred_at=first.occurred_at,
        privacy_decision=first.privacy_decision,
        payload=changed_payload,
        redaction_receipt=_receipt(EventRecord.output_digest_sha256(changed_payload), canary),
    )
    caplog.set_level(logging.DEBUG)

    with SqliteEventStore(
        root=tmp_path, database_name="events.sqlite3", clock=FixedClock()
    ) as store:
        store.append(first)
        with pytest.raises(DuplicateConflictError) as raised:
            store.append(collision)

    assert canary not in str(raised.value)
    assert canary not in caplog.text


@pytest.mark.parametrize("decision", _disallowed_privacy_decisions())
def test_work_tier_sinks_reject_disallowed_privacy_before_io(
    tmp_path: Path, decision: PrivacyDecision, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = {"text": "[removed]"}
    event = EventRecord.create(
        event_id="event.rejected-" + decision.reason.value,
        stream_id=STREAM_ID,
        event_type="capture.redacted",
        occurred_at=FIXED_TIME,
        privacy_decision=decision,
        payload=payload,
        redaction_receipt=_receipt(EventRecord.output_digest_sha256(payload), "source"),
    )
    document = RedactedMarkdownDocument.create(
        document_id="note.rejected-" + decision.reason.value,
        logical_key="capture.rejected-" + decision.reason.value,
        privacy_decision=decision,
        frontmatter={"summary": "[removed]"},
        body="[removed]",
        redaction_receipt=_receipt(
            RedactedMarkdownDocument.output_digest_sha256({"summary": "[removed]"}, "[removed]"),
            "source",
        ),
    )

    with SqliteEventStore(
        root=tmp_path, database_name="events.sqlite3", clock=FixedClock()
    ) as store:

        class NoSqliteActivity:
            def execute(self, *args: object) -> None:
                raise AssertionError("SQLite transaction attempted")

            def close(self) -> None:
                pass

        store._connection = NoSqliteActivity()  # type: ignore[assignment]
        with pytest.raises(Exception, match="work-tier privacy decision rejected"):
            store.append(event)

    def no_file_open(*args: object, **kwargs: object) -> None:
        raise AssertionError("Markdown write attempted")

    monkeypatch.setattr("open_brain.storage.frontmatter.atomic_write_new", no_file_open)
    with pytest.raises(Exception, match="work-tier privacy decision rejected"):
        AtomicMarkdownSink(root=tmp_path).write_if_absent(document)


@pytest.mark.parametrize("decision", _allowed_privacy_decisions())
def test_work_tier_sinks_accept_allowed_privacy_decisions(
    tmp_path: Path, decision: PrivacyDecision
) -> None:
    payload = {"text": "[removed]"}
    event = EventRecord.create(
        event_id="event.allowed-" + decision.reason.value,
        stream_id=STREAM_ID,
        event_type="capture.redacted",
        occurred_at=FIXED_TIME,
        privacy_decision=decision,
        payload=payload,
        redaction_receipt=_receipt(EventRecord.output_digest_sha256(payload), "source"),
    )
    document = RedactedMarkdownDocument.create(
        document_id="note.allowed-" + decision.reason.value,
        logical_key="capture.allowed-" + decision.reason.value,
        privacy_decision=decision,
        frontmatter={"summary": "[removed]"},
        body="[removed]",
        redaction_receipt=_receipt(
            RedactedMarkdownDocument.output_digest_sha256({"summary": "[removed]"}, "[removed]"),
            "source",
        ),
    )

    with SqliteEventStore(
        root=tmp_path, database_name="events.sqlite3", clock=FixedClock()
    ) as store:
        assert store.append(event).record_id == event.event_id
    markdown_result = AtomicMarkdownSink(root=tmp_path).write_if_absent(document)
    assert markdown_result.record_id == document.document_id
