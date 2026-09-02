from dataclasses import replace
from datetime import UTC, datetime

import pytest
from open_brain_engine.core.models import (
    Authority,
    CaptureEnvelope,
    CaptureSource,
    CaptureWhyOrigin,
    ContentKind,
    ContentOrigin,
    Intent,
    PrivacyDecision,
    PrivacyReason,
    PrivacyTier,
    Provenance,
    SourceType,
)
from open_brain_engine.core.policy import (
    BoundaryErrorCode,
    IntentPolicyReason,
    classify_privacy,
    construct_with_cloud_authority,
    route_intent,
)


def _capture(*, automated: bool = False, tier: PrivacyTier = PrivacyTier.PUBLIC) -> CaptureEnvelope:
    origin = CaptureWhyOrigin.AUTOMATION_ABSENT if automated else CaptureWhyOrigin.OWNER_AUTHORED
    source = CaptureSource.PLAYLIST if automated else CaptureSource.SHORTCUT
    reason = dict(
        (
            (PrivacyTier.PUBLIC, PrivacyReason.POLICY_PUBLIC),
            (PrivacyTier.WORK, PrivacyReason.POLICY_WORK),
            (PrivacyTier.PERSONAL, PrivacyReason.PERSONAL_LOCAL_ONLY),
            (PrivacyTier.SECRET, PrivacyReason.SECRET_DETECTED),
            (PrivacyTier.UNKNOWN, PrivacyReason.CLASSIFICATION_MISSING),
        )
    )[tier]
    privacy = PrivacyDecision.create(
        tier=tier,
        reason=reason,
        policy_version="v1",
        authority=Authority(cloud=False, external_egress=False),
    )
    return CaptureEnvelope.create(
        source_type=SourceType.WEB,
        content_kind=ContentKind.ARTICLE,
        source_url="https://example.invalid/item",
        title=None,
        shared_text="Synthetic advice",
        captured_at=datetime(2026, 8, 13, tzinfo=UTC),
        capture_why="" if automated else "Keep this",
        capture_why_origin=origin,
        capture_source=source,
        provenance=Provenance.create(
            source_ref="https://example.invalid/item",
            content_origin=ContentOrigin.THIRD_PARTY,
            owner_context=origin,
        ),
        raw_assets=(),
        privacy_decision=privacy,
    )


@pytest.mark.parametrize("route", ["reference", "idea", "action_candidate", "hold"])
def test_closed_intent_accepts_exactly_four_routes(route: str) -> None:
    assert (
        route_intent(
            _capture(), route, "A reason", now=datetime(2026, 8, 13, tzinfo=UTC)
        ).intent.value
        == route
    )


@pytest.mark.parametrize("route", ["", "IDEA", "unknown", None])
def test_raw_intent_proposal_safely_holds_invalid_routes(route: str | None) -> None:
    result = route_intent(_capture(), route, "A reason", now=datetime(2026, 8, 13, tzinfo=UTC))
    assert result.intent.value == "hold"
    assert result.reason is IntentPolicyReason.INVALID_PROPOSAL
    assert result.review_proposal is None


@pytest.mark.parametrize("route", ["", "IDEA", "unknown", None])
def test_closed_intent_directly_rejects_invalid_values(route: str | None) -> None:
    with pytest.raises((TypeError, ValueError)):
        Intent(route)  # type: ignore[arg-type]


@pytest.mark.parametrize("route", ["idea", "action_candidate"])
def test_automation_absence_rejects_reviewable_routes(route: str) -> None:
    result = route_intent(
        _capture(automated=True), route, "A reason", now=datetime(2026, 8, 13, tzinfo=UTC)
    )
    assert result.intent.value == "hold"
    assert result.reason is IntentPolicyReason.OWNER_CONTEXT_REQUIRED
    assert result.review_proposal is None


@pytest.mark.parametrize("route", ["reference", "hold"])
def test_automation_absence_accepts_non_reviewable_routes(route: str) -> None:
    result = route_intent(
        _capture(automated=True), route, "A reason", now=datetime(2026, 8, 13, tzinfo=UTC)
    )

    assert result.intent.value == route
    assert result.reason is IntentPolicyReason.PROPOSAL_ACCEPTED
    assert result.review_proposal is None


@pytest.mark.parametrize("route", ["idea", "action_candidate"])
def test_idea_and_action_emit_review_proposals_only(route: str) -> None:
    result = route_intent(_capture(), route, "A reason", now=datetime(2026, 8, 13, tzinfo=UTC))
    assert result.review_proposal is not None
    assert result.review_proposal.proposed_intent.value == route


@pytest.mark.parametrize("route", ["idea", "action_candidate"])
def test_whitespace_owner_context_rejects_reviewable_routes(route: str) -> None:
    forged_capture = replace(_capture(), capture_why="   ")

    result = route_intent(forged_capture, route, "A reason", now=datetime(2026, 8, 13, tzinfo=UTC))

    assert result.intent is Intent.HOLD
    assert result.reason is IntentPolicyReason.OWNER_CONTEXT_REQUIRED
    assert result.review_proposal is None


@pytest.mark.parametrize("route", ["reference", "hold"])
def test_reference_and_hold_do_not_emit_review_proposals(route: str) -> None:
    assert (
        route_intent(
            _capture(), route, "A reason", now=datetime(2026, 8, 13, tzinfo=UTC)
        ).review_proposal
        is None
    )


@pytest.mark.parametrize("tier", [PrivacyTier.UNKNOWN, PrivacyTier.SECRET])
def test_unsafe_privacy_holds_before_routing(tier: PrivacyTier) -> None:
    result = route_intent(
        _capture(tier=tier), "idea", "A reason", now=datetime(2026, 8, 13, tzinfo=UTC)
    )
    assert result.intent.value == "hold"
    assert result.reason is IntentPolicyReason.PRIVACY_HOLD


@pytest.mark.parametrize(
    ("raw", "expected_reason"),
    [
        (None, PrivacyReason.CLASSIFICATION_MISSING),
        ("invalid", PrivacyReason.CLASSIFICATION_INVALID),
        ("ambiguous", PrivacyReason.CLASSIFICATION_AMBIGUOUS),
    ],
)
def test_each_classification_failure_routes_to_privacy_hold(
    raw: str | None, expected_reason: PrivacyReason
) -> None:
    privacy = classify_privacy(raw, policy_version="v1")
    capture = replace(_capture(), privacy_decision=privacy)

    result = route_intent(capture, "idea", "A reason", now=datetime(2026, 8, 13, tzinfo=UTC))

    assert privacy.reason is expected_reason
    assert result.intent is Intent.HOLD
    assert result.reason is IntentPolicyReason.PRIVACY_HOLD
    assert result.review_proposal is None


@pytest.mark.parametrize("raw", [None, "invalid", "ambiguous", PrivacyTier.PERSONAL])
def test_fail_closed_privacy_never_constructs_provider(
    raw: str | PrivacyTier | None,
) -> None:
    privacy = classify_privacy(raw, policy_version="v1")
    factory_calls = 0

    def factory() -> object:
        nonlocal factory_calls
        factory_calls += 1
        return object()

    result = construct_with_cloud_authority(privacy, factory)

    assert factory_calls == 0
    assert result.value is None
    assert result.error_code is BoundaryErrorCode.CLOUD_AUTHORITY_REQUIRED


def test_cloud_authority_guard_calls_factory_once_when_allowed() -> None:
    privacy = PrivacyDecision.create(
        tier=PrivacyTier.PUBLIC,
        reason=PrivacyReason.POLICY_PUBLIC,
        policy_version="v1",
        authority=Authority(cloud=True, external_egress=False),
    )
    instance = object()
    factory_calls = 0

    def factory() -> object:
        nonlocal factory_calls
        factory_calls += 1
        return instance

    result = construct_with_cloud_authority(privacy, factory)

    assert factory_calls == 1
    assert result.value is instance
    assert result.error_code is None
