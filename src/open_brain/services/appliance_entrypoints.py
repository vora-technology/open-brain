"""Appliance entry points for init/status and read-only MCP during Phase 3 W1."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections.abc import Mapping
from pathlib import Path

from open_brain import __version__
from open_brain.cli._common import ExitCode
from open_brain.engine import ReadViewUnavailableError
from open_brain.profile import ProfileError
from open_brain.services.appliance_application import ApplianceApplication
from open_brain.services.appliance_init import ApplianceInitError, initialize_appliance
from open_brain.services.appliance_status import read_appliance_status
from open_brain.services.mcp_stdio import serve_stdio_mcp

_MCP_SPACE_ID = re.compile(r"space_[A-Za-z0-9][A-Za-z0-9_.-]{0,127}")


def run_cli(
    argv: tuple[str, ...] | list[str] | None = None,
    *,
    environment: Mapping[str, object] | None = None,
) -> int:
    env = os.environ if environment is None else environment
    arguments = tuple(sys.argv[1:] if argv is None else argv)
    parser_arguments = tuple(argument for argument in arguments if argument != "--json")
    root_free_exit = _root_free_exit(arguments)
    if root_free_exit is not None:
        return root_free_exit
    parser = _parser()
    namespace = parser.parse_args(parser_arguments)
    root = _root_from_environment(env)
    try:
        if namespace.command == "init":
            receipt = initialize_appliance(root, starter_spaces=tuple(namespace.starter_space))
            _write_json(receipt.to_dict())
            return ExitCode.SUCCESS
        if namespace.command == "status":
            _write_json(read_appliance_status(root).to_dict())
            return ExitCode.SUCCESS
    except (ApplianceInitError, ProfileError, ReadViewUnavailableError) as error:
        payload = error.receipt.to_dict() if isinstance(error, ApplianceInitError) else {
            "status": "failed",
            "detail": str(error),
        }
        _write_json(payload)
        return ExitCode.CONFIGURATION
    return ExitCode.USAGE


def run_mcp() -> int:
    try:
        application = ApplianceApplication.open_read_only(
            _root_from_environment(os.environ),
            allowed_space_ids=_mcp_allowed_space_ids(os.environ),
        )
        serve_stdio_mcp(
            application.mcp_adapter(),
            input_stream=sys.stdin.buffer,
            output_stream=sys.stdout.buffer,
        )
    except (ProfileError, ReadViewUnavailableError, ValueError):
        return ExitCode.CONFIGURATION
    return ExitCode.SUCCESS


def run_http() -> int:
    return ExitCode.CONFIGURATION


def _root_free_exit(arguments: tuple[str, ...]) -> ExitCode | None:
    if tuple(argument for argument in arguments if argument != "--json") == ("--version",):
        print(f"open-brain {__version__}")
        return ExitCode.SUCCESS
    if "--help" in arguments or "-h" in arguments:
        try:
            _parser().parse_args(tuple(argument for argument in arguments if argument != "--json"))
        except SystemExit as error:
            return ExitCode.SUCCESS if error.code == 0 else ExitCode.USAGE
    return None


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="open-brain",
        description="Phase 3 appliance init, status, and read-only MCP entry points.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--json", action="store_true", help="Write JSON output.")
    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")
    init_parser = subparsers.add_parser("init", help="Initialize one appliance root.")
    init_parser.add_argument(
        "--starter-space",
        action="append",
        default=[],
        help="Create one optional starter space.",
    )
    subparsers.add_parser("status", help="Read bounded appliance status.")
    return parser


def _root_from_environment(environment: Mapping[str, object]) -> Path:
    root = environment.get("OPEN_BRAIN_ROOT")
    if not isinstance(root, str) or not root or "\x00" in root or not Path(root).is_absolute():
        raise ValueError("invalid OPEN_BRAIN_ROOT")
    return Path(root)


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


def _write_json(value: Mapping[str, object]) -> None:
    sys.stdout.write(json.dumps(dict(value), sort_keys=True, separators=(",", ":")) + "\n")
