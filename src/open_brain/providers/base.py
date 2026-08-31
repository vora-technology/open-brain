"""One-provider selection with closed, redacted failures."""

from __future__ import annotations

import importlib
from typing import Protocol, cast

from open_brain.capture.redaction import has_redaction_finding
from open_brain.core.models import PrivacyDecision, ValidationError
from open_brain.core.policy import BoundaryErrorCode, BoundaryResult
from open_brain.core.ports import Provider, TextModelRequest, TextModelResult


class ProviderFailure(Exception):
    """An adapter failure represented by a public closed error code."""

    def __init__(self, code: BoundaryErrorCode) -> None:
        self.code = code
        super().__init__(code.value)


class LocalFactory(Protocol):
    def __call__(self) -> Provider: ...


class CloudFactory(Protocol):
    def __call__(self, credential: str) -> Provider: ...


class SecretResolver(Protocol):
    def __call__(self) -> str | None: ...


class OptionalExtraUnavailable(Exception):
    """Internal signal that never exposes optional-package details."""


class ProviderService:
    """Select exactly one explicit provider for one immutable decision."""

    def __init__(
        self,
        *,
        provider_name: str,
        cloud_enabled: bool,
        local_factory: LocalFactory,
        cloud_factory: CloudFactory,
        resolve_cloud_secret: SecretResolver,
    ) -> None:
        if provider_name not in {"local", "cloud"}:
            raise ValidationError("invalid provider")
        if not isinstance(cloud_enabled, bool):
            raise ValidationError("invalid provider configuration")
        self._provider_name = provider_name
        self._cloud_enabled = cloud_enabled
        self._local_factory = local_factory
        self._cloud_factory = cloud_factory
        self._resolve_cloud_secret = resolve_cloud_secret

    def complete(
        self, request: TextModelRequest, *, privacy: PrivacyDecision
    ) -> BoundaryResult[TextModelResult]:
        if not isinstance(request, TextModelRequest) or not isinstance(privacy, PrivacyDecision):
            raise ValidationError("invalid provider request")
        if self._provider_name == "local":
            return self._complete_selected(self._local_factory, request, privacy)
        if not self._cloud_enabled or not privacy.authority.cloud:
            return BoundaryResult(None, BoundaryErrorCode.CLOUD_AUTHORITY_REQUIRED)
        try:
            privacy.authority.narrow(cloud=True, external_egress=False)
        except Exception:
            return BoundaryResult(None, BoundaryErrorCode.CLOUD_AUTHORITY_REQUIRED)
        if _has_cloud_redaction_finding(request.prompt):
            return BoundaryResult(None, BoundaryErrorCode.PROVIDER_REJECTED)
        try:
            credential_value = self._resolve_cloud_secret()
        except Exception:
            return BoundaryResult(None, BoundaryErrorCode.CREDENTIAL_UNAVAILABLE)
        if not isinstance(credential_value, str) or not credential_value:
            return BoundaryResult(None, BoundaryErrorCode.CREDENTIAL_UNAVAILABLE)
        try:
            provider = self._cloud_factory(credential_value)
        except OptionalExtraUnavailable:
            return BoundaryResult(None, BoundaryErrorCode.OPTIONAL_EXTRA_UNAVAILABLE)
        except ProviderFailure as error:
            return BoundaryResult(None, error.code)
        except Exception:
            return BoundaryResult(None, BoundaryErrorCode.IMPLEMENTATION_FAILURE)
        return self._complete_provider(provider, request, privacy)

    def _complete_selected(
        self,
        factory: LocalFactory,
        request: TextModelRequest,
        privacy: PrivacyDecision,
    ) -> BoundaryResult[TextModelResult]:
        try:
            provider = factory()
        except ProviderFailure as error:
            return BoundaryResult(None, error.code)
        except Exception:
            return BoundaryResult(None, BoundaryErrorCode.IMPLEMENTATION_FAILURE)
        return self._complete_provider(provider, request, privacy)

    @staticmethod
    def _complete_provider(
        provider: Provider,
        request: TextModelRequest,
        privacy: PrivacyDecision,
    ) -> BoundaryResult[TextModelResult]:
        try:
            result = provider.complete(request, privacy=privacy)
        except ProviderFailure as error:
            return BoundaryResult(None, error.code)
        except Exception:
            return BoundaryResult(None, BoundaryErrorCode.IMPLEMENTATION_FAILURE)
        if not isinstance(result, TextModelResult):
            return BoundaryResult(None, BoundaryErrorCode.MALFORMED_RESPONSE)
        try:
            return BoundaryResult(result.validate_for(request), None)
        except ValidationError:
            return BoundaryResult(None, BoundaryErrorCode.OUTPUT_LIMIT)


def lazy_cloud_factory(module_name: str, *, model: str | None = None) -> CloudFactory:
    """Load an optional cloud adapter only inside an authorized factory call."""

    if model is not None and (not isinstance(model, str) or not model or model.isspace()):
        raise ValidationError("invalid cloud provider model")

    def factory(credential: str) -> Provider:
        if not isinstance(credential, str) or not credential:
            raise ProviderFailure(BoundaryErrorCode.CREDENTIAL_UNAVAILABLE)
        try:
            module = importlib.import_module(module_name)
        except ModuleNotFoundError as error:
            raise OptionalExtraUnavailable from error
        create_provider = getattr(module, "create_provider", None)
        if not callable(create_provider):
            raise OptionalExtraUnavailable
        provider = (
            create_provider(credential)
            if model is None
            else create_provider(credential, model=model)
        )
        return cast(Provider, provider)

    return factory


def _has_cloud_redaction_finding(prompt: str) -> bool:
    return has_redaction_finding(prompt)
