from __future__ import annotations

import json

import pytest

from open_brain.core.ids import canonical_json_bytes
from open_brain.core.models import (
    Authority,
    PrivacyDecision,
    PrivacyReason,
    PrivacyTier,
)
from open_brain.core.policy import BoundaryErrorCode
from open_brain.core.ports import TextModelRequest
from open_brain.providers.base import ProviderFailure
from open_brain.providers.deterministic import DeterministicDistillationProvider


def _privacy() -> PrivacyDecision:
    return PrivacyDecision.create(
        tier=PrivacyTier.WORK,
        reason=PrivacyReason.POLICY_WORK,
        policy_version="privacy-v1",
        authority=Authority(cloud=False, external_egress=False),
    )


def _request(payload: dict[str, object]) -> TextModelRequest:
    return TextModelRequest.create(
        request_id="distill-cap_" + "a" * 64,
        purpose="capture-distillation-v1",
        prompt="Return bounded JSON.\n" + canonical_json_bytes(payload).decode(),
        timeout_seconds=2.0,
        max_output_bytes=8_192,
    )


def test_deterministic_distiller_returns_bounded_schema_without_network() -> None:
    result = DeterministicDistillationProvider().complete(
        _request(
            {
                "capture_id": "cap_" + "a" * 64,
                "capture_why": "Keep this synthetic context",
                "content_kind": "article",
                "source_type": "web",
                "source_title": "Synthetic source",
                "text": "Synthetic body\nSecond line",
                "transcript": None,
            }
        ),
        privacy=_privacy(),
    )

    assert result.provider_name == "deterministic-local"
    assert json.loads(result.text) == {
        "summary": "Synthetic body\nSecond line",
        "title": "Synthetic source",
        "topics": [],
    }


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"capture_id": "cap_" + "a" * 64},
        {
            "capture_id": "cap_" + "a" * 64,
            "capture_why": "Synthetic",
            "content_kind": "article",
            "source_type": "web",
            "source_title": None,
            "text": "",
            "transcript": None,
            "extra": True,
        },
    ],
)
def test_deterministic_distiller_rejects_non_contract_prompt(
    payload: dict[str, object],
) -> None:
    with pytest.raises(ProviderFailure) as raised:
        DeterministicDistillationProvider().complete(_request(payload), privacy=_privacy())

    assert raised.value.code is BoundaryErrorCode.MALFORMED_RESPONSE
