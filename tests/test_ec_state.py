"""EC setup state domain: three states, reasons, maintenance status.

Tests assert the externally visible state vocabulary from issue #86:
EC setup state is independent of control mode and maintenance status;
unavailable always carries a structured reason; pending_reboot records
a reboot-completable action and is consumed by the next different boot.
"""

import pytest

from threshold.ec_state import (
    PendingAction,
    ECSetupState,
    ECSetupReason,
    ECMaintenanceStatus,
    PendingReboot,
    ECStatus,
    consume_pending_reboot,
)


def test_setup_state_has_exactly_three_values():
    assert {s.value for s in ECSetupState} == {
        "available",
        "pending_reboot",
        "unavailable",
    }


def test_control_mode_values_unchanged():
    from threshold.battery import ControlMode
    assert {m.value for m in ControlMode} == {"msi-ec", "sysfs", "notify"}


def test_maintenance_status_has_three_values():
    assert {s.value for s in ECMaintenanceStatus} == {
        "ok",
        "pending",
        "failed",
    }


def test_unavailable_requires_reason():
    with pytest.raises(ValueError):
        ECStatus(state=ECSetupState.UNAVAILABLE, reason=None)


def test_available_default_reason_is_none():
    status = ECStatus(state=ECSetupState.AVAILABLE)
    assert status.reason is None
    assert status.maintenance == ECMaintenanceStatus.OK


def test_unavailable_carries_structured_reason():
    status = ECStatus(
        state=ECSetupState.UNAVAILABLE,
        reason=ECSetupReason.KERNEL_HEADERS_MISSING,
    )
    assert status.reason.value == "kernel_headers_missing"
    assert status.is_repairable


def test_neutral_reason_maps_to_neutral_presentation():
    status = ECStatus(
        state=ECSetupState.UNAVAILABLE,
        reason=ECSetupReason.NOT_MSI_HARDWARE,
    )
    assert not status.is_repairable
    assert status.presentation == "neutral"


def test_pending_reboot_records_boot_identity_and_action():
    pending = PendingReboot(
        boot_id="abc123",
        target_kernel="6.11.0",
        action=PendingAction.SETUP,
    )
    status = ECStatus(
        state=ECSetupState.PENDING_REBOOT,
        pending=pending,
    )
    assert status.pending.boot_id == "abc123"
    assert status.presentation == "reboot"


def test_first_different_boot_consumes_pending():
    pending = PendingReboot(boot_id="old-boot", target_kernel="6.11.0", action=PendingAction.SETUP)
    # Same boot: pending persists
    assert consume_pending_reboot(pending, current_boot_id="old-boot") == pending
    # Different boot: consumed (returns None)
    assert consume_pending_reboot(pending, current_boot_id="new-boot") is None


def test_setup_state_independent_of_control_mode():
    """EC setup history must not imply live control capability."""
    from threshold.battery import ControlMode
    status = ECStatus(state=ECSetupState.AVAILABLE)
    # Vendor sysfs control with EC setup available is a valid combination
    assert status.state == ECSetupState.AVAILABLE
    assert ControlMode.SYSFS_VENDOR.value == "sysfs"


def test_working_older_module_keeps_setup_available_despite_failed_replacement():
    status = ECStatus(
        state=ECSetupState.AVAILABLE,
        maintenance=ECMaintenanceStatus.FAILED,
    )
    assert status.state == ECSetupState.AVAILABLE
    assert status.maintenance == ECMaintenanceStatus.FAILED
    assert status.presentation == "maintenance_failed"
