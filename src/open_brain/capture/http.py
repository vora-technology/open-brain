from __future__ import annotations

import json
import unicodedata
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from urllib.parse import urlsplit

from open_brain.capture.auth import BearerAuthenticator
from open_brain.capture.models import (
    CapturePipeline,
    CaptureWorkItem,
    ShareRequest,
    ShareResponse,
    ShareStatus,
)
from open_brain.capture.queue import QueueImmutableConflictError
from open_brain.core.ids import canonical_json_bytes
from open_brain.core.models import (
    CaptureEnvelope,
    CaptureSource,
    CaptureWhyOrigin,
    ContentKind,
    ContentOrigin,
    Provenance,
    SourceType,
)
from open_brain.core.policy import classify_privacy
from open_brain.core.ports import PutDisposition, PutResult

BODY_LIMIT_BYTES = 100_000
REQUEST_TIMEOUT_SECONDS = 5.0
_PRIVACY_POLICY_VERSION = "privacy-v1"
_YOUTUBE_HOSTS = {"youtube.com", "youtu.be"}
_SOCIAL_HOSTS = {
    "bsky.app",
    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "reddit.com",
    "tiktok.com",
    "twitter.com",
    "x.com",
}


class RequestReadTimeout(Exception):
    """The injected request reader exceeded the intake read deadline."""


class _FieldTooLarge(Exception):
    pass


class BodyReader(Protocol):
    def __call__(self, maximum_bytes: int, timeout_seconds: float) -> bytes: ...


class ShareQueue(Protocol):
    def enqueue(self, item: CaptureWorkItem, *, item_id: str, payload_digest: str) -> PutResult: ...


@dataclass(frozen=True, slots=True)
class HttpRequest:
    method: str
    path: str
    headers: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class HttpResponse:
    status: int
    body: bytes
    headers: tuple[tuple[str, str], ...] = (("Content-Type", "application/json"),)


class ShareHttpHandler:
    """A framework-neutral, bounded HTTP boundary for POST /share."""

    def __init__(
        self,
        *,
        expected_bearer_token: str,
        queue: ShareQueue,
        clock: Callable[[], datetime],
        body_reader: BodyReader,
    ) -> None:
        if not callable(clock) or not callable(body_reader):
            raise ValueError("invalid share handler dependencies")
        self._authenticator = BearerAuthenticator(expected_bearer_token)
        self._queue = queue
        self._clock = clock
        self._body_reader = body_reader

    def handle(self, request: HttpRequest) -> HttpResponse:
        if not isinstance(request, HttpRequest) or (
            request.method != "POST" or request.path != "/share"
        ):
            return _error(400, "invalid_request")

        headers = _headers(request.headers)
        if headers is None:
            return _error(400, "invalid_request")
        content_length = _content_length(headers)
        if content_length is None or content_length > BODY_LIMIT_BYTES:
            return _error(413, "request_too_large")
        if not _is_json_content_type(headers):
            return _error(415, "unsupported_media_type")
        if not self._authenticator.authenticate(headers.get("authorization", ())):
            return _error(401, "unauthorized")

        try:
            body = self._body_reader(BODY_LIMIT_BYTES, REQUEST_TIMEOUT_SECONDS)
        except RequestReadTimeout:
            return _error(408, "request_timeout")
        except Exception:
            return _error(400, "invalid_request")
        if not isinstance(body, bytes):
            return _error(400, "invalid_request")
        if len(body) > BODY_LIMIT_BYTES:
            return _error(413, "request_too_large")
        if len(body) != content_length:
            return _error(400, "invalid_request")

        try:
            share_request = _parse_share_request(body)
        except _FieldTooLarge:
            return _error(413, "request_too_large")
        if share_request is None:
            return _error(400, "invalid_request")
        try:
            response = enqueue_share(
                request=share_request,
                queue=self._queue,
                clock=self._clock,
            )
        except QueueImmutableConflictError:
            return _error(409, "immutable_conflict")
        except Exception:
            return _error(500, "queue_unavailable")
        return HttpResponse(status=202, body=canonical_json_bytes(response.to_dict()))


def enqueue_share(
    *,
    request: ShareRequest,
    queue: ShareQueue,
    clock: Callable[[], datetime],
) -> ShareResponse:
    """Submit one validated share through the same durable queue path as HTTP."""
    if not isinstance(request, ShareRequest) or not callable(clock):
        raise ValueError("invalid share submission")
    item, pipeline = _capture_item(request, clock)
    put_result = queue.enqueue(
        item,
        item_id=str(item.envelope.capture_id),
        payload_digest=item.payload_digest_sha256(),
    )
    if not isinstance(put_result, PutResult) or put_result.disposition not in {
        PutDisposition.CREATED,
        PutDisposition.DUPLICATE,
    }:
        raise ValueError("invalid share queue result")
    duplicate = put_result.disposition is PutDisposition.DUPLICATE
    return ShareResponse.create(
        capture_id=item.envelope.capture_id,
        pipeline=pipeline,
        duplicate=duplicate,
        status=ShareStatus.DUPLICATE if duplicate else ShareStatus.QUEUED,
    )


def _headers(value: object) -> dict[str, tuple[str, ...]] | None:
    if not isinstance(value, tuple):
        return None
    normalized: dict[str, list[str]] = {}
    for header in value:
        if (
            not isinstance(header, tuple)
            or len(header) != 2
            or not isinstance(header[0], str)
            or not isinstance(header[1], str)
            or not header[0].isascii()
        ):
            return None
        normalized.setdefault(header[0].lower(), []).append(header[1])
    return {key: tuple(values) for key, values in normalized.items()}


def _content_length(headers: Mapping[str, tuple[str, ...]]) -> int | None:
    values = headers.get("content-length", ())
    if len(values) != 1 or not values[0] or not values[0].isascii() or not values[0].isdigit():
        return None
    return int(values[0])


def _is_json_content_type(headers: Mapping[str, tuple[str, ...]]) -> bool:
    values = headers.get("content-type", ())
    return len(values) == 1 and values[0].strip().lower() == "application/json"


def _parse_share_request(body: bytes) -> ShareRequest | None:
    try:
        decoded = json.loads(body.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
        required_fields = {"url", "why"}
        optional_fields = {"text", "privacy"}
        if (
            not isinstance(decoded, dict)
            or not required_fields.issubset(decoded)
            or not set(decoded).issubset(required_fields | optional_fields)
        ):
            return None
        url = decoded["url"]
        why = decoded["why"]
        text = decoded.get("text", "")
        privacy = decoded.get("privacy")
        if (
            not isinstance(url, str)
            or not isinstance(why, str)
            or not isinstance(text, str)
            or (privacy is not None and not isinstance(privacy, str))
        ):
            return None
        if len(unicodedata.normalize("NFC", url).encode("utf-8")) > 2_048:
            raise _FieldTooLarge
        return ShareRequest.create(
            url=url,
            why=why,
            text=text,
            privacy_tier=privacy,
        )
    except (UnicodeDecodeError, ValueError, json.JSONDecodeError):
        return None


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _capture_item(
    request: ShareRequest, clock: Callable[[], datetime]
) -> tuple[CaptureWorkItem, CapturePipeline]:
    pipeline, source_type, content_kind = _classify_pipeline(request.url)
    envelope = CaptureEnvelope.create(
        source_type=source_type,
        content_kind=content_kind,
        source_url=request.url,
        title=None,
        shared_text=request.text,
        captured_at=clock(),
        capture_why=request.why,
        capture_why_origin=CaptureWhyOrigin.OWNER_AUTHORED,
        capture_source=CaptureSource.SHORTCUT,
        provenance=Provenance.create(
            source_ref=request.url,
            content_origin=ContentOrigin.THIRD_PARTY,
            owner_context=CaptureWhyOrigin.OWNER_AUTHORED,
        ),
        raw_assets=(),
        privacy_decision=classify_privacy(
            request.privacy_tier,
            policy_version=_PRIVACY_POLICY_VERSION,
        ),
    )
    return CaptureWorkItem.create(envelope=envelope, available_at=envelope.captured_at), pipeline


def _classify_pipeline(url: str) -> tuple[CapturePipeline, SourceType, ContentKind]:
    host = urlsplit(url).hostname or ""
    if _matches_host(host, _YOUTUBE_HOSTS):
        return CapturePipeline.YOUTUBE, SourceType.YOUTUBE, ContentKind.VIDEO
    if _matches_host(host, _SOCIAL_HOSTS):
        return CapturePipeline.SOCIAL, SourceType.SOCIAL, ContentKind.POST
    return CapturePipeline.WEB, SourceType.WEB, ContentKind.ARTICLE


def _matches_host(host: str, allowed_hosts: set[str]) -> bool:
    return any(host == allowed or host.endswith("." + allowed) for allowed in allowed_hosts)


def _error(status: int, code: str) -> HttpResponse:
    return HttpResponse(status=status, body=canonical_json_bytes({"code": code}))
