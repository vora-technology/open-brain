from __future__ import annotations

import hmac
import json
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from typing import cast

import pytest

from open_brain.capture.http import (
    BODY_LIMIT_BYTES,
    REQUEST_TIMEOUT_SECONDS,
    HttpRequest,
    RequestReadTimeout,
    ShareHttpHandler,
)
from open_brain.capture.models import CaptureWorkItem
from open_brain.capture.queue import QueueImmutableConflictError
from open_brain.core.ports import PutDisposition, PutResult

FIXED_TIME = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)


class FakeQueue:
    def __init__(self, disposition: PutDisposition = PutDisposition.CREATED) -> None:
        self.disposition = disposition
        self.items: list[CaptureWorkItem] = []
        self.failure: Exception | None = None

    def enqueue(self, item: CaptureWorkItem, *, item_id: str, payload_digest: str) -> PutResult:
        if self.failure is not None:
            raise self.failure
        self.items.append(item)
        return PutResult(self.disposition, item_id, payload_digest)


class RecordingBodyReader:
    def __init__(self, body: bytes) -> None:
        self.body = body
        self.calls: list[tuple[int, float]] = []
        self.failure: Exception | None = None

    def __call__(self, maximum_bytes: int, timeout_seconds: float) -> bytes:
        self.calls.append((maximum_bytes, timeout_seconds))
        if self.failure is not None:
            raise self.failure
        return self.body


def _marker(kind: str) -> str:
    return "synthetic" + "-" + kind + "-marker"


def _bearer() -> str:
    return "bearer" + "-" + "token"


def _payload(**overrides: object) -> bytes:
    value: dict[str, object] = {
        "url": "https://example.test/shared",
        "why": "Keep this reference",
        "text": "Shared note",
    }
    value.update(overrides)
    return json.dumps(value, separators=(",", ":")).encode("utf-8")


def _request(
    body: bytes,
    *,
    authorization: str | None = None,
    path: str = "/share",
    content_type: str = "application/json",
    length: str | None = None,
    extra_headers: tuple[tuple[str, str], ...] = (),
) -> HttpRequest:
    headers: list[tuple[str, str]] = [
        ("Content-Length", str(len(body)) if length is None else length),
        ("Content-Type", content_type),
    ]
    if authorization is not None:
        headers.append(("Authorization", authorization))
    headers.extend(extra_headers)
    return HttpRequest(method="POST", path=path, headers=tuple(headers))


def _handler(
    reader: RecordingBodyReader,
    queue: FakeQueue | None = None,
    *,
    clock: Callable[[], datetime] = lambda: FIXED_TIME,
    expected_bearer_token: str | None = None,
) -> tuple[ShareHttpHandler, FakeQueue]:
    actual_queue = queue or FakeQueue()
    token = _bearer() if expected_bearer_token is None else expected_bearer_token
    return (
        ShareHttpHandler(
            expected_bearer_token=token,
            queue=actual_queue,
            clock=clock,
            body_reader=reader,
        ),
        actual_queue,
    )


def _response_body(response_body: bytes) -> dict[str, object]:
    return cast(dict[str, object], json.loads(response_body))


def test_h01_bearer_authentication_is_constant_time_and_all_invalid_values_are_identical(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: list[tuple[bytes, bytes]] = []
    original = hmac.compare_digest

    def compare(left: bytes, right: bytes) -> bool:
        observed.append((left, right))
        return bool(original(left, right))

    monkeypatch.setattr(hmac, "compare_digest", compare)
    body = _payload()
    reader = RecordingBodyReader(body)
    handler, queue = _handler(reader)

    valid = handler.handle(_request(body, authorization="Bearer " + _bearer()))
    invalid = [
        handler.handle(_request(body)),
        handler.handle(_request(body, authorization="Bearer ")),
        handler.handle(_request(body, authorization="Token " + _bearer())),
        handler.handle(_request(body, authorization="Bearer " + _bearer() + "-wrong")),
        handler.handle(_request(body, authorization="Bearer non\u00e4scii")),
    ]

    assert valid.status == 202
    expected = _bearer().encode("ascii")
    assert observed == [(expected, expected), (b"bearer-token-wrong", expected)]
    assert {(response.status, response.body) for response in invalid} == {
        (401, b'{"code":"unauthorized"}')
    }
    assert len(queue.items) == 1


def test_h02_blank_expected_bearer_refuses_handler_composition() -> None:
    with pytest.raises(ValueError):
        ShareHttpHandler(
            expected_bearer_token=" ",
            queue=FakeQueue(),
            clock=lambda: FIXED_TIME,
            body_reader=RecordingBodyReader(_payload()),
        )


@pytest.mark.parametrize("length", [None, "", "-1", "not-a-number", "100001"])
def test_h03_invalid_or_oversized_content_length_never_reads_or_queues(length: str | None) -> None:
    body = _payload()
    reader = RecordingBodyReader(body)
    handler, queue = _handler(reader)
    request = _request(body, authorization="Bearer " + _bearer(), length=length)
    if length is None:
        request = HttpRequest(
            method=request.method,
            path=request.path,
            headers=tuple(header for header in request.headers if header[0] != "Content-Length"),
        )

    response = handler.handle(request)

    assert response.status == 413
    assert reader.calls == []
    assert queue.items == []


def test_h03_duplicate_length_and_exact_or_one_over_body_and_field_bounds_are_closed() -> None:
    exact_body = _payload(text="x" * (BODY_LIMIT_BYTES - len(_payload(text=""))))
    one_over_body = exact_body + b" "
    assert len(exact_body) == BODY_LIMIT_BYTES
    reader = RecordingBodyReader(exact_body)
    handler, queue = _handler(reader)

    exact = handler.handle(_request(exact_body, authorization="Bearer " + _bearer()))
    too_large = handler.handle(_request(one_over_body, authorization="Bearer " + _bearer()))
    duplicate_length = handler.handle(
        _request(
            _payload(),
            authorization="Bearer " + _bearer(),
            extra_headers=(("Content-Length", str(len(_payload()))),),
        )
    )
    exact_url = "https://example.test/" + "x" * (2_048 - len("https://example.test/"))
    field_cases = [
        _payload(url=exact_url),
        _payload(url=exact_url + "x"),
        _payload(why="x" * 280),
        _payload(why="x" * 281),
    ]
    responses = []
    for value in field_cases:
        field_handler, field_queue = _handler(RecordingBodyReader(value))
        responses.append(field_handler.handle(_request(value, authorization="Bearer " + _bearer())))
        queue.items.extend(field_queue.items)

    assert exact.status == 202
    assert too_large.status == 413
    assert duplicate_length.status == 413
    assert [response.status for response in responses] == [202, 413, 202, 400]
    assert len(queue.items) == 3
    assert reader.calls[0] == (BODY_LIMIT_BYTES, REQUEST_TIMEOUT_SECONDS)


@pytest.mark.parametrize(
    ("http_request", "status", "body"),
    [
        (
            _request(_payload(), authorization="Bearer bearer-token", path="/other"),
            400,
            b'{"code":"invalid_request"}',
        ),
        (
            _request(_payload(), authorization="Bearer bearer-token", content_type="text/plain"),
            415,
            b'{"code":"unsupported_media_type"}',
        ),
        (_request(b"", authorization="Bearer bearer-token"), 400, b'{"code":"invalid_request"}'),
        (_request(b"{", authorization="Bearer bearer-token"), 400, b'{"code":"invalid_request"}'),
        (_request(b"[]", authorization="Bearer bearer-token"), 400, b'{"code":"invalid_request"}'),
        (
            _request(_payload(extra="no"), authorization="Bearer bearer-token"),
            400,
            b'{"code":"invalid_request"}',
        ),
        (
            _request(_payload(url="ftp://example.test/file"), authorization="Bearer bearer-token"),
            400,
            b'{"code":"invalid_request"}',
        ),
        (
            _request(_payload(why="line\none"), authorization="Bearer bearer-token"),
            400,
            b'{"code":"invalid_request"}',
        ),
    ],
)
def test_h04_only_the_closed_json_contract_is_accepted(
    http_request: HttpRequest, status: int, body: bytes
) -> None:
    reader = RecordingBodyReader(b"ignored")
    handler, queue = _handler(reader)

    response = handler.handle(http_request)

    assert (response.status, response.body) == (status, body)
    assert queue.items == []


def test_h05_slow_body_reader_returns_closed_timeout_without_enqueue() -> None:
    reader = RecordingBodyReader(_payload())
    reader.failure = RequestReadTimeout()
    handler, queue = _handler(reader)

    response = handler.handle(_request(_payload(), authorization="Bearer " + _bearer()))

    assert (response.status, response.body) == (408, b'{"code":"request_timeout"}')
    assert reader.calls == [(BODY_LIMIT_BYTES, REQUEST_TIMEOUT_SECONDS)]
    assert queue.items == []


def test_h06_failures_do_not_expose_body_or_bearer_markers(
    caplog: pytest.LogCaptureFixture,
) -> None:
    body_marker = _marker("body")
    bearer_marker = _marker("bearer")
    reader = RecordingBodyReader(_payload(text=body_marker))
    queue = FakeQueue()
    queue.failure = RuntimeError(body_marker + bearer_marker)
    handler, _ = _handler(reader, queue, expected_bearer_token=bearer_marker)
    auth_handler, _ = _handler(RecordingBodyReader(reader.body))
    parser_handler, _ = _handler(RecordingBodyReader(b"{"), expected_bearer_token=bearer_marker)

    with caplog.at_level(logging.DEBUG):
        responses = [
            auth_handler.handle(_request(reader.body, authorization="Bearer " + bearer_marker)),
            parser_handler.handle(_request(b"{", authorization="Bearer " + bearer_marker)),
            handler.handle(_request(reader.body, authorization="Bearer " + bearer_marker)),
        ]

    exposed = (
        b"".join(response.body for response in responses)
        + "\n".join(record.getMessage() for record in caplog.records).encode()
    )
    assert [(response.status, response.body) for response in responses] == [
        (401, b'{"code":"unauthorized"}'),
        (400, b'{"code":"invalid_request"}'),
        (500, b'{"code":"queue_unavailable"}'),
    ]
    assert body_marker.encode() not in exposed
    assert bearer_marker.encode() not in exposed


def test_h07_ios_shaped_request_queues_once_with_owner_reason_and_duplicate_response() -> None:
    body = _payload(
        url="https://www.youtube.com/watch?v=synthetic123",
        why="Watch this before the planning meeting",
        text="A teammate shared this from iOS.",
        privacy="work",
    )
    reader = RecordingBodyReader(body)
    handler, queue = _handler(reader)
    request = _request(body, authorization="Bearer " + _bearer())

    created = handler.handle(request)
    queue.disposition = PutDisposition.DUPLICATE
    duplicate = handler.handle(request)

    created_body = _response_body(created.body)
    assert created.status == 202
    assert created_body == {
        "capture_id": str(queue.items[0].envelope.capture_id),
        "pipeline": "youtube",
        "duplicate": False,
        "status": "queued",
    }
    assert queue.items[0].envelope.capture_why == "Watch this before the planning meeting"
    assert queue.items[0].envelope.captured_at == FIXED_TIME
    assert queue.items[0].envelope.privacy_decision.reason.value == "policy_work"
    assert queue.items[0].envelope.privacy_decision.authority.external_egress is False
    assert duplicate.status == 202
    assert _response_body(duplicate.body) == {
        **created_body,
        "duplicate": True,
        "status": "duplicate",
    }
    assert len(queue.items) == 2


def test_queue_conflict_and_queue_failure_are_closed() -> None:
    body = _payload()
    reader = RecordingBodyReader(body)
    queue = FakeQueue()
    handler, _ = _handler(reader, queue)
    queue.failure = QueueImmutableConflictError("synthetic")

    conflict = handler.handle(_request(body, authorization="Bearer " + _bearer()))
    queue.failure = RuntimeError("synthetic")
    unavailable = handler.handle(_request(body, authorization="Bearer " + _bearer()))

    assert (conflict.status, conflict.body) == (409, b'{"code":"immutable_conflict"}')
    assert (unavailable.status, unavailable.body) == (500, b'{"code":"queue_unavailable"}')
