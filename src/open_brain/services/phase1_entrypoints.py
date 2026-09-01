"""Fail-closed app-owned process entry points for the local Phase 1 surfaces."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections.abc import Mapping
from pathlib import Path

from open_brain import __version__
from open_brain.cli._common import (
    ExitCode,
    adapter_failed_envelope,
    invalid_envelope,
    validate_adapter_envelope,
    write_envelope,
)
from open_brain.config import AppConfig, ConfigError
from open_brain.services.phase1_application import SingleUserLocalApplication
from open_brain.services.runtime import (
    ServiceConfigurationError,
    bind_from_environment,
    compose_http_from_config,
    compose_mcp_from_config,
    read_private_service_secret,
)

_PHASE1_COMMANDS = frozenset({"capture", "inbox", "proposals", "query", "review", "spaces"})
_MCP_SPACE_ID = re.compile(r"space_[A-Za-z0-9][A-Za-z0-9_.-]{0,127}")


def run_cli(
    argv: tuple[str, ...] | list[str] | None = None,
    *,
    environment: Mapping[str, object] | None = None,
) -> int:
    """Open one explicit Brain root and dispatch one retained Phase 1 CLI family."""
    env = os.environ if environment is None else environment
    arguments = tuple(sys.argv[1:] if argv is None else argv)
    json_output = "--json" in arguments
    if (
        any(not isinstance(argument, str) or "\x00" in argument for argument in arguments)
        or arguments.count("--json") > 1
        or arguments.count("--dry-run") > 1
    ):
        write_envelope(invalid_envelope(), json_output=json_output, stream=sys.stdout)
        return ExitCode.USAGE
    root_free_exit = _root_free_exit(arguments)
    if root_free_exit is not None:
        return root_free_exit
    try:
        application = _open_single_user_application(env)
    except (OSError, ValueError):
        return ExitCode.CONFIGURATION
    if not arguments:
        return ExitCode.SUCCESS
    command_index = next(
        (index for index, argument in enumerate(arguments) if not argument.startswith("-")),
        None,
    )
    if command_index is None:
        write_envelope(invalid_envelope(), json_output=json_output, stream=sys.stdout)
        return ExitCode.USAGE
    command = arguments[command_index]
    if command not in _PHASE1_COMMANDS:
        write_envelope(invalid_envelope(), json_output=json_output, stream=sys.stdout)
        return ExitCode.USAGE
    adapter_argv = tuple(
        argument for argument in arguments[:command_index] if argument != "--json"
    ) + arguments[command_index + 1 :]
    adapter = application.cli_adapters().get(command)
    assert adapter is not None
    try:
        result = adapter.dispatch(adapter_argv)
        envelope = validate_adapter_envelope(command, result.envelope, argv=adapter_argv)
        exit_code = ExitCode(result.exit_code)
    except Exception:
        write_envelope(adapter_failed_envelope(command), json_output=json_output, stream=sys.stdout)
        return ExitCode.FAILURE
    write_envelope(envelope, json_output=json_output, stream=sys.stdout)
    return exit_code


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


def run_mcp() -> int:
    """Open one root-scoped app and serve bounded MCP over stdio until EOF."""
    try:
        allowed_space_ids = _mcp_allowed_space_ids(os.environ)
        application = _open_single_user_application(os.environ)
        lifecycle = compose_mcp_from_config(
            application=application,
            allowed_space_ids=allowed_space_ids,
        )
        lifecycle.serve(input_stream=sys.stdin.buffer, output_stream=sys.stdout.buffer)
    except (ServiceConfigurationError, ValueError):
        return ExitCode.CONFIGURATION
    return ExitCode.SUCCESS


def run_http() -> int:
    """Open one root-scoped app and serve authenticated HTTP until stopped."""
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
        return ExitCode.CONFIGURATION
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
    return ExitCode.SUCCESS


def _root_free_exit(arguments: tuple[str, ...]) -> ExitCode | None:
    representation_free = tuple(argument for argument in arguments if argument != "--json")
    if representation_free == ("--version",):
        print(f"open-brain {__version__}")
        return ExitCode.SUCCESS
    if "--help" in arguments or "-h" in arguments:
        try:
            _phase1_parser().parse_args(representation_free)
        except SystemExit as error:
            return ExitCode.SUCCESS if error.code == 0 else ExitCode.USAGE
        return ExitCode.USAGE
    return None


def _phase1_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="open-brain",
        description="Local-first capture, provenance, review, and knowledge pipeline.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--json", action="store_true", help="Write a JSON envelope.")
    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")
    for command in sorted(_PHASE1_COMMANDS):
        subparsers.add_parser(
            command,
            help=f"{command} commands",
            description=f"Dispatch the {command} command family.",
        )
    return parser


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
            not isinstance(space_id, str) or _MCP_SPACE_ID.fullmatch(space_id) is None
            for space_id in value
        )
        or len(set(value)) != len(value)
    ):
        raise ValueError("invalid MCP allow-list")
    return frozenset(value)


__all__ = ["run_cli", "run_http", "run_mcp"]
