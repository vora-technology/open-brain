from __future__ import annotations

import json
from collections.abc import Callable
from hashlib import sha256

import pytest

from tools.phase4.readiness_preflight import (
    PHASE4_READINESS_WAVES,
    ReadinessObservation,
    ReadinessProbes,
    ReadinessResult,
    run_readiness_preflight,
)


def _receipt(label: str) -> str:
    return "rct_v1_" + sha256(label.encode("utf-8")).hexdigest()


def test_one_read_only_snapshot_covers_every_required_readiness_check() -> None:
    calls: list[str] = []

    def probe(name: str, ready: bool = True) -> Callable[[], ReadinessObservation]:
        def observe() -> ReadinessObservation:
            calls.append(name)
            return ReadinessObservation(ready=ready, receipt=_receipt(name))

        return observe

    result = run_readiness_preflight(
        ReadinessProbes(
            signing=probe("signing"),
            notarization=probe("notarization"),
            macos_arm64=probe("macos_arm64"),
            linux_x86_64=probe("linux_x86_64"),
            disk_capacity=probe("disk_capacity"),
            recovery_access=probe("recovery_access", ready=False),
        )
    )

    assert calls == [
        "signing",
        "notarization",
        "macos_arm64",
        "linux_x86_64",
        "disk_capacity",
        "recovery_access",
    ]
    assert result.all_ready is False
    assert result.to_dict() == {
        "all_ready": False,
        "disk_capacity_ready": True,
        "disk_capacity_receipt": _receipt("disk_capacity"),
        "linux_x86_64_ready": True,
        "linux_x86_64_receipt": _receipt("linux_x86_64"),
        "macos_arm64_ready": True,
        "macos_arm64_receipt": _receipt("macos_arm64"),
        "notarization_ready": True,
        "notarization_receipt": _receipt("notarization"),
        "preflight_receipt": result.preflight_receipt,
        "recovery_access_ready": False,
        "recovery_access_receipt": _receipt("recovery_access"),
        "signing_ready": True,
        "signing_receipt": _receipt("signing"),
    }


def test_snapshot_is_reused_through_p4_w9_without_rerunning_probes() -> None:
    calls = 0

    def observe() -> ReadinessObservation:
        nonlocal calls
        calls += 1
        return ReadinessObservation(ready=True, receipt=_receipt(str(calls)))

    result = run_readiness_preflight(
        ReadinessProbes(
            signing=observe,
            notarization=observe,
            macos_arm64=observe,
            linux_x86_64=observe,
            disk_capacity=observe,
            recovery_access=observe,
        )
    )
    restored = ReadinessResult.from_dict(json.loads(json.dumps(result.to_dict(), sort_keys=True)))

    assert calls == 6
    assert PHASE4_READINESS_WAVES == ("P4-W5", "P4-W6", "P4-W7", "P4-W8", "P4-W9")
    for wave in PHASE4_READINESS_WAVES:
        assert restored.for_wave(wave) is restored
    assert calls == 6


def test_probe_failures_emit_only_booleans_and_opaque_receipts() -> None:
    canaries = (
        "/private/recovery/path",
        "credential=synthetic-secret",
        "builder.internal.example",
    )

    def failed() -> ReadinessObservation:
        raise RuntimeError(" ".join(canaries))

    result = run_readiness_preflight(
        ReadinessProbes(
            signing=failed,
            notarization=failed,
            macos_arm64=failed,
            linux_x86_64=failed,
            disk_capacity=failed,
            recovery_access=failed,
        )
    )
    rendered = json.dumps(result.to_dict(), sort_keys=True)

    assert result.all_ready is False
    assert all(isinstance(value, bool) or _is_receipt(value) for value in result.to_dict().values())
    assert not any(canary in rendered for canary in canaries)


@pytest.mark.parametrize(
    "value",
    [
        {"ready": True, "receipt": "/private/path"},
        {"ready": 1, "receipt": _receipt("invalid-bool")},
        {"ready": False, "receipt": "credential=synthetic-secret"},
    ],
)
def test_observation_rejects_non_opaque_or_non_boolean_values(
    value: dict[str, object],
) -> None:
    with pytest.raises(ValueError, match="readiness observation"):
        ReadinessObservation(**value)  # type: ignore[arg-type]


def test_snapshot_rejects_unknown_wave_and_tampered_aggregate_receipt() -> None:
    observation = ReadinessObservation(ready=True, receipt=_receipt("ready"))
    result = run_readiness_preflight(
        ReadinessProbes(
            signing=lambda: observation,
            notarization=lambda: observation,
            macos_arm64=lambda: observation,
            linux_x86_64=lambda: observation,
            disk_capacity=lambda: observation,
            recovery_access=lambda: observation,
        )
    )

    with pytest.raises(ValueError, match="readiness wave"):
        result.for_wave("P4-W10")
    with pytest.raises(ValueError, match="readiness result"):
        ReadinessResult.from_dict({**result.to_dict(), "preflight_receipt": _receipt("tampered")})


def _is_receipt(value: object) -> bool:
    return (
        isinstance(value, str)
        and value.startswith("rct_v1_")
        and len(value) == len("rct_v1_") + 64
        and all(character in "0123456789abcdef" for character in value.removeprefix("rct_v1_"))
    )
