from __future__ import annotations

import socket
from importlib import import_module
from pathlib import Path
from typing import cast

import pytest


def _extend_unmoved_workspace_packages() -> None:
    repository_root = Path(__file__).resolve().parents[1]
    source_root = repository_root / "src/open_brain"
    for name in ("cli", "integrations", "services"):
        source = source_root / name
        if not source.is_dir():
            continue
        package = import_module(f"open_brain.{name}")
        search_locations = cast(list[str], package.__path__)
        if str(source) not in search_locations:
            search_locations.append(str(source))


_extend_unmoved_workspace_packages()


@pytest.fixture(autouse=True)
def deny_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def blocked(*args: object, **kwargs: object) -> None:
        raise AssertionError("network access is forbidden in the Phase 2 test suite")

    for name in ("connect", "connect_ex", "bind", "listen"):
        monkeypatch.setattr(socket.socket, name, blocked)
    for name in ("getaddrinfo", "gethostbyname", "gethostbyname_ex", "gethostbyaddr"):
        monkeypatch.setattr(socket, name, blocked)
