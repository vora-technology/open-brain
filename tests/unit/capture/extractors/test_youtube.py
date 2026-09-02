from __future__ import annotations

from dataclasses import dataclass, field

import pytest
from open_brain_engine.capture.models import ExtractionFailure, ExtractionState, TranscriptState
from open_brain_engine.core.models import Authority, PrivacyDecision, PrivacyReason, PrivacyTier

from open_brain.capture.extractors.youtube import (
    YouTubeExtractionRequest,
    YouTubeExtractor,
    YouTubeMediaResult,
)
from open_brain.capture.media import DEFAULT_MEDIA_LIMITS, MediaCommand


def _privacy(*, egress: bool = True) -> PrivacyDecision:
    return PrivacyDecision.create(
        tier=PrivacyTier.PUBLIC,
        reason=PrivacyReason.POLICY_PUBLIC,
        policy_version="test-v1",
        authority=Authority(cloud=False, external_egress=egress),
    )


@dataclass
class FakeMediaAdapter:
    playlist: tuple[str, ...] = ()
    result: YouTubeMediaResult = field(default_factory=YouTubeMediaResult)
    calls: list[tuple[str, object]] = field(default_factory=list)

    def playlist_items(self, url: str, *, command: MediaCommand) -> tuple[str, ...]:
        self.calls.append(("playlist", command))
        return self.playlist

    def media(self, video_id: str, *, command: MediaCommand) -> YouTubeMediaResult:
        self.calls.append((video_id, command))
        return self.result


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://www.youtube.com/shorts/dQw4w9WgXcQ",
        "https://www.youtube.com/embed/dQw4w9WgXcQ",
        "https://www.youtube.com/live/dQw4w9WgXcQ",
    ],
)
def test_supported_youtube_urls_normalize_to_a_valid_video_id(url: str) -> None:
    result = YouTubeExtractor(FakeMediaAdapter()).extract(
        YouTubeExtractionRequest(url=url), privacy=_privacy()
    )

    assert result.state is ExtractionState.PENDING_TRANSCRIPT
    assert result.metadata.video_id == "dQw4w9WgXcQ"


@pytest.mark.parametrize(
    "url",
    [
        "https://example.test/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/no",
        "https://youtube.com/watch?v=bad!",
    ],
)
def test_invalid_or_non_youtube_urls_are_rejected_without_adapter_calls(url: str) -> None:
    adapter = FakeMediaAdapter()

    result = YouTubeExtractor(adapter).extract(
        YouTubeExtractionRequest(url=url), privacy=_privacy()
    )

    assert result.state is ExtractionState.REJECTED
    assert result.failure is ExtractionFailure.UNSUPPORTED_URL
    assert adapter.calls == []


def test_playlist_is_bounded_and_returned_oldest_first() -> None:
    adapter = FakeMediaAdapter(playlist=("newest", "middle", "oldest"))
    extractor = YouTubeExtractor(adapter)

    assert extractor.playlist_items(
        "https://www.youtube.com/playlist?list=PL123", max_items=3, privacy=_privacy()
    ) == (
        "oldest",
        "middle",
        "newest",
    )
    assert (
        extractor.playlist_items(
            "https://www.youtube.com/playlist?list=PL123", max_items=2, privacy=_privacy()
        )
        == ()
    )


def test_vtt_is_cleaned_and_supplied_transcript_wins_without_media_call() -> None:
    adapter = FakeMediaAdapter(
        result=YouTubeMediaResult(
            caption_vtt=(
                "WEBVTT\n\n00:00.000 --> 00:01.000\ncaption <b>one</b>\n\n"
                "00:01.000 --> 00:02.000\ncaption one"
            )
        )
    )
    result = YouTubeExtractor(adapter).extract(
        YouTubeExtractionRequest(
            url="https://youtu.be/dQw4w9WgXcQ",
            supplied_transcript="owner supplied transcript",
        ),
        privacy=_privacy(),
    )

    assert result.transcript == "owner supplied transcript"
    assert result.transcript_state is TranscriptState.SUPPLIED
    assert adapter.calls == []

    acquired = YouTubeExtractor(adapter).extract(
        YouTubeExtractionRequest(url="https://youtu.be/dQw4w9WgXcQ"), privacy=_privacy()
    )
    assert acquired.transcript == "caption one"
    assert acquired.transcript_state is TranscriptState.ACQUIRED


def test_supplied_transcript_needs_no_external_egress() -> None:
    adapter = FakeMediaAdapter()

    result = YouTubeExtractor(adapter).extract(
        YouTubeExtractionRequest(
            url="https://youtu.be/dQw4w9WgXcQ",
            supplied_transcript="locally acquired transcript",
        ),
        privacy=_privacy(egress=False),
    )

    assert result.state is ExtractionState.COMPLETE
    assert result.transcript == "locally acquired transcript"
    assert result.transcript_state is TranscriptState.SUPPLIED
    assert adapter.calls == []


def test_missing_captions_are_pending_with_metadata_and_privacy_denial_calls_no_adapter() -> None:
    adapter = FakeMediaAdapter(
        result=YouTubeMediaResult(title="Synthetic title", captions_pending=True)
    )
    extractor = YouTubeExtractor(adapter)

    pending = extractor.extract(
        YouTubeExtractionRequest(url="https://youtu.be/dQw4w9WgXcQ"), privacy=_privacy()
    )
    denied = extractor.extract(
        YouTubeExtractionRequest(url="https://youtu.be/dQw4w9WgXcQ"), privacy=_privacy(egress=False)
    )

    assert pending.state is ExtractionState.PENDING_TRANSCRIPT
    assert pending.metadata.title == "Synthetic title"
    assert pending.transcript is None
    assert denied.state is ExtractionState.REJECTED
    assert denied.failure is ExtractionFailure.PRIVACY_DENIED
    assert len(adapter.calls) == 1


def test_media_commands_are_fixed_and_bounded_and_missing_adapter_fails_closed() -> None:
    adapter = FakeMediaAdapter()
    extractor = YouTubeExtractor(adapter)
    extractor.extract(
        YouTubeExtractionRequest(url="https://youtu.be/dQw4w9WgXcQ"), privacy=_privacy()
    )
    command = adapter.calls[0][1]

    assert isinstance(command, MediaCommand)
    assert command.argv == ("yt-dlp", "--skip-download", "--no-playlist")
    assert command.environment == ()
    assert command.limits == DEFAULT_MEDIA_LIMITS

    unavailable = YouTubeExtractor().extract(
        YouTubeExtractionRequest(url="https://youtu.be/dQw4w9WgXcQ"), privacy=_privacy()
    )
    assert unavailable.state is ExtractionState.FAILED
    assert unavailable.failure is ExtractionFailure.TOOL_UNAVAILABLE


@pytest.mark.parametrize(
    "failure",
    [
        ExtractionFailure.TOOL_TIMEOUT,
        ExtractionFailure.TOOL_RESOURCE_LIMIT,
        ExtractionFailure.MALFORMED_TOOL_OUTPUT,
    ],
)
def test_media_runner_failures_remain_closed(failure: ExtractionFailure) -> None:
    adapter = FakeMediaAdapter(result=YouTubeMediaResult(failure=failure))

    result = YouTubeExtractor(adapter).extract(
        YouTubeExtractionRequest(url="https://youtu.be/dQw4w9WgXcQ"), privacy=_privacy()
    )

    assert result.state is ExtractionState.FAILED
    assert result.failure is failure
    assert result.assets == ()
