from __future__ import annotations

import io
import json
import tomllib
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from open_brain.config import AppConfig, NamedSecretRef, RetainedRoots, SecretRef
from open_brain.core.ids import canonical_json_bytes
from open_brain.integrations.ui import UiBindConfig
from open_brain.production.application import compose_production_application
from open_brain.services.entrypoints import (
    ServiceConfigurationError,
    compose_http_from_config,
    compose_mcp_from_config,
    load_private_http_bind_config,
)
from open_brain.services.http_server import HttpRouteMode


def test_cli_process_startup_uses_the_app_owned_composition_root() -> None:
    root = Path(__file__).parents[3]
    application = root / "src" / "open_brain" / "services" / "application.py"
    scripts = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]["scripts"]
    module_source = (root / "src" / "open_brain" / "__main__.py").read_text(
        encoding="utf-8"
    )

    assert application.is_file()
    assert scripts["open-brain"] == "open_brain.services.entrypoints:run_cli"
    assert "from open_brain.services.entrypoints import run_cli" in module_source


def _config(tmp_path: Path, *, with_token: bool = False) -> AppConfig:
    roots = {
        name: tmp_path / name
        for name in ("work", "personal", "capture", "saved", "state", "backup")
    }
    for root in roots.values():
        root.mkdir()
    pages = roots["work"] / "pages"
    pages.mkdir()
    (pages / "topic.md").write_text("# Synthetic topic\n\nBounded work text.\n")
    return AppConfig(
        roots=RetainedRoots(
            work=roots["work"],
            personal=roots["personal"],
            capture=roots["capture"],
            saved_content=roots["saved"],
            state=roots["state"],
        ),
        backup=roots["backup"],
        secret_refs=(
            (
                NamedSecretRef(
                    "service_token",
                    SecretRef.parse("env:SYNTHETIC_SERVICE_TOKEN"),
                ),
            )
            if with_token
            else ()
        ),
    )


def _clock() -> datetime:
    return datetime(2026, 8, 25, 12, 0, tzinfo=UTC)


def test_mcp_composes_without_an_http_secret_and_serves_work_tools(tmp_path: Path) -> None:
    config = _config(tmp_path)
    application = compose_production_application(config=config, clock=_clock)
    lifecycle = compose_mcp_from_config(config=config, application=application)
    requests = (
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {},
            },
        },
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
    )
    source = io.BytesIO(
        b"".join(
            json.dumps(request, separators=(",", ":")).encode() + b"\n"
            for request in requests
        )
    )
    output = io.BytesIO()

    lifecycle.serve(input_stream=source, output_stream=output)
    responses = [json.loads(line) for line in output.getvalue().splitlines()]

    assert responses[0]["result"]["serverInfo"]["name"] == "open-brain"
    names = {tool["name"] for tool in responses[1]["result"]["tools"]}
    assert names == {"brain_query", "brain_retrieval_feedback"}


def test_http_composition_requires_and_resolves_only_named_secret_ref(
    tmp_path: Path,
) -> None:
    config = _config(tmp_path, with_token=True)
    application = compose_production_application(config=config, clock=_clock)

    lifecycle = compose_http_from_config(
        config=config,
        application=application,
        environment={"SYNTHETIC_SERVICE_TOKEN": "synthetic-service-token"},
        file_reader=lambda _path: "not-used",
    )
    response = lifecycle.dispatch(
        method="GET",
        path="/health",
        headers=(("Authorization", "Bearer synthetic-service-token"),),
        body_reader=lambda _maximum, _timeout: b"",
    )

    assert response.status == 200
    assert response.body == b'{"status":"ok"}'


def test_http_composition_fails_closed_without_service_secret(tmp_path: Path) -> None:
    config = _config(tmp_path)
    application = compose_production_application(config=config, clock=_clock)

    with pytest.raises(ServiceConfigurationError, match="service credential unavailable"):
        compose_http_from_config(
            config=config,
            application=application,
            environment={},
            file_reader=lambda _path: "not-used",
        )


def test_http_jobs_select_distinct_named_tokens_and_route_modes(tmp_path: Path) -> None:
    config = replace(
        _config(tmp_path),
        secret_refs=(
            NamedSecretRef(
                "ingress_service_token",
                SecretRef.parse("env:SYNTHETIC_INGRESS_TOKEN"),
            ),
            NamedSecretRef(
                "ui_service_token",
                SecretRef.parse("env:SYNTHETIC_UI_TOKEN"),
            ),
        ),
    )
    application = compose_production_application(config=config, clock=_clock)
    environment = {
        "SYNTHETIC_UI_TOKEN": "synthetic-ui-token",
        "SYNTHETIC_INGRESS_TOKEN": "synthetic-ingress-token",
    }

    ui = compose_http_from_config(
        config=config,
        application=application,
        environment=environment,
        file_reader=lambda _path: "not-used",
        secret_name="ui_service_token",
        route_mode=HttpRouteMode.UI_ONLY,
    )
    ingress = compose_http_from_config(
        config=config,
        application=application,
        environment=environment,
        file_reader=lambda _path: "not-used",
        secret_name="ingress_service_token",
        route_mode=HttpRouteMode.SHARE_ONLY,
    )

    assert ui.service.config.route_mode is HttpRouteMode.UI_ONLY
    assert ingress.service.config.route_mode is HttpRouteMode.SHARE_ONLY
    assert ui.dispatch(
        method="GET",
        path="/health",
        headers=(("Authorization", "Bearer synthetic-ui-token"),),
        body_reader=lambda _a, _b: b"",
    ).status == 200
    assert ingress.dispatch(
        method="GET",
        path="/health",
        headers=(("Authorization", "Bearer synthetic-ingress-token"),),
        body_reader=lambda _a, _b: b"",
    ).status == 405


def test_private_http_bind_config_is_owner_only_and_canonical(tmp_path: Path) -> None:
    path = tmp_path / "http-bind.json"
    path.write_bytes(
        canonical_json_bytes(
            {
                "schema_version": 1,
                "host": "127.0.0.1",
                "port": 8789,
                "allow_private_network": False,
            }
        )
    )
    path.chmod(0o600)

    assert load_private_http_bind_config(path) == UiBindConfig(
        host="127.0.0.1",
        port=8789,
        allow_private_network=False,
    )

    path.chmod(0o644)
    with pytest.raises(ServiceConfigurationError, match="HTTP service configuration"):
        load_private_http_bind_config(path)
