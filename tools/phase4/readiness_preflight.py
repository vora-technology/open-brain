"""Read-only Phase 4 readiness aggregation with bounded public output."""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from hashlib import sha256
from typing import Final, Self

PHASE4_READINESS_WAVES: Final = ("P4-W5", "P4-W6", "P4-W7", "P4-W8", "P4-W9")

_RECEIPT = re.compile(r"rct_v1_[0-9a-f]{64}")
_RESULT_KEYS = frozenset(
    {
        "all_ready",
        "disk_capacity_ready",
        "disk_capacity_receipt",
        "linux_x86_64_ready",
        "linux_x86_64_receipt",
        "macos_arm64_ready",
        "macos_arm64_receipt",
        "notarization_ready",
        "notarization_receipt",
        "preflight_receipt",
        "recovery_access_ready",
        "recovery_access_receipt",
        "signing_ready",
        "signing_receipt",
    }
)


@dataclass(frozen=True, slots=True)
class ReadinessObservation:
    """One private probe's closed result, stripped to readiness and an opaque receipt."""

    ready: bool
    receipt: str

    def __post_init__(self) -> None:
        if type(self.ready) is not bool or not _is_receipt(self.receipt):
            raise ValueError("invalid readiness observation")


ReadinessProbe = Callable[[], ReadinessObservation]


@dataclass(frozen=True, slots=True)
class ReadinessProbes:
    """Injected read-only probes; private implementations stay outside this repository."""

    signing: ReadinessProbe
    notarization: ReadinessProbe
    macos_arm64: ReadinessProbe
    linux_x86_64: ReadinessProbe
    disk_capacity: ReadinessProbe
    recovery_access: ReadinessProbe

    def __post_init__(self) -> None:
        if not all(
            callable(probe)
            for probe in (
                self.signing,
                self.notarization,
                self.macos_arm64,
                self.linux_x86_64,
                self.disk_capacity,
                self.recovery_access,
            )
        ):
            raise ValueError("invalid readiness probes")


@dataclass(frozen=True, slots=True)
class ReadinessResult:
    """Reusable six-check snapshot whose public values are closed and metadata-only."""

    signing: ReadinessObservation
    notarization: ReadinessObservation
    macos_arm64: ReadinessObservation
    linux_x86_64: ReadinessObservation
    disk_capacity: ReadinessObservation
    recovery_access: ReadinessObservation
    preflight_receipt: str

    def __post_init__(self) -> None:
        observations = self._observations()
        if (
            any(type(value) is not ReadinessObservation for value in observations.values())
            or not _is_receipt(self.preflight_receipt)
            or self.preflight_receipt != _aggregate_receipt(observations)
        ):
            raise ValueError("invalid readiness result")

    @property
    def all_ready(self) -> bool:
        return all(observation.ready for observation in self._observations().values())

    def for_wave(self, wave: str) -> Self:
        """Reuse this exact snapshot at one governed P4-W5 through P4-W9 gate."""
        if wave not in PHASE4_READINESS_WAVES:
            raise ValueError("invalid readiness wave")
        return self

    def to_dict(self) -> dict[str, bool | str]:
        """Return only booleans and validated opaque receipt identifiers."""
        return {
            "all_ready": self.all_ready,
            "disk_capacity_ready": self.disk_capacity.ready,
            "disk_capacity_receipt": self.disk_capacity.receipt,
            "linux_x86_64_ready": self.linux_x86_64.ready,
            "linux_x86_64_receipt": self.linux_x86_64.receipt,
            "macos_arm64_ready": self.macos_arm64.ready,
            "macos_arm64_receipt": self.macos_arm64.receipt,
            "notarization_ready": self.notarization.ready,
            "notarization_receipt": self.notarization.receipt,
            "preflight_receipt": self.preflight_receipt,
            "recovery_access_ready": self.recovery_access.ready,
            "recovery_access_receipt": self.recovery_access.receipt,
            "signing_ready": self.signing.ready,
            "signing_receipt": self.signing.receipt,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> ReadinessResult:
        """Validate and restore one bounded snapshot without rerunning private probes."""
        if not isinstance(value, Mapping) or set(value) != _RESULT_KEYS:
            raise ValueError("invalid readiness result")
        try:
            result = cls._from_values(value)
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("invalid readiness result") from error
        if value["all_ready"] is not result.all_ready:
            raise ValueError("invalid readiness result")
        return result

    @classmethod
    def _from_values(cls, value: Mapping[str, object]) -> ReadinessResult:
        def observation(name: str) -> ReadinessObservation:
            ready = value[f"{name}_ready"]
            receipt = value[f"{name}_receipt"]
            if type(ready) is not bool or not isinstance(receipt, str):
                raise ValueError("invalid readiness result")
            return ReadinessObservation(ready=ready, receipt=receipt)

        aggregate = value["preflight_receipt"]
        if not isinstance(aggregate, str):
            raise ValueError("invalid readiness result")
        return cls(
            signing=observation("signing"),
            notarization=observation("notarization"),
            macos_arm64=observation("macos_arm64"),
            linux_x86_64=observation("linux_x86_64"),
            disk_capacity=observation("disk_capacity"),
            recovery_access=observation("recovery_access"),
            preflight_receipt=aggregate,
        )

    def _observations(self) -> dict[str, ReadinessObservation]:
        return {
            "disk_capacity": self.disk_capacity,
            "linux_x86_64": self.linux_x86_64,
            "macos_arm64": self.macos_arm64,
            "notarization": self.notarization,
            "recovery_access": self.recovery_access,
            "signing": self.signing,
        }


def run_readiness_preflight(probes: ReadinessProbes) -> ReadinessResult:
    """Run each injected read-only probe once and close over all raw failure detail."""
    if type(probes) is not ReadinessProbes:
        raise ValueError("invalid readiness probes")
    observations = {
        "signing": _observe("signing", probes.signing),
        "notarization": _observe("notarization", probes.notarization),
        "macos_arm64": _observe("macos_arm64", probes.macos_arm64),
        "linux_x86_64": _observe("linux_x86_64", probes.linux_x86_64),
        "disk_capacity": _observe("disk_capacity", probes.disk_capacity),
        "recovery_access": _observe("recovery_access", probes.recovery_access),
    }
    return ReadinessResult(
        signing=observations["signing"],
        notarization=observations["notarization"],
        macos_arm64=observations["macos_arm64"],
        linux_x86_64=observations["linux_x86_64"],
        disk_capacity=observations["disk_capacity"],
        recovery_access=observations["recovery_access"],
        preflight_receipt=_aggregate_receipt(observations),
    )


def _observe(name: str, probe: ReadinessProbe) -> ReadinessObservation:
    try:
        observation = probe()
        if type(observation) is not ReadinessObservation:
            raise ValueError("invalid readiness observation")
        return observation
    except (Exception, SystemExit):
        return ReadinessObservation(
            ready=False,
            receipt=_opaque_receipt({"check": name, "state": "unavailable"}),
        )


def _aggregate_receipt(observations: Mapping[str, ReadinessObservation]) -> str:
    return _opaque_receipt(
        {
            name: {"ready": observation.ready, "receipt": observation.receipt}
            for name, observation in sorted(observations.items())
        }
    )


def _opaque_receipt(value: Mapping[str, object]) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")
    return "rct_v1_" + sha256(payload).hexdigest()


def _is_receipt(value: object) -> bool:
    return isinstance(value, str) and _RECEIPT.fullmatch(value) is not None


__all__ = [
    "PHASE4_READINESS_WAVES",
    "ReadinessObservation",
    "ReadinessProbe",
    "ReadinessProbes",
    "ReadinessResult",
    "run_readiness_preflight",
]
