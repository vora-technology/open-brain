"""Queue-only scheduled applications for capture ingress jobs."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Protocol

from open_brain.capture.models import CaptureWorkItem
from open_brain.core.models import CaptureEnvelope
from open_brain.core.ports import PutDisposition, PutResult

from .catalog import get_job
from .models import HostRole, JobSpec, JobState, LockScope, OutputPolicy, WriterScope


class CaptureJobContractError(ValueError):
    """A scheduled capture job exceeds its append-only authority."""


class CaptureWrite(StrEnum):
    """The only durable effect available to a capture scheduled application."""

    QUEUE_ENVELOPE = "queue-envelope"


class CaptureQueue(Protocol):
    """Append-only capture queue port used by scheduled ingress applications."""

    def enqueue(self, item: CaptureWorkItem, *, item_id: str, payload_digest: str) -> PutResult: ...


_EXPECTED_COMMANDS = MappingProxyType(
    {
        "JOB-005": (
            "open-brain",
            "capture",
            "imessage-ingress",
            "--append",
            "--json",
        ),
        "JOB-027": (
            "open-brain",
            "capture",
            "serve",
            "--bind=CONFIGURED_PRIVATE_BIND",
            "--port=CONFIGURED_PORT",
        ),
        "JOB-028": (
            "open-brain",
            "capture",
            "serve",
            "--mode=ingress",
            "--bind=CONFIGURED_PRIVATE_BIND",
            "--port=CONFIGURED_PORT",
        ),
        "JOB-029": (
            "open-brain",
            "capture",
            "poll",
            "--source=youtube",
            "--mode=ingress",
            "--json",
        ),
    }
)


@dataclass(frozen=True, slots=True)
class CaptureAppendResult:
    """Opaque append metadata safe for scheduled-job output."""

    job_id: str
    capture_id: str
    disposition: PutDisposition

    def to_dict(self) -> dict[str, str]:
        return {
            "capture_id": self.capture_id,
            "disposition": self.disposition.value,
            "job_id": self.job_id,
        }


@dataclass(frozen=True, slots=True)
class CaptureJobApplication:
    """A validated public CLI specification with queue-append authority only."""

    job: JobSpec

    def __post_init__(self) -> None:
        expected_command = _EXPECTED_COMMANDS.get(self.job.id)
        if expected_command is None or self.job.command != expected_command:
            raise CaptureJobContractError("invalid capture job public CLI argv")
        if (
            self.job.host_role is not HostRole.INGRESS
            or self.job.writer_scope is not WriterScope.CAPTURE_INGRESS
            or self.job.lock_scope is not LockScope.INGRESS
            or self.job.output_policy is not OutputPolicy.REDACTED_REPORT
        ):
            raise CaptureJobContractError("capture job must remain queue-only ingress")
        if self.job.state is not JobState.ENABLED:
            raise CaptureJobContractError("production capture job must remain enabled")

    @property
    def argv(self) -> tuple[str, ...]:
        return self.job.command

    @property
    def allowed_writes(self) -> frozenset[CaptureWrite]:
        return frozenset({CaptureWrite.QUEUE_ENVELOPE})

    @property
    def service_actions(self) -> tuple[str, ...]:
        return ()

    def append(self, *, queue: CaptureQueue, envelope: CaptureEnvelope) -> CaptureAppendResult:
        if not isinstance(envelope, CaptureEnvelope):
            raise CaptureJobContractError("invalid capture envelope")
        item = CaptureWorkItem.create(envelope=envelope, available_at=envelope.captured_at)
        item_id = str(envelope.capture_id)
        payload_digest = item.payload_digest_sha256()
        result = queue.enqueue(item, item_id=item_id, payload_digest=payload_digest)
        if (
            not isinstance(result, PutResult)
            or result.disposition not in {PutDisposition.CREATED, PutDisposition.DUPLICATE}
            or result.record_id != item_id
            or result.digest_sha256 != payload_digest
        ):
            raise CaptureJobContractError("invalid capture queue append result")
        return CaptureAppendResult(
            job_id=self.job.id,
            capture_id=item_id,
            disposition=result.disposition,
        )


def get_capture_job(job_id: str) -> CaptureJobApplication:
    """Return one validated capture scheduled-application specification."""
    return CaptureJobApplication(get_job(job_id))
