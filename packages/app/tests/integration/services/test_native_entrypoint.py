from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

import open_brain.services.native_entrypoint as native_entrypoint


def test_native_entrypoint_routes_cli_daemon_and_connector_worker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: list[tuple[str, object]] = []

    def cli(argv: tuple[str, ...], *, environment: dict[str, str]) -> int:
        observed.append(("cli", (argv, environment)))
        return 11

    def daemon(
        argv: tuple[str, ...],
        *,
        environment: dict[str, str],
    ) -> int:
        observed.append(("daemon", (argv, environment)))
        return 12

    def worker() -> int:
        observed.append(("worker", None))
        return 13

    monkeypatch.setattr(native_entrypoint, "run_cli", cli)
    monkeypatch.setattr(native_entrypoint, "run_appliance_daemon", daemon)
    monkeypatch.setattr(native_entrypoint, "run_connector_worker", worker)
    environment = {"OPEN_BRAIN_ROOT": "/tmp/brain"}

    assert native_entrypoint.main(("--version",), environment=environment) == 11
    assert (
        native_entrypoint.main(
            ("__appliance-daemon", "--root", "/tmp/brain"),
            environment=environment,
        )
        == 12
    )
    assert native_entrypoint.main(("__connector-worker",), environment=environment) == 13
    assert observed == [
        ("cli", (("--version",), environment)),
        ("daemon", (("--root", "/tmp/brain"), environment)),
        ("worker", None),
    ]


def test_native_self_check_exercises_packaged_resources_and_direct_commands(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    executable = Path("/opt/open-brain/current/open-brain")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(executable))
    monkeypatch.setattr(native_entrypoint, "native_platform_tag", lambda: "macos-arm64")

    assert native_entrypoint.main(("__native-self-check",), environment={}) == 0

    output = capsys.readouterr().out
    payload = json.loads(output)
    assert payload == {
        "artifact_kind": "native-onedir",
        "connector_child": "direct-frozen-executable",
        "daemon_launch": "direct-frozen-executable",
        "frozen": True,
        "package_resources": "available",
        "platform": "macos-arm64",
        "status": "ok",
    }
    assert str(executable) not in output
