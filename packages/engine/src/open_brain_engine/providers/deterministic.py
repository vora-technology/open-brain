"""Deterministic local fallback for the capture-distillation schema."""

from __future__ import annotations

import json
import unicodedata
from collections.abc import Mapping
from typing import cast

from open_brain_engine.core.ids import canonical_json_bytes, validate_identifier
from open_brain_engine.core.models import PrivacyDecision, PrivacyTier
from open_brain_engine.core.policy import BoundaryErrorCode
from open_brain_engine.core.ports import TextModelRequest, TextModelResult
from open_brain_engine.providers.base import ProviderFailure

_FIELDS = {
    "capture_id",
    "capture_why",
    "content_kind",
    "source_type",
    "source_title",
    "text",
    "transcript",
}


class DeterministicDistillationProvider:
    """Produce the existing JSON response shape with no model, network, or secret lookup."""

    def complete(
        self,
        request: TextModelRequest,
        *,
        privacy: PrivacyDecision,
    ) -> TextModelResult:
        if (
            not isinstance(request, TextModelRequest)
            or request.purpose != "capture-distillation-v1"
            or not isinstance(privacy, PrivacyDecision)
            or privacy.tier in {PrivacyTier.SECRET, PrivacyTier.UNKNOWN}
        ):
            raise ProviderFailure(BoundaryErrorCode.PROVIDER_REJECTED)
        try:
            _, encoded = request.prompt.rsplit("\n", 1)
            payload = _mapping(json.loads(encoded))
            if set(payload) != _FIELDS:
                raise ValueError
            validate_identifier(_string(payload["capture_id"]), prefix="cap_")
            capture_why = _text(payload["capture_why"], maximum_bytes=2_000)
            _text(payload["content_kind"], maximum_bytes=128)
            _text(payload["source_type"], maximum_bytes=128)
            source_title = _optional_text(payload["source_title"], maximum_bytes=512)
            text = _text(payload["text"], maximum_bytes=2 * 1024 * 1024, allow_empty=True)
            transcript = _optional_text(
                payload["transcript"], maximum_bytes=2 * 1024 * 1024
            )
            body = transcript or text or capture_why
            title = source_title or next(
                (line.strip() for line in body.split("\n") if line.strip()),
                "Captured reference",
            )
            response = canonical_json_bytes(
                {
                    "title": _truncate(title, 512),
                    "summary": _truncate(body, 8_192),
                    "topics": [],
                }
            ).decode("utf-8")
        except (KeyError, TypeError, ValueError, UnicodeError, json.JSONDecodeError):
            raise ProviderFailure(BoundaryErrorCode.MALFORMED_RESPONSE) from None
        return TextModelResult(text=response, provider_name="deterministic-local")


def _mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ValueError
    return cast(Mapping[str, object], value)


def _string(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError
    return value


def _text(value: object, *, maximum_bytes: int, allow_empty: bool = False) -> str:
    result = unicodedata.normalize("NFC", _string(value))
    if (not allow_empty and not result.strip()) or len(result.encode("utf-8")) > maximum_bytes:
        raise ValueError
    return result


def _optional_text(value: object, *, maximum_bytes: int) -> str | None:
    if value is None:
        return None
    return _text(value, maximum_bytes=maximum_bytes)


def _truncate(value: str, maximum_bytes: int) -> str:
    encoded = value.encode("utf-8")
    if len(encoded) <= maximum_bytes:
        return value
    return encoded[:maximum_bytes].decode("utf-8", errors="ignore")


__all__ = ["DeterministicDistillationProvider"]
