from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from open_brain_engine.core.models import (
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
    SourceType,
)

from open_brain_connectors.capture.extractors.youtube import YouTubeMediaResult
from open_brain_connectors.capture.media import MediaCommand
from open_brain_connectors.capture.poll import (
    FilesystemYouTubePollState,
    PollItemState,
    PollRecord,
    PollRequestDisposition,
    PrivacyReclassificationProof,
    PrivacyReclassificationVerifier,
    YouTubePoller,
)

FIXED_TIME = datetime(2026, 8, 13, 12, 0, tzinfo=UTC)


def _privacy(*, egress: bool = True) -> PrivacyDecision:
    return PrivacyDecision.create(
        tier=PrivacyTier.PUBLIC,
        reason=PrivacyReason.POLICY_PUBLIC,
        policy_version="privacy-v1",
        authority=Authority(cloud=False, external_egress=egress),
    )


def _unclassified_privacy() -> PrivacyDecision:
    return PrivacyDecision.create(
        tier=PrivacyTier.UNKNOWN,
        reason=PrivacyReason.CLASSIFICATION_MISSING,
        policy_version="privacy-v1",
        authority=Authority(cloud=False, external_egress=False),
    )


def _envelope(
    *,
    video_id: str = "direct00001",
    privacy: PrivacyDecision | None = None,
) -> CaptureEnvelope:
    url = f"https://www.youtube.com/watch?v={video_id}"
    return CaptureEnvelope.create(
        source_type=SourceType.YOUTUBE,
        content_kind=ContentKind.VIDEO,
        source_url=url,
        title=None,
        shared_text="",
        captured_at=FIXED_TIME,
        capture_why="Review before the synthetic planning session",
        capture_why_origin=CaptureWhyOrigin.OWNER_AUTHORED,
        capture_source=CaptureSource.SHORTCUT,
        provenance=Provenance.create(
            source_ref=url,
            content_origin=ContentOrigin.THIRD_PARTY,
            owner_context=CaptureWhyOrigin.OWNER_AUTHORED,
        ),
        raw_assets=(),
        privacy_decision=privacy or _privacy(),
    )


@dataclass
class _MediaAdapter:
    playlist: tuple[str, ...] = ()
    pending: bool = False
    calls: list[str] = field(default_factory=list)

    def playlist_items(self, url: str, *, command: MediaCommand) -> tuple[str, ...]:
        del url, command
        self.calls.append("playlist")
        return self.playlist

    def media(self, video_id: str, *, command: MediaCommand) -> YouTubeMediaResult:
        del command
        self.calls.append(video_id)
        if self.pending:
            return YouTubeMediaResult(title="Synthetic pending", captions_pending=True)
        return YouTubeMediaResult(
            title="Synthetic video",
            caption_vtt="WEBVTT\n\n00:00.000 --> 00:01.000\nSynthetic transcript",
            captions_pending=False,
        )


@dataclass
class _Verifier(PrivacyReclassificationVerifier):
    allowed_refs: frozenset[str]
    calls: int = 0

    def verify(
        self,
        proof: PrivacyReclassificationProof,
        *,
        capture_id: str,
        prior: PrivacyDecision,
        replacement: PrivacyDecision,
    ) -> bool:
        del capture_id, prior, replacement
        self.calls += 1
        return proof.authorization_ref in self.allowed_refs


def _poller(
    root: Path,
    adapter: _MediaAdapter,
    *,
    max_attempts: int = 3,
    verifier: PrivacyReclassificationVerifier | None = None,
) -> YouTubePoller:
    return YouTubePoller(
        state=FilesystemYouTubePollState(root),
        media_adapter=adapter,
        max_attempts=max_attempts,
        max_playlist_items=2,
        reclassification_verifier=verifier,
    )


def test_direct_and_playlist_requests_preserve_requested_seen_duplicate_state(
    tmp_path: Path,
) -> None:
    adapter = _MediaAdapter(playlist=("playlist002", "playlist001"))
    poller = _poller(tmp_path / "poll", adapter)
    envelope = _envelope()

    created = poller.request_direct(envelope)
    duplicate_requested = poller.request_direct(envelope)
    playlist = poller.request_playlist(
        "https://www.youtube.com/playlist?list=synthetic",
        privacy=_privacy(),
        requested_at=FIXED_TIME + timedelta(seconds=1),
    )
    completed = poller.poll_one(privacy=_privacy())
    duplicate_seen = poller.request_direct(envelope)

    assert created.disposition is PollRequestDisposition.CREATED
    assert duplicate_requested.disposition is PollRequestDisposition.DUPLICATE
    assert [result.record.video_id for result in playlist] == ["playlist001", "playlist002"]
    assert all(result.disposition is PollRequestDisposition.CREATED for result in playlist)
    assert completed is not None
    assert completed.record.state is PollItemState.SEEN
    assert completed.record.attempt_count == 1
    assert completed.record.capture_id == str(envelope.capture_id)
    assert completed.record.capture_why == envelope.capture_why
    assert completed.record.extraction is not None
    assert completed.record.extraction.transcript == "Synthetic transcript"
    assert duplicate_seen.disposition is PollRequestDisposition.DUPLICATE
    assert duplicate_seen.record.state is PollItemState.SEEN

    restored = FilesystemYouTubePollState(tmp_path / "poll").get("direct00001")
    assert restored == completed.record


def test_pending_video_retries_to_durable_failure_stub_and_terminal_replay_is_noop(
    tmp_path: Path,
) -> None:
    adapter = _MediaAdapter(pending=True)
    poller = _poller(tmp_path / "poll", adapter)
    envelope = _envelope()
    poller.request_direct(envelope)

    first = poller.poll_one(privacy=_privacy())
    second = poller.poll_one(privacy=_privacy())
    terminal = poller.poll_one(privacy=_privacy())

    assert first is not None and first.record.state is PollItemState.REQUESTED
    assert second is not None and second.record.attempt_count == 2
    assert terminal is not None and terminal.record.state is PollItemState.STUBBED
    assert terminal.record.attempt_count == 3
    assert terminal.record.failure_code == "pending_transcript"
    assert terminal.record.capture_why == envelope.capture_why
    assert poller.poll_one(privacy=_privacy()) is None
    assert adapter.calls == ["direct00001", "direct00001", "direct00001"]

    replay = _poller(tmp_path / "poll", adapter).request_direct(envelope)
    assert replay.disposition is PollRequestDisposition.DUPLICATE
    assert replay.record == terminal.record
    assert adapter.calls == ["direct00001", "direct00001", "direct00001"]


def test_playlist_discovery_is_bounded_and_private_decisions_make_no_adapter_call(
    tmp_path: Path,
) -> None:
    adapter = _MediaAdapter(playlist=("playlist003", "playlist002", "playlist001"))
    poller = _poller(tmp_path / "poll", adapter)

    over_limit = poller.request_playlist(
        "https://www.youtube.com/playlist?list=synthetic",
        privacy=_privacy(),
        requested_at=FIXED_TIME,
    )
    before_private = list(adapter.calls)
    private = poller.request_playlist(
        "https://www.youtube.com/playlist?list=synthetic",
        privacy=_privacy(egress=False),
        requested_at=FIXED_TIME,
    )

    assert over_limit == ()
    assert private == ()
    assert adapter.calls == before_private == ["playlist"]


def test_direct_share_requires_bound_reclassification_proof_before_egress(
    tmp_path: Path,
) -> None:
    adapter = _MediaAdapter()
    state = FilesystemYouTubePollState(tmp_path / "poll")
    verifier = _Verifier(frozenset({"private-policy.synthetic-001"}))
    poller = YouTubePoller(
        state=state,
        media_adapter=adapter,
        reclassification_verifier=verifier,
    )
    envelope = _envelope(privacy=_unclassified_privacy())
    replacement = _privacy()

    poller.request_direct(envelope)
    assert poller.poll_one(privacy=envelope.privacy_decision) is None
    assert adapter.calls == []

    proof = PrivacyReclassificationProof.create(
        capture_id=str(envelope.capture_id),
        prior=envelope.privacy_decision,
        replacement=replacement,
        authorization_ref="private-policy.synthetic-001",
        policy_version=replacement.policy_version,
    )
    result = poller.poll_one(privacy=replacement, reclassification=proof)

    assert result is not None and result.record.state is PollItemState.SEEN
    assert result.record.capture_id == str(envelope.capture_id)
    assert result.record.capture_why == envelope.capture_why
    assert result.record.privacy == envelope.privacy_decision
    assert result.record.reclassification == proof
    assert adapter.calls == ["direct00001"]
    assert state.get("direct00001") == result.record
    assert verifier.calls == 1


def test_reclassification_proof_cannot_be_replayed_for_another_capture(
    tmp_path: Path,
) -> None:
    adapter = _MediaAdapter()
    poller = _poller(
        tmp_path / "poll",
        adapter,
        verifier=_Verifier(frozenset({"confirmation.synthetic-001"})),
    )
    first = _envelope(privacy=_unclassified_privacy())
    second = _envelope(video_id="direct00002", privacy=_unclassified_privacy())
    replacement = _privacy()
    proof = PrivacyReclassificationProof.create(
        capture_id=str(first.capture_id),
        prior=first.privacy_decision,
        replacement=replacement,
        authorization_ref="confirmation.synthetic-001",
        policy_version=replacement.policy_version,
    )
    poller.request_direct(second)

    with pytest.raises(ValueError, match="invalid privacy reclassification proof"):
        poller.poll_one(privacy=replacement, reclassification=proof)

    assert adapter.calls == []


def test_unverified_reclassification_reference_cannot_enable_egress(tmp_path: Path) -> None:
    adapter = _MediaAdapter()
    verifier = _Verifier(frozenset({"confirmation.synthetic-approved"}))
    poller = _poller(tmp_path / "poll", adapter, verifier=verifier)
    envelope = _envelope(privacy=_unclassified_privacy())
    replacement = _privacy()
    poller.request_direct(envelope)
    forged = PrivacyReclassificationProof.create(
        capture_id=str(envelope.capture_id),
        prior=envelope.privacy_decision,
        replacement=replacement,
        authorization_ref="confirmation.synthetic-forged",
        policy_version=replacement.policy_version,
    )

    with pytest.raises(ValueError, match="invalid privacy reclassification proof"):
        poller.poll_one(privacy=replacement, reclassification=forged)

    assert verifier.calls == 1
    assert adapter.calls == []
    assert poller.poll_one(privacy=envelope.privacy_decision) is None


def test_poll_state_claim_is_atomic_and_expired_claim_is_recoverable(tmp_path: Path) -> None:
    state = FilesystemYouTubePollState(tmp_path / "poll")
    state.request(
        PollRecord.create(
            video_id="direct00001",
            source_url="https://www.youtube.com/watch?v=direct00001",
            state=PollItemState.REQUESTED,
            origin="direct",
            requested_at=FIXED_TIME,
            capture_id=str(_envelope().capture_id),
            capture_why=_envelope().capture_why,
            privacy=_privacy(),
        )
    )

    first = state.claim_next(now=FIXED_TIME, lease_seconds=30)
    concurrent = state.claim_next(now=FIXED_TIME, lease_seconds=30)
    recovered = state.claim_next(now=FIXED_TIME + timedelta(seconds=31), lease_seconds=30)

    assert first is not None and first.state is PollItemState.PROCESSING
    assert concurrent is None
    assert recovered is not None and recovered.state is PollItemState.PROCESSING
    assert recovered.lease_id != first.lease_id
