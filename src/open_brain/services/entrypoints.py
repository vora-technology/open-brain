"""Runnable, fail-closed process entry points for Open Brain local services."""

from __future__ import annotations

import json
import os
import re
import sys
from collections.abc import Mapping
from pathlib import Path

from open_brain.config import AppConfig, ConfigError
from open_brain.services.application import (
    ConfigurationFailedScheduledAdapters,
    ConfiguredScheduledAdapters,
    SingleUserLocalApplication,
    _degraded_doctor_adapters,
    _SystemClock,
    build_command_adapters,
    compose_production_application,
)
from open_brain.services.runtime import (
    ServiceConfigurationError,
    _utc_now,
    bind_from_environment,
    compose_http_from_config,
    compose_mcp_from_config,
    load_private_http_bind_config,
    read_private_service_secret,
)


def run_mcp() -> int:
    """Open one root-scoped application and serve bounded stdio MCP until EOF."""
    try:
        allowed_space_ids = _mcp_allowed_space_ids(os.environ)
        application = _open_single_user_application(os.environ)
        lifecycle = compose_mcp_from_config(
            application=application,
            allowed_space_ids=allowed_space_ids,
        )
        lifecycle.serve(
            input_stream=sys.stdin.buffer,
            output_stream=sys.stdout.buffer,
        )
    except (ServiceConfigurationError, ValueError):
        return 78
    return 0


def run_cli(
    argv: tuple[str, ...] | list[str] | None = None,
    *,
    environment: Mapping[str, object] | None = None,
) -> int:
    """Load process configuration and dispatch through the CLI representation."""
    from open_brain.cli._common import ExitCode
    from open_brain.cli._registry import scheduled_route_spec
    from open_brain.cli.main import main
    from open_brain.operations.models import ExitClass
    from open_brain.operations.runlog import (
        RunErrorClass,
        RunMetadata,
        RunOutcome,
        classify_exit_code,
    )
    from open_brain.operations.runlog_store import FilesystemRunLogStore, RunLogStoreError
    from open_brain.storage.locks import LockBusyError

    env = os.environ if environment is None else environment
    arguments = tuple(sys.argv[1:] if argv is None else argv)
    scheduled_job_id = env.get("OPEN_BRAIN_JOB_ID")
    public_application: SingleUserLocalApplication | None = None
    if env.get("OPEN_BRAIN_ROOT") is not None:
        try:
            public_application = _open_single_user_application(env)
        except (OSError, ValueError, LockBusyError):
            if scheduled_job_id in {"JOB-005", "JOB-027", "JOB-028", "JOB-029"}:
                return ExitClass.CONFIGURATION
        if (
            public_application is not None
            and scheduled_job_id not in {"JOB-005", "JOB-027", "JOB-028", "JOB-029"}
        ):
            return main(argv, command_adapters=public_application.cli_adapters())
    try:
        config = AppConfig.load(environment=env)
    except ConfigError:
        return main(
            argv,
            command_adapters=_degraded_doctor_adapters(),
            scheduled_adapters=ConfigurationFailedScheduledAdapters(),
        )
    scheduled_adapters = ConfiguredScheduledAdapters(
        config,
        _SystemClock(),
        environment=env,
        imessage_service_mode=scheduled_job_id == "JOB-005",
        http_service_mode=scheduled_job_id in {"JOB-026", "JOB-027", "JOB-028"},
        public_application=public_application,
    )
    route = scheduled_route_spec(
        arguments,
        job_id=scheduled_job_id if isinstance(scheduled_job_id, str) else None,
    )
    if (
        route is not None
        and isinstance(scheduled_job_id, str)
        and scheduled_job_id == route.job_id
    ):
        started_at = _utc_now()
        exit_code = main(
            argv,
            scheduled_adapters=scheduled_adapters,
            scheduled_job_id=scheduled_job_id,
        )
        finished_at = _utc_now()
        try:
            outcome = classify_exit_code(int(exit_code))
            error_class = {
                RunOutcome.SUCCEEDED: None,
                RunOutcome.SKIPPED_LOCKED: RunErrorClass.LOCK_HELD,
                RunOutcome.CONFIGURATION_FAILED: RunErrorClass.CONFIGURATION,
                RunOutcome.FAILED: RunErrorClass.JOB_FAILURE,
            }[outcome]
            FilesystemRunLogStore(root=config.state_root).append(
                RunMetadata.create(
                    job_id=scheduled_job_id,
                    started_at=started_at,
                    finished_at=finished_at,
                    exit_code=int(exit_code),
                    error_class=error_class,
                    metrics={},
                )
            )
        except (RunLogStoreError, ValueError):
            return ExitCode.FAILURE
        return exit_code
    return main(
        argv,
        command_adapters=build_command_adapters(config, environment=env),
        scheduled_adapters=scheduled_adapters,
    )


def run_http() -> int:
    """Open one root-scoped application and serve authenticated HTTP until stopped."""
    try:
        application = _open_single_user_application(os.environ)
        config = AppConfig.load(environment=os.environ)
        lifecycle = compose_http_from_config(
            config=config,
            application=application,
            environment=os.environ,
            file_reader=read_private_service_secret,
            bind=bind_from_environment(os.environ),
        )
        server = lifecycle.start()
    except (ConfigError, ServiceConfigurationError, ValueError):
        return 78
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
    return 0


def _open_single_user_application(environment: Mapping[str, object]) -> SingleUserLocalApplication:
    root = environment.get("OPEN_BRAIN_ROOT")
    if (
        not isinstance(root, str)
        or not root
        or "\x00" in root
        or not Path(root).is_absolute()
    ):
        raise ValueError("invalid OPEN_BRAIN_ROOT")
    return SingleUserLocalApplication.open(Path(root))


def _mcp_allowed_space_ids(environment: Mapping[str, object]) -> frozenset[str]:
    raw = environment.get("OPEN_BRAIN_MCP_ALLOWED_SPACE_IDS")
    if not isinstance(raw, str) or not raw or len(raw.encode("utf-8")) > 8_192:
        raise ValueError("invalid MCP allow-list")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError("invalid MCP allow-list") from error
    if (
        not isinstance(value, list)
        or len(value) > 128
        or any(
            not isinstance(space_id, str)
            or _MCP_SPACE_ID.fullmatch(space_id) is None
            for space_id in value
        )
        or len(set(value)) != len(value)
    ):
        raise ValueError("invalid MCP allow-list")
    return frozenset(value)


_MCP_SPACE_ID = re.compile(r"space_[A-Za-z0-9][A-Za-z0-9_.-]{0,127}")


__all__ = [
    "ServiceConfigurationError",
    "compose_http_from_config",
    "compose_mcp_from_config",
    "compose_production_application",
    "load_private_http_bind_config",
    "read_private_service_secret",
    "run_cli",
    "run_http",
    "run_mcp",
]
