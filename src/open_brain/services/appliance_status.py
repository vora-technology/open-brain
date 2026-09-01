"""Bounded appliance status receipt over the read-only maintenance surface."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from open_brain.engine import MaintenanceSnapshot, read_maintenance_snapshot
from open_brain.profile import open_existing_single_user_local


@dataclass(frozen=True, slots=True)
class ApplianceStatusReceipt:
    tenant_id: str
    owner_actor_id: str
    provider_mode: str
    maintenance: MaintenanceSnapshot

    def to_dict(self) -> dict[str, object]:
        return {
            "status": "ok",
            "tenant_id": self.tenant_id,
            "owner_actor_id": self.owner_actor_id,
            "provider_mode": self.provider_mode,
            "maintenance": self.maintenance.to_dict(),
        }


def read_appliance_status(root: Path) -> ApplianceStatusReceipt:
    profile = open_existing_single_user_local(root)
    return ApplianceStatusReceipt(
        tenant_id=profile.tenant_id,
        owner_actor_id=profile.owner_actor_id,
        provider_mode=profile.provider_mode.value,
        maintenance=read_maintenance_snapshot(profile),
    )
