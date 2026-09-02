"""EC setup state domain model.

Separates three concepts the presentation must never conflate:
- control mode (live capability: EC msi-ec / vendor sysfs / notification only)
- EC setup state (available / pending_reboot / unavailable) with a
  structured reason when unavailable
- EC maintenance status (update/repair health: ok / pending / failed)

The machine-wide charge threshold lives in GSettings (Config) and is
independent of any of these; the active threshold is the live sysfs value.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ECSetupState(Enum):
    AVAILABLE = "available"
    PENDING_REBOOT = "pending_reboot"
    UNAVAILABLE = "unavailable"


class ECSetupReason(Enum):
    """Structured reasons for `unavailable`; each maps to presentation."""

    NOT_MSI_HARDWARE = "not_msi_hardware"
    DKMS_MISSING = "dkms_missing"
    KERNEL_HEADERS_MISSING = "kernel_headers_missing"
    BUILD_FAILED = "build_failed"
    LOAD_FAILED = "load_failed"
    LOAD_FAILED_SECURE_BOOT = "load_failed_secure_boot"
    FIRMWARE_UNSUPPORTED = "firmware_unsupported"
    VERIFICATION_FAILED = "verification_failed"
    THRESHOLD_INTERFACE_MISSING = "threshold_interface_missing"

    # Presentation mapping: repair guidance / retry / diagnostics-only.
    @property
    def is_repairable(self) -> bool:
        return self not in (
            ECSetupReason.NOT_MSI_HARDWARE,
            ECSetupReason.FIRMWARE_UNSUPPORTED,
        )


class ECMaintenanceStatus(Enum):
    """Health of the last EC update/repair attempt, separate from setup."""

    OK = "ok"
    PENDING = "pending"
    FAILED = "failed"


class PendingAction(Enum):
    """Reboot-completable EC actions; the only permitted pending kinds."""

    SETUP = "setup"
    UPDATE = "update"
    REPAIR = "repair"
    REMOVAL = "removal"


@dataclass(frozen=True)
class PendingReboot:
    """A known reboot-completable EC action.

    Consumed by the first different boot (boot reconciliation).
    """

    boot_id: str
    target_kernel: str
    action: PendingAction


@dataclass(frozen=True)
class ECStatus:
    """EC setup + maintenance snapshot (independent of control mode)."""

    state: ECSetupState
    reason: Optional[ECSetupReason] = None
    pending: Optional[PendingReboot] = None
    maintenance: ECMaintenanceStatus = ECMaintenanceStatus.OK

    def __post_init__(self):
        if self.state == ECSetupState.UNAVAILABLE and self.reason is None:
            raise ValueError("unavailable EC setup requires a structured reason")

    @property
    def is_repairable(self) -> bool:
        return self.reason is None or self.reason.is_repairable

    @property
    def presentation(self) -> str:
        """Which guidance family the UI shows (neutral | reboot | ...)."""
        if self.state == ECSetupState.PENDING_REBOOT:
            return "reboot"
        if self.state == ECSetupState.UNAVAILABLE:
            if self.reason is not None and self.reason.is_repairable:
                return "repairable"
            return "neutral"
        if self.maintenance == ECMaintenanceStatus.FAILED:
            return "maintenance_failed"
        if self.maintenance == ECMaintenanceStatus.PENDING:
            return "maintenance_pending"
        return "working"


def consume_pending_reboot(
    pending: PendingReboot, current_boot_id: str
) -> Optional[PendingReboot]:
    """Consume a pending-reboot record on the first different boot.

    Same boot identity: the attempt has not happened yet — record persists.
    Different boot identity: the attempt was consumed; boot reconciliation
    now produces `available` or a reasoned `unavailable` outcome.
    """
    if pending.boot_id == current_boot_id:
        return pending
    return None
