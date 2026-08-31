from __future__ import annotations

import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from .ids import review_id_for
from .models import (
    Authority,
    CaptureEnvelope,
    CaptureWhyOrigin,
    Intent,
    PrivacyDecision,
    PrivacyReason,
    PrivacyTier,
    ValidationError,
)

if TYPE_CHECKING:
    from .ids import ReviewId
    from .ports import (
        Provider,
        StagedAssetExecutor,
        StagedExecutionRequest,
        StagedExecutionResult,
        TextModelRequest,
        TextModelResult,
    )


class IntentPolicyReason(StrEnum):
    PROPOSAL_ACCEPTED = "proposal_accepted"
    PRIVACY_HOLD = "privacy_hold"
    OWNER_CONTEXT_REQUIRED = "owner_context_required"
    INVALID_PROPOSAL = "invalid_proposal"


class BoundaryErrorCode(StrEnum):
    CLOUD_AUTHORITY_REQUIRED = "cloud_authority_required"
    EGRESS_AUTHORITY_REQUIRED = "egress_authority_required"
    NETWORK_HOST_DENIED = "network_host_denied"
    OPTIONAL_EXTRA_UNAVAILABLE = "optional_extra_unavailable"
    CREDENTIAL_UNAVAILABLE = "credential_unavailable"
    LOCAL_UNAVAILABLE = "local_unavailable"
    PROVIDER_TIMEOUT = "provider_timeout"
    OUTPUT_LIMIT = "output_limit"
    MALFORMED_RESPONSE = "malformed_response"
    PROVIDER_REJECTED = "provider_rejected"
    IMPLEMENTATION_FAILURE = "implementation_failure"


@dataclass(frozen=True, slots=True)
class BoundaryResult[T]:
    value: T | None
    error_code: BoundaryErrorCode | None


@dataclass(frozen=True, slots=True)
class ReviewProposalDraft:
    review_id: ReviewId
    capture_id: str
    source_ref: str
    privacy_tier: PrivacyTier
    proposed_intent: Intent
    proposal_reason: str
    capture_why: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class IntentRoute:
    intent: Intent
    reason: IntentPolicyReason
    review_proposal: ReviewProposalDraft | None


def construct_with_cloud_authority[T](
    privacy: PrivacyDecision, factory: Callable[[], T]
) -> BoundaryResult[T]:
    if not isinstance(privacy, PrivacyDecision) or not privacy.authority.cloud:
        return BoundaryResult(None, BoundaryErrorCode.CLOUD_AUTHORITY_REQUIRED)
    try:
        return BoundaryResult(factory(), None)
    except Exception:
        return BoundaryResult(None, BoundaryErrorCode.IMPLEMENTATION_FAILURE)


def invoke_provider(
    provider: Provider,
    request: TextModelRequest,
    *,
    privacy: PrivacyDecision,
) -> BoundaryResult[TextModelResult]:
    if not privacy.authority.cloud:
        return BoundaryResult(None, BoundaryErrorCode.CLOUD_AUTHORITY_REQUIRED)
    try:
        return BoundaryResult(provider.complete(request, privacy=privacy), None)
    except Exception:
        return BoundaryResult(None, BoundaryErrorCode.IMPLEMENTATION_FAILURE)


def invoke_staged_executor(
    executor: StagedAssetExecutor,
    request: StagedExecutionRequest,
    *,
    privacy: PrivacyDecision,
    permitted_network_hosts: tuple[str, ...],
) -> BoundaryResult[StagedExecutionResult]:
    if not privacy.authority.cloud:
        return BoundaryResult(None, BoundaryErrorCode.CLOUD_AUTHORITY_REQUIRED)
    if request.allowed_network_hosts and not privacy.authority.external_egress:
        return BoundaryResult(None, BoundaryErrorCode.EGRESS_AUTHORITY_REQUIRED)
    if not set(request.allowed_network_hosts).issubset(permitted_network_hosts):
        return BoundaryResult(None, BoundaryErrorCode.NETWORK_HOST_DENIED)
    try:
        return BoundaryResult(executor.execute(request, privacy=privacy), None)
    except Exception:
        return BoundaryResult(None, BoundaryErrorCode.IMPLEMENTATION_FAILURE)


def classify_privacy(raw: str | PrivacyTier | None, *, policy_version: str) -> PrivacyDecision:
    if raw is None:
        return _local_hold(PrivacyReason.CLASSIFICATION_MISSING, policy_version)
    if raw == "ambiguous":
        return _local_hold(PrivacyReason.CLASSIFICATION_AMBIGUOUS, policy_version)
    try:
        tier = PrivacyTier(raw)
    except (TypeError, ValueError):
        return _local_hold(PrivacyReason.CLASSIFICATION_INVALID, policy_version)
    if tier is PrivacyTier.UNKNOWN:
        return _local_hold(PrivacyReason.CLASSIFICATION_MISSING, policy_version)
    if tier is PrivacyTier.SECRET:
        return PrivacyDecision.create(
            tier=tier,
            reason=PrivacyReason.SECRET_DETECTED,
            policy_version=policy_version,
            authority=Authority(cloud=False, external_egress=False),
        )
    if tier is PrivacyTier.PERSONAL:
        return PrivacyDecision.create(
            tier=tier,
            reason=PrivacyReason.PERSONAL_LOCAL_ONLY,
            policy_version=policy_version,
            authority=Authority(cloud=False, external_egress=False),
        )
    return PrivacyDecision.create(
        tier=tier,
        reason=PrivacyReason.POLICY_PUBLIC
        if tier is PrivacyTier.PUBLIC
        else PrivacyReason.POLICY_WORK,
        policy_version=policy_version,
        authority=Authority(cloud=False, external_egress=False),
    )


def route_intent(
    capture: CaptureEnvelope,
    proposed_intent: str | None,
    proposal_reason: str,
    *,
    now: datetime,
) -> IntentRoute:
    if _must_hold_for_privacy(capture.privacy_decision):
        return IntentRoute(Intent.HOLD, IntentPolicyReason.PRIVACY_HOLD, None)
    if not isinstance(proposed_intent, str):
        return IntentRoute(Intent.HOLD, IntentPolicyReason.INVALID_PROPOSAL, None)
    try:
        intent = Intent(proposed_intent)
    except (TypeError, ValueError):
        return IntentRoute(Intent.HOLD, IntentPolicyReason.INVALID_PROPOSAL, None)
    if intent in {Intent.IDEA, Intent.ACTION_CANDIDATE}:
        if (
            capture.capture_why_origin is not CaptureWhyOrigin.OWNER_AUTHORED
            or not capture.capture_why
            or capture.capture_why.isspace()
        ):
            return IntentRoute(Intent.HOLD, IntentPolicyReason.OWNER_CONTEXT_REQUIRED, None)
        reason = _validate_reason(proposal_reason)
        draft = ReviewProposalDraft(
            review_id=review_id_for(capture.capture_id, intent.value),
            capture_id=str(capture.capture_id),
            source_ref=capture.provenance.source_ref,
            privacy_tier=capture.privacy_decision.tier,
            proposed_intent=intent,
            proposal_reason=reason,
            capture_why=capture.capture_why,
            created_at=now,
        )
        return IntentRoute(intent, IntentPolicyReason.PROPOSAL_ACCEPTED, draft)
    return IntentRoute(intent, IntentPolicyReason.PROPOSAL_ACCEPTED, None)


def _local_hold(reason: PrivacyReason, policy_version: str) -> PrivacyDecision:
    return PrivacyDecision.create(
        tier=PrivacyTier.UNKNOWN,
        reason=reason,
        policy_version=policy_version,
        authority=Authority(cloud=False, external_egress=False),
    )


def _must_hold_for_privacy(decision: PrivacyDecision) -> bool:
    return decision.tier in {PrivacyTier.UNKNOWN, PrivacyTier.SECRET} or decision.reason in {
        PrivacyReason.CLASSIFICATION_MISSING,
        PrivacyReason.CLASSIFICATION_INVALID,
        PrivacyReason.CLASSIFICATION_AMBIGUOUS,
    }


def _validate_reason(value: str) -> str:
    if not isinstance(value, str):
        raise ValidationError("invalid proposal reason")
    normalized = unicodedata.normalize("NFC", value)
    if (
        not normalized
        or normalized.isspace()
        or len(normalized) > 1000
        or any(marker in normalized for marker in ("\r", "\n", "\u0085", "\u2028", "\u2029"))
    ):
        raise ValidationError("invalid proposal reason")
    return normalized
