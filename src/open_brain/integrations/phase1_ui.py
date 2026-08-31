"""Authenticated, framework-neutral local UI over Phase 1 engine tasks."""

from __future__ import annotations

import base64
import html
import json
from dataclasses import dataclass
from typing import cast
from urllib.parse import parse_qs, urlsplit

from open_brain.capture.auth import BearerAuthenticator
from open_brain.core.ids import canonical_json_bytes
from open_brain.engine import (
    CaptureAction,
    DecisionOutcome,
    EngineTaskSet,
    EventPayload,
    FilePayload,
    MeasurementPayload,
    ReferencePayload,
    TextPayload,
)

_MAX_BODY = 1_500_000


@dataclass(frozen=True, slots=True)
class Phase1UiRequest:
    method: str
    path: str
    headers: tuple[tuple[str, str], ...]
    body: bytes = b""


@dataclass(frozen=True, slots=True)
class Phase1UiResponse:
    status: int
    body: bytes
    headers: tuple[tuple[str, str], ...]


class Phase1UiHandler:
    """Map authenticated local UI routes to injected engine task capabilities."""

    def __init__(self, *, expected_bearer_token: str, tasks: EngineTaskSet) -> None:
        if not isinstance(tasks, EngineTaskSet):
            raise ValueError("invalid Phase 1 UI tasks")
        self._authenticator = BearerAuthenticator(expected_bearer_token)
        self.tasks = tasks

    def handle(self, request: Phase1UiRequest) -> Phase1UiResponse:
        if not isinstance(request, Phase1UiRequest):
            return _text(400, "invalid_request")
        authorization = _authorization(request.headers)
        if authorization is None:
            return _text(400, "invalid_request")
        if not self._authenticator.authenticate(authorization):
            return _text(401, "unauthorized")
        if (
            not isinstance(request.method, str)
            or not isinstance(request.path, str)
            or not isinstance(request.body, bytes)
        ):
            return _text(400, "invalid_request")
        if len(request.body) > _MAX_BODY:
            return _text(413, "payload_too_large")
        try:
            if request.method == "GET":
                return self._get(request.path)
            if request.method == "POST":
                return self._post(request.path, request.body)
            return _text(405, "method_not_allowed", allow="GET, POST")
        except ValueError:
            return _json(409, {"error": "request_conflict", "status": "failed"})
        except Exception:
            return _json(503, {"error": "service_unavailable", "status": "failed"})

    def _get(self, path: str) -> Phase1UiResponse:
        parsed = urlsplit(path)
        query = _query(parsed.query)
        if parsed.path == "/health" and not query:
            return _json(200, {"status": "ok"})
        if parsed.path == "/" and not query:
            return _html(self._dashboard())
        if parsed.path == "/api/inbox" and not query:
            return _json(
                200,
                {
                    "captures": [
                        {
                            "capture_id": item.capture_id,
                            "payload_family": item.payload_family,
                            "space_id": item.space_id,
                            "state": item.state,
                        }
                        for item in self.tasks.inbox.list()
                    ],
                    "status": "listed",
                },
            )
        if parsed.path == "/api/spaces" and not query:
            return _json(
                200,
                {
                    "spaces": [
                        {"name": space.name, "slug": space.slug, "space_id": space.space_id}
                        for space in self.tasks.inbox.spaces()
                    ],
                    "status": "listed",
                },
            )
        if parsed.path == "/api/proposals" and set(query) <= {"capture", "status"}:
            proposals = self.tasks.review.list(
                capture_id=query.get("capture"), status=query.get("status")
            )
            return _json(
                200,
                {
                    "proposals": [
                        {
                            "capture_id": proposal.capture_id,
                            "decision_id": proposal.terminal_decision_id,
                            "proposal_id": proposal.proposal_id,
                            "sibling_proposal_ids": list(proposal.sibling_proposal_ids),
                            "space_id": proposal.space_id,
                            "state": proposal.status,
                        }
                        for proposal in proposals
                    ],
                    "status": "listed",
                },
            )
        if parsed.path == "/api/search" and "q" in query and set(query) <= {
            "q",
            "space",
            "family",
            "type",
            "limit",
        }:
            results = self.tasks.retrieval.search(
                query["q"],
                space_id=query.get("space"),
                payload_family=query.get("family"),
                record_type=query.get("type"),
                limit=int(query.get("limit", "10")),
            )
            return _json(
                200,
                {
                    "results": [
                        {
                            "capture_id": result.capture_id,
                            "excerpt": result.excerpt,
                            "explanation": result.explanation,
                            "payload_family": result.payload_family,
                            "provenance": dict(result.provenance),
                            "record_type": result.record_type,
                            "result_id": result.result_id,
                            "space_id": result.space_id,
                            "title": result.title,
                            "trust": result.trust,
                        }
                        for result in results
                    ],
                    "status": "ok",
                },
            )
        return _text(404, "not_found")

    def _post(self, path: str, body: bytes) -> Phase1UiResponse:
        value = _body(body)
        if path in {"/api/captures/quick", "/api/captures/canonical"}:
            metadata = {"capture_why", "intent", "space_id", "title"}
            if "payload" in value:
                _keys(value, required={"delivery_id", "payload"}, optional=metadata)
                payload = _capture_payload(value["payload"])
            else:
                _keys(value, required={"delivery_id", "text"}, optional=metadata)
                payload = TextPayload(_string(value, "text"))
            space_id = _optional_string(value, "space_id")
            canonical = path.endswith("canonical")
            if canonical and (not isinstance(payload, TextPayload) or space_id is None):
                raise ValueError("canonical capture requires text and a space")
            receipt = self.tasks.capture.accept(
                payload,
                delivery_id=_string(value, "delivery_id"),
                action=(
                    CaptureAction.CANONICAL_NOTE
                    if canonical
                    else CaptureAction.QUICK
                ),
                space_id=space_id,
                intent=_optional_string(value, "intent"),
                capture_why=_optional_string(value, "capture_why"),
                title=_optional_string(value, "title"),
            )
            return _json(
                200,
                {
                    "canonical": receipt.canonical_path is not None,
                    "capture_id": receipt.capture_id,
                    "duplicate": receipt.duplicate,
                    "enrichment_state": receipt.enrichment_state,
                    "payload_family": receipt.payload_family,
                    "space_id": receipt.space_id,
                    "state": receipt.state,
                    "status": "accepted",
                },
            )
        if path == "/api/spaces":
            _keys(value, required={"delivery_id", "name"})
            space = self.tasks.inbox.create_space(
                _string(value, "name"), delivery_id=_string(value, "delivery_id")
            )
            return _json(200, {"space_id": space.space_id, "status": "created"})
        parts = tuple(part for part in path.split("/") if part)
        if len(parts) == 4 and parts[:2] == ("api", "spaces") and parts[3] == "rename":
            _keys(value, required={"delivery_id", "name"})
            space = self.tasks.inbox.rename_space(
                parts[2],
                _string(value, "name"),
                delivery_id=_string(value, "delivery_id"),
            )
            return _json(200, {"space_id": space.space_id, "status": "renamed"})
        if len(parts) == 4 and parts[:2] == ("api", "captures") and parts[3] == "route":
            _keys(value, required={"delivery_id", "space_id"})
            routed = self.tasks.inbox.route(
                parts[2],
                _string(value, "space_id"),
                delivery_id=_string(value, "delivery_id"),
            )
            return _json(
                200,
                {
                    "capture_id": routed.capture_id,
                    "space_id": routed.space_id,
                    "status": "routed",
                },
            )
        if len(parts) == 4 and parts[:2] == ("api", "proposals") and parts[3] == "decision":
            _keys(
                value,
                required={"delivery_id", "outcome"},
                optional={"edited_markdown"},
            )
            outcome = DecisionOutcome(_string(value, "outcome"))
            decision = self.tasks.review.decide(
                parts[2],
                outcome,
                delivery_id=_string(value, "delivery_id"),
                edited_markdown=_optional_string(value, "edited_markdown"),
            )
            return _json(
                200,
                {
                    "decision_id": decision.decision_id,
                    "duplicate": decision.duplicate,
                    "page_id": decision.page_id,
                    "proposal_id": decision.proposal_id,
                    "publication_id": decision.publication_id,
                    "state": decision.outcome.value,
                    "status": "decided",
                },
            )
        return _text(404, "not_found")

    def _dashboard(self) -> bytes:
        captures = self.tasks.inbox.list()
        spaces = self.tasks.inbox.spaces()
        proposals = self.tasks.review.list()
        capture_items = "".join(
            f"<li><code>{html.escape(item.capture_id)}</code> {html.escape(item.state)}</li>"
            for item in captures
        ) or "<li>Inbox empty</li>"
        space_items = "".join(
            f"<li><code>{html.escape(space.space_id)}</code> {html.escape(space.name)}</li>"
            for space in spaces
        ) or "<li>No spaces</li>"
        proposal_items = "".join(
            f"<li><code>{html.escape(item.proposal_id)}</code> {html.escape(item.status)}</li>"
            for item in proposals
        ) or "<li>No proposals</li>"
        return (
            "<!doctype html><html><head><meta charset=\"utf-8\"><title>Open Brain</title>"
            "</head><body><main><h1>Open Brain</h1>"
            f"<h2>Inbox</h2><ul>{capture_items}</ul>"
            f"<h2>Spaces</h2><ul>{space_items}</ul>"
            f"<h2>Proposals</h2><ul>{proposal_items}</ul>"
            "</main></body></html>"
        ).encode()


def _authorization(headers: object) -> tuple[str, ...] | None:
    if not isinstance(headers, tuple):
        return None
    values: list[str] = []
    for header in headers:
        if (
            not isinstance(header, tuple)
            or len(header) != 2
            or not isinstance(header[0], str)
            or not isinstance(header[1], str)
            or not header[0].isascii()
        ):
            return None
        if header[0].casefold() == "authorization":
            values.append(header[1])
    return tuple(values)


def _body(payload: bytes) -> dict[str, object]:
    try:
        value = json.loads(payload.decode("utf-8"), object_pairs_hook=_unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise ValueError("invalid UI body") from error
    if not isinstance(value, dict):
        raise ValueError("invalid UI body")
    return cast(dict[str, object], value)


def _capture_payload(
    value: object,
) -> TextPayload | ReferencePayload | FilePayload | EventPayload | MeasurementPayload:
    if not isinstance(value, dict):
        raise ValueError("invalid capture payload")
    payload = cast(dict[str, object], value)
    family = _string(payload, "family")
    if family == "text":
        _keys(payload, required={"family", "text"})
        return TextPayload(_string(payload, "text"))
    if family == "reference_or_file":
        kind = _string(payload, "kind")
        if kind == "reference":
            _keys(
                payload,
                required={"family", "kind", "url"},
                optional={"supplied_text"},
            )
            return ReferencePayload(
                _string(payload, "url"),
                _optional_string(payload, "supplied_text"),
            )
        if kind == "file":
            _keys(
                payload,
                required={"data_base64", "family", "file_name", "kind", "media_type"},
            )
            return FilePayload(
                _string(payload, "file_name"),
                _string(payload, "media_type"),
                base64.b64decode(_string(payload, "data_base64"), validate=True),
            )
        raise ValueError("invalid capture payload")
    if family == "event":
        _keys(
            payload,
            required={"attributes", "event_type", "family"},
            optional={"occurrence_at"},
        )
        return EventPayload(
            _string(payload, "event_type"),
            _optional_string(payload, "occurrence_at"),
            _string_mapping(payload.get("attributes")),
        )
    if family == "measurement":
        _keys(
            payload,
            required={"dimensions", "family", "unit", "value"},
            optional={"occurrence_at"},
        )
        return MeasurementPayload(
            _string(payload, "value"),
            _string(payload, "unit"),
            _optional_string(payload, "occurrence_at"),
            _string_mapping(payload.get("dimensions")),
        )
    raise ValueError("invalid capture payload")


def _string_mapping(value: object) -> dict[str, str]:
    if not isinstance(value, dict) or any(
        not isinstance(key, str) or not isinstance(item, str)
        for key, item in value.items()
    ):
        raise ValueError("invalid capture payload")
    return cast(dict[str, str], value)


def _keys(
    value: dict[str, object],
    *,
    required: set[str],
    optional: set[str] | None = None,
) -> None:
    if not required <= set(value) or set(value) - required - (optional or set()):
        raise ValueError("invalid UI body")


def _string(value: dict[str, object], key: str) -> str:
    item = value.get(key)
    if not isinstance(item, str):
        raise ValueError("invalid UI body")
    return item


def _optional_string(value: dict[str, object], key: str) -> str | None:
    item = value.get(key)
    if item is None:
        return None
    if not isinstance(item, str):
        raise ValueError("invalid UI body")
    return item


def _query(value: str) -> dict[str, str]:
    parsed = parse_qs(value, keep_blank_values=True, strict_parsing=True)
    if any(len(items) != 1 or not items[0] for items in parsed.values()):
        raise ValueError("invalid UI query")
    return {key: items[0] for key, items in parsed.items()}


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _json(status: int, value: dict[str, object]) -> Phase1UiResponse:
    return Phase1UiResponse(
        status=status,
        body=canonical_json_bytes(value),
        headers=(
            ("Content-Type", "application/json"),
            ("Cache-Control", "no-store"),
            ("X-Content-Type-Options", "nosniff"),
        ),
    )


def _text(status: int, value: str, *, allow: str | None = None) -> Phase1UiResponse:
    headers = [("Content-Type", "text/plain; charset=utf-8"), ("Cache-Control", "no-store")]
    if allow is not None:
        headers.append(("Allow", allow))
    return Phase1UiResponse(status=status, body=value.encode("utf-8"), headers=tuple(headers))


def _html(body: bytes) -> Phase1UiResponse:
    return Phase1UiResponse(
        status=200,
        body=body,
        headers=(
            ("Content-Type", "text/html; charset=utf-8"),
            (
                "Content-Security-Policy",
                "default-src 'none'; base-uri 'none'; form-action 'none'; "
                "frame-ancestors 'none'",
            ),
            ("Cache-Control", "no-store"),
            ("X-Content-Type-Options", "nosniff"),
        ),
    )
