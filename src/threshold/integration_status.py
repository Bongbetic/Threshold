"""Detect native boot-reconciliation integration without changing it."""

from pathlib import Path
from typing import Optional

RUNIT_SERVICE = Path("/etc/sv/threshold-boot-reconcile")
RUNIT_ENABLED_LOCATIONS = (
    Path("/var/service/threshold-boot-reconcile"),
    Path("/etc/runit/runsvdir/default/threshold-boot-reconcile"),
)
RUNIT_ENABLE_COMMAND = (
    "sudo ln -s /etc/sv/threshold-boot-reconcile /var/service/"
)


def detect_boot_reconciliation(
    service: Path = RUNIT_SERVICE,
    enabled_locations: tuple[Path, ...] = RUNIT_ENABLED_LOCATIONS,
) -> tuple[Optional[bool], Optional[str]]:
    """Return runit enablement and guidance, or ``(None, None)`` off Void.

    The application deliberately observes this privileged configuration; it
    never modifies it.
    """
    if not service.is_dir():
        return None, None
    enabled = any(path.is_symlink() or path.exists() for path in enabled_locations)
    return enabled, None if enabled else RUNIT_ENABLE_COMMAND
