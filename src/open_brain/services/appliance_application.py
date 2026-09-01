"""App-owned appliance composition for init/status and read-only MCP."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from open_brain.engine import ScopedRetrievalTask, open_local_read_view
from open_brain.integrations.mcp import EngineMcpAdapter
from open_brain.integrations.ports import RetrievalFeedbackReceipt, RetrievalFeedbackRequest
from open_brain.profile import open_existing_single_user_local


class ApplianceRetrievalFeedback:
    """Metadata-only feedback acknowledgement for the offline appliance MCP view."""

    def record(self, request: RetrievalFeedbackRequest) -> RetrievalFeedbackReceipt:
        if not isinstance(request, RetrievalFeedbackRequest):
            raise ValueError("invalid retrieval feedback")
        return RetrievalFeedbackReceipt(
            retrieval_id=request.retrieval_id,
            outcome=request.outcome,
            result_count=len(request.result_ids),
            recorded=False,
        )


@dataclass(frozen=True, slots=True)
class ApplianceApplication:
    retrieval: ScopedRetrievalTask
    feedback: ApplianceRetrievalFeedback = field(default_factory=ApplianceRetrievalFeedback)

    @classmethod
    def open_read_only(
        cls,
        root: Path,
        *,
        allowed_space_ids: frozenset[str] = frozenset(),
    ) -> ApplianceApplication:
        profile = open_existing_single_user_local(root)
        retrieval = open_local_read_view(profile, allowed_space_ids=allowed_space_ids)
        return cls(retrieval=retrieval)

    def mcp_adapter(self) -> EngineMcpAdapter:
        return EngineMcpAdapter(retrieval=self.retrieval, feedback=self.feedback)
