"""Task-shaped local engine facade for the Phase 1 vertical slice."""

from open_brain.core.locks import LockScope

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
    "LockScope",
    "MeasurementPayload",
    "ProposalDraft",
    "ReferencePayload",
    "TextPayload",
]
