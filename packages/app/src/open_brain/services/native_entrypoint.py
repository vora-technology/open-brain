"""Single executable entry point for the native one-folder artifact."""

from __future__ import annotations

import json
import os
import plistlib
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast

from open_brain.extensions.connector_worker_v1 import (
    _child_main as run_connector_worker,
)
from open_brain.extensions.connector_worker_v1 import _worker_command
from open_brain.services.appliance_daemon import main as run_appliance_daemon
from open_brain.services.appliance_entrypoints import run_cli
from open_brain.services.appliance_supervisors import LaunchdSupervisor, SystemdSupervisor
from open_brain.services.native_artifacts import NATIVE_ARTIFACT_KIND, native_platform_tag

_DAEMON_COMMAND = "__appliance-daemon"
_CONNECTOR_WORKER_COMMAND = "__connector-worker"
_SELF_CHECK_COMMAND = "__native-self-check"
_SELF_CHECK_ROOT = Path("/open-brain-native-self-check")


def main(
    argv: Sequence[str] | None = None,
    *,
    environment: Mapping[str, str] | None = None,
) -> int:
    arguments = tuple(sys.argv[1:] if argv is None else argv)
    selected_environment = dict(os.environ if environment is None else environment)
    if arguments[:1] == (_DAEMON_COMMAND,):
        return run_appliance_daemon(arguments[1:], environment=selected_environment)
    if arguments == (_CONNECTOR_WORKER_COMMAND,):
        return run_connector_worker()
    if arguments == (_SELF_CHECK_COMMAND,):
        return _native_self_check()
    return int(run_cli(arguments, environment=selected_environment))


def _native_self_check() -> int:
    try:
        executable = Path(sys.executable)
        if not getattr(sys, "frozen", False) or not executable.is_absolute():
            raise ValueError("native runtime unavailable")
        launchd = LaunchdSupervisor(
            root=_SELF_CHECK_ROOT,
            checkout_root=None,
            python_executable=str(executable),
            unit_directory=_SELF_CHECK_ROOT / "launchd",
            user_id=0,
            runtime_kind=NATIVE_ARTIFACT_KIND,
        )
        systemd = SystemdSupervisor(
            root=_SELF_CHECK_ROOT,
            checkout_root=None,
            python_executable=str(executable),
            unit_directory=_SELF_CHECK_ROOT / "systemd",
            runtime_kind=NATIVE_ARTIFACT_KIND,
        )
        launchd_payload = cast(dict[str, object], plistlib.loads(launchd.render().encode()))
        daemon_command = [
            str(executable),
            _DAEMON_COMMAND,
            "--root",
            str(_SELF_CHECK_ROOT),
        ]
        systemd_payload = systemd.render()
        if (
            launchd_payload.get("ProgramArguments") != daemon_command
            or "PYTHONPATH" in systemd_payload
            or " -m " in systemd_payload
            or tuple(_worker_command())
            != (str(executable), _CONNECTOR_WORKER_COMMAND)
        ):
            raise ValueError("native runtime unavailable")
        payload: dict[str, object] = {
            "artifact_kind": NATIVE_ARTIFACT_KIND,
            "connector_child": "direct-frozen-executable",
            "daemon_launch": "direct-frozen-executable",
            "frozen": True,
            "package_resources": "available",
            "platform": native_platform_tag(),
            "status": "ok",
        }
    except Exception:
        payload = {"status": "failed"}
        exit_code = 1
    else:
        exit_code = 0
    sys.stdout.write(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["main"]
