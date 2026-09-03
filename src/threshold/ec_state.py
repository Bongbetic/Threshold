"""EC setup state domain model.

Separates three concepts the presentation must never conflate:
- control mode (live capability: EC msi-ec / vendor sysfs / notification only)
- EC setup state (available / pending_reboot / unavailable) with a
  structured reason when unavailable
- EC maintenance status (update/repair health: ok / pending / failed)

The machine-wide charge threshold lives in GSettings (Config) and is
independent of any of these; the active threshold is the live sysfs value.

Kernel lifecycle (issue #92):
- A kernel becomes known-good only after a real boot, live capability
  verification, and successful reconciliation.
- Known-good markers are per-kernel files in the EC state directory.
- Failed new-kernel builds preserve successful older kernel records.
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
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
    def recovery_actions(self) -> tuple[str, ...]:
        """Actions the UI may offer, mapped from state; never automatic."""
        if self.state == ECSetupState.PENDING_REBOOT:
            return ("reboot",)
        if self.state == ECSetupState.UNAVAILABLE:
            if self.reason is not None and self.reason.is_repairable:
                return ("repair", "diagnostics")
            return ("diagnostics",)
        if self.maintenance == ECMaintenanceStatus.FAILED:
            return ("repair", "diagnostics")
        if self.maintenance == ECMaintenanceStatus.PENDING:
            return ("reboot", "diagnostics")
        return ()

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


# ── Kernel lifecycle (issue #92) ──────────────────────────────────────────

EC_KERNEL_DIR = Path("/var/lib/threshold/ec/kernels")


@dataclass(frozen=True)
class KernelRecord:
    """A per-kernel lifecycle record with known-good status.

    A kernel becomes known-good only after a real boot, live capability
    verification, and successful reconciliation. The marker file is
    never created before all three conditions are satisfied.
    """

    kernel: str
    known_good: bool
    log_lines: tuple[str, ...] = ()

    @classmethod
    def read_from_dir(cls, kernel_dir: Path, kernel: str) -> "KernelRecord":
        """Read a kernel record from the lifecycle directory."""
        log_file = kernel_dir / f"{kernel}.log"
        known_good_file = kernel_dir / f"{kernel}.known-good"

        log_lines: tuple[str, ...] = ()
        if log_file.exists():
            try:
                log_lines = tuple(log_file.read_text(encoding="utf-8").splitlines())
            except OSError:
                pass

        known_good = known_good_file.exists()

        return cls(kernel=kernel, known_good=known_good, log_lines=log_lines)


def read_known_good_kernels(kernel_dir: Optional[Path] = None) -> tuple[str, ...]:
    """Return kernel versions that have been verified as known-good.

    A kernel is known-good when its ``.known-good`` marker file exists
    in the kernel lifecycle directory.
    """
    kdir = kernel_dir or EC_KERNEL_DIR
    if not kdir.is_dir():
        return ()

    kernels: list[str] = []
    for marker in sorted(kdir.glob("*.known-good")):
        kernels.append(marker.stem)
    return tuple(kernels)


def read_kernel_records(kernel_dir: Optional[Path] = None) -> tuple[KernelRecord, ...]:
    """Read all kernel records from the lifecycle directory."""
    kdir = kernel_dir or EC_KERNEL_DIR
    if not kdir.is_dir():
        return ()

    records: list[KernelRecord] = []
    for log_file in sorted(kdir.glob("*.log")):
        kernel = log_file.stem
        records.append(KernelRecord.read_from_dir(kdir, kernel))
    return tuple(records)


def get_oldest_known_good(
    kernel_dir: Optional[Path] = None,
) -> Optional[str]:
    """Return the oldest known-good kernel version, or None.

    Used for fallback when a new kernel build fails — preserves the
    working older kernel.
    """
    kg = read_known_good_kernels(kernel_dir)
    return kg[0] if kg else None
