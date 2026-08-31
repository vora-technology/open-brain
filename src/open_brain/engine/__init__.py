"""Task-shaped local engine facade for the Phase 1 vertical slice."""

from .local import (
    BrainEngine,
    CaptureAction,
    CaptureFault,
    DecisionOutcome,
    EnrichmentProvider,
    EnrichmentRequest,
    EnrichmentUnavailable,
    EventPayload,
    FilePayload,
    InjectedFault,
    LocalEngineContext,
    MeasurementPayload,
    ProposalDraft,
    ReferencePayload,
    TextPayload,
)

__all__ = [
    "BrainEngine",
    "CaptureAction",
    "CaptureFault",
    "DecisionOutcome",
    "EnrichmentProvider",
    "EnrichmentRequest",
    "EnrichmentUnavailable",
    "EventPayload",
    "FilePayload",
    "InjectedFault",
    "LocalEngineContext",
    "MeasurementPayload",
    "ProposalDraft",
    "ReferencePayload",
    "TextPayload",
]
