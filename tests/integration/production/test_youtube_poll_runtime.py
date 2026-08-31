from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import pytest

from open_brain.capture.extractors.youtube import YouTubeMediaResult
from open_brain.capture.media import MediaCommand
from open_brain.capture.queue import FilesystemCaptureQueue
from open_brain.core.ids import canonical_json_bytes
from open_brain.core.models import (
    Authority,
    CaptureSource,
    PrivacyDecision,
    PrivacyReason,
    PrivacyTier,
)
from open_brain.production.youtube_poll import (
    YouTubePollConfigError,
    compose_production_youtube_poll_runtime,
    load_private_youtube_config,
)

FIXED_TIME = datetime(2026, 8, 25, 12, 0, tzinfo=UTC)


@dataclass
class _MediaAdapter:
    playlist: tuple[str, ...] = ("video000001", "video000002")
    calls: list[str] = field(default_factory=list)

    def playlist_items(self, url: str, *, command: MediaCommand) -> tuple[str, ...]:
        del url, command
        self.calls.append("playlist")
        return self.playlist

    def media(self, video_id: str, *, command: MediaCommand) -> YouTubeMediaResult:
        del command
        self.calls.append(video_id)
        return YouTubeMediaResult(
            title="Synthetic video " + video_id,
            caption_vtt="WEBVTT\n\n00:00.000 --> 00:01.000\nSynthetic transcript",
            captions_pending=False,
        )


def _privacy(*, egress: bool = True) -> PrivacyDecision:
    if egress:
        return PrivacyDecision.create(
            tier=PrivacyTier.PUBLIC,
            reason=PrivacyReason.POLICY_PUBLIC,
            policy_version="privacy-v1",
            authority=Authority(cloud=False, external_egress=True),
        )
    return PrivacyDecision.create(
        tier=PrivacyTier.UNKNOWN,
        reason=PrivacyReason.CLASSIFICATION_MISSING,
        policy_version="privacy-v1",
        authority=Authority(cloud=False, external_egress=False),
    )


def _config(path: Path, *, privacy: PrivacyDecision | None = None) -> Path:
    path.write_bytes(
        canonical_json_bytes(
            {
                "schema_version": 1,
                "subscriptions": [
                    {
                        "url": "https://www.youtube.com/playlist?list=synthetic",
                        "privacy": (privacy or _privacy()).to_dict(),
                    }
                ],
            }
        )
    )
    path.chmod(0o600)
    return path


def test_poll_runtime_republishes_seen_transcripts_after_queue_loss(tmp_path: Path) -> None:
    config = _config(tmp_path / "youtube.json")
    state_root = tmp_path / "state"
    first_queue = FilesystemCaptureQueue(tmp_path / "first-queue")
    media = _MediaAdapter()

    first = compose_production_youtube_poll_runtime(
        config_path=config,
        state_root=state_root,
        queue=first_queue,
        media_adapter=media,
        clock=lambda: FIXED_TIME,
    ).run(max_items=10)
    recovered_queue = FilesystemCaptureQueue(tmp_path / "recovered-queue")
    replay = compose_production_youtube_poll_runtime(
        config_path=config,
        state_root=state_root,
        queue=recovered_queue,
        media_adapter=media,
        clock=lambda: FIXED_TIME,
    ).run(max_items=10)

    assert first.discovered_count == 2
    assert first.polled_count == 2
    assert first.created_count == 2
    assert replay.polled_count == 0
    assert replay.created_count == 2
    assert media.calls == ["playlist", "video000001", "video000002", "playlist"]
    assert recovered_queue.pending_snapshot().pending_count == 2
    lease = recovered_queue.claim(worker_id="synthetic", now=FIXED_TIME)
    assert lease is not None
    assert lease.item.envelope.capture_source is CaptureSource.PLAYLIST
    assert lease.item.envelope.shared_text == "Synthetic transcript"
    assert lease.item.envelope.capture_why == ""


def test_local_only_subscription_causes_zero_media_or_queue_effects(tmp_path: Path) -> None:
    config = _config(tmp_path / "youtube.json", privacy=_privacy(egress=False))
    media = _MediaAdapter()
    queue = FilesystemCaptureQueue(tmp_path / "queue")

    result = compose_production_youtube_poll_runtime(
        config_path=config,
        state_root=tmp_path / "state",
        queue=queue,
        media_adapter=media,
        clock=lambda: FIXED_TIME,
    ).run(max_items=10)

    assert result.discovered_count == 0
    assert result.polled_count == 0
    assert result.created_count == 0
    assert media.calls == []
    assert queue.pending_snapshot().pending_count == 0


def test_private_youtube_config_requires_owner_only_regular_canonical_file(
    tmp_path: Path,
) -> None:
    config = _config(tmp_path / "youtube.json")
    config.chmod(0o644)

    with pytest.raises(YouTubePollConfigError, match="private YouTube config"):
        load_private_youtube_config(config)

    config.chmod(0o600)
    linked = tmp_path / "linked.json"
    linked.symlink_to(config)
    with pytest.raises(YouTubePollConfigError, match="private YouTube config"):
        load_private_youtube_config(linked)
