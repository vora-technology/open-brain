import inspect
from collections.abc import Mapping, Sequence
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from hashlib import sha256

import pytest
from open_brain_engine.core import ports
from open_brain_engine.core.ids import CaptureId, ReviewId, canonical_json_bytes
from open_brain_engine.core.models import (
    Authority,
    Intent,
    PrivacyDecision,
    PrivacyReason,
    PrivacyTier,
    RawCapture,
    ValidationError,
)
from open_brain_engine.core.policy import (
    BoundaryErrorCode,
    invoke_provider,
    invoke_staged_executor,
)


def _privacy() -> PrivacyDecision:
    return PrivacyDecision.create(
        tier=PrivacyTier.WORK,
        reason=PrivacyReason.POLICY_WORK,
        policy_version="privacy-v1",
        authority=Authority(cloud=False, external_egress=False),
    )


def _authorized_privacy(*, egress: bool = False) -> PrivacyDecision:
    return PrivacyDecision.create(
        tier=PrivacyTier.PUBLIC,
        reason=PrivacyReason.POLICY_PUBLIC,
        policy_version="privacy-v1",
        authority=Authority(cloud=True, external_egress=egress),
    )


def _digest(value: object) -> str:
    return sha256(canonical_json_bytes(value)).hexdigest()


def _receipt(output_digest: str) -> ports.RedactionReceipt:
    return ports.RedactionReceipt.create(
        source_digest_sha256=_digest({"source": "synthetic"}),
        output_digest_sha256=output_digest,
        policy_version="redaction-v1",
        findings=(
            ports.RedactionFinding.create(
                category=ports.RedactionFindingCategory.PRIVATE_PATH,
                count=1,
            ),
        ),
    )


def test_phase2_ports_expose_required_contracts() -> None:
    required = {
        "RawStore",
        "EventRecord",
        "EventStore",
        "RedactionReceipt",
        "RedactedMarkdownDocument",
        "CaptureQueue",
        "ReviewStore",
        "LedgerStore",
        "MarkdownSink",
        "Provider",
        "Clock",
        "IdGenerator",
        "OutboundFetcher",
        "StagedAssetExecutor",
    }
    assert {name for name in required if hasattr(ports, name)} == required
    assert "execute" in dict(inspect.getmembers(ports.StagedAssetExecutor))
    assert "fetch" in dict(inspect.getmembers(ports.OutboundFetcher))


PORT_METHOD_SIGNATURES = {
    ports.RawStore: {
        "get": (("self", "capture_id"), ()),
        "put_if_absent": (("self", "capture"), ()),
    },
    ports.EventStore: {
        "append": (("self", "record"), ()),
        "read": (("self", "stream_id", "after_sequence"), ("after_sequence",)),
    },
    ports.CaptureQueue: {
        "enqueue": (("self", "item", "item_id", "payload_digest"), ("item_id", "payload_digest")),
        "claim": (("self", "worker_id", "now"), ("worker_id", "now")),
        "acknowledge": (("self", "lease", "completed_at"), ("completed_at",)),
        "retry": (("self", "lease", "available_at", "error_code"), ("available_at", "error_code")),
        "quarantine": (("self", "lease", "at", "error_code"), ("at", "error_code")),
    },
    ports.ReviewStore: {
        "get": (("self", "review_id"), ()),
        "create_if_absent": (("self", "review", "payload_digest"), ("payload_digest",)),
        "decide": (("self", "command"), ()),
        "pending_outputs": (("self", "limit"), ("limit",)),
        "mark_output_delivered": (("self", "output_id", "delivered_at"), ("delivered_at",)),
    },
    ports.LedgerStore: {
        "get": (("self", "record_id"), ()),
        "append_if_absent": (
            ("self", "record", "record_id", "payload_digest"),
            ("record_id", "payload_digest"),
        ),
    },
    ports.MarkdownSink: {"write_if_absent": (("self", "document"), ())},
    ports.Provider: {"complete": (("self", "request", "privacy"), ("privacy",))},
    ports.Clock: {"now": (("self",), ())},
    ports.IdGenerator: {
        "capture_id": (("self", "identity"), ()),
        "review_id": (("self", "capture_id", "intent"), ()),
        "event_id": (("self", "stream_id", "event_type", "payload_digest"), ()),
        "decision_id": (("self",), ()),
    },
    ports.OutboundFetcher: {"fetch": (("self", "request", "privacy"), ("privacy",))},
    ports.StagedAssetExecutor: {"execute": (("self", "request", "privacy"), ("privacy",))},
}


@pytest.mark.parametrize(("protocol", "methods"), PORT_METHOD_SIGNATURES.items())
def test_each_phase2_port_method_has_exact_signature(
    protocol: type[object],
    methods: dict[str, tuple[tuple[str, ...], tuple[str, ...]]],
) -> None:
    public_methods = {
        name
        for name, member in inspect.getmembers(protocol, inspect.isfunction)
        if not name.startswith("__")
    }
    assert public_methods == set(methods)

    for name, (parameter_names, keyword_only_names) in methods.items():
        parameters = inspect.signature(getattr(protocol, name)).parameters
        assert tuple(parameters) == parameter_names
        assert (
            tuple(
                parameter.name
                for parameter in parameters.values()
                if parameter.kind is inspect.Parameter.KEYWORD_ONLY
            )
            == keyword_only_names
        )


def _put_result() -> ports.PutResult:
    return ports.PutResult(ports.PutDisposition.CREATED, "synthetic", "a" * 64)


class _RawStoreFake:
    def get(self, capture_id: CaptureId) -> RawCapture | None:
        return None

    def put_if_absent(self, capture: RawCapture) -> ports.PutResult:
        return _put_result()


class _EventStoreFake:
    def append(self, record: ports.EventRecord) -> ports.PutResult:
        return _put_result()

    def read(self, stream_id: CaptureId, *, after_sequence: int = 0) -> Sequence[ports.EventRecord]:
        return ()


class _CaptureQueueFake:
    def enqueue(self, item: object, *, item_id: str, payload_digest: str) -> ports.PutResult:
        return _put_result()

    def claim(self, *, worker_id: str, now: datetime) -> object | None:
        return None

    def acknowledge(self, lease: object, *, completed_at: datetime) -> None:
        return None

    def retry(self, lease: object, *, available_at: datetime, error_code: str) -> None:
        return None

    def quarantine(self, lease: object, *, at: datetime, error_code: str) -> None:
        return None


class _ReviewStoreFake:
    def get(self, review_id: ReviewId) -> object | None:
        return None

    def create_if_absent(self, review: object, *, payload_digest: str) -> ports.PutResult:
        return _put_result()

    def decide(self, command: object) -> object:
        return object()

    def pending_outputs(self, *, limit: int) -> Sequence[object]:
        return ()

    def mark_output_delivered(self, output_id: str, *, delivered_at: datetime) -> None:
        return None


class _LedgerStoreFake:
    def get(self, record_id: str) -> object | None:
        return None

    def append_if_absent(
        self, record: object, *, record_id: str, payload_digest: str
    ) -> ports.PutResult:
        return _put_result()


class _MarkdownSinkFake:
    def write_if_absent(self, document: ports.RedactedMarkdownDocument) -> ports.PutResult:
        return _put_result()


class _ClockFake:
    def now(self) -> datetime:
        return datetime(2026, 8, 13, tzinfo=UTC)


class _IdGeneratorFake:
    def capture_id(self, identity: Mapping[str, object]) -> CaptureId:
        return CaptureId("cap_" + "a" * 64)

    def review_id(self, capture_id: CaptureId, intent: Intent) -> ReviewId:
        return ReviewId("review_" + "b" * 64)

    def event_id(self, stream_id: str, event_type: str, payload_digest: str) -> str:
        return "event.synthetic"

    def decision_id(self) -> str:
        return "decision.synthetic"


class _OutboundFetcherFake:
    def fetch(
        self, request: ports.FetchRequest, *, privacy: PrivacyDecision
    ) -> ports.FetchResponse:
        return ports.FetchResponse(
            final_url="https://example.invalid/",
            status=200,
            media_type="text/plain",
            body=b"synthetic",
        )


def test_minimal_fakes_structurally_satisfy_every_phase2_port() -> None:
    raw_store: ports.RawStore = _RawStoreFake()
    event_store: ports.EventStore = _EventStoreFake()
    queue: ports.CaptureQueue[object, object] = _CaptureQueueFake()
    review_store: ports.ReviewStore[object, object, object] = _ReviewStoreFake()
    ledger_store: ports.LedgerStore[object] = _LedgerStoreFake()
    markdown_sink: ports.MarkdownSink = _MarkdownSinkFake()
    provider: ports.Provider = _ProviderSpy()
    clock: ports.Clock = _ClockFake()
    id_generator: ports.IdGenerator = _IdGeneratorFake()
    fetcher: ports.OutboundFetcher = _OutboundFetcherFake()
    executor: ports.StagedAssetExecutor = _ExecutorSpy()

    implementations = (
        raw_store,
        event_store,
        queue,
        review_store,
        ledger_store,
        markdown_sink,
        provider,
        clock,
        id_generator,
        fetcher,
        executor,
    )
    assert all(implementation is not None for implementation in implementations)


def test_redaction_receipt_is_immutable_json_compatible_and_strict() -> None:
    receipt = _receipt("a" * 64)
    restored = ports.RedactionReceipt.from_dict(receipt.to_dict())

    assert restored == receipt
    assert restored.to_dict() == {
        "source_digest_sha256": _digest({"source": "synthetic"}),
        "output_digest_sha256": "a" * 64,
        "policy_version": "redaction-v1",
        "findings": [{"category": "private_path", "count": 1}],
    }
    with pytest.raises((FrozenInstanceError, AttributeError)):
        receipt.policy_version = "changed"  # type: ignore[misc]
    with pytest.raises(ValidationError):
        ports.RedactionReceipt.from_dict({**receipt.to_dict(), "matched_text": "forbidden"})
    with pytest.raises(ValidationError):
        ports.RedactionFinding.create(category="not_closed", count=1)


def test_event_record_validates_receipt_digest_and_round_trips() -> None:
    payload = {"kind": "capture.redacted", "nested": {"count": 2}, "labels": ["safe"]}
    receipt = _receipt(ports.EventRecord.output_digest_sha256(payload))
    record = ports.EventRecord.create(
        event_id="event_001",
        stream_id=CaptureId("cap_" + "a" * 64),
        event_type="capture.redacted",
        occurred_at=datetime(2026, 8, 13, 12, 30, tzinfo=UTC),
        privacy_decision=_privacy(),
        payload=payload,
        redaction_receipt=receipt,
    )

    restored = ports.EventRecord.from_dict(record.to_dict())
    assert restored.to_dict() == record.to_dict()
    assert restored.canonical_bytes() == record.canonical_bytes()
    assert restored.privacy_decision is not record.privacy_decision
    assert restored.privacy_decision == record.privacy_decision
    assert restored.redaction_receipt.output_digest_sha256 == _digest(payload)

    with pytest.raises(TypeError):
        record.payload["new"] = "value"  # type: ignore[index]
    with pytest.raises(ValidationError):
        ports.EventRecord.create(
            event_id="event_001",
            stream_id=CaptureId("cap_" + "a" * 64),
            event_type="capture.redacted",
            occurred_at=datetime(2026, 8, 13, 12, 30, tzinfo=UTC),
            privacy_decision=_privacy(),
            payload={"changed": True},
            redaction_receipt=receipt,
        )


def test_redacted_markdown_validates_receipt_digest_and_round_trips() -> None:
    frontmatter = {"capture_id": "cap_" + "a" * 64, "labels": ["safe"]}
    body = "Redacted synthetic body."
    output_digest = ports.RedactedMarkdownDocument.output_digest_sha256(frontmatter, body)
    document = ports.RedactedMarkdownDocument.create(
        document_id="intent_" + "b" * 64,
        logical_key="intent_" + "b" * 64,
        privacy_decision=_privacy(),
        frontmatter=frontmatter,
        body=body,
        redaction_receipt=_receipt(output_digest),
    )

    restored = ports.RedactedMarkdownDocument.from_dict(document.to_dict())
    assert restored.to_dict() == document.to_dict()
    assert restored.canonical_bytes() == document.canonical_bytes()
    assert restored.privacy_decision == document.privacy_decision

    with pytest.raises(TypeError):
        document.frontmatter["new"] = "value"  # type: ignore[index]
    with pytest.raises(ValidationError):
        ports.RedactedMarkdownDocument.create(
            document_id="intent_" + "b" * 64,
            logical_key="../derived-from-content",
            privacy_decision=_privacy(),
            frontmatter=frontmatter,
            body=body,
            redaction_receipt=_receipt(output_digest),
        )
    with pytest.raises(ValidationError):
        ports.RedactedMarkdownDocument.create(
            document_id="intent_" + "b" * 64,
            logical_key="intent_" + "b" * 64,
            privacy_decision=_privacy(),
            frontmatter=frontmatter,
            body="Changed body",
            redaction_receipt=_receipt(output_digest),
        )


def test_raw_store_remains_private_canonical_capture_persistence() -> None:
    methods = dict(inspect.getmembers(ports.RawStore, inspect.isfunction))
    assert {name for name in methods if not name.startswith("__")} == {"get", "put_if_absent"}
    put_signature = inspect.signature(ports.RawStore.put_if_absent)
    assert list(put_signature.parameters) == ["self", "capture"]
    assert "redaction" not in str(put_signature).lower()


def test_event_and_markdown_ports_accept_only_concrete_redacted_records() -> None:
    event_signature = inspect.signature(ports.EventStore.append)
    markdown_signature = inspect.signature(ports.MarkdownSink.write_if_absent)
    assert list(event_signature.parameters) == ["self", "record"]
    assert event_signature.parameters["record"].annotation == "EventRecord"
    assert markdown_signature.parameters["document"].annotation == "RedactedMarkdownDocument"


class _ProviderSpy:
    def __init__(self, *, failure: Exception | None = None) -> None:
        self.calls = 0
        self.failure = failure
        self.requests: list[ports.TextModelRequest] = []
        self.privacies: list[PrivacyDecision] = []

    def complete(
        self, request: ports.TextModelRequest, *, privacy: PrivacyDecision
    ) -> ports.TextModelResult:
        self.calls += 1
        self.requests.append(request)
        self.privacies.append(privacy)
        if self.failure is not None:
            raise self.failure
        return ports.TextModelResult(text="safe", provider_name="synthetic")


class _ExecutorSpy:
    def __init__(self, *, failure: Exception | None = None) -> None:
        self.calls = 0
        self.failure = failure
        self.requests: list[ports.StagedExecutionRequest] = []
        self.privacies: list[PrivacyDecision] = []

    def execute(
        self, request: ports.StagedExecutionRequest, *, privacy: PrivacyDecision
    ) -> ports.StagedExecutionResult:
        self.calls += 1
        self.requests.append(request)
        self.privacies.append(privacy)
        if self.failure is not None:
            raise self.failure
        return ports.StagedExecutionResult(text="safe", produced_assets=())


def _provider_request() -> ports.TextModelRequest:
    return ports.TextModelRequest(
        request_id="request.provider-001",
        purpose="synthetic",
        prompt="Synthetic prompt",
        timeout_seconds=1.0,
        max_output_bytes=100,
    )


def _execution_request(*, hosts: tuple[str, ...] = ()) -> ports.StagedExecutionRequest:
    return ports.StagedExecutionRequest(
        request_id="request.executor-001",
        purpose="synthetic",
        prompt="Synthetic prompt",
        readable_assets=(),
        allowed_network_hosts=hosts,
        timeout_seconds=1.0,
        max_output_bytes=100,
    )


def test_provider_invocation_requires_cloud_authority_before_call() -> None:
    provider = _ProviderSpy()

    result = invoke_provider(provider, _provider_request(), privacy=_privacy())

    assert provider.calls == 0
    assert result.value is None
    assert result.error_code is BoundaryErrorCode.CLOUD_AUTHORITY_REQUIRED


def test_provider_invocation_passes_bounded_request_and_privacy() -> None:
    provider = _ProviderSpy()
    request = _provider_request()
    privacy = _authorized_privacy()

    result = invoke_provider(provider, request, privacy=privacy)

    assert result.value == ports.TextModelResult(text="safe", provider_name="synthetic")
    assert result.error_code is None
    assert provider.requests == [request]
    assert provider.privacies == [privacy]


def test_staged_executor_authorizes_egress_and_network_hosts_before_call() -> None:
    requested_host = "requested.example.invalid"
    executor = _ExecutorSpy()
    allowed_request = _execution_request(hosts=(requested_host,))
    allowed_privacy = _authorized_privacy(egress=True)

    no_cloud = invoke_staged_executor(
        executor,
        _execution_request(hosts=(requested_host,)),
        privacy=_privacy(),
        permitted_network_hosts=(requested_host,),
    )
    no_egress = invoke_staged_executor(
        executor,
        _execution_request(hosts=(requested_host,)),
        privacy=_authorized_privacy(),
        permitted_network_hosts=(requested_host,),
    )
    disallowed_host = invoke_staged_executor(
        executor,
        _execution_request(hosts=(requested_host,)),
        privacy=_authorized_privacy(egress=True),
        permitted_network_hosts=("allowed.example.invalid",),
    )
    allowed = invoke_staged_executor(
        executor,
        allowed_request,
        privacy=allowed_privacy,
        permitted_network_hosts=(requested_host,),
    )

    assert no_cloud.error_code is BoundaryErrorCode.CLOUD_AUTHORITY_REQUIRED
    assert no_egress.error_code is BoundaryErrorCode.EGRESS_AUTHORITY_REQUIRED
    assert disallowed_host.error_code is BoundaryErrorCode.NETWORK_HOST_DENIED
    assert allowed.error_code is None
    assert allowed.value == ports.StagedExecutionResult(text="safe", produced_assets=())
    assert executor.calls == 1
    assert executor.requests == [allowed_request]
    assert executor.privacies == [allowed_privacy]


@pytest.mark.parametrize("boundary", ["provider", "executor"])
def test_implementation_failures_expose_only_closed_redacted_error_code(boundary: str) -> None:
    sensitive_parts = (
        "cred" + "ential-value",
        "/synthetic/" + "private/location",
        "private-" + "host.invalid",
        ".".join(("10", "20", "30", "40")),
    )
    failure = RuntimeError(" | ".join(sensitive_parts))

    if boundary == "provider":
        provider = _ProviderSpy(failure=failure)
        provider_result = invoke_provider(
            provider,
            _provider_request(),
            privacy=_authorized_privacy(),
        )
        exposed = repr(provider_result)
        value_is_none = provider_result.value is None
        error_code = provider_result.error_code
    else:
        executor = _ExecutorSpy(failure=failure)
        executor_result = invoke_staged_executor(
            executor,
            _execution_request(),
            privacy=_authorized_privacy(),
            permitted_network_hosts=(),
        )
        exposed = repr(executor_result)
        value_is_none = executor_result.value is None
        error_code = executor_result.error_code

    assert value_is_none
    assert error_code is BoundaryErrorCode.IMPLEMENTATION_FAILURE
    assert all(part not in exposed for part in sensitive_parts)
