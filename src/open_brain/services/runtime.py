"""Shared, app-owned HTTP, MCP, configuration, and secret composition helpers."""

from __future__ import annotations

import json
import os
import stat
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path

from open_brain.config import (
    AppConfig,
    NamedSecretRef,
    SecretResolutionError,
    resolve_secret,
)
from open_brain.core.ids import canonical_json_bytes
from open_brain.integrations.mcp import LocalStdioMcpAdapter
from open_brain.integrations.ui import UiBindConfig

from .capabilities import ProductionApplication
from .composition import (
    HttpLifecycle,
    ProductionServiceDependencies,
    StdioMcpLifecycle,
    compose_production_services,
)
from .http_server import HttpRouteMode

_SERVICE_SECRET_NAME = "service_token"
_SERVICE_SECRET_NAMES = frozenset(
    {_SERVICE_SECRET_NAME, "ui_service_token", "ingress_service_token"}
)
_MAXIMUM_SECRET_BYTES = 4_096


class ServiceConfigurationError(RuntimeError):
    """A service cannot start from the supplied non-secret configuration."""


def compose_mcp_from_config(
    *,
    config: AppConfig,
    application: ProductionApplication,
) -> StdioMcpLifecycle:
    """Compose work-only MCP without requiring unrelated HTTP credentials."""
    if not isinstance(config, AppConfig) or not isinstance(application, ProductionApplication):
        raise ServiceConfigurationError("invalid MCP service configuration")
    try:
        adapter = LocalStdioMcpAdapter(
            retriever=application.retriever,
            feedback=application.feedback,
        )
    except Exception as error:
        raise ServiceConfigurationError("invalid MCP service configuration") from error
    return StdioMcpLifecycle(adapter)


def compose_http_from_config(
    *,
    config: AppConfig,
    application: ProductionApplication,
    environment: Mapping[str, str],
    file_reader: Callable[[Path], str],
    bind: UiBindConfig | None = None,
    secret_name: str = _SERVICE_SECRET_NAME,
    route_mode: HttpRouteMode = HttpRouteMode.COMBINED,
) -> HttpLifecycle:
    """Resolve one named credential, then compose authenticated UI/share HTTP."""
    if (
        not isinstance(config, AppConfig)
        or not isinstance(application, ProductionApplication)
        or not isinstance(environment, Mapping)
        or not callable(file_reader)
        or secret_name not in _SERVICE_SECRET_NAMES
        or not isinstance(route_mode, HttpRouteMode)
    ):
        raise ServiceConfigurationError("invalid HTTP service configuration")
    token = _service_token(
        config,
        secret_name=secret_name,
        environment=environment,
        file_reader=file_reader,
    )
    try:
        services = compose_production_services(
            ProductionServiceDependencies(
                retriever=application.retriever,
                feedback=application.feedback,
                page_reader=application.page_reader,
                share_queue=application.capture_queue,
                expected_bearer_token=token,
                clock=_utc_now,
                bind=bind or UiBindConfig(),
                http_route_mode=route_mode,
            )
        )
    except Exception as error:
        raise ServiceConfigurationError("invalid HTTP service configuration") from error
    return services.http


def read_private_service_secret(path: Path) -> str:
    payload = _read_owner_file(path)
    value = payload.decode("utf-8").rstrip("\r\n")
    if not value:
        raise OSError("invalid secret file")
    return value


def load_private_http_bind_config(path: Path) -> UiBindConfig:
    """Load one canonical owner-only, non-secret HTTP bind configuration."""
    try:
        payload = _read_owner_file(path)
        value = json.loads(payload.decode("utf-8"), object_pairs_hook=_unique_object)
        if (
            not isinstance(value, dict)
            or set(value)
            != {"schema_version", "host", "port", "allow_private_network"}
            or value["schema_version"] != 1
            or not isinstance(value["host"], str)
            or not isinstance(value["port"], int)
            or isinstance(value["port"], bool)
            or type(value["allow_private_network"]) is not bool
            or canonical_json_bytes(value) != payload
        ):
            raise ValueError
        return UiBindConfig(
            host=value["host"],
            port=value["port"],
            allow_private_network=value["allow_private_network"],
        )
    except (OSError, TypeError, ValueError, UnicodeError, json.JSONDecodeError):
        raise ServiceConfigurationError("invalid HTTP service configuration") from None


def bind_from_environment(environment: Mapping[str, str]) -> UiBindConfig:
    """Build the public HTTP bind settings from bounded process configuration."""
    host = environment.get("OPEN_BRAIN_UI_BIND", "127.0.0.1")
    raw_port = environment.get("OPEN_BRAIN_UI_PORT", "8788")
    raw_private = environment.get("OPEN_BRAIN_UI_ALLOW_PRIVATE", "false")
    if not isinstance(host, str) or not isinstance(raw_port, str) or not isinstance(
        raw_private, str
    ):
        raise ServiceConfigurationError("invalid HTTP service configuration")
    if not raw_port.isascii() or not raw_port.isdigit():
        raise ServiceConfigurationError("invalid HTTP service configuration")
    if raw_private not in {"true", "false"}:
        raise ServiceConfigurationError("invalid HTTP service configuration")
    try:
        return UiBindConfig(
            host=host,
            port=int(raw_port),
            allow_private_network=raw_private == "true",
        )
    except ValueError:
        raise ServiceConfigurationError("invalid HTTP service configuration") from None


def _service_token(
    config: AppConfig,
    *,
    secret_name: str,
    environment: Mapping[str, str],
    file_reader: Callable[[Path], str],
) -> str:
    references = tuple(
        reference
        for reference in config.secret_refs
        if reference.name == secret_name
    )
    if len(references) != 1 or not isinstance(references[0], NamedSecretRef):
        raise ServiceConfigurationError("service credential unavailable")
    try:
        value = resolve_secret(
            references[0].reference,
            environment=environment,
            file_reader=file_reader,
        )
    except SecretResolutionError:
        raise ServiceConfigurationError("service credential unavailable") from None
    if len(value.encode("utf-8")) > _MAXIMUM_SECRET_BYTES:
        raise ServiceConfigurationError("service credential unavailable")
    return value


def _read_owner_file(path: Path) -> bytes:
    if not isinstance(path, Path) or not path.is_absolute():
        raise OSError("invalid secret file")
    metadata = path.lstat()
    if (
        stat.S_ISLNK(metadata.st_mode)
        or not stat.S_ISREG(metadata.st_mode)
        or metadata.st_mode & 0o077
        or metadata.st_uid not in {0, os.geteuid()}
        or metadata.st_size > _MAXIMUM_SECRET_BYTES
    ):
        raise OSError("invalid secret file")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    file_descriptor = os.open(path, flags)
    try:
        current = os.fstat(file_descriptor)
        if (current.st_dev, current.st_ino) != (metadata.st_dev, metadata.st_ino):
            raise OSError("secret file changed")
        payload = os.read(file_descriptor, _MAXIMUM_SECRET_BYTES + 1)
    finally:
        os.close(file_descriptor)
    if len(payload) > _MAXIMUM_SECRET_BYTES:
        raise OSError("invalid secret file")
    return payload


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError
        value[key] = item
    return value


def _utc_now() -> datetime:
    return datetime.now(UTC)
