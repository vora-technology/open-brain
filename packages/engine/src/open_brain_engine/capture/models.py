from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from hashlib import sha256
from types import MappingProxyType
from typing import Any, Protocol, TypeVar, cast

from open_brain_engine.core.ids import (
    CaptureId,
    canonical_json_bytes,
    canonicalize_source_url,
    validate_identifier,
)
from open_brain_engine.core.models import (
    CaptureEnvelope,
    ContentKind,
    PrivacyDecision,
    PrivacyTier,
    RawAssetRef,
    SourceType,
    ValidationError,
)
from open_brain_engine.core.ports import EventRecord, JsonValue, RedactionReceipt


class QueueItemState(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    QUARANTINED = "quarantined"
    ACKNOWLEDGED = "acknowledged"


class QueueErrorCode(StrEnum):
    INVALID_ITEM = "invalid_item"
    INVALID_DIGEST = "invalid_digest"
    INVALID_SCHEMA = "invalid_schema"
    IMMUTABLE_CONFLICT = "immutable_conflict"
    DURABILITY_FAILED = "durability_failed"
    RETRYABLE_FAILURE = "retryable_failure"
    RETRY_EXHAUSTED = "retry_exhausted"
    PRIVACY_HOLD = "privacy_hold"
    REDACTION_FAILED = "redaction_failed"
    EXTRACTION_FAILED = "extraction_failed"


class CapturePipeline(StrEnum):
    YOUTUBE = "youtube"
    SOCIAL = "social"
    WEB = "web"


class ShareStatus(StrEnum):
    QUEUED = "queued"
    DUPLICATE = "duplicate"


class ExtractorKind(StrEnum):
    TEXT = "text"
    ARTICLE = "article"
    YOUTUBE = "youtube"
    SOCIAL = "social"


class ExtractionState(StrEnum):
    COMPLETE = "complete"
    PENDING_TRANSCRIPT = "pending_transcript"
    NO_CONTENT = "no_content"
    REJECTED = "rejected"
    FAILED = "failed"


class TranscriptState(StrEnum):
    NOT_APPLICABLE = "not_applicable"
    SUPPLIED = "supplied"
    ACQUIRED = "acquired"
    PENDING = "pending"


class ExtractionFailure(StrEnum):
    INVALID_INPUT = "invalid_input"
    PRIVACY_DENIED = "privacy_denied"
    EGRESS_DENIED = "egress_denied"
    UNSUPPORTED_URL = "unsupported_url"
    FETCH_FAILED = "fetch_failed"
    BODY_LIMIT = "body_limit"
    MEDIA_LIMIT = "media_limit"
    TOOL_UNAVAILABLE = "tool_unavailable"
    TOOL_TIMEOUT = "tool_timeout"
    TOOL_RESOURCE_LIMIT = "tool_resource_limit"
    MALFORMED_TOOL_OUTPUT = "malformed_tool_output"
    EXECUTOR_DENIED = "executor_denied"
    EXECUTOR_FAILED = "executor_failed"


@dataclass(frozen=True, slots=True)
class CaptureWorkItem:
    schema_version: int
    envelope: CaptureEnvelope
    available_at: datetime
    attempt_count: int
    last_error_code: QueueErrorCode | None

    @classmethod
    def create(
        cls,
        *,
        envelope: CaptureEnvelope,
        available_at: datetime,
        attempt_count: int = 0,
        last_error_code: QueueErrorCode | str | None = None,
    ) -> CaptureWorkItem:
        if not isinstance(envelope, CaptureEnvelope):
            raise ValueError("invalid capture work item")
        if (
            not isinstance(attempt_count, int)
            or isinstance(attempt_count, bool)
            or attempt_count < 0
        ):
            raise ValueError("invalid capture work item")
        return cls(
            schema_version=1,
            envelope=envelope,
            available_at=_utc_datetime(available_at),
            attempt_count=attempt_count,
            last_error_code=_queue_code(last_error_code),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "envelope": self.envelope.to_dict(),
            "available_at": _timestamp(self.available_at),
            "attempt_count": self.attempt_count,
            "last_error_code": None if self.last_error_code is None else self.last_error_code.value,
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    def payload_digest_sha256(self) -> str:
        return sha256(self.canonical_bytes()).hexdigest()

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> CaptureWorkItem:
        _exact_keys(
            value,
            {"schema_version", "envelope", "available_at", "attempt_count", "last_error_code"},
        )
        if value["schema_version"] != 1 or not isinstance(value["attempt_count"], int):
            raise ValueError("invalid capture work item")
        try:
            return cls.create(
                envelope=CaptureEnvelope.from_dict(_mapping(value["envelope"])),
                available_at=_parse_timestamp(_string(value["available_at"])),
                attempt_count=value["attempt_count"],
                last_error_code=cast(str | None, value["last_error_code"]),
            )
        except (ValidationError, TypeError, ValueError) as error:
            raise ValueError("invalid capture work item") from error

    @classmethod
    def from_canonical_bytes(cls, payload: bytes) -> CaptureWorkItem:
        try:
            decoded = json.loads(payload.decode("utf-8"), object_pairs_hook=_reject_duplicates)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
            raise ValueError("invalid capture work item") from error
        result = cls.from_dict(_mapping(decoded))
        if result.canonical_bytes() != payload:
            raise ValueError("non-canonical capture work item")
        return result


@dataclass(frozen=True, slots=True)
class CaptureLease:
    item: CaptureWorkItem
    item_id: str
    payload_digest_sha256: str
    worker_id: str
    lease_token: str
    claimed_at: datetime

    @classmethod
    def create(
        cls,
        *,
        item: CaptureWorkItem,
        item_id: str,
        payload_digest_sha256: str,
        worker_id: str,
        lease_token: str,
        claimed_at: datetime,
    ) -> CaptureLease:
        if (
            not isinstance(item, CaptureWorkItem)
            or item_id != str(item.envelope.capture_id)
            or payload_digest_sha256 != item.payload_digest_sha256()
            or not _OPAQUE.fullmatch(worker_id)
            or not _OPAQUE.fullmatch(lease_token)
        ):
            raise ValueError("invalid capture lease")
        return cls(
            item=item,
            item_id=item_id,
            payload_digest_sha256=payload_digest_sha256,
            worker_id=worker_id,
            lease_token=lease_token,
            claimed_at=_utc_datetime(claimed_at),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "item": self.item.to_dict(),
            "item_id": self.item_id,
            "payload_digest_sha256": self.payload_digest_sha256,
            "worker_id": self.worker_id,
            "lease_token": self.lease_token,
            "claimed_at": _timestamp(self.claimed_at),
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> CaptureLease:
        _exact_keys(
            value,
            {
                "item",
                "item_id",
                "payload_digest_sha256",
                "worker_id",
                "lease_token",
                "claimed_at",
            },
        )
        return cls.create(
            item=CaptureWorkItem.from_dict(_mapping(value["item"])),
            item_id=_string(value["item_id"]),
            payload_digest_sha256=_string(value["payload_digest_sha256"]),
            worker_id=_string(value["worker_id"]),
            lease_token=_string(value["lease_token"]),
            claimed_at=_parse_timestamp(_string(value["claimed_at"])),
        )

    @classmethod
    def from_canonical_bytes(cls, payload: bytes) -> CaptureLease:
        result = cls.from_dict(_decode_canonical_mapping(payload))
        if result.canonical_bytes() != payload:
            raise ValueError("non-canonical capture lease")
        return result


@dataclass(frozen=True, slots=True)
class ShareRequest:
    url: str
    why: str
    text: str
    privacy_tier: PrivacyTier

    @classmethod
    def create(
        cls,
        *,
        url: str,
        why: str,
        text: str = "",
        privacy_tier: PrivacyTier | str | None = None,
    ) -> ShareRequest:
        normalized_url = _bounded_text(url, field="share URL", max_bytes=2_048)
        try:
            canonical_url = canonicalize_source_url(normalized_url)
        except ValueError as error:
            raise ValueError("invalid share request") from error
        normalized_why = _bounded_text(why, field="share reason", max_characters=280)
        if normalized_why.isspace() or any(
            separator in normalized_why for separator in {"\n", "\u0085", "\u2028", "\u2029"}
        ):
            raise ValueError("invalid share request")
        normalized_text = _bounded_text(
            text,
            field="share text",
            max_bytes=100_000,
            allow_empty=True,
            normalize_lines=True,
        )
        try:
            normalized_privacy = (
                PrivacyTier.UNKNOWN
                if privacy_tier is None
                else PrivacyTier(privacy_tier)
            )
        except (TypeError, ValueError) as error:
            raise ValueError("invalid share request") from error
        return cls(
            url=canonical_url,
            why=normalized_why,
            text=normalized_text,
            privacy_tier=normalized_privacy,
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "url": self.url,
            "why": self.why,
            "text": self.text,
            "privacy_tier": self.privacy_tier.value,
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> ShareRequest:
        _exact_keys(value, {"url", "why", "text", "privacy_tier"})
        return cls.create(
            url=_string(value["url"]),
            why=_string(value["why"]),
            text=_string(value["text"]),
            privacy_tier=_string(value["privacy_tier"]),
        )

    @classmethod
    def from_canonical_bytes(cls, payload: bytes) -> ShareRequest:
        result = cls.from_dict(_decode_canonical_mapping(payload))
        if result.canonical_bytes() != payload:
            raise ValueError("non-canonical share request")
        return result


@dataclass(frozen=True, slots=True)
class ShareResponse:
    capture_id: str
    pipeline: CapturePipeline
    duplicate: bool
    status: ShareStatus

    @classmethod
    def create(
        cls,
        *,
        capture_id: str,
        pipeline: CapturePipeline | str,
        duplicate: bool,
        status: ShareStatus | str,
    ) -> ShareResponse:
        try:
            normalized_id = str(capture_id)
            if not normalized_id.startswith(("cap_", "capture_")):
                raise ValueError
            normalized_pipeline = CapturePipeline(pipeline)
            normalized_status = ShareStatus(status)
        except (TypeError, ValueError) as error:
            raise ValueError("invalid share response") from error
        if not isinstance(duplicate, bool) or duplicate is not (
            normalized_status is ShareStatus.DUPLICATE
        ):
            raise ValueError("invalid share response")
        return cls(normalized_id, normalized_pipeline, duplicate, normalized_status)

    def to_dict(self) -> dict[str, object]:
        return {
            "capture_id": str(self.capture_id),
            "pipeline": self.pipeline.value,
            "duplicate": self.duplicate,
            "status": self.status.value,
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> ShareResponse:
        _exact_keys(value, {"capture_id", "pipeline", "duplicate", "status"})
        return cls.create(
            capture_id=_string(value["capture_id"]),
            pipeline=_string(value["pipeline"]),
            duplicate=_boolean(value["duplicate"]),
            status=_string(value["status"]),
        )

    @classmethod
    def from_canonical_bytes(cls, payload: bytes) -> ShareResponse:
        result = cls.from_dict(_decode_canonical_mapping(payload))
        if result.canonical_bytes() != payload:
            raise ValueError("non-canonical share response")
        return result


@dataclass(frozen=True, slots=True)
class ExtractionMetadata:
    title: str | None
    author: str | None
    published_at: datetime | None
    canonical_url: str | None
    platform: str | None
    video_id: str | None

    @classmethod
    def create(
        cls,
        *,
        title: str | None = None,
        author: str | None = None,
        published_at: datetime | None = None,
        canonical_url: str | None = None,
        platform: str | None = None,
        video_id: str | None = None,
    ) -> ExtractionMetadata:
        normalized_url: str | None = None
        if canonical_url is not None:
            bounded_url = _bounded_text(
                canonical_url,
                field="canonical URL",
                max_bytes=2_048,
            )
            try:
                normalized_url = canonicalize_source_url(bounded_url)
            except ValueError as error:
                raise ValueError("invalid extraction metadata") from error
        return cls(
            title=_optional_bounded_text(title, field="title", max_characters=512),
            author=_optional_bounded_text(author, field="author", max_characters=256),
            published_at=None if published_at is None else _utc_datetime(published_at),
            canonical_url=normalized_url,
            platform=_optional_bounded_text(platform, field="platform", max_characters=64),
            video_id=_optional_bounded_text(video_id, field="video ID", max_characters=128),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "title": self.title,
            "author": self.author,
            "published_at": None if self.published_at is None else _timestamp(self.published_at),
            "canonical_url": self.canonical_url,
            "platform": self.platform,
            "video_id": self.video_id,
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> ExtractionMetadata:
        _exact_keys(
            value,
            {"title", "author", "published_at", "canonical_url", "platform", "video_id"},
        )
        published_at = value["published_at"]
        return cls.create(
            title=_optional_string(value["title"]),
            author=_optional_string(value["author"]),
            published_at=None if published_at is None else _parse_timestamp(_string(published_at)),
            canonical_url=_optional_string(value["canonical_url"]),
            platform=_optional_string(value["platform"]),
            video_id=_optional_string(value["video_id"]),
        )

    @classmethod
    def from_canonical_bytes(cls, payload: bytes) -> ExtractionMetadata:
        result = cls.from_dict(_decode_canonical_mapping(payload))
        if result.canonical_bytes() != payload:
            raise ValueError("non-canonical extraction metadata")
        return result


@dataclass(frozen=True, slots=True)
class NormalizedExtraction:
    extractor: ExtractorKind
    state: ExtractionState
    source_type: SourceType
    content_kind: ContentKind
    metadata: ExtractionMetadata
    text: str
    transcript: str | None
    transcript_state: TranscriptState
    assets: tuple[RawAssetRef, ...]
    failure: ExtractionFailure | None

    @classmethod
    def create(
        cls,
        *,
        extractor: ExtractorKind | str,
        state: ExtractionState | str,
        source_type: SourceType | str,
        content_kind: ContentKind | str,
        metadata: ExtractionMetadata,
        text: str,
        transcript: str | None,
        transcript_state: TranscriptState | str,
        assets: tuple[RawAssetRef, ...],
        failure: ExtractionFailure | str | None,
    ) -> NormalizedExtraction:
        try:
            normalized_extractor = ExtractorKind(extractor)
            normalized_state = ExtractionState(state)
            normalized_source = SourceType(source_type)
            normalized_kind = ContentKind(content_kind)
            normalized_transcript_state = TranscriptState(transcript_state)
            normalized_failure = None if failure is None else ExtractionFailure(failure)
        except (TypeError, ValueError) as error:
            raise ValueError("invalid normalized extraction") from error
        if not isinstance(metadata, ExtractionMetadata):
            raise ValueError("invalid normalized extraction")
        successful_states = {
            ExtractionState.COMPLETE,
            ExtractionState.PENDING_TRANSCRIPT,
            ExtractionState.NO_CONTENT,
        }
        if (normalized_state in successful_states) is not (normalized_failure is None):
            raise ValueError("invalid normalized extraction")
        if (normalized_state is ExtractionState.PENDING_TRANSCRIPT) is not (
            normalized_transcript_state is TranscriptState.PENDING
        ):
            raise ValueError("invalid normalized extraction")
        normalized_text = _bounded_text(
            text,
            field="extracted text",
            max_bytes=2 * 1024 * 1024,
            allow_empty=True,
            normalize_lines=True,
        )
        normalized_transcript = None
        if transcript is not None:
            normalized_transcript = _bounded_text(
                transcript,
                field="transcript",
                max_bytes=2 * 1024 * 1024,
                normalize_lines=True,
            )
        if normalized_transcript_state in {TranscriptState.SUPPLIED, TranscriptState.ACQUIRED}:
            if normalized_transcript is None or normalized_transcript.isspace():
                raise ValueError("invalid normalized extraction")
        elif normalized_transcript is not None:
            raise ValueError("invalid normalized extraction")
        if (
            not isinstance(assets, tuple)
            or any(not isinstance(asset, RawAssetRef) for asset in assets)
            or tuple(sorted(assets, key=lambda asset: str(asset.asset_id))) != assets
            or len({asset.asset_id for asset in assets}) != len(assets)
        ):
            raise ValueError("invalid normalized extraction")
        return cls(
            normalized_extractor,
            normalized_state,
            normalized_source,
            normalized_kind,
            metadata,
            normalized_text,
            normalized_transcript,
            normalized_transcript_state,
            assets,
            normalized_failure,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "extractor": self.extractor.value,
            "state": self.state.value,
            "source_type": self.source_type.value,
            "content_kind": self.content_kind.value,
            "metadata": self.metadata.to_dict(),
            "text": self.text,
            "transcript": self.transcript,
            "transcript_state": self.transcript_state.value,
            "assets": [asset.to_dict() for asset in self.assets],
            "failure": None if self.failure is None else self.failure.value,
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> NormalizedExtraction:
        _exact_keys(
            value,
            {
                "extractor",
                "state",
                "source_type",
                "content_kind",
                "metadata",
                "text",
                "transcript",
                "transcript_state",
                "assets",
                "failure",
            },
        )
        raw_assets = value["assets"]
        if not isinstance(raw_assets, list):
            raise ValueError("invalid normalized extraction")
        return cls.create(
            extractor=_string(value["extractor"]),
            state=_string(value["state"]),
            source_type=_string(value["source_type"]),
            content_kind=_string(value["content_kind"]),
            metadata=ExtractionMetadata.from_dict(_mapping(value["metadata"])),
            text=_string(value["text"]),
            transcript=_optional_string(value["transcript"]),
            transcript_state=_string(value["transcript_state"]),
            assets=tuple(RawAssetRef.from_dict(_mapping(asset)) for asset in raw_assets),
            failure=_optional_string(value["failure"]),
        )

    @classmethod
    def from_canonical_bytes(cls, payload: bytes) -> NormalizedExtraction:
        result = cls.from_dict(_decode_canonical_mapping(payload))
        if result.canonical_bytes() != payload:
            raise ValueError("non-canonical normalized extraction")
        return result


@dataclass(frozen=True, slots=True)
class DistillationWorkItem:
    schema_version: int
    capture_id: CaptureId
    event_id: str
    redacted_event_digest_sha256: str

    @classmethod
    def create(
        cls,
        *,
        capture_id: CaptureId | str,
        event_id: str,
        redacted_event_digest_sha256: str,
    ) -> DistillationWorkItem:
        try:
            normalized_capture_id = CaptureId(validate_identifier(str(capture_id), prefix="cap_"))
        except ValueError as error:
            raise ValueError("invalid distillation work item") from error
        if (
            not isinstance(event_id, str)
            or not _OPAQUE.fullmatch(event_id)
            or not isinstance(redacted_event_digest_sha256, str)
            or not _SHA256.fullmatch(redacted_event_digest_sha256)
        ):
            raise ValueError("invalid distillation work item")
        return cls(1, normalized_capture_id, event_id, redacted_event_digest_sha256)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "capture_id": str(self.capture_id),
            "event_id": self.event_id,
            "redacted_event_digest_sha256": self.redacted_event_digest_sha256,
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    def payload_digest_sha256(self) -> str:
        return sha256(self.canonical_bytes()).hexdigest()

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> DistillationWorkItem:
        _exact_keys(
            value,
            {
                "schema_version",
                "capture_id",
                "event_id",
                "redacted_event_digest_sha256",
            },
        )
        if value["schema_version"] != 1:
            raise ValueError("invalid distillation work item")
        return cls.create(
            capture_id=_string(value["capture_id"]),
            event_id=_string(value["event_id"]),
            redacted_event_digest_sha256=_string(value["redacted_event_digest_sha256"]),
        )

    @classmethod
    def from_canonical_bytes(cls, payload: bytes) -> DistillationWorkItem:
        result = cls.from_dict(_decode_canonical_mapping(payload))
        if result.canonical_bytes() != payload:
            raise ValueError("non-canonical distillation work item")
        return result


@dataclass(frozen=True, slots=True)
class DistillationLease:
    item: DistillationWorkItem
    item_id: str
    payload_digest_sha256: str
    worker_id: str
    lease_token: str
    claimed_at: datetime

    @classmethod
    def create(
        cls,
        *,
        item: DistillationWorkItem,
        item_id: str,
        payload_digest_sha256: str,
        worker_id: str,
        lease_token: str,
        claimed_at: datetime,
    ) -> DistillationLease:
        if (
            not isinstance(item, DistillationWorkItem)
            or item_id != item.event_id
            or payload_digest_sha256 != item.payload_digest_sha256()
            or not _OPAQUE.fullmatch(worker_id)
            or not _OPAQUE.fullmatch(lease_token)
        ):
            raise ValueError("invalid distillation lease")
        return cls(
            item,
            item_id,
            payload_digest_sha256,
            worker_id,
            lease_token,
            _utc_datetime(claimed_at),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "item": self.item.to_dict(),
            "item_id": self.item_id,
            "payload_digest_sha256": self.payload_digest_sha256,
            "worker_id": self.worker_id,
            "lease_token": self.lease_token,
            "claimed_at": _timestamp(self.claimed_at),
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> DistillationLease:
        _exact_keys(
            value,
            {
                "item",
                "item_id",
                "payload_digest_sha256",
                "worker_id",
                "lease_token",
                "claimed_at",
            },
        )
        return cls.create(
            item=DistillationWorkItem.from_dict(_mapping(value["item"])),
            item_id=_string(value["item_id"]),
            payload_digest_sha256=_string(value["payload_digest_sha256"]),
            worker_id=_string(value["worker_id"]),
            lease_token=_string(value["lease_token"]),
            claimed_at=_parse_timestamp(_string(value["claimed_at"])),
        )

    @classmethod
    def from_canonical_bytes(cls, payload: bytes) -> DistillationLease:
        result = cls.from_dict(_decode_canonical_mapping(payload))
        if result.canonical_bytes() != payload:
            raise ValueError("non-canonical distillation lease")
        return result


@dataclass(frozen=True, slots=True)
class CaptureRedactionResult:
    payload: Mapping[str, JsonValue]
    receipt: RedactionReceipt

    @classmethod
    def create(
        cls,
        *,
        payload: Mapping[str, object],
        receipt: RedactionReceipt,
    ) -> CaptureRedactionResult:
        frozen_payload = _freeze_json_mapping(payload)
        if not isinstance(
            receipt, RedactionReceipt
        ) or receipt.output_digest_sha256 != EventRecord.output_digest_sha256(frozen_payload):
            raise ValueError("invalid capture redaction result")
        return cls(frozen_payload, receipt)

    def to_dict(self) -> dict[str, object]:
        return {
            "payload": _thaw_json(self.payload),
            "receipt": self.receipt.to_dict(),
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> CaptureRedactionResult:
        _exact_keys(value, {"payload", "receipt"})
        try:
            return cls.create(
                payload=_mapping(value["payload"]),
                receipt=RedactionReceipt.from_dict(_mapping(value["receipt"])),
            )
        except ValidationError as error:
            raise ValueError("invalid capture redaction result") from error

    @classmethod
    def from_canonical_bytes(cls, payload: bytes) -> CaptureRedactionResult:
        result = cls.from_dict(_decode_canonical_mapping(payload))
        if result.canonical_bytes() != payload:
            raise ValueError("non-canonical capture redaction result")
        return result


TExtractionRequest = TypeVar("TExtractionRequest", contravariant=True)


class Extractor(Protocol[TExtractionRequest]):
    def extract(
        self,
        request: TExtractionRequest,
        *,
        privacy: PrivacyDecision,
    ) -> NormalizedExtraction: ...


class CaptureRedactor(Protocol):
    def redact(
        self,
        extraction: NormalizedExtraction,
        envelope: CaptureEnvelope,
    ) -> CaptureRedactionResult: ...


_OPAQUE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}")
_SHA256 = re.compile(r"[0-9a-f]{64}")


def _bounded_text(
    value: object,
    *,
    field: str,
    max_bytes: int | None = None,
    max_characters: int | None = None,
    allow_empty: bool = False,
    normalize_lines: bool = False,
) -> str:
    if not isinstance(value, str):
        raise ValueError(f"invalid {field}")
    normalized = unicodedata.normalize("NFC", value)
    if normalize_lines:
        normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    if "\x00" in normalized or not allow_empty and not normalized:
        raise ValueError(f"invalid {field}")
    if max_bytes is not None and len(normalized.encode("utf-8")) > max_bytes:
        raise ValueError(f"invalid {field}")
    if max_characters is not None and len(normalized) > max_characters:
        raise ValueError(f"invalid {field}")
    return normalized


def _optional_bounded_text(
    value: object,
    *,
    field: str,
    max_characters: int,
) -> str | None:
    if value is None:
        return None
    return _bounded_text(value, field=field, max_characters=max_characters)


def _freeze_json_mapping(value: Mapping[str, object]) -> Mapping[str, JsonValue]:
    if not isinstance(value, Mapping):
        raise ValueError("invalid redacted payload")
    normalized: dict[str, JsonValue] = {}
    for raw_key, raw_value in value.items():
        if not isinstance(raw_key, str):
            raise ValueError("invalid redacted payload")
        key = unicodedata.normalize("NFC", raw_key)
        if not key or "\x00" in key or key in normalized:
            raise ValueError("invalid redacted payload")
        normalized[key] = _freeze_json(raw_value)
    return MappingProxyType(dict(sorted(normalized.items())))


def _freeze_json(value: object) -> JsonValue:
    if value is None or isinstance(value, bool | int):
        return value
    if isinstance(value, str):
        return _bounded_text(
            value,
            field="redacted payload",
            max_bytes=2 * 1024 * 1024,
            allow_empty=True,
            normalize_lines=True,
        )
    if isinstance(value, tuple | list):
        return tuple(_freeze_json(item) for item in value)
    if isinstance(value, Mapping):
        return _freeze_json_mapping(value)
    raise ValueError("invalid redacted payload")


def _thaw_json(value: JsonValue | Mapping[str, JsonValue]) -> object:
    if isinstance(value, Mapping):
        return {key: _thaw_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    return value


def _queue_code(value: QueueErrorCode | str | None) -> QueueErrorCode | None:
    if value is None:
        return None
    try:
        return QueueErrorCode(value)
    except (TypeError, ValueError) as error:
        raise ValueError("invalid queue error code") from error


def _utc_datetime(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("invalid timestamp")
    return value.astimezone(UTC)


def _timestamp(value: datetime) -> str:
    normalized = _utc_datetime(value)
    return (
        normalized.isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
        .replace(".000000Z", "Z")
    )


def _parse_timestamp(value: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("invalid timestamp")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise ValueError("invalid timestamp") from error
    if _timestamp(parsed) != value:
        raise ValueError("invalid timestamp")
    return parsed


def _string(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("invalid string")
    return value


def _optional_string(value: object) -> str | None:
    if value is not None and not isinstance(value, str):
        raise ValueError("invalid string")
    return value


def _boolean(value: object) -> bool:
    if not isinstance(value, bool):
        raise ValueError("invalid boolean")
    return value


def _mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ValueError("invalid object")
    return cast(Mapping[str, object], value)


def _exact_keys(value: Mapping[str, object], expected: set[str]) -> None:
    if set(value) != expected:
        raise ValueError("invalid object")


def _decode_canonical_mapping(payload: bytes) -> Mapping[str, object]:
    try:
        decoded = json.loads(payload.decode("utf-8"), object_pairs_hook=_reject_duplicates)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise ValueError("invalid canonical value") from error
    return _mapping(decoded)


def _reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result
