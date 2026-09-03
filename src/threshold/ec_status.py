"""Read the sanitized world-readable EC lifecycle status summary.

The lifecycle script writes a bounded, world-readable ``status`` file after
every state-changing verb.  This module reads it and constructs an
:class:`~threshold.ec_state.ECStatus` value that the presentation layer
may safely use without holding privileges.

Only these fields appear in the sanitized summary:

- ``setup_state``   (available | pending_reboot | unavailable)
- ``reason``        (optional; structured reason when unavailable)
- ``maintenance``   (ok | pending | failed)
- ``charge_threshold`` (the machine-wide policy value; may be empty)

Privileged evidence (boot_id, kernel version, DMI paths, DKMS source
locations) remains in the root-owned state file and lifecycle log and
is never exposed through this reader.
"""

from pathlib import Path
from typing import Optional

from threshold.ec_state import (
    ECSetupState,
    ECMaintenanceStatus,
    ECSetupReason,
    ECStatus,
)

EC_STATUS_FILE = Path("/var/lib/threshold/ec/status")

_SETUP_STATE_MAP = {
    "available": ECSetupState.AVAILABLE,
    "pending_reboot": ECSetupState.PENDING_REBOOT,
    "unavailable": ECSetupState.UNAVAILABLE,
}

_MAINTENANCE_MAP = {
    "ok": ECMaintenanceStatus.OK,
    "pending": ECMaintenanceStatus.PENDING,
    "failed": ECMaintenanceStatus.FAILED,
}

_REASON_MAP = {r.value: r for r in ECSetupReason}


def read_ec_status(path: Optional[Path] = None) -> Optional[ECStatus]:
    """Read the sanitized status file and return an :class:`ECStatus`.

    Returns ``None`` when the file is absent or unreadable (e.g. before
    the first lifecycle verb has run, or on a non-EC system).
    """
    status_path = path or EC_STATUS_FILE
    try:
        raw = status_path.read_text(encoding="utf-8")
    except OSError:
        return None

    kv: dict[str, str] = {}
    for line in raw.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            kv[k.strip()] = v.strip()

    raw_state = kv.get("setup_state")
    if raw_state is None:
        return None

    setup_state = _SETUP_STATE_MAP.get(raw_state)
    if setup_state is None:
        return None

    raw_reason = kv.get("reason") or None
    reason: Optional[ECSetupReason] = None
    if raw_reason is not None:
        reason = _REASON_MAP.get(raw_reason)

    raw_maintenance = kv.get("maintenance", "ok")
    maintenance = _MAINTENANCE_MAP.get(raw_maintenance, ECMaintenanceStatus.OK)

    return ECStatus(
        state=setup_state,
        reason=reason,
        maintenance=maintenance,
    )
