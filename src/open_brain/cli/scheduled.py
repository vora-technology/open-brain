"""Typed, dependency-injected dispatch for scheduled public CLI routes."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, TextIO

from open_brain.cli._common import ExitCode, redacted_error
from open_brain.cli._registry import ScheduledRouteSpec
from open_brain.operations.capture_jobs import CaptureJobApplication, get_capture_job
from open_brain.operations.catalog import get_job
from open_brain.operations.models import ExitClass, JobSpec
from open_brain.operations.writer_jobs import WriterJobSpec, get_writer_job_spec


class ScheduledDispatchStatus(StrEnum):
    """Closed metadata-only outcomes for one scheduled route dispatch."""

    COMPLETED = "completed"
    FAILED = "failed"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class ScheduledDispatchResult:
    """A redaction-safe result returned by a scheduled application adapter."""

    job_id: str
    exit_code: int
    status: ScheduledDispatchStatus

    def __post_init__(self) -> None:
        if not isinstance(self.job_id, str) or not self.job_id.startswith("JOB-"):
            raise ValueError("invalid scheduled dispatch job")
        if not isinstance(self.exit_code, int) or self.exit_code not in {
            int(ExitCode.SUCCESS),
            int(ExitCode.FAILURE),
            int(ExitClass.LOCK_HELD),
            int(ExitClass.CONFIGURATION),
        }:
            raise ValueError("scheduled dispatch cannot return usage or deferred")
        if not isinstance(self.status, ScheduledDispatchStatus):
            raise ValueError("invalid scheduled dispatch status")
        if (self.status is ScheduledDispatchStatus.COMPLETED) != (
            self.exit_code == ExitCode.SUCCESS
        ):
            raise ValueError("scheduled dispatch status and exit disagree")

    @classmethod
    def completed(cls, job_id: str) -> ScheduledDispatchResult:
        return cls(job_id, ExitCode.SUCCESS, ScheduledDispatchStatus.COMPLETED)

    @classmethod
    def failed(cls, job_id: str) -> ScheduledDispatchResult:
        return cls(job_id, ExitCode.FAILURE, ScheduledDispatchStatus.FAILED)

    @classmethod
    def unavailable(cls, job_id: str) -> ScheduledDispatchResult:
        return cls(job_id, ExitCode.FAILURE, ScheduledDispatchStatus.UNAVAILABLE)

    @classmethod
    def lock_held(cls, job_id: str) -> ScheduledDispatchResult:
        return cls(job_id, ExitClass.LOCK_HELD, ScheduledDispatchStatus.FAILED)

    @classmethod
    def configuration(cls, job_id: str) -> ScheduledDispatchResult:
        return cls(job_id, ExitClass.CONFIGURATION, ScheduledDispatchStatus.FAILED)

    def to_envelope(self) -> dict[str, object]:
        envelope: dict[str, object] = {
            "command": self.job_id,
            "status": self.status.value,
        }
        if self.status is not ScheduledDispatchStatus.COMPLETED:
            if self.exit_code == ExitClass.LOCK_HELD:
                error_code = "scheduled_application_lock_held"
            elif self.exit_code == ExitClass.CONFIGURATION:
                error_code = "scheduled_application_configuration"
            elif self.status is ScheduledDispatchStatus.FAILED:
                error_code = "scheduled_application_failed"
            else:
                error_code = "scheduled_application_unavailable"
            envelope["error"] = redacted_error(error_code)
        return envelope


class ScheduledApplicationAdapters(Protocol):
    """Effect boundary supplied by the runtime composition layer."""

    def dispatch_capture(
        self, application: CaptureJobApplication
    ) -> ScheduledDispatchResult: ...

    def dispatch_writer(self, application: WriterJobSpec) -> ScheduledDispatchResult: ...

    def dispatch_optional(self, application: JobSpec) -> ScheduledDispatchResult: ...


@dataclass(frozen=True, slots=True)
class UnavailableScheduledAdapters:
    """Safe normal-console adapter that grants no application effect capability."""

    def dispatch_capture(
        self, application: CaptureJobApplication
    ) -> ScheduledDispatchResult:
        return ScheduledDispatchResult.unavailable(application.job.id)

    def dispatch_writer(self, application: WriterJobSpec) -> ScheduledDispatchResult:
        return ScheduledDispatchResult.unavailable(application.job_id)

    def dispatch_optional(self, application: JobSpec) -> ScheduledDispatchResult:
        return ScheduledDispatchResult.unavailable(application.id)


def dispatch_scheduled_route(
    route: ScheduledRouteSpec,
    adapters: ScheduledApplicationAdapters,
) -> ScheduledDispatchResult:
    """Resolve one catalog route to the existing typed application adapter."""
    job = get_job(route.job_id)
    if route.adapter == "capture":
        result = adapters.dispatch_capture(get_capture_job(route.job_id))
    elif route.adapter == "writer":
        result = adapters.dispatch_writer(get_writer_job_spec(route.job_id))
    else:
        result = adapters.dispatch_optional(job)
    if not isinstance(result, ScheduledDispatchResult) or result.job_id != route.job_id:
        raise ValueError("scheduled adapter returned a mismatched result")
    return result


def write_scheduled_result(
    result: ScheduledDispatchResult,
    *,
    json_output: bool,
    stream: TextIO,
) -> None:
    """Write only closed, metadata-safe scheduled dispatch fields."""
    if json_output:
        stream.write(json.dumps(result.to_envelope(), sort_keys=True, separators=(",", ":")) + "\n")
        return
    stream.write(f"scheduled application {result.status.value}\n")
