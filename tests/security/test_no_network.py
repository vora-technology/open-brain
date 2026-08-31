from __future__ import annotations

import socket

import pytest


@pytest.mark.parametrize("operation", ["connect", "connect_ex", "bind", "listen"])
def test_socket_operations_are_blocked(operation: str) -> None:
    with socket.socket() as sock, pytest.raises(AssertionError, match="network access"):
        getattr(sock, operation)(("example.invalid", 443))


def test_dns_operations_are_blocked() -> None:
    with pytest.raises(AssertionError, match="network access"):
        socket.getaddrinfo("example.invalid", 443)
