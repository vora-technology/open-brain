from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from hashlib import sha256
from typing import Literal, cast

from open_brain.core.ids import (
    CaptureId,
    ReviewId,
    approved_intent_record_id_for,
    canonical_json_bytes,
    review_id_for,
    validate_identifier,
)
from open_brain.core.models import Intent, PrivacyTier, ValidationError


class ReviewState(StrEnum):
    OPEN = "open"
    APPLIED = "applied"
    REJECTED = "rejected"
    DEFERRED = "deferred"
    BLOCKED = "blocked"


class ActorKind(StrEnum):
    OWNER = "owner"
    SYSTEM = "system"


class ReviewStateConflict(ValidationError):
    """A terminal review cannot receive a different transition."""


def capture_reference_for(capture_id: CaptureId | str) -> str:
    try:
        capture = validate_identifier(str(capture_id), prefix="cap_")
    except ValueError:
        raise ValidationError("invalid capture reference") from None
    digest = sha256(
        canonical_json_bytes({"identity_version": 1, "capture_id": capture})
    ).hexdigest()
    return "capture_ref_" + digest


@dataclass(frozen=True, slots=True)
class Actor:
    kind: ActorKind
    label: str

    def __post_init__(self) -> None:
        if not isinstance(self.kind, ActorKind) or not _one_line(self.label, maximum=100):
            raise ValidationError("invalid actor")

    def to_dict(self) -> dict[str, str]:
        return {"kind": self.kind.value, "label": self.label}

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> Actor:
        _exact_keys(value, {"kind", "label"})
        try:
            return cls(ActorKind(cast(str, value["kind"])), cast(str, value["label"]))
        except ValueError as error:
            raise ValidationError("invalid actor") from error


@dataclass(frozen=True, slots=True)
class ReviewProposal:
    schema_version: Literal[1]
    review_id: ReviewId
    capture_id: CaptureId
    source_ref: str
    privacy_tier: PrivacyTier
    proposed_intent: Intent
    proposal_reason: str
    capture_why: str
    state: ReviewState
    created_at: datetime
    created_by: Actor

    @classmethod
    def create(
        cls,
        *,
        capture_id: CaptureId | str,
        source_ref: str,
        privacy_tier: PrivacyTier | str,
        proposed_intent: Intent | str,
        proposal_reason: str,
        capture_why: str,
        created_at: datetime,
        created_by: Actor,
        review_id: ReviewId | str | None = None,
    ) -> ReviewProposal:
        try:
            capture = CaptureId(validate_identifier(str(capture_id), prefix="cap_"))
            intent = Intent(proposed_intent)
            tier = PrivacyTier(privacy_tier)
        except ValueError as error:
            raise ValidationError("invalid review") from error
        if (
            intent not in {Intent.IDEA, Intent.ACTION_CANDIDATE}
            or not isinstance(source_ref, str)
            or not source_ref
        ):
            raise ValidationError("invalid review")
        expected_id = review_id_for(capture, intent.value)
        if review_id is not None and str(review_id) != expected_id:
            raise ValidationError("invalid review")
        if not isinstance(created_by, Actor):
            raise ValidationError("invalid review")
        return cls(
            1,
            expected_id,
            capture,
            _nfc(source_ref),
            tier,
            intent,
            _reason(proposal_reason),
            _reason(capture_why),
            ReviewState.OPEN,
            _utc(created_at),
            created_by,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "review_id": str(self.review_id),
            "capture_id": str(self.capture_id),
            "source_ref": self.source_ref,
            "privacy_tier": self.privacy_tier.value,
            "proposed_intent": self.proposed_intent.value,
            "proposal_reason": self.proposal_reason,
            "capture_why": self.capture_why,
            "state": self.state.value,
            "created_at": _timestamp(self.created_at),
            "created_by": self.created_by.to_dict(),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> ReviewProposal:
        _exact_keys(
            value,
            {
                "schema_version",
                "review_id",
                "capture_id",
                "source_ref",
                "privacy_tier",
                "proposed_intent",
                "proposal_reason",
                "capture_why",
                "state",
                "created_at",
                "created_by",
            },
        )
        if value["schema_version"] != 1 or value["state"] != ReviewState.OPEN.value:
            raise ValidationError("invalid review")
        return cls.create(
            review_id=cast(str, value["review_id"]),
            capture_id=cast(str, value["capture_id"]),
            source_ref=cast(str, value["source_ref"]),
            privacy_tier=cast(str, value["privacy_tier"]),
            proposed_intent=cast(str, value["proposed_intent"]),
            proposal_reason=cast(str, value["proposal_reason"]),
            capture_why=cast(str, value["capture_why"]),
            created_at=_parse_timestamp(cast(str, value["created_at"])),
            created_by=Actor.from_dict(_mapping(value["created_by"])),
        )


@dataclass(frozen=True, slots=True)
class ReviewDecisionCommand:
    decision_id: str
    target_state: ReviewState
    reason: str
    occurred_at: datetime
    actor: Actor

    @classmethod
    def create(
        cls,
        *,
        decision_id: str,
        target_state: ReviewState | str,
        reason: str,
        occurred_at: datetime,
        actor: Actor,
    ) -> ReviewDecisionCommand:
        if not re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", decision_id) or not isinstance(actor, Actor):
            raise ValidationError("invalid decision")
        try:
            state = ReviewState(target_state)
        except ValueError as error:
            raise ValidationError("invalid decision") from error
        if state is ReviewState.OPEN:
            raise ValidationError("invalid decision")
        return cls(decision_id, state, _reason(reason), _utc(occurred_at), actor)


@dataclass(frozen=True, slots=True)
class ReviewEvent:
    decision_id: str
    review_id: ReviewId
    from_state: ReviewState
    to_state: ReviewState
    reason: str
    occurred_at: datetime
    actor: Actor

    def to_dict(self) -> dict[str, object]:
        return {
            "decision_id": self.decision_id,
            "review_id": str(self.review_id),
            "from_state": self.from_state.value,
            "to_state": self.to_state.value,
            "reason": self.reason,
            "occurred_at": _timestamp(self.occurred_at),
            "actor": self.actor.to_dict(),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> ReviewEvent:
        _exact_keys(
            value,
            {
                "decision_id",
                "review_id",
                "from_state",
                "to_state",
                "reason",
                "occurred_at",
                "actor",
            },
        )
        command = ReviewDecisionCommand.create(
            decision_id=cast(str, value["decision_id"]),
            target_state=cast(str, value["to_state"]),
            reason=cast(str, value["reason"]),
            occurred_at=_parse_timestamp(cast(str, value["occurred_at"])),
            actor=Actor.from_dict(_mapping(value["actor"])),
        )
        try:
            review_id = ReviewId(
                validate_identifier(cast(str, value["review_id"]), prefix="review_")
            )
            from_state = ReviewState(cast(str, value["from_state"]))
        except ValueError as error:
            raise ValidationError("invalid event") from error
        return cls(
            command.decision_id,
            review_id,
            from_state,
            command.target_state,
            command.reason,
            command.occurred_at,
            command.actor,
        )


@dataclass(frozen=True, slots=True)
class ApprovedIntentRecord:
    record_id: str
    review_id: ReviewId
    capture_id: CaptureId
    intent: Intent
    owner_statement: str
    source_ref: str
    privacy_tier: PrivacyTier
    approved_at: datetime
    approved_by: Actor

    def __post_init__(self) -> None:
        if (
            self.record_id != approved_intent_record_id_for(self.review_id, self.intent.value)
            or self.source_ref != capture_reference_for(self.capture_id)
            or self.intent not in {Intent.IDEA, Intent.ACTION_CANDIDATE}
            or not isinstance(self.privacy_tier, PrivacyTier)
            or not isinstance(self.approved_by, Actor)
            or self.approved_by.kind is not ActorKind.OWNER
        ):
            raise ValidationError("invalid approved intent record")
        _reason(self.owner_statement)
        _utc(self.approved_at)

    @classmethod
    def _from_approval(cls, proposal: ReviewProposal, event: ReviewEvent) -> ApprovedIntentRecord:
        return cls(
            approved_intent_record_id_for(proposal.review_id, proposal.proposed_intent.value),
            proposal.review_id,
            proposal.capture_id,
            proposal.proposed_intent,
            proposal.capture_why,
            capture_reference_for(proposal.capture_id),
            proposal.privacy_tier,
            event.occurred_at,
            event.actor,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "record_id": self.record_id,
            "review_id": str(self.review_id),
            "capture_id": str(self.capture_id),
            "intent": self.intent.value,
            "owner_statement": self.owner_statement,
            "source_ref": self.source_ref,
            "privacy_tier": self.privacy_tier.value,
            "approved_at": _timestamp(self.approved_at),
            "approved_by": self.approved_by.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class ReviewAggregate:
    proposal: ReviewProposal
    events: tuple[ReviewEvent, ...]
    approved_record: ApprovedIntentRecord | None

    @classmethod
    def create(cls, proposal: ReviewProposal) -> ReviewAggregate:
        if not isinstance(proposal, ReviewProposal) or proposal.state is not ReviewState.OPEN:
            raise ValidationError("invalid review aggregate")
        return cls(proposal, (), None)

    def decide(self, command: ReviewDecisionCommand) -> ReviewDecisionResult:
        if (
            command.target_state is ReviewState.APPLIED
            and command.actor.kind is not ActorKind.OWNER
        ):
            raise ValidationError("invalid review decision")
        if (
            command.target_state in {ReviewState.REJECTED, ReviewState.DEFERRED}
            and command.actor.kind is not ActorKind.OWNER
        ):
            raise ValidationError("invalid review decision")
        if (
            command.target_state is ReviewState.BLOCKED
            and command.actor.kind is not ActorKind.SYSTEM
        ):
            raise ValidationError("invalid review decision")
        if self.proposal.state is not ReviewState.OPEN:
            if self.proposal.state is command.target_state:
                return ReviewDecisionResult(self, self.approved_record, True)
            raise ReviewStateConflict("review is terminal")
        event = ReviewEvent(
            command.decision_id,
            self.proposal.review_id,
            ReviewState.OPEN,
            command.target_state,
            command.reason,
            command.occurred_at,
            command.actor,
        )
        next_proposal = ReviewProposal(
            self.proposal.schema_version,
            self.proposal.review_id,
            self.proposal.capture_id,
            self.proposal.source_ref,
            self.proposal.privacy_tier,
            self.proposal.proposed_intent,
            self.proposal.proposal_reason,
            self.proposal.capture_why,
            command.target_state,
            self.proposal.created_at,
            self.proposal.created_by,
        )
        approved = (
            ApprovedIntentRecord._from_approval(next_proposal, event)
            if command.target_state is ReviewState.APPLIED
            else None
        )
        return ReviewDecisionResult(
            ReviewAggregate(next_proposal, self.events + (event,), approved), approved, False
        )

    def to_dict(self) -> dict[str, object]:
        proposal = self.proposal.to_dict()
        proposal["state"] = self.proposal.state.value
        return {
            "proposal": proposal,
            "events": [event.to_dict() for event in self.events],
            "approved_record": None
            if self.approved_record is None
            else self.approved_record.to_dict(),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> ReviewAggregate:
        _exact_keys(value, {"proposal", "events", "approved_record"})
        proposal_value = dict(_mapping(value["proposal"]))
        state_value = proposal_value.pop("state", None)
        if state_value not in {state.value for state in ReviewState} or not isinstance(
            value["events"], list
        ):
            raise ValidationError("invalid review aggregate")
        proposal_value["state"] = ReviewState.OPEN.value
        proposal = ReviewProposal.from_dict(proposal_value)
        events = tuple(ReviewEvent.from_dict(_mapping(item)) for item in value["events"])
        if any(event.review_id != proposal.review_id for event in events):
            raise ValidationError("invalid review aggregate")
        if state_value == ReviewState.OPEN.value and events:
            raise ValidationError("invalid review aggregate")
        if state_value != ReviewState.OPEN.value:
            if (
                len(events) != 1
                or events[0].from_state is not ReviewState.OPEN
                or events[0].to_state.value != state_value
            ):
                raise ValidationError("invalid review aggregate")
            proposal = ReviewProposal(
                proposal.schema_version,
                proposal.review_id,
                proposal.capture_id,
                proposal.source_ref,
                proposal.privacy_tier,
                proposal.proposed_intent,
                proposal.proposal_reason,
                proposal.capture_why,
                ReviewState(state_value),
                proposal.created_at,
                proposal.created_by,
            )
        approved: ApprovedIntentRecord | None = None
        if proposal.state is ReviewState.APPLIED:
            expected_approved = ApprovedIntentRecord._from_approval(proposal, events[0])
            if _mapping(value["approved_record"]) != expected_approved.to_dict():
                raise ValidationError("invalid review aggregate")
            approved = expected_approved
        elif value["approved_record"] is not None:
            raise ValidationError("invalid review aggregate")
        return cls(proposal, events, approved)


@dataclass(frozen=True, slots=True)
class ReviewDecisionResult:
    aggregate: ReviewAggregate
    approved_record: ApprovedIntentRecord | None
    idempotent: bool


def _one_line(value: str, *, maximum: int) -> bool:
    return (
        isinstance(value, str)
        and bool(value)
        and len(value) <= maximum
        and not value.isspace()
        and not any(marker in value for marker in ("\r", "\n", "\u0085", "\u2028", "\u2029"))
    )


def _reason(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value) if isinstance(value, str) else ""
    if not _one_line(normalized, maximum=1000):
        raise ValidationError("invalid review reason")
    return normalized


def _nfc(value: str) -> str:
    if not isinstance(value, str):
        raise ValidationError("invalid text")
    return unicodedata.normalize("NFC", value)


def _utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValidationError("invalid timestamp")
    return value.astimezone(UTC)


def _timestamp(value: datetime) -> str:
    return _utc(value).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _parse_timestamp(value: str) -> datetime:
    if not isinstance(value, str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z", value
    ):
        raise ValidationError("invalid timestamp")
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=UTC)


def _mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        raise ValidationError("invalid object")
    return value


def _exact_keys(value: Mapping[str, object], expected: set[str]) -> None:
    if set(value) != expected:
        raise ValidationError("invalid fields")
