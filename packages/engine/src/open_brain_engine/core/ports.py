from __future__ import annotations

import json
import math
import re
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from hashlib import sha256
from types import MappingProxyType
from typing import Protocol

from .ids import CaptureId, ReviewId, canonical_json_bytes, validate_identifier
from .models import Intent, PrivacyDecision, RawAssetRef, RawCapture, ValidationError

type JsonScalar = str | int | bool | None
type JsonValue = JsonScalar | tuple[JsonValue, ...] | Mapping[str, JsonValue]

_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
_OPAQUE_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}")
_EVENT_TYPE_PATTERN = re.compile(r"[a-z][a-z0-9_.-]{0,127}")
_FRONTMATTER_KEY_PATTERN = re.compile(r"[a-z][a-z0-9_]*")


class PutDisposition(StrEnum):
    CREATED = "created"
    DUPLICATE = "duplicate"


@dataclass(frozen=True, slots=True)
class PutResult:
    disposition: PutDisposition
    record_id: str
    digest_sha256: str


class RawStore(Protocol):
    def get(self, capture_id: CaptureId) -> RawCapture | None: ...

    def put_if_absent(self, capture: RawCapture) -> PutResult: ...


class RedactionFindingCategory(StrEnum):
    CREDENTIAL = "credential"
    NETWORK_LOCATION = "network_location"
    PERSONAL_IDENTIFIER = "personal_identifier"
    PRIVATE_PATH = "private_path"


@dataclass(frozen=True, slots=True)
class RedactionFinding:
    category: RedactionFindingCategory
    count: int

    @classmethod
    def create(
        cls,
        *,
        category: RedactionFindingCategory | str,
        count: int,
    ) -> RedactionFinding:
        try:
            normalized_category = RedactionFindingCategory(category)
        except (TypeError, ValueError) as error:
            raise ValidationError("invalid redaction finding") from error
        if not isinstance(count, int) or isinstance(count, bool) or count < 1:
            raise ValidationError("invalid redaction finding")
        return cls(category=normalized_category, count=count)

    def to_dict(self) -> dict[str, object]:
        return {"category": self.category.value, "count": self.count}

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> RedactionFinding:
        _require_exact_keys(value, {"category", "count"})
        return cls.create(
            category=_require_string(value["category"]),
            count=_require_integer(value["count"]),
        )


@dataclass(frozen=True, slots=True)
class RedactionReceipt:
    source_digest_sha256: str
    output_digest_sha256: str
    policy_version: str
    findings: tuple[RedactionFinding, ...]

    @classmethod
    def create(
        cls,
        *,
        source_digest_sha256: str,
        output_digest_sha256: str,
        policy_version: str,
        findings: tuple[RedactionFinding, ...] = (),
    ) -> RedactionReceipt:
        source_digest = _require_sha256(source_digest_sha256)
        output_digest = _require_sha256(output_digest_sha256)
        version = _require_stable_label(policy_version, field="redaction policy version")
        if not isinstance(findings, tuple) or any(
            not isinstance(finding, RedactionFinding) for finding in findings
        ):
            raise ValidationError("invalid redaction receipt")
        ordered = tuple(sorted(findings, key=lambda finding: finding.category.value))
        if findings != ordered or len({finding.category for finding in findings}) != len(findings):
            raise ValidationError("invalid redaction receipt")
        return cls(
            source_digest_sha256=source_digest,
            output_digest_sha256=output_digest,
            policy_version=version,
            findings=findings,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "source_digest_sha256": self.source_digest_sha256,
            "output_digest_sha256": self.output_digest_sha256,
            "policy_version": self.policy_version,
            "findings": [finding.to_dict() for finding in self.findings],
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> RedactionReceipt:
        _require_exact_keys(
            value,
            {
                "source_digest_sha256",
                "output_digest_sha256",
                "policy_version",
                "findings",
            },
        )
        raw_findings = value["findings"]
        if not isinstance(raw_findings, list):
            raise ValidationError("invalid redaction receipt")
        return cls.create(
            source_digest_sha256=_require_string(value["source_digest_sha256"]),
            output_digest_sha256=_require_string(value["output_digest_sha256"]),
            policy_version=_require_string(value["policy_version"]),
            findings=tuple(
                RedactionFinding.from_dict(_require_mapping(finding)) for finding in raw_findings
            ),
        )


@dataclass(frozen=True, slots=True)
class EventRecord:
    event_id: str
    stream_id: CaptureId
    event_type: str
    occurred_at: datetime
    privacy_decision: PrivacyDecision
    payload: Mapping[str, JsonValue]
    redaction_receipt: RedactionReceipt

    @classmethod
    def create(
        cls,
        *,
        event_id: str,
        stream_id: CaptureId | str,
        event_type: str,
        occurred_at: datetime,
        privacy_decision: PrivacyDecision,
        payload: Mapping[str, object],
        redaction_receipt: RedactionReceipt,
    ) -> EventRecord:
        normalized_event_id = _require_opaque_id(event_id, field="event ID")
        try:
            normalized_stream_id = CaptureId(validate_identifier(str(stream_id), prefix="cap_"))
        except ValueError as error:
            raise ValidationError("invalid event stream ID") from error
        if not isinstance(event_type, str) or not _EVENT_TYPE_PATTERN.fullmatch(event_type):
            raise ValidationError("invalid event type")
        timestamp = _require_utc_datetime(occurred_at)
        if not isinstance(privacy_decision, PrivacyDecision):
            raise ValidationError("invalid event privacy decision")
        frozen_payload = _freeze_json_mapping(payload)
        if not isinstance(redaction_receipt, RedactionReceipt):
            raise ValidationError("invalid event redaction receipt")
        expected_digest = cls.output_digest_sha256(frozen_payload)
        if redaction_receipt.output_digest_sha256 != expected_digest:
            raise ValidationError("event output digest does not match redaction receipt")
        return cls(
            event_id=normalized_event_id,
            stream_id=normalized_stream_id,
            event_type=event_type,
            occurred_at=timestamp,
            privacy_decision=privacy_decision,
            payload=frozen_payload,
            redaction_receipt=redaction_receipt,
        )

    @staticmethod
    def output_digest_sha256(payload: Mapping[str, object]) -> str:
        normalized = _thaw_json(_freeze_json_mapping(payload))
        return sha256(canonical_json_bytes(normalized)).hexdigest()

    def to_dict(self) -> dict[str, object]:
        return {
            "event_id": self.event_id,
            "stream_id": str(self.stream_id),
            "event_type": self.event_type,
            "occurred_at": _format_timestamp(self.occurred_at),
            "privacy_decision": self.privacy_decision.to_dict(),
            "payload": _thaw_json(self.payload),
            "redaction_receipt": self.redaction_receipt.to_dict(),
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> EventRecord:
        _require_exact_keys(
            value,
            {
                "event_id",
                "stream_id",
                "event_type",
                "occurred_at",
                "privacy_decision",
                "payload",
                "redaction_receipt",
            },
        )
        return cls.create(
            event_id=_require_string(value["event_id"]),
            stream_id=_require_string(value["stream_id"]),
            event_type=_require_string(value["event_type"]),
            occurred_at=_parse_timestamp(_require_string(value["occurred_at"])),
            privacy_decision=PrivacyDecision.from_dict(_require_mapping(value["privacy_decision"])),
            payload=_require_mapping(value["payload"]),
            redaction_receipt=RedactionReceipt.from_dict(
                _require_mapping(value["redaction_receipt"])
            ),
        )

    @classmethod
    def from_canonical_bytes(cls, payload: bytes) -> EventRecord:
        value = _decode_canonical_json(payload)
        record = cls.from_dict(_require_mapping(value))
        if record.canonical_bytes() != payload:
            raise ValidationError("non-canonical event record")
        return record


class EventStore(Protocol):
    def append(self, record: EventRecord) -> PutResult: ...

    def read(
        self,
        stream_id: CaptureId,
        *,
        after_sequence: int = 0,
    ) -> Sequence[EventRecord]: ...


class CaptureQueue[TQueueItem, TLease](Protocol):
    def enqueue(self, item: TQueueItem, *, item_id: str, payload_digest: str) -> PutResult: ...

    def claim(self, *, worker_id: str, now: datetime) -> TLease | None: ...

    def acknowledge(self, lease: TLease, *, completed_at: datetime) -> None: ...

    def retry(self, lease: TLease, *, available_at: datetime, error_code: str) -> None: ...

    def quarantine(self, lease: TLease, *, at: datetime, error_code: str) -> None: ...


class ReviewStore[TReview, TReviewCommand, TReviewResult](Protocol):
    def get(self, review_id: ReviewId) -> TReview | None: ...

    def create_if_absent(self, review: TReview, *, payload_digest: str) -> PutResult: ...

    def decide(self, command: TReviewCommand) -> TReviewResult: ...

    def pending_outputs(self, *, limit: int) -> Sequence[object]: ...

    def mark_output_delivered(self, output_id: str, *, delivered_at: datetime) -> None: ...


class LedgerStore[TLedgerRecord](Protocol):
    def get(self, record_id: str) -> TLedgerRecord | None: ...

    def append_if_absent(
        self, record: TLedgerRecord, *, record_id: str, payload_digest: str
    ) -> PutResult: ...


@dataclass(frozen=True, slots=True)
class RedactedMarkdownDocument:
    document_id: str
    logical_key: str
    privacy_decision: PrivacyDecision
    frontmatter: Mapping[str, JsonValue]
    body: str
    redaction_receipt: RedactionReceipt

    @classmethod
    def create(
        cls,
        *,
        document_id: str,
        logical_key: str,
        privacy_decision: PrivacyDecision,
        frontmatter: Mapping[str, object],
        body: str,
        redaction_receipt: RedactionReceipt,
    ) -> RedactedMarkdownDocument:
        normalized_document_id = _require_opaque_id(document_id, field="document ID")
        normalized_logical_key = _require_opaque_id(logical_key, field="logical key")
        if not isinstance(privacy_decision, PrivacyDecision):
            raise ValidationError("invalid Markdown privacy decision")
        frozen_frontmatter = _freeze_json_mapping(
            frontmatter,
            key_pattern=_FRONTMATTER_KEY_PATTERN,
        )
        normalized_body = _normalize_text(body, field="Markdown body")
        if not isinstance(redaction_receipt, RedactionReceipt):
            raise ValidationError("invalid Markdown redaction receipt")
        expected_digest = cls.output_digest_sha256(frozen_frontmatter, normalized_body)
        if redaction_receipt.output_digest_sha256 != expected_digest:
            raise ValidationError("Markdown output digest does not match redaction receipt")
        return cls(
            document_id=normalized_document_id,
            logical_key=normalized_logical_key,
            privacy_decision=privacy_decision,
            frontmatter=frozen_frontmatter,
            body=normalized_body,
            redaction_receipt=redaction_receipt,
        )

    @staticmethod
    def output_digest_sha256(frontmatter: Mapping[str, object], body: str) -> str:
        normalized_frontmatter = _thaw_json(
            _freeze_json_mapping(frontmatter, key_pattern=_FRONTMATTER_KEY_PATTERN)
        )
        normalized_body = _normalize_text(body, field="Markdown body")
        output = {"body": normalized_body, "frontmatter": normalized_frontmatter}
        return sha256(canonical_json_bytes(output)).hexdigest()

    def to_dict(self) -> dict[str, object]:
        return {
            "document_id": self.document_id,
            "logical_key": self.logical_key,
            "privacy_decision": self.privacy_decision.to_dict(),
            "frontmatter": _thaw_json(self.frontmatter),
            "body": self.body,
            "redaction_receipt": self.redaction_receipt.to_dict(),
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> RedactedMarkdownDocument:
        _require_exact_keys(
            value,
            {
                "document_id",
                "logical_key",
                "privacy_decision",
                "frontmatter",
                "body",
                "redaction_receipt",
            },
        )
        return cls.create(
            document_id=_require_string(value["document_id"]),
            logical_key=_require_string(value["logical_key"]),
            privacy_decision=PrivacyDecision.from_dict(_require_mapping(value["privacy_decision"])),
            frontmatter=_require_mapping(value["frontmatter"]),
            body=_require_string(value["body"]),
            redaction_receipt=RedactionReceipt.from_dict(
                _require_mapping(value["redaction_receipt"])
            ),
        )

    @classmethod
    def from_canonical_bytes(cls, payload: bytes) -> RedactedMarkdownDocument:
        value = _decode_canonical_json(payload)
        document = cls.from_dict(_require_mapping(value))
        if document.canonical_bytes() != payload:
            raise ValidationError("non-canonical redacted Markdown document")
        return document


class MarkdownSink(Protocol):
    def write_if_absent(self, document: RedactedMarkdownDocument) -> PutResult: ...


@dataclass(frozen=True, slots=True)
class TextModelRequest:
    request_id: str
    purpose: str
    prompt: str
    timeout_seconds: float
    max_output_bytes: int

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "request_id",
            _require_bounded_text(self.request_id, field="request ID", limit=128),
        )
        object.__setattr__(
            self,
            "purpose",
            _require_bounded_text(self.purpose, field="purpose", limit=128),
        )
        object.__setattr__(
            self,
            "prompt",
            _require_bounded_text(self.prompt, field="prompt", limit=100_000),
        )
        object.__setattr__(self, "timeout_seconds", _require_timeout(self.timeout_seconds))
        object.__setattr__(self, "max_output_bytes", _require_output_limit(self.max_output_bytes))

    @classmethod
    def create(
        cls,
        *,
        request_id: str,
        purpose: str,
        prompt: str,
        timeout_seconds: float,
        max_output_bytes: int,
    ) -> TextModelRequest:
        return cls(request_id, purpose, prompt, timeout_seconds, max_output_bytes)

    def to_dict(self) -> dict[str, object]:
        return {
            "request_id": self.request_id,
            "purpose": self.purpose,
            "prompt": self.prompt,
            "timeout_seconds": self.timeout_seconds,
            "max_output_bytes": self.max_output_bytes,
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> TextModelRequest:
        _require_exact_keys(
            value,
            {"request_id", "purpose", "prompt", "timeout_seconds", "max_output_bytes"},
        )
        return cls.create(
            request_id=_require_string(value["request_id"]),
            purpose=_require_string(value["purpose"]),
            prompt=_require_string(value["prompt"]),
            timeout_seconds=_require_timeout(value["timeout_seconds"]),
            max_output_bytes=_require_integer(value["max_output_bytes"]),
        )

    @classmethod
    def from_canonical_bytes(cls, payload: bytes) -> TextModelRequest:
        value = _decode_canonical_json(payload)
        request = cls.from_dict(_require_mapping(value))
        if request.canonical_bytes() != payload:
            raise ValidationError("non-canonical text model request")
        return request


@dataclass(frozen=True, slots=True)
class TextModelResult:
    text: str
    provider_name: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "text",
            _require_bounded_text(self.text, field="model output", limit=1_000_000),
        )
        object.__setattr__(
            self,
            "provider_name",
            _require_bounded_text(self.provider_name, field="provider name", limit=128),
        )

    @classmethod
    def create(cls, *, text: str, provider_name: str) -> TextModelResult:
        return cls(text=text, provider_name=provider_name)

    def validate_for(self, request: TextModelRequest) -> TextModelResult:
        if len(self.text.encode("utf-8")) > request.max_output_bytes:
            raise ValidationError("text model output exceeds limit")
        return self

    def to_dict(self) -> dict[str, object]:
        return {"text": self.text, "provider_name": self.provider_name}

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> TextModelResult:
        _require_exact_keys(value, {"text", "provider_name"})
        return cls.create(
            text=_require_string(value["text"]),
            provider_name=_require_string(value["provider_name"]),
        )

    @classmethod
    def from_canonical_bytes(cls, payload: bytes) -> TextModelResult:
        value = _decode_canonical_json(payload)
        result = cls.from_dict(_require_mapping(value))
        if result.canonical_bytes() != payload:
            raise ValidationError("non-canonical text model result")
        return result


class Provider(Protocol):
    def complete(
        self, request: TextModelRequest, *, privacy: PrivacyDecision
    ) -> TextModelResult: ...


class Clock(Protocol):
    def now(self) -> datetime: ...


class IdGenerator(Protocol):
    def capture_id(self, identity: Mapping[str, object]) -> CaptureId: ...

    def review_id(self, capture_id: CaptureId, intent: Intent) -> ReviewId: ...

    def event_id(self, stream_id: str, event_type: str, payload_digest: str) -> str: ...

    def decision_id(self) -> str: ...


@dataclass(frozen=True, slots=True)
class FetchRequest:
    request_id: str
    url: str
    timeout_seconds: float
    max_bytes: int
    max_redirects: int
    allowed_cookie_domains: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class FetchResponse:
    final_url: str
    status: int
    media_type: str | None
    body: bytes


class OutboundFetcher(Protocol):
    def fetch(self, request: FetchRequest, *, privacy: PrivacyDecision) -> FetchResponse: ...


@dataclass(frozen=True, slots=True)
class StagedExecutionRequest:
    request_id: str
    purpose: str
    prompt: str
    readable_assets: tuple[RawAssetRef, ...]
    allowed_network_hosts: tuple[str, ...]
    timeout_seconds: float
    max_output_bytes: int


@dataclass(frozen=True, slots=True)
class StagedExecutionResult:
    text: str
    produced_assets: tuple[RawAssetRef, ...]


class StagedAssetExecutor(Protocol):
    def execute(
        self, request: StagedExecutionRequest, *, privacy: PrivacyDecision
    ) -> StagedExecutionResult: ...


def _require_sha256(value: object) -> str:
    if not isinstance(value, str) or not _SHA256_PATTERN.fullmatch(value):
        raise ValidationError("invalid SHA-256 digest")
    return value


def _require_opaque_id(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not _OPAQUE_ID_PATTERN.fullmatch(value):
        raise ValidationError(f"invalid {field}")
    return value


def _require_stable_label(value: object, *, field: str) -> str:
    normalized = _normalize_text(value, field=field)
    if not _OPAQUE_ID_PATTERN.fullmatch(normalized):
        raise ValidationError(f"invalid {field}")
    return normalized


def _normalize_text(value: object, *, field: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"invalid {field}")
    normalized = unicodedata.normalize("NFC", value)
    if "\x00" in normalized:
        raise ValidationError(f"invalid {field}")
    return normalized


def _freeze_json_mapping(
    value: Mapping[str, object],
    *,
    key_pattern: re.Pattern[str] | None = None,
) -> Mapping[str, JsonValue]:
    if not isinstance(value, Mapping):
        raise ValidationError("invalid JSON object")
    normalized: dict[str, JsonValue] = {}
    for raw_key, raw_value in value.items():
        if not isinstance(raw_key, str):
            raise ValidationError("invalid JSON object key")
        key = _normalize_text(raw_key, field="JSON object key")
        if key in normalized or key_pattern is not None and not key_pattern.fullmatch(key):
            raise ValidationError("invalid JSON object key")
        normalized[key] = _freeze_json(raw_value)
    return MappingProxyType(dict(sorted(normalized.items())))


def _freeze_json(value: object) -> JsonValue:
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return _normalize_text(value, field="JSON string")
    if isinstance(value, tuple | list):
        return tuple(_freeze_json(item) for item in value)
    if isinstance(value, Mapping):
        return _freeze_json_mapping(value)
    raise ValidationError("invalid JSON value")


def _thaw_json(value: JsonValue | Mapping[str, JsonValue]) -> object:
    if isinstance(value, Mapping):
        return {key: _thaw_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    return value


def _require_utc_datetime(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValidationError("invalid timestamp")
    return value.astimezone(UTC)


def _format_timestamp(value: datetime) -> str:
    return _require_utc_datetime(value).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _parse_timestamp(value: str) -> datetime:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z", value):
        raise ValidationError("invalid timestamp")
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=UTC)


def _require_mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        raise ValidationError("invalid object")
    return value


def _require_string(value: object) -> str:
    if not isinstance(value, str):
        raise ValidationError("invalid string")
    return value


def _require_integer(value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValidationError("invalid integer")
    return value


def _require_bounded_text(value: object, *, field: str, limit: int) -> str:
    normalized = _normalize_text(value, field=field)
    if not normalized or normalized.isspace() or len(normalized) > limit:
        raise ValidationError(f"invalid {field}")
    return normalized


def _require_timeout(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, float) or not math.isfinite(value):
        raise ValidationError("invalid timeout")
    if value <= 0 or value > 300:
        raise ValidationError("invalid timeout")
    return value


def _require_output_limit(value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1 or value > 1_000_000:
        raise ValidationError("invalid output limit")
    return value


def _require_exact_keys(value: Mapping[str, object], expected: set[str]) -> None:
    if set(value) != expected:
        raise ValidationError("invalid fields")


def _decode_canonical_json(payload: bytes) -> object:
    try:
        return json.loads(payload.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
    except (UnicodeDecodeError, json.JSONDecodeError, ValidationError) as error:
        raise ValidationError("invalid canonical JSON") from error


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValidationError("duplicate JSON key")
        result[key] = value
    return result
