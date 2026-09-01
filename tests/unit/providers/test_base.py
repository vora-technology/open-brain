import sys
from dataclasses import dataclass

import pytest

from open_brain.core.models import (
    Authority,
    PrivacyDecision,
    PrivacyReason,
    PrivacyTier,
    ValidationError,
)
from open_brain.core.policy import BoundaryErrorCode
from open_brain.core.ports import TextModelRequest, TextModelResult
from open_brain.providers.base import (
    EnrichmentState,
    NoneProvider,
    ProviderFailure,
    ProviderService,
    lazy_cloud_factory,
    unavailable_cloud_factory,
)


def _request(*, max_output_bytes: int = 64) -> TextModelRequest:
    return TextModelRequest.create(
        request_id="request.provider-001",
        purpose="synthetic",
        prompt="Synthetic prompt",
        timeout_seconds=1.0,
        max_output_bytes=max_output_bytes,
    )


def _local_privacy() -> PrivacyDecision:
    return PrivacyDecision.create(
        tier=PrivacyTier.PERSONAL,
        reason=PrivacyReason.PERSONAL_LOCAL_ONLY,
        policy_version="privacy-v1",
        authority=Authority(cloud=False, external_egress=False),
    )


def _cloud_privacy() -> PrivacyDecision:
    return PrivacyDecision.create(
        tier=PrivacyTier.PERSONAL,
        reason=PrivacyReason.PERSONAL_CONFIRMED,
        policy_version="privacy-v1",
        authority=Authority(cloud=True, external_egress=False),
        confirmation_ref="confirmation.synthetic-001",
    )


def test_none_provider_is_inspectably_pending_without_constructing_an_adapter() -> None:
    provider = NoneProvider()

    assert provider.enrichment_state() is EnrichmentState.PENDING


@dataclass
class _ProviderFake:
    result: TextModelResult | Exception
    calls: int = 0

    def complete(self, request: TextModelRequest, *, privacy: PrivacyDecision) -> TextModelResult:
        self.calls += 1
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def test_none_provider_service_constructs_no_adapter_or_credential(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    monkeypatch.delitem(sys.modules, "open_brain.providers.optional_cloud", raising=False)

    def local_factory() -> _ProviderFake:
        calls.append("local")
        return _ProviderFake(TextModelResult(text="local", provider_name="local"))

    def cloud_factory(credential: str) -> _ProviderFake:
        assert credential == "synthetic"
        calls.append("cloud")
        return _ProviderFake(TextModelResult(text="cloud", provider_name="cloud"))

    def resolve_secret() -> str:
        calls.append("secret")
        return "synthetic"

    service = ProviderService(
        provider_name="none",
        cloud_enabled=False,
        local_factory=local_factory,
        cloud_factory=cloud_factory,
        resolve_cloud_secret=resolve_secret,
    )

    result = service.complete(_request(), privacy=_local_privacy())

    assert result.value is None
    assert result.error_code is BoundaryErrorCode.LOCAL_UNAVAILABLE
    assert calls == []
    assert "open_brain.providers.optional_cloud" not in sys.modules


def test_text_model_values_are_bounded_canonical_and_immutable() -> None:
    request = _request()
    restored = TextModelRequest.from_canonical_bytes(request.canonical_bytes())

    assert restored == request
    assert TextModelResult.from_dict({"text": "safe", "provider_name": "local"}) == TextModelResult(
        text="safe", provider_name="local"
    )
    with pytest.raises(ValidationError):
        TextModelRequest.create(
            request_id="",
            purpose="synthetic",
            prompt="Synthetic prompt",
            timeout_seconds=0.0,
            max_output_bytes=1,
        )


def test_local_selection_never_constructs_cloud_for_local_only_decision() -> None:
    local = _ProviderFake(TextModelResult(text="safe", provider_name="local"))
    cloud_factory_calls = 0
    secret_calls = 0

    def cloud_factory(credential: str) -> _ProviderFake:
        nonlocal cloud_factory_calls
        assert credential == "synthetic"
        cloud_factory_calls += 1
        return _ProviderFake(TextModelResult(text="cloud", provider_name="cloud"))

    def resolve_secret() -> str | None:
        nonlocal secret_calls
        secret_calls += 1
        return "synthetic"

    service = ProviderService(
        provider_name="local",
        cloud_enabled=True,
        local_factory=lambda: local,
        cloud_factory=cloud_factory,
        resolve_cloud_secret=resolve_secret,
    )

    result = service.complete(_request(), privacy=_local_privacy())

    assert result.value == TextModelResult(text="safe", provider_name="local")
    assert result.error_code is None
    assert local.calls == 1
    assert cloud_factory_calls == 0
    assert secret_calls == 0


def test_non_decision_and_secret_decision_are_blocked_before_cloud_construction() -> None:
    cloud_factory_calls = 0
    secret_calls = 0

    def cloud_factory(credential: str) -> _ProviderFake:
        nonlocal cloud_factory_calls
        assert credential == "synthetic"
        cloud_factory_calls += 1
        return _ProviderFake(TextModelResult(text="cloud", provider_name="cloud"))

    def resolve_secret() -> str | None:
        nonlocal secret_calls
        secret_calls += 1
        return "synthetic"

    service = ProviderService(
        provider_name="cloud",
        cloud_enabled=True,
        local_factory=lambda: _ProviderFake(TextModelResult(text="local", provider_name="local")),
        cloud_factory=cloud_factory,
        resolve_cloud_secret=resolve_secret,
    )

    with pytest.raises(ValidationError):
        service.complete(_request(), privacy=True)  # type: ignore[arg-type]

    secret_decision = PrivacyDecision.create(
        tier=PrivacyTier.SECRET,
        reason=PrivacyReason.SECRET_DETECTED,
        policy_version="privacy-v1",
        authority=Authority(cloud=False, external_egress=False),
    )
    result = service.complete(_request(), privacy=secret_decision)

    assert result.error_code is BoundaryErrorCode.CLOUD_AUTHORITY_REQUIRED
    assert cloud_factory_calls == 0
    assert secret_calls == 0


def test_cloud_extra_is_lazy_and_missing_extra_is_closed() -> None:
    service = ProviderService(
        provider_name="cloud",
        cloud_enabled=True,
        local_factory=lambda: _ProviderFake(TextModelResult(text="local", provider_name="local")),
        cloud_factory=unavailable_cloud_factory,
        resolve_cloud_secret=lambda: "synthetic",
    )

    result = service.complete(_request(), privacy=_cloud_privacy())

    assert result.value is None
    assert result.error_code is BoundaryErrorCode.OPTIONAL_EXTRA_UNAVAILABLE


def test_lazy_cloud_factory_passes_only_credential_and_configured_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: list[tuple[str, str]] = []
    provider = _ProviderFake(TextModelResult(text="cloud", provider_name="cloud"))

    def create_provider(credential: str, *, model: str) -> _ProviderFake:
        observed.append((credential, model))
        return provider

    result = lazy_cloud_factory(
        create_provider,
        model="synthetic-model",
    )("synthetic-credential")

    assert result is provider
    assert observed == [("synthetic-credential", "synthetic-model")]


def test_missing_cloud_credential_stops_before_the_selected_provider_call() -> None:
    cloud = _ProviderFake(TextModelResult(text="cloud", provider_name="cloud"))

    result = ProviderService(
        provider_name="cloud",
        cloud_enabled=True,
        local_factory=lambda: _ProviderFake(TextModelResult(text="local", provider_name="local")),
        cloud_factory=lambda credential: cloud,
        resolve_cloud_secret=lambda: None,
    ).complete(_request(), privacy=_cloud_privacy())

    assert result.value is None
    assert result.error_code is BoundaryErrorCode.CREDENTIAL_UNAVAILABLE
    assert cloud.calls == 0


@pytest.mark.parametrize(
    ("failure", "expected"),
    [
        (ProviderFailure(BoundaryErrorCode.LOCAL_UNAVAILABLE), BoundaryErrorCode.LOCAL_UNAVAILABLE),
        (ProviderFailure(BoundaryErrorCode.PROVIDER_TIMEOUT), BoundaryErrorCode.PROVIDER_TIMEOUT),
        (
            ProviderFailure(BoundaryErrorCode.MALFORMED_RESPONSE),
            BoundaryErrorCode.MALFORMED_RESPONSE,
        ),
        (RuntimeError("synthetic transport detail"), BoundaryErrorCode.IMPLEMENTATION_FAILURE),
    ],
)
def test_selected_provider_failures_are_closed_and_never_fall_back(
    failure: Exception, expected: BoundaryErrorCode
) -> None:
    local = _ProviderFake(failure)
    cloud_factory_calls = 0

    def cloud_factory(credential: str) -> _ProviderFake:
        nonlocal cloud_factory_calls
        assert credential == "synthetic"
        cloud_factory_calls += 1
        return _ProviderFake(TextModelResult(text="cloud", provider_name="cloud"))

    result = ProviderService(
        provider_name="local",
        cloud_enabled=True,
        local_factory=lambda: local,
        cloud_factory=cloud_factory,
        resolve_cloud_secret=lambda: "synthetic",
    ).complete(_request(), privacy=_local_privacy())

    assert result.value is None
    assert result.error_code is expected
    assert local.calls == 1
    assert cloud_factory_calls == 0
    assert "synthetic transport detail" not in repr(result)


def test_authorized_cloud_failure_has_one_attempt_and_no_local_fallback() -> None:
    cloud = _ProviderFake(ProviderFailure(BoundaryErrorCode.PROVIDER_REJECTED))
    local_factory_calls = 0

    def local_factory() -> _ProviderFake:
        nonlocal local_factory_calls
        local_factory_calls += 1
        return _ProviderFake(TextModelResult(text="local", provider_name="local"))

    result = ProviderService(
        provider_name="cloud",
        cloud_enabled=True,
        local_factory=local_factory,
        cloud_factory=lambda credential: cloud,
        resolve_cloud_secret=lambda: "synthetic",
    ).complete(_request(), privacy=_cloud_privacy())

    assert result.value is None
    assert result.error_code is BoundaryErrorCode.PROVIDER_REJECTED
    assert cloud.calls == 1
    assert local_factory_calls == 0


def test_authorized_cloud_factory_receives_only_the_resolved_credential() -> None:
    observed: list[str] = []
    cloud = _ProviderFake(TextModelResult(text="cloud", provider_name="cloud"))

    def cloud_factory(credential: str) -> _ProviderFake:
        observed.append(credential)
        return cloud

    result = ProviderService(
        provider_name="cloud",
        cloud_enabled=True,
        local_factory=lambda: _ProviderFake(TextModelResult(text="local", provider_name="local")),
        cloud_factory=cloud_factory,
        resolve_cloud_secret=lambda: "synthetic-credential",
    ).complete(_request(), privacy=_cloud_privacy())

    assert result.value == TextModelResult(text="cloud", provider_name="cloud")
    assert observed == ["synthetic-credential"]
