"""Framework-neutral, work-only tool adapter for a local stdio MCP server."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal, TypedDict

from .ports import (
    FeedbackOutcome,
    IntegrationScope,
    RetrievalBatch,
    RetrievalFeedback,
    RetrievalFeedbackReceipt,
    RetrievalFeedbackRequest,
    RetrievalRequest,
    WorkRetriever,
)


class McpCallError(ValueError):
    """Safe adapter error that omits raw service or argument details."""


_OPAQUE_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}")
_OPAQUE_ID_SCHEMA = {
    "type": "string",
    "minLength": 1,
    "maxLength": 128,
    "pattern": r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$",
}


class McpInputSchema(TypedDict):
    type: Literal["object"]
    properties: dict[str, object]
    required: list[str]
    additionalProperties: Literal[False]


class McpToolDefinition(TypedDict):
    name: str
    description: str
    inputSchema: McpInputSchema


@dataclass(slots=True)
class LocalStdioMcpAdapter:
    """Expose bounded work retrieval and metadata-only feedback as MCP tools."""

    retriever: WorkRetriever
    feedback: RetrievalFeedback

    @property
    def transport(self) -> Literal["stdio"]:
        return "stdio"

    @property
    def scope(self) -> IntegrationScope:
        return IntegrationScope.WORK

    def list_tools(self) -> tuple[McpToolDefinition, ...]:
        return (
            {
                "name": "brain_query",
                "description": "Search bounded, redacted work context.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "question": {"type": "string", "minLength": 1, "maxLength": 4096},
                        "limit": {"type": "integer", "minimum": 1, "maximum": 8},
                    },
                    "required": ["question"],
                    "additionalProperties": False,
                },
            },
            {
                "name": "brain_retrieval_feedback",
                "description": "Record allow-listed retrieval outcome metadata.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "retrieval_id": dict(_OPAQUE_ID_SCHEMA),
                        "outcome": {
                            "type": "string",
                            "enum": ["used", "cited", "ignored", "empty"],
                        },
                        "result_ids": {
                            "type": "array",
                            "items": dict(_OPAQUE_ID_SCHEMA),
                            "maxItems": 8,
                            "uniqueItems": True,
                        },
                    },
                    "required": ["retrieval_id", "outcome"],
                    "additionalProperties": False,
                },
            },
        )

    def call_tool(self, name: str, arguments: Mapping[str, object]) -> dict[str, object]:
        try:
            if name == "brain_query":
                return self._query(arguments)
            if name == "brain_retrieval_feedback":
                return self._record_feedback(arguments)
            raise McpCallError("unknown tool")
        except McpCallError:
            raise
        except (KeyError, TypeError, ValueError):
            raise McpCallError("invalid tool arguments") from None
        except Exception:
            raise McpCallError("tool call failed") from None

    def _query(self, arguments: Mapping[str, object]) -> dict[str, object]:
        _require_keys(arguments, required={"question"}, optional={"limit"})
        question = arguments["question"]
        limit = arguments.get("limit", 5)
        if not isinstance(question, str):
            raise ValueError("invalid question")
        request = RetrievalRequest(question=question, limit=limit)  # type: ignore[arg-type]
        batch = self.retriever.search(request)
        if not isinstance(batch, RetrievalBatch):
            raise TypeError("invalid retrieval response")
        hits = batch.hits[: request.limit]
        return {
            "retrieval_id": batch.retrieval_id,
            "scope": IntegrationScope.WORK.value,
            "results": [hit.to_dict() for hit in hits],
            "truncated": batch.truncated or len(batch.hits) > request.limit,
        }

    def _record_feedback(self, arguments: Mapping[str, object]) -> dict[str, object]:
        _require_keys(
            arguments,
            required={"retrieval_id", "outcome"},
            optional={"result_ids"},
        )
        retrieval_id = arguments["retrieval_id"]
        outcome = arguments["outcome"]
        result_ids = arguments.get("result_ids", [])
        if (
            not isinstance(retrieval_id, str)
            or not isinstance(outcome, str)
            or not isinstance(result_ids, list)
            or any(not isinstance(result_id, str) for result_id in result_ids)
        ):
            raise ValueError("invalid feedback")
        _require_opaque_id(retrieval_id)
        for result_id in result_ids:
            _require_opaque_id(result_id)
        request = RetrievalFeedbackRequest(
            retrieval_id=retrieval_id,
            outcome=FeedbackOutcome(outcome),
            result_ids=tuple(result_ids),
        )
        receipt = self.feedback.record(request)
        if not isinstance(receipt, RetrievalFeedbackReceipt):
            raise TypeError("invalid feedback response")
        return receipt.to_dict()


def _require_keys(
    arguments: Mapping[str, object],
    *,
    required: set[str],
    optional: set[str],
) -> None:
    keys = set(arguments)
    if not required.issubset(keys) or not keys.issubset(required | optional):
        raise ValueError("invalid arguments")


def _require_opaque_id(value: str) -> None:
    if _OPAQUE_ID_PATTERN.fullmatch(value) is None:
        raise ValueError("invalid opaque identifier")
