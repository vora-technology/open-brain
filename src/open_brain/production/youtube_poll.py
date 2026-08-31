"""Replay-safe production composition for YouTube playlist capture ingress."""

from __future__ import annotations

import json
import os
import stat
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import cast
from urllib.parse import parse_qs, urlsplit

from open_brain.capture.extractors.youtube import YouTubeMediaAdapter
from open_brain.capture.poll import (
    FilesystemYouTubePollState,
    PollItemState,
    PollRequestDisposition,
    PollRequestOrigin,
    PollRunResult,
    YouTubePoller,
)
from open_brain.core.ids import canonical_json_bytes, canonicalize_source_url
from open_brain.core.models import (
    CaptureEnvelope,
    CaptureSource,
    CaptureWhyOrigin,
    ContentOrigin,
    PrivacyDecision,
    Provenance,
    SourceType,
)
from open_brain.engine import PublicJobCaptureSink
from open_brain.operations.capture_jobs import get_capture_job

_MAX_CONFIG_BYTES = 64 * 1024
_MAX_SUBSCRIPTIONS = 50
_YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com"}


class YouTubePollConfigError(ValueError):
    """A private YouTube poll configuration is absent, unsafe, or malformed."""


@dataclass(frozen=True, slots=True)
class YouTubeSubscription:
    url: str
    privacy: PrivacyDecision

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> YouTubeSubscription:
        if set(value) != {"url", "privacy"}:
            raise YouTubePollConfigError("invalid private YouTube config")
        raw_url = value["url"]
        raw_privacy = value["privacy"]
        if not isinstance(raw_url, str) or not isinstance(raw_privacy, Mapping):
            raise YouTubePollConfigError("invalid private YouTube config")
        try:
            url = canonicalize_source_url(raw_url)
            parsed = urlsplit(url)
            privacy = PrivacyDecision.from_dict(_mapping(raw_privacy))
        except (TypeError, ValueError) as error:
            raise YouTubePollConfigError("invalid private YouTube config") from error
        if (
            parsed.hostname not in _YOUTUBE_HOSTS
            or len(parse_qs(parsed.query).get("list", ())) != 1
        ):
            raise YouTubePollConfigError("invalid private YouTube config")
        return cls(url=url, privacy=privacy)

    def to_dict(self) -> dict[str, object]:
        return {"url": self.url, "privacy": self.privacy.to_dict()}


@dataclass(frozen=True, slots=True)
class YouTubePollConfig:
    subscriptions: tuple[YouTubeSubscription, ...]

    @property
    def requires_external_egress(self) -> bool:
        return any(
            subscription.privacy.authority.external_egress
            for subscription in self.subscriptions
        )

    @classmethod
    def from_canonical_bytes(cls, payload: bytes) -> YouTubePollConfig:
        try:
            decoded = json.loads(payload.decode("utf-8"), object_pairs_hook=_reject_duplicates)
            value = _mapping(decoded)
            raw_subscriptions = value["subscriptions"]
            if (
                set(value) != {"schema_version", "subscriptions"}
                or value["schema_version"] != 1
                or not isinstance(raw_subscriptions, list)
                or len(raw_subscriptions) > _MAX_SUBSCRIPTIONS
            ):
                raise YouTubePollConfigError("invalid private YouTube config")
            subscriptions = tuple(
                YouTubeSubscription.from_dict(_mapping(item))
                for item in raw_subscriptions
            )
            result = cls(subscriptions=subscriptions)
        except (KeyError, TypeError, ValueError, UnicodeDecodeError, json.JSONDecodeError) as error:
            if isinstance(error, YouTubePollConfigError):
                raise
            raise YouTubePollConfigError("invalid private YouTube config") from error
        if (
            len({subscription.url for subscription in subscriptions}) != len(subscriptions)
            or tuple(sorted(subscriptions, key=lambda item: item.url)) != subscriptions
            or result.canonical_bytes() != payload
        ):
            raise YouTubePollConfigError("invalid private YouTube config")
        return result

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(
            {
                "schema_version": 1,
                "subscriptions": [item.to_dict() for item in self.subscriptions],
            }
        )


@dataclass(frozen=True, slots=True)
class ProductionYouTubePollResult:
    discovered_count: int
    polled_count: int
    stubbed_count: int
    created_count: int
    duplicate_count: int


class ProductionYouTubePollRuntime:
    def __init__(
        self,
        *,
        config: YouTubePollConfig,
        state: FilesystemYouTubePollState,
        sink: PublicJobCaptureSink,
        media_adapter: YouTubeMediaAdapter,
        clock: Callable[[], datetime],
    ) -> None:
        if (
            not isinstance(config, YouTubePollConfig)
            or not isinstance(state, FilesystemYouTubePollState)
            or not isinstance(sink, PublicJobCaptureSink)
            or not callable(clock)
        ):
            raise ValueError("invalid production YouTube poll runtime")
        self._config = config
        self._state = state
        self._sink = sink
        self._poller = YouTubePoller(state=state, media_adapter=media_adapter)
        self._clock = clock

    @property
    def requires_external_egress(self) -> bool:
        return self._config.requires_external_egress

    def run(self, *, max_items: int = 100) -> ProductionYouTubePollResult:
        if (
            not isinstance(max_items, int)
            or isinstance(max_items, bool)
            or not 1 <= max_items <= 1_000
        ):
            raise ValueError("invalid YouTube poll batch")
        discovered = 0
        for subscription in self._config.subscriptions:
            requests = self._poller.request_playlist(
                subscription.url,
                privacy=subscription.privacy,
                requested_at=self._clock(),
            )
            discovered += sum(
                request.disposition is PollRequestDisposition.CREATED
                for request in requests
            )

        polled = 0
        stubbed = 0
        for _ in range(max_items):
            pending = next(
                (
                    record
                    for record in self._state.records()
                    if record.state is PollItemState.REQUESTED
                ),
                None,
            )
            if pending is None:
                break
            result = self._poller.poll_one(privacy=pending.privacy)
            if not isinstance(result, PollRunResult):
                break
            polled += 1
            stubbed += result.record.state is PollItemState.STUBBED

        created = 0
        duplicates = 0
        application = get_capture_job("JOB-029")
        for record in self._state.records():
            if (
                record.state is not PollItemState.SEEN
                or record.origin is not PollRequestOrigin.PLAYLIST
            ):
                continue
            append = application.submit(sink=self._sink, envelope=_playlist_envelope(record))
            self._state.replace(
                record,
                type(record).from_dict(
                    {
                        **record.to_dict(),
                        "capture_id": append.capture_id,
                        "state": PollItemState.ACCEPTED.value,
                    }
                ),
            )
            if append.disposition.value == "created":
                created += 1
            else:
                duplicates += 1
        return ProductionYouTubePollResult(
            discovered_count=discovered,
            polled_count=polled,
            stubbed_count=stubbed,
            created_count=created,
            duplicate_count=duplicates,
        )


def load_private_youtube_config(path: Path) -> YouTubePollConfig:
    if not isinstance(path, Path) or not path.is_absolute():
        raise YouTubePollConfigError("invalid private YouTube config")
    descriptor = -1
    try:
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.getuid()
            or stat.S_IMODE(metadata.st_mode) & 0o077
            or metadata.st_nlink != 1
            or not 0 < metadata.st_size <= _MAX_CONFIG_BYTES
        ):
            raise YouTubePollConfigError("invalid private YouTube config")
        with os.fdopen(descriptor, "rb") as stream:
            descriptor = -1
            payload = stream.read(_MAX_CONFIG_BYTES + 1)
    except YouTubePollConfigError:
        raise
    except OSError as error:
        raise YouTubePollConfigError("invalid private YouTube config") from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if len(payload) > _MAX_CONFIG_BYTES:
        raise YouTubePollConfigError("invalid private YouTube config")
    return YouTubePollConfig.from_canonical_bytes(payload)


def compose_production_youtube_poll_runtime(
    *,
    config_path: Path,
    state_root: Path,
    sink: PublicJobCaptureSink,
    media_adapter: YouTubeMediaAdapter,
    clock: Callable[[], datetime],
) -> ProductionYouTubePollRuntime:
    if not isinstance(state_root, Path) or not state_root.is_absolute():
        raise ValueError("invalid production YouTube poll state")
    return ProductionYouTubePollRuntime(
        config=load_private_youtube_config(config_path),
        state=FilesystemYouTubePollState(state_root / "youtube-poll"),
        sink=sink,
        media_adapter=media_adapter,
        clock=clock,
    )


def _playlist_envelope(record: object) -> CaptureEnvelope:
    from open_brain.capture.poll import PollRecord

    if not isinstance(record, PollRecord) or record.extraction is None:
        raise ValueError("invalid completed playlist record")
    extraction = record.extraction
    shared_text = extraction.transcript or extraction.text
    if (
        extraction.source_type is not SourceType.YOUTUBE
        or not shared_text.strip()
        or extraction.assets
    ):
        raise ValueError("invalid completed playlist extraction")
    privacy = (
        record.reclassification.replacement
        if record.reclassification is not None
        else record.privacy
    )
    return CaptureEnvelope.create(
        source_type=SourceType.YOUTUBE,
        content_kind=extraction.content_kind,
        source_url=record.source_url,
        title=extraction.metadata.title,
        shared_text=shared_text,
        captured_at=record.requested_at,
        capture_why="",
        capture_why_origin=CaptureWhyOrigin.AUTOMATION_ABSENT,
        capture_source=CaptureSource.PLAYLIST,
        provenance=Provenance.create(
            source_ref=record.source_url,
            content_origin=ContentOrigin.THIRD_PARTY,
            owner_context=CaptureWhyOrigin.AUTOMATION_ABSENT,
        ),
        raw_assets=(),
        privacy_decision=privacy,
    )


def _mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        raise YouTubePollConfigError("invalid private YouTube config")
    return cast(Mapping[str, object], value)


def _reject_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise YouTubePollConfigError("invalid private YouTube config")
        result[key] = value
    return result


__all__ = [
    "ProductionYouTubePollResult",
    "ProductionYouTubePollRuntime",
    "YouTubePollConfig",
    "YouTubePollConfigError",
    "YouTubeSubscription",
    "compose_production_youtube_poll_runtime",
    "load_private_youtube_config",
]
