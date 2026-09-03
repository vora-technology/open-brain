from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta, timezone
from hashlib import sha256
from types import MappingProxyType
from typing import Any

import pytest
from open_brain_engine.capture.models import (
    CapturePipeline,
    CaptureRedactionResult,
    DistillationLease,
    DistillationWorkItem,
    ExtractionFailure,
    ExtractionMetadata,
    ExtractionState,
    ExtractorKind,
    NormalizedExtraction,
    ShareRequest,
    ShareResponse,
    ShareStatus,
    TranscriptState,
)
from open_brain_engine.core.ids import canonical_json_bytes
from open_brain_engine.core.models import ContentKind, SourceType
from open_brain_engine.core.ports import EventRecord, RedactionReceipt

CAPTURE_ID = "cap_" + "a" * 64
EVENT_ID = "event_" + "b" * 64
DIGEST = "c" * 64


def test_closed_shared_enums_have_only_brief_values() -> None:
    assert {value.value for value in CapturePipeline} == {"youtube", "social", "web"}
    assert {value.value for value in ShareStatus} == {"queued", "duplicate"}
    assert {value.value for value in ExtractorKind} == {
        "text",
        "article",
        "youtube",
        "social",
    }
    assert {value.value for value in ExtractionState} == {
        "complete",
        "pending_transcript",
        "no_content",
        "rejected",
        "failed",
    }
    assert {value.value for value in TranscriptState} == {
        "not_applicable",
        "supplied",
        "acquired",
        "pending",
    }
    assert {value.value for value in ExtractionFailure} == {
        "invalid_input",
        "privacy_denied",
        "egress_denied",
        "unsupported_url",
        "fetch_failed",
        "body_limit",
        "media_limit",
        "tool_unavailable",
        "tool_timeout",
        "tool_resource_limit",
        "malformed_tool_output",
        "executor_denied",
        "executor_failed",
    }


def test_share_request_normalizes_and_round_trips_exact_canonical_shape() -> None:
    request = ShareRequest.create(
        url="HTTPS://Example.Test/path",
        why="Cafe\u0301 reference",
        text="Cafe\u0301\r\nline",
        privacy_tier="personal",
    )

    assert request.url == "https://example.test/path"
    assert request.why == "Caf\u00e9 reference"
    assert request.text == "Caf\u00e9\nline"
    assert request.privacy_tier.value == "personal"
    assert ShareRequest.from_canonical_bytes(request.canonical_bytes()) == request
    assert set(json.loads(request.canonical_bytes())) == {
        "url",
        "why",
        "text",
        "privacy_tier",
    }

    with pytest.raises(ValueError):
        ShareRequest.from_dict({**request.to_dict(), "extra": "rejected"})


@pytest.mark.parametrize(
    "overrides",
    [
        {"url": "https://example.test/" + "x" * 2048},
        {"why": "x" * 281},
        {"why": "line one\nline two"},
        {"why": "   "},
        {"text": "x" * 100_001},
    ],
)
def test_share_request_rejects_unbounded_or_invalid_strings(overrides: dict[str, str]) -> None:
    values = {"url": "https://example.test/", "why": "Synthetic reason", "text": ""}
    values.update(overrides)
    with pytest.raises(ValueError):
        ShareRequest.create(**values)


def test_share_response_binds_duplicate_flag_to_closed_status() -> None:
    queued = ShareResponse.create(
        capture_id=CAPTURE_ID,
        pipeline=CapturePipeline.WEB,
        duplicate=False,
        status=ShareStatus.QUEUED,
    )
    duplicate = ShareResponse.create(
        capture_id=CAPTURE_ID,
        pipeline="web",
        duplicate=True,
        status="duplicate",
    )

    assert ShareResponse.from_canonical_bytes(queued.canonical_bytes()) == queued
    assert duplicate.duplicate is True
    with pytest.raises(ValueError):
        ShareResponse.create(
            capture_id=CAPTURE_ID,
            pipeline="web",
            duplicate=False,
            status="duplicate",
        )


def _metadata() -> ExtractionMetadata:
    eastern = timezone(timedelta(hours=-5))
    return ExtractionMetadata.create(
        title="Cafe\u0301 title",
        author="Synthetic author",
        published_at=datetime(2026, 1, 2, 3, 4, 5, tzinfo=eastern),
        canonical_url="HTTPS://Example.Test/article",
        platform="synthetic",
        video_id="video_123",
    )


def _extraction(**overrides: object) -> NormalizedExtraction:
    values: dict[str, Any] = {
        "extractor": ExtractorKind.ARTICLE,
        "state": ExtractionState.COMPLETE,
        "source_type": SourceType.WEB,
        "content_kind": ContentKind.ARTICLE,
        "metadata": _metadata(),
        "text": "Cafe\u0301 body\r\nline",
        "transcript": None,
        "transcript_state": TranscriptState.NOT_APPLICABLE,
        "assets": (),
        "failure": None,
    }
    values.update(overrides)
    return NormalizedExtraction.create(**values)


def test_extraction_metadata_and_result_are_canonical_frozen_and_utc() -> None:
    extraction = _extraction()

    assert extraction.metadata.title == "Caf\u00e9 title"
    assert extraction.metadata.published_at == datetime(2026, 1, 2, 8, 4, 5, tzinfo=UTC)
    assert extraction.metadata.canonical_url == "https://example.test/article"
    assert extraction.text == "Caf\u00e9 body\nline"
    assert NormalizedExtraction.from_canonical_bytes(extraction.canonical_bytes()) == extraction
    assert set(json.loads(extraction.canonical_bytes())["metadata"]) == {
        "title",
        "author",
        "published_at",
        "canonical_url",
        "platform",
        "video_id",
    }


@pytest.mark.parametrize(
    "overrides",
    [
        {"state": ExtractionState.COMPLETE, "failure": ExtractionFailure.FETCH_FAILED},
        {"state": ExtractionState.REJECTED, "failure": None},
        {"state": ExtractionState.FAILED, "failure": None},
        {"state": ExtractionState.PENDING_TRANSCRIPT, "transcript_state": "not_applicable"},
        {"state": ExtractionState.COMPLETE, "transcript_state": "pending"},
        {"transcript_state": "supplied", "transcript": None},
        {"transcript_state": "not_applicable", "transcript": "unexpected"},
        {"text": "x" * (2 * 1024 * 1024 + 1)},
    ],
)
def test_normalized_extraction_rejects_invalid_state_combinations(
    overrides: dict[str, object],
) -> None:
    with pytest.raises(ValueError):
        _extraction(**overrides)


def test_distillation_item_and_lease_bind_ids_and_digests() -> None:
    item = DistillationWorkItem.create(
        capture_id=CAPTURE_ID,
        event_id=EVENT_ID,
        redacted_event_digest_sha256=DIGEST,
    )
    lease = DistillationLease.create(
        item=item,
        item_id=EVENT_ID,
        payload_digest_sha256=item.payload_digest_sha256(),
        worker_id="worker-1",
        lease_token="lease-1",
        claimed_at=datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone(timedelta(hours=-5))),
    )

    assert DistillationWorkItem.from_canonical_bytes(item.canonical_bytes()) == item
    assert DistillationLease.from_canonical_bytes(lease.canonical_bytes()) == lease
    assert lease.claimed_at == datetime(2026, 1, 2, 8, 4, 5, tzinfo=UTC)
    assert item.payload_digest_sha256() == sha256(item.canonical_bytes()).hexdigest()
    with pytest.raises(ValueError):
        DistillationLease.create(
            item=item,
            item_id="different-event",
            payload_digest_sha256=item.payload_digest_sha256(),
            worker_id="worker-1",
            lease_token="lease-1",
            claimed_at=datetime.now(UTC),
        )
    with pytest.raises(ValueError):
        DistillationWorkItem.create(
            capture_id=CAPTURE_ID,
            event_id=EVENT_ID,
            redacted_event_digest_sha256="not-a-digest",
        )


def test_redaction_result_freezes_payload_and_binds_receipt_digest() -> None:
    payload = {"title": "Cafe\u0301", "nested": ["synthetic", 1]}
    output_digest = EventRecord.output_digest_sha256(payload)
    receipt = RedactionReceipt.create(
        source_digest_sha256="d" * 64,
        output_digest_sha256=output_digest,
        policy_version="redaction-v1",
    )
    result = CaptureRedactionResult.create(payload=payload, receipt=receipt)

    assert isinstance(result.payload, MappingProxyType)
    assert result.payload["title"] == "Caf\u00e9"
    assert result.payload["nested"] == ("synthetic", 1)
    assert CaptureRedactionResult.from_canonical_bytes(result.canonical_bytes()) == result
    assert canonical_json_bytes(result.to_dict()) == result.canonical_bytes()

    wrong_receipt = RedactionReceipt.create(
        source_digest_sha256="d" * 64,
        output_digest_sha256="e" * 64,
        policy_version="redaction-v1",
    )
    with pytest.raises(ValueError):
        CaptureRedactionResult.create(payload=payload, receipt=wrong_receipt)
