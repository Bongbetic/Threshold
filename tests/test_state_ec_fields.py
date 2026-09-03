"""State snapshot extensions for issue #86 vocabulary.

The presentation must keep distinct: control mode (live), EC setup state,
EC maintenance status, the machine-wide charge threshold, and the active
threshold verified through the live interface.
"""

import pytest

from threshold.battery import ControlMode
from threshold.config import Config
from threshold.state import ThresholdState
from threshold.ec_state import (
    ECSetupState,
    ECSetupReason,
    ECMaintenanceStatus,
)


class FakeGSettings:
    def __init__(self):
        self._values = {
            "charge-threshold": 80,
            "dark-mode": False,
            "autostart": False,
            "minimize-to-tray": True,
            "show-notifications": True,
            "accent-color": "orange",
            "compact-mode": False,
            "title-percentage": True,
            "last-applied-time": 0,
            "window-width": 800,
            "window-height": 600,
            "maximized": False,
        }

    def get_boolean(self, k): return self._values[k]
    def set_boolean(self, k, v): self._values[k] = v
    def get_int(self, k): return self._values[k]
    def set_int(self, k, v): self._values[k] = v
    def get_int64(self, k): return self._values[k]
    def set_int64(self, k, v): self._values[k] = v
    def get_string(self, k): return self._values[k]
    def set_string(self, k, v): self._values[k] = v
    def connect(self, *a): return 0


def test_state_has_ec_setup_fields():
    state = ThresholdState(
        control_mode=ControlMode.EC_MSI,
        ec_setup_state=ECSetupState.AVAILABLE,
        charge_threshold=80,
        active_threshold=80,
    )
    assert state.ec_setup_state == ECSetupState.AVAILABLE
    assert state.ec_setup_reason is None
    assert state.ec_maintenance_status == ECMaintenanceStatus.OK


def test_charge_threshold_persists_independently_of_active():
    state = ThresholdState(
        control_mode=ControlMode.NOTIFY_ONLY,
        ec_setup_state=ECSetupState.UNAVAILABLE,
        ec_setup_reason=ECSetupReason.NOT_MSI_HARDWARE,
        charge_threshold=70,
        active_threshold=None,
    )
    # Machine-wide policy survives even with no live interface
    assert state.charge_threshold == 70
    assert state.active_threshold is None


def test_adapter_builds_state_with_ec_fields(tmp_path):
    from threshold.adapter import build_state

    config = Config(settings=FakeGSettings())
    state = build_state(battery_path=None, config=config)
    assert state.charge_threshold == config.get_charge_threshold()
    assert state.active_threshold is None
    assert state.ec_setup_state is None or isinstance(
        state.ec_setup_state, (ECSetupState, type(None))
    )


def test_adapter_passes_ec_status_through(tmp_path):
    from threshold.adapter import build_state
    from threshold.ec_state import ECStatus

    config = Config(settings=FakeGSettings())
    ec = ECStatus(
        state=ECSetupState.PENDING_REBOOT,
        pending=None,
    )
    state = build_state(
        battery_path=None, config=config, ec_status=ec
    )
    assert state.ec_setup_state == ECSetupState.PENDING_REBOOT


def test_adapter_reads_ec_status_from_file(tmp_path, monkeypatch):
    from threshold.adapter import build_state
    from threshold.ec_status import EC_STATUS_FILE

    status_file = tmp_path / "status"
    status_file.write_text(
        "setup_state=unavailable\n"
        "reason=not_msi_hardware\n"
        "maintenance=ok\n"
        "charge_threshold=75\n"
    )
    monkeypatch.setattr(
        "threshold.ec_status.EC_STATUS_FILE", status_file
    )
    config = Config(settings=FakeGSettings())
    state = build_state(battery_path=None, config=config)
    assert state.ec_setup_state == ECSetupState.UNAVAILABLE
    assert state.ec_setup_reason == ECSetupReason.NOT_MSI_HARDWARE
    assert state.charge_threshold == 75
