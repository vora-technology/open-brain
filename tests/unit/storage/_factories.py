from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256

from open_brain.core.models import (
    Authority,
    CaptureEnvelope,
    CaptureSource,
    CaptureWhyOrigin,
    ContentKind,
    ContentOrigin,
    PrivacyDecision,
    PrivacyReason,
    PrivacyTier,
    Provenance,
    RawCapture,
    SourceType,
)

FIXED_TIME = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)


def privacy() -> PrivacyDecision:
    return PrivacyDecision.create(
        tier=PrivacyTier.WORK,
        reason=PrivacyReason.POLICY_WORK,
        policy_version="privacy-v1",
        authority=Authority(cloud=False, external_egress=False),
    )


def raw_capture(*, title: str = "Synthetic title") -> RawCapture:
    shared_text = "Synthetic capture text"
    source_ref = "urn:open-brain:text:sha256:" + sha256(shared_text.encode()).hexdigest()
    envelope = CaptureEnvelope.create(
        source_type=SourceType.TEXT,
        content_kind=ContentKind.OTHER,
        source_url=None,
        title=title,
        shared_text=shared_text,
        captured_at=FIXED_TIME,
        capture_why="Synthetic owner context",
        capture_why_origin=CaptureWhyOrigin.OWNER_AUTHORED,
        capture_source=CaptureSource.CLI,
        provenance=Provenance.create(
            source_ref=source_ref,
            content_origin=ContentOrigin.OWNER_AUTHORED,
            owner_context=CaptureWhyOrigin.OWNER_AUTHORED,
        ),
        raw_assets=(),
        privacy_decision=privacy(),
    )
    return RawCapture.create(envelope=envelope, assets=())


class FixedClock:
    def now(self) -> datetime:
        return FIXED_TIME
