from __future__ import annotations

import inspect
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
from open_brain.services.application import SingleUserLocalApplication
from open_brain.services.entrypoints import (
    ServiceConfigurationError,
    compose_http_from_config,
    compose_mcp_from_config,
    load_private_http_bind_config,
    run_http,
    run_mcp,
)
from open_brain.services.http_server import HttpRouteMode


def test_cli_process_startup_uses_the_app_owned_composition_root() -> None:
    root = Path(__file__).parents[3]
    application = root / "src" / "open_brain" / "services" / "application.py"
    scripts = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"][
        "scripts"
    ]
    module_source = (root / "src" / "open_brain" / "__main__.py").read_text(encoding="utf-8")

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
    application = SingleUserLocalApplication.open(tmp_path / "brain")
    lifecycle = compose_mcp_from_config(application=application)
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
            json.dumps(request, separators=(",", ":")).encode() + b"\n" for request in requests
        )
    )
    output = io.BytesIO()

    lifecycle.serve(input_stream=source, output_stream=output)
    responses = [json.loads(line) for line in output.getvalue().splitlines()]

    assert responses[0]["result"]["serverInfo"]["name"] == "open-brain"
    names = {tool["name"] for tool in responses[1]["result"]["tools"]}
    assert names == {"brain_fetch", "brain_query", "brain_retrieval_feedback"}


def test_http_composition_requires_and_resolves_only_named_secret_ref(
    tmp_path: Path,
) -> None:
    config = _config(tmp_path, with_token=True)
    application = SingleUserLocalApplication.open(tmp_path / "brain")

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
    application = SingleUserLocalApplication.open(tmp_path / "brain")

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
    application = SingleUserLocalApplication.open(tmp_path / "brain")
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
    assert (
        ui.dispatch(
            method="GET",
            path="/health",
            headers=(("Authorization", "Bearer synthetic-ui-token"),),
            body_reader=lambda _a, _b: b"",
        ).status
        == 200
    )
    assert (
        ingress.dispatch(
            method="GET",
            path="/health",
            headers=(("Authorization", "Bearer synthetic-ingress-token"),),
            body_reader=lambda _a, _b: b"",
        ).status
        == 405
    )


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


class _McpLifecycle:
    def serve(self, *, input_stream: object, output_stream: object) -> None:
        del input_stream, output_stream


class _HttpServer:
    def serve_forever(self) -> None:
        return None

    def shutdown(self) -> None:
        return None


class _HttpLifecycle:
    def start(self) -> _HttpServer:
        return _HttpServer()


def test_run_mcp_opens_exactly_one_root_app_and_injects_scoped_tasks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    application = SingleUserLocalApplication.open(tmp_path / "brain")
    observed: list[object] = []

    def open_application(root: Path) -> SingleUserLocalApplication:
        observed.append(root)
        return application

    def compose_mcp(
        *,
        application: SingleUserLocalApplication,
        allowed_space_ids: frozenset[str],
    ) -> _McpLifecycle:
        observed.extend((application, allowed_space_ids, application.tasks.retrieval))
        return _McpLifecycle()

    monkeypatch.setattr(
        "open_brain.services.entrypoints.SingleUserLocalApplication.open",
        open_application,
    )
    monkeypatch.setattr(
        "open_brain.services.entrypoints.compose_mcp_from_config",
        compose_mcp,
    )
    monkeypatch.setattr(
        "open_brain.services.entrypoints.os.environ",
        {
            "OPEN_BRAIN_ROOT": str(tmp_path / "brain"),
            "OPEN_BRAIN_MCP_ALLOWED_SPACE_IDS": "[]",
        },
    )

    assert run_mcp() == 0
    assert observed == [
        tmp_path / "brain",
        application,
        frozenset(),
        application.tasks.retrieval,
    ]
    source = inspect.getsource(run_mcp)
    assert not any(
        name in source
        for name in ("ProductionApplication", "FilesystemWorkRetriever", "FilesystemCaptureQueue")
    )


@pytest.mark.parametrize(
    "environment",
    (
        {},
        {"OPEN_BRAIN_ROOT": "relative"},
        {"OPEN_BRAIN_ROOT": "/tmp/synthetic"},
        {
            "OPEN_BRAIN_ROOT": "/tmp/synthetic",
            "OPEN_BRAIN_MCP_ALLOWED_SPACE_IDS": "{}",
        },
    ),
)
def test_run_mcp_fails_closed_without_a_valid_root_and_allow_list(
    monkeypatch: pytest.MonkeyPatch, environment: dict[str, str]
) -> None:
    monkeypatch.setattr("open_brain.services.entrypoints.os.environ", environment)

    assert run_mcp() == 78


def test_run_http_opens_exactly_one_root_app_without_legacy_task_construction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    application = SingleUserLocalApplication.open(tmp_path / "brain")
    config = _config(tmp_path, with_token=True)
    observed: list[object] = []

    def open_application(root: Path) -> SingleUserLocalApplication:
        observed.append(root)
        return application

    def compose_http(**kwargs: object) -> _HttpLifecycle:
        selected = kwargs["application"]
        assert isinstance(selected, SingleUserLocalApplication)
        observed.extend((selected, selected.tasks.capture))
        return _HttpLifecycle()

    monkeypatch.setattr(
        "open_brain.services.entrypoints.SingleUserLocalApplication.open",
        open_application,
    )
    monkeypatch.setattr(
        "open_brain.services.entrypoints.AppConfig.load",
        lambda *, environment: config,
    )
    monkeypatch.setattr(
        "open_brain.services.entrypoints.compose_http_from_config",
        compose_http,
    )
    monkeypatch.setattr(
        "open_brain.services.entrypoints.os.environ",
        {"OPEN_BRAIN_ROOT": str(tmp_path / "brain")},
    )

    assert run_http() == 0
    assert observed == [tmp_path / "brain", application, application.tasks.capture]
    source = inspect.getsource(run_http)
    assert not any(
        name in source
        for name in ("ProductionApplication", "FilesystemWorkRetriever", "FilesystemCaptureQueue")
    )
