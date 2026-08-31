"""Local engine composition and legacy compatibility re-exports."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from hashlib import sha256

from open_brain.providers.base import ProviderMode
from open_brain.storage.locks import FileLease

from .capture import CaptureOperations, CaptureTasks
from .contracts import (
    CaptureAction,
    CaptureFault,
    CaptureReceipt,
    CaptureSubmission,
    CaptureSubmissionPath,
    DecisionOutcome,
    DecisionRecord,
    EngineTaskSet,
    EnrichmentProvider,
    EnrichmentRequest,
    EnrichmentUnavailable,
    EventPayload,
    FilePayload,
    InboxItem,
    InjectedFault,
    LocalEngineContext,
    MeasurementPayload,
    Payload,
    ProposalDraft,
    ProposalRecord,
    PublicJobCaptureContext,
    PublicJobCaptureSink,
    PublicProvenance,
    ReferencePayload,
    RetrievalResult,
    RoutedCapture,
    SpaceRecord,
    TextPayload,
)
from .local_store import _LocalStore
from .normalization import _done, _utc_now
from .retrieval import RetrievalOperations, RetrievalTasks, ScopedRetrieval
from .review import ReviewOperations, ReviewTasks
from .spaces import InboxSpaceTasks, SpaceOperations


class BrainEngine(CaptureOperations, SpaceOperations, ReviewOperations, RetrievalOperations):
    """Concrete local engine retained as a compatibility facade over task modules."""

    def __init__(
        self,
        profile: LocalEngineContext,
        *,
        faults: set[CaptureFault],
        clock: Callable[[], datetime],
        enrichment_provider: EnrichmentProvider | None,
    ) -> None:
        if profile.provider_mode is ProviderMode.CLOUD:
            raise ValueError("Phase 1 local engine does not enable cloud enrichment")
        if profile.provider_mode is ProviderMode.NONE and enrichment_provider is not None:
            raise ValueError("provider-none mode cannot construct an enrichment provider")
        if enrichment_provider is not None and not callable(
            getattr(enrichment_provider, "enrich", None)
        ):
            raise ValueError("invalid enrichment provider")
        self.profile = profile
        self._faults = set(faults)
        self._clock = clock
        self._enrichment_provider = enrichment_provider
        lease_identity = "engine-" + sha256(profile.owner_actor_id.encode("utf-8")).hexdigest()[:32]
        self._writer_lease = FileLease(profile.root / ".open-brain", lease_identity, clock=clock)
        with self._writer_lease.acquire_shared_writer():
            self._store = _LocalStore(profile)
        self.capture = CaptureTasks(self)
        self.inbox = InboxSpaceTasks(self)
        self.review = ReviewTasks(self)
        self.retrieval = RetrievalTasks(self)
        self._task_set = EngineTaskSet(
            profile=profile,
            capture=self.capture,
            inbox=self.inbox,
            review=self.review,
            retrieval=self.retrieval,
        )

    @classmethod
    def open(
        cls,
        profile: LocalEngineContext,
        *,
        faults: set[CaptureFault] | None = None,
        clock: Callable[[], datetime] | None = None,
        enrichment_provider: EnrichmentProvider | None = None,
    ) -> BrainEngine:
        if not isinstance(profile, LocalEngineContext):
            raise ValueError("invalid local profile")
        engine = cls(
            profile,
            faults=faults or set(),
            clock=clock or _utc_now,
            enrichment_provider=enrichment_provider,
        )
        with engine._writer_lease.acquire_shared_writer():
            engine._recover()
            for name in profile.starter_spaces:
                key = sha256(name.encode("utf-8")).hexdigest()
                engine._space_operation("create", None, name, f"starter.{key}")
        return engine

    @property
    def tasks(self) -> EngineTaskSet:
        return self._task_set

    def recover(self) -> int:
        with self._writer_lease.acquire_shared_writer():
            return self._recover()

    def _recover(self) -> int:
        recovered = 0
        for table, processor in (
            ("space_operations", self._process_space_operation),
            ("captures", self._process_capture),
            ("route_operations", self._process_route),
            ("proposal_sets", self._process_proposal_set),
            ("decisions", self._process_decision),
        ):
            connection = self._store.connect()
            try:
                rows = tuple(
                    connection.execute(f"SELECT * FROM {table} WHERE stage < ?", (_done(table),))
                )
            finally:
                connection.close()
            for row in rows:
                processor(row)
                recovered += 1
        return recovered

    def _fault(self, point: CaptureFault) -> None:
        if point in self._faults:
            self._faults.remove(point)
            raise InjectedFault(point)


def open_local_engine(
    profile: LocalEngineContext,
    *,
    faults: set[CaptureFault] | None = None,
    clock: Callable[[], datetime] | None = None,
    enrichment_provider: EnrichmentProvider | None = None,
) -> EngineTaskSet:
    """Open one local root and expose only its named task capabilities."""
    return BrainEngine.open(
        profile,
        faults=faults,
        clock=clock,
        enrichment_provider=enrichment_provider,
    ).tasks


__all__ = [
    "BrainEngine",
    "CaptureAction",
    "CaptureFault",
    "CaptureReceipt",
    "CaptureSubmission",
    "CaptureSubmissionPath",
    "CaptureTasks",
    "DecisionOutcome",
    "DecisionRecord",
    "EnrichmentProvider",
    "EnrichmentRequest",
    "EnrichmentUnavailable",
    "EngineTaskSet",
    "EventPayload",
    "FilePayload",
    "InboxItem",
    "InboxSpaceTasks",
    "InjectedFault",
    "LocalEngineContext",
    "MeasurementPayload",
    "Payload",
    "ProposalDraft",
    "ProposalRecord",
    "PublicJobCaptureContext",
    "PublicJobCaptureSink",
    "PublicProvenance",
    "ReferencePayload",
    "RetrievalResult",
    "RetrievalTasks",
    "ReviewTasks",
    "RoutedCapture",
    "ScopedRetrieval",
    "SpaceRecord",
    "TextPayload",
    "open_local_engine",
]
