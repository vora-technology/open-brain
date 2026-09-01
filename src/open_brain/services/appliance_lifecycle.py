from __future__ import annotations

from pathlib import Path

from .appliance_daemon import ControlReceipt, ControlRequest, request_control


def submit_control_request(root: Path, request: ControlRequest) -> ControlReceipt:
    if not isinstance(root, Path) or not isinstance(request, ControlRequest):
        raise ValueError("invalid appliance control request")
    return request_control(root, request)
