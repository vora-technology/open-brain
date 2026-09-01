from __future__ import annotations

import os
import platform
import sys
from pathlib import Path

from .appliance_daemon import (
    CliControlReceipt,
    CliControlRequest,
    ControlReceipt,
    ControlRequest,
    StatusControlReceipt,
    request_cli_dispatch,
    request_control,
    request_status,
)
from .appliance_supervisors import LaunchdSupervisor, SystemdSupervisor

_SUPERVISOR_ACTIONS = frozenset(
    {"discover", "install", "start", "stop", "restart", "status", "remove"}
)


def submit_control_request(root: Path, request: ControlRequest) -> ControlReceipt:
    if not isinstance(root, Path) or not isinstance(request, ControlRequest):
        raise ValueError("invalid appliance control request")
    return request_control(root, request)


def dispatch_phase1_command(
    root: Path,
    *,
    command: str,
    argv: tuple[str, ...],
) -> CliControlReceipt:
    if not isinstance(root, Path) or not isinstance(command, str) or not isinstance(argv, tuple):
        raise ValueError("invalid appliance control request")
    return request_cli_dispatch(root, CliControlRequest(command=command, argv=argv))


def read_status_via_control(root: Path) -> StatusControlReceipt:
    if not isinstance(root, Path):
        raise ValueError("invalid appliance control request")
    return request_status(root)


def run_supervisor_action(root: Path, *, action: str) -> dict[str, object]:
    if (
        not isinstance(root, Path)
        or not isinstance(action, str)
        or action not in _SUPERVISOR_ACTIONS
    ):
        raise ValueError("invalid appliance supervisor request")
    supervisor = _supervisor(root)
    if action == "discover":
        return {
            "action": action,
            "command": "supervisor",
            "status": "ok",
            "supervisor": type(supervisor).__name__.removesuffix("Supervisor").casefold(),
            "unit_name": supervisor.unit_name,
        }
    operation = {
        "install": supervisor.install,
        "start": supervisor.start,
        "stop": supervisor.stop,
        "restart": supervisor.restart,
        "status": supervisor.status,
        "remove": supervisor.remove,
    }[action]
    operation()
    return {
        "action": action,
        "command": "supervisor",
        "status": "ok",
        "supervisor": type(supervisor).__name__.removesuffix("Supervisor").casefold(),
        "unit_name": supervisor.unit_name,
    }


def _supervisor(root: Path) -> LaunchdSupervisor | SystemdSupervisor:
    checkout_root = Path(__file__).resolve().parents[3]
    host = platform.system()
    if host == "Darwin":
        return LaunchdSupervisor(
            root=root,
            checkout_root=checkout_root,
            python_executable=sys.executable,
            unit_directory=Path.home() / "Library" / "LaunchAgents",
            user_id=os.getuid(),
        )
    if host == "Linux":
        return SystemdSupervisor(
            root=root,
            checkout_root=checkout_root,
            python_executable=sys.executable,
            unit_directory=Path.home() / ".config" / "systemd" / "user",
        )
    raise ValueError("unsupported appliance supervisor")
