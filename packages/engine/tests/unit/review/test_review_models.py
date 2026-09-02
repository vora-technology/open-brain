from datetime import UTC, datetime

import pytest
from open_brain_engine.core.models import CaptureId, Intent, PrivacyTier, ValidationError
from open_brain_engine.review.models import (
    Actor,
    ActorKind,
    ReviewAggregate,
    ReviewDecisionCommand,
    ReviewProposal,
    ReviewState,
    ReviewStateConflict,
)


def _proposal(*, capture_id: CaptureId | None = None) -> ReviewProposal:
    return ReviewProposal.create(
        capture_id=capture_id or CaptureId("cap_" + "a" * 64),
        source_ref="https://example.invalid/item",
        privacy_tier=PrivacyTier.PUBLIC,
        proposed_intent=Intent.IDEA,
        proposal_reason="Potential idea",
        capture_why="Keep this",
        created_at=datetime(2026, 8, 13, tzinfo=UTC),
        created_by=Actor(kind=ActorKind.SYSTEM, label="router"),
    )


def _command(
    target: ReviewState, *, decision_id: str = "decision_1", actor: ActorKind = ActorKind.OWNER
) -> ReviewDecisionCommand:
    return ReviewDecisionCommand.create(
        decision_id=decision_id,
        target_state=target,
        reason="Owner decision",
        occurred_at=datetime(2026, 8, 13, 1, tzinfo=UTC),
        actor=Actor(kind=actor, label="owner" if actor is ActorKind.OWNER else "system"),
    )


def test_approval_creates_owner_authored_record_with_audit_link() -> None:
    result = ReviewAggregate.create(_proposal()).decide(_command(ReviewState.APPLIED))
    assert result.approved_record is not None
    assert result.approved_record.owner_statement == "Keep this"
    assert result.approved_record.review_id == result.aggregate.proposal.review_id
    assert result.approved_record.approved_by.kind is ActorKind.OWNER


@pytest.mark.parametrize("state", [ReviewState.REJECTED, ReviewState.DEFERRED])
def test_rejection_and_deferral_round_trip(state: ReviewState) -> None:
    result = ReviewAggregate.create(_proposal()).decide(_command(state))
    restored = ReviewAggregate.from_dict(result.aggregate.to_dict())
    assert restored.proposal.state is state
    assert restored.events[0].actor.kind is ActorKind.OWNER


def test_terminal_review_state_rejects_different_transition() -> None:
    aggregate = ReviewAggregate.create(_proposal()).decide(_command(ReviewState.REJECTED)).aggregate
    with pytest.raises(ReviewStateConflict):
        aggregate.decide(_command(ReviewState.DEFERRED, decision_id="decision_2"))


def test_repeated_approval_is_idempotent_and_has_one_event() -> None:
    aggregate = ReviewAggregate.create(_proposal())
    first = aggregate.decide(_command(ReviewState.APPLIED))
    second = first.aggregate.decide(_command(ReviewState.APPLIED, decision_id="decision_2"))
    assert second.idempotent is True
    assert second.approved_record == first.approved_record
    assert len(second.aggregate.events) == 1


def test_review_deserialization_rejects_spliced_approval_event() -> None:
    target = ReviewAggregate.create(_proposal()).decide(_command(ReviewState.APPLIED)).aggregate
    other = (
        ReviewAggregate.create(_proposal(capture_id=CaptureId("cap_" + "b" * 64)))
        .decide(_command(ReviewState.APPLIED))
        .aggregate
    )
    assert other.approved_record is not None
    payload = target.to_dict()
    payload["events"] = [other.events[0].to_dict()]

    with pytest.raises(ValidationError):
        ReviewAggregate.from_dict(payload)


@pytest.mark.parametrize("approved_record", [None, "spliced"])
def test_review_deserialization_requires_exact_approved_record(approved_record: object) -> None:
    target = ReviewAggregate.create(_proposal()).decide(_command(ReviewState.APPLIED)).aggregate
    other = (
        ReviewAggregate.create(_proposal(capture_id=CaptureId("cap_" + "b" * 64)))
        .decide(_command(ReviewState.APPLIED))
        .aggregate
    )
    assert other.approved_record is not None
    payload = target.to_dict()
    payload["approved_record"] = (
        other.approved_record.to_dict() if approved_record == "spliced" else approved_record
    )

    with pytest.raises(ValidationError):
        ReviewAggregate.from_dict(payload)


def test_review_deserialization_rejects_extra_approved_record() -> None:
    approved = ReviewAggregate.create(_proposal()).decide(_command(ReviewState.APPLIED)).aggregate
    rejected = ReviewAggregate.create(_proposal()).decide(_command(ReviewState.REJECTED)).aggregate
    assert approved.approved_record is not None
    payload = rejected.to_dict()
    payload["approved_record"] = approved.approved_record.to_dict()

    with pytest.raises(ValidationError):
        ReviewAggregate.from_dict(payload)
