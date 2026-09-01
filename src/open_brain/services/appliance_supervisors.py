"""Deterministic launchd and systemd lifecycle adapters for one appliance daemon."""

from __future__ import annotations

import plistlib
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Final

_LABEL: Final[str] = "org.open-brain.appliance-daemon"
_SYSTEMD_UNIT: Final[str] = "open-brain-appliance.service"
_SUPERVISOR_FAILURE: Final[str] = "appliance supervisor action failed"

FileWriter = Callable[[Path, str], None]
FileRemover = Callable[[Path], None]
CommandRunner = Callable[[tuple[str, ...]], str]


class SupervisorCommandError(RuntimeError):
    """A host-supervisor action failed after deterministic local preparation."""


def _daemon_command(root: Path, python_executable: str) -> tuple[str, ...]:
    return (
        python_executable,
        "-m",
        "open_brain.services.appliance_daemon",
        "--root",
        str(root),
    )


def _launchd_target(user_id: int) -> str:
    return f"gui/{user_id}/{_LABEL}"


def _validate_supervisor_inputs(
    root: Path,
    checkout_root: Path,
    python_executable: str,
    unit_directory: Path,
) -> None:
    if (
        not isinstance(root, Path)
        or not isinstance(checkout_root, Path)
        or not isinstance(unit_directory, Path)
        or not root.is_absolute()
        or not checkout_root.is_absolute()
        or not unit_directory.is_absolute()
        or not isinstance(python_executable, str)
        or not python_executable
        or not Path(python_executable).is_absolute()
        or _contains_unsafe_text(python_executable)
        or any(_contains_unsafe_text(str(path)) for path in (root, checkout_root, unit_directory))
    ):
        raise ValueError("invalid appliance supervisor configuration")


def _write_file(path: Path, content: str) -> None:
    del path, content
    raise _supervisor_failure()


def _remove_file(path: Path) -> None:
    del path
    raise _supervisor_failure()


def _run_command(argv: tuple[str, ...]) -> str:
    del argv
    raise SupervisorCommandError(_SUPERVISOR_FAILURE)


def _contains_unsafe_text(value: str) -> bool:
    return any(ord(character) < 32 or ord(character) == 127 for character in value)


def _systemd_escape(value: str) -> str:
    escaped: list[str] = []
    for character in value:
        if character == "%":
            escaped.append("%%")
        elif character == "\\":
            escaped.append("\\\\")
        elif character == " ":
            escaped.append("\\x20")
        elif character == '"':
            escaped.append("\\x22")
        elif character == "'":
            escaped.append("\\x27")
        else:
            escaped.append(character)
    return "".join(escaped)


def _supervisor_failure() -> SupervisorCommandError:
    return SupervisorCommandError(_SUPERVISOR_FAILURE)


@dataclass(frozen=True, slots=True)
class LaunchdSupervisor:
    root: Path
    checkout_root: Path
    python_executable: str
    unit_directory: Path
    user_id: int
    write_file: FileWriter = _write_file
    remove_file: FileRemover = _remove_file
    run_command: CommandRunner = _run_command

    def __post_init__(self) -> None:
        _validate_supervisor_inputs(
            self.root,
            self.checkout_root,
            self.python_executable,
            self.unit_directory,
        )
        if (
            not isinstance(self.user_id, int)
            or isinstance(self.user_id, bool)
            or self.user_id < 0
        ):
            raise ValueError("invalid launchd user id")

    @property
    def unit_path(self) -> Path:
        return self.unit_directory / f"{_LABEL}.plist"

    @property
    def unit_name(self) -> str:
        return _LABEL

    def render(self) -> str:
        payload = {
            "EnvironmentVariables": {"PYTHONPATH": str(self.checkout_root / "src")},
            "KeepAlive": True,
            "Label": self.unit_name,
            "ProgramArguments": list(_daemon_command(self.root, self.python_executable)),
            "RunAtLoad": False,
            "StandardErrorPath": str(self.root / ".open-brain" / "run" / "daemon.stderr.log"),
            "StandardOutPath": str(self.root / ".open-brain" / "run" / "daemon.stdout.log"),
            "Umask": 0o077,
            "WorkingDirectory": str(self.checkout_root),
        }
        return plistlib.dumps(payload, sort_keys=True).decode("utf-8")

    def install(self) -> None:
        written = False
        try:
            self.write_file(self.unit_path, self.render())
            written = True
            self.run_command(("launchctl", "bootstrap", f"gui/{self.user_id}", str(self.unit_path)))
        except Exception as error:
            if written:
                with suppress(Exception):
                    self.remove_file(self.unit_path)
            raise _supervisor_failure() from error

    def start(self) -> str:
        return self.run_command(("launchctl", "kickstart", "-k", _launchd_target(self.user_id)))

    def stop(self) -> str:
        return self.run_command(("launchctl", "kill", "TERM", _launchd_target(self.user_id)))

    def restart(self) -> None:
        self.stop()
        self.start()

    def status(self) -> str:
        return self.run_command(("launchctl", "print", _launchd_target(self.user_id)))

    def remove(self) -> None:
        self.run_command(("launchctl", "bootout", f"gui/{self.user_id}", str(self.unit_path)))
        self.remove_file(self.unit_path)


@dataclass(frozen=True, slots=True)
class SystemdSupervisor:
    root: Path
    checkout_root: Path
    python_executable: str
    unit_directory: Path
    write_file: FileWriter = _write_file
    remove_file: FileRemover = _remove_file
    run_command: CommandRunner = _run_command

    def __post_init__(self) -> None:
        _validate_supervisor_inputs(
            self.root,
            self.checkout_root,
            self.python_executable,
            self.unit_directory,
        )

    @property
    def unit_path(self) -> Path:
        return self.unit_directory / self.unit_name

    @property
    def unit_name(self) -> str:
        return _SYSTEMD_UNIT

    def render(self) -> str:
        command = " ".join(
            _systemd_escape(part)
            for part in _daemon_command(self.root, self.python_executable)
        )
        return "\n".join(
            (
                "[Unit]",
                "Description=Open Brain appliance daemon",
                "",
                "[Service]",
                "Type=simple",
                f"Environment=PYTHONPATH={_systemd_escape(str(self.checkout_root / 'src'))}",
                f"ExecStart={command}",
                f"WorkingDirectory={_systemd_escape(str(self.checkout_root))}",
                "Restart=on-failure",
                "",
                "[Install]",
                "WantedBy=default.target",
            )
        ) + "\n"

    def install(self) -> None:
        written = False
        try:
            self.write_file(self.unit_path, self.render())
            written = True
            self.run_command(("systemctl", "--user", "daemon-reload"))
            self.run_command(("systemctl", "--user", "enable", self.unit_name))
        except Exception as error:
            if written:
                with suppress(Exception):
                    self.remove_file(self.unit_path)
            raise _supervisor_failure() from error

    def start(self) -> str:
        return self.run_command(("systemctl", "--user", "start", self.unit_name))

    def stop(self) -> str:
        return self.run_command(("systemctl", "--user", "stop", self.unit_name))

    def restart(self) -> str:
        return self.run_command(("systemctl", "--user", "restart", self.unit_name))

    def status(self) -> str:
        return self.run_command(("systemctl", "--user", "status", self.unit_name, "--no-pager"))

    def remove(self) -> None:
        self.run_command(("systemctl", "--user", "disable", "--now", self.unit_name))
        self.remove_file(self.unit_path)
        self.run_command(("systemctl", "--user", "daemon-reload"))


__all__ = [
    "LaunchdSupervisor",
    "SupervisorCommandError",
    "SystemdSupervisor",
]
