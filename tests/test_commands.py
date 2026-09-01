"""Tests for the command dispatcher — observable results and persisted effects."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure src is importable
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from threshold.commands import CommandDispatcher, CommandResult, ErrorCode, VALID_ACCENT_COLORS
from threshold.battery import ControlMode, THRESHOLD_MIN, THRESHOLD_MAX
from threshold.state import ThresholdState, Capabilities


# ── Golden fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def mock_config():
    """In-memory Config mock that records setter calls."""
    config = MagicMock()
    config.get_dark_mode.return_value = False
    config.get_accent_color.return_value = "orange"
    config.get_compact_mode.return_value = False
    config.get_title_percentage.return_value = True
    config.get_show_notifications.return_value = True
    config.get_minimize_to_tray.return_value = True
    config.get_charge_threshold.return_value = 80
    config.get_last_applied_time.return_value = 0
    return config


@pytest.fixture
def dispatcher(mock_config):
    return CommandDispatcher(mock_config)


@pytest.fixture
def no_battery_state():
    return ThresholdState(battery_available=False)


@pytest.fixture
def ec_msi_state():
    return ThresholdState(
        battery_available=True,
        battery_path=Path("/sys/class/power_supply/BAT0"),
        control_mode=ControlMode.EC_MSI,
        charge_percent=75,
        charge_status="Charging",
        active_threshold=80,
    )


@pytest.fixture
def sysfs_vendor_state():
    return ThresholdState(
        battery_available=True,
        battery_path=Path("/sys/class/power_supply/BAT0"),
        control_mode=ControlMode.SYSFS_VENDOR,
        charge_percent=60,
        charge_status="Discharging",
        active_threshold=70,
    )


@pytest.fixture
def notify_only_state():
    return ThresholdState(
        battery_available=True,
        battery_path=Path("/sys/class/power_supply/BAT0"),
        control_mode=ControlMode.NOTIFY_ONLY,
        charge_percent=85,
        charge_status="Charging",
        active_threshold=None,
    )


@pytest.fixture
def populated_state():
    return ThresholdState(
        battery_available=True,
        battery_path=Path("/sys/class/power_supply/BAT0"),
        control_mode=ControlMode.EC_MSI,
        charge_percent=85,
        charge_status="Charging",
        active_threshold=80,
        pending_threshold=80,
        health_percent=92,
        health_grade="Good",
        cycle_count=142,
        capacity_full_wh=52.5,
        capacity_design_wh=56.0,
        dark_mode=False,
        accent_color="orange",
        compact_mode=False,
        title_percentage=True,
        show_notifications=True,
        minimize_to_tray=True,
    )


# ── Unknown / invalid commands ───────────────────────────────────────────────


class TestUnknownCommands:
    def test_unknown_command_returns_structured_failure(self, dispatcher):
        result = dispatcher.dispatch("nonexistent")
        assert result.success is False
        assert result.error_code == ErrorCode.UNKNOWN_COMMAND
        assert "nonexistent" in result.message

    def test_empty_command_name(self, dispatcher):
        result = dispatcher.dispatch("")
        assert result.success is False
        assert result.error_code == ErrorCode.UNKNOWN_COMMAND


class TestInvalidArgs:
    def test_apply_threshold_missing_arg(self, dispatcher, ec_msi_state):
        result = dispatcher.dispatch("apply_threshold", args={}, state=ec_msi_state)
        assert result.success is False
        assert result.error_code == ErrorCode.INVALID_ARGS
        assert "threshold" in result.message

    def test_apply_threshold_wrong_type(self, dispatcher, ec_msi_state):
        result = dispatcher.dispatch(
            "apply_threshold", args={"threshold": "eighty"}, state=ec_msi_state
        )
        assert result.success is False
        assert result.error_code == ErrorCode.INVALID_ARGS

    def test_set_dark_mode_missing_value(self, dispatcher):
        result = dispatcher.dispatch("set_dark_mode", args={})
        assert result.success is False
        assert result.error_code == ErrorCode.INVALID_ARGS

    def test_set_dark_mode_wrong_type(self, dispatcher):
        result = dispatcher.dispatch("set_dark_mode", args={"value": "yes"})
        assert result.success is False
        assert result.error_code == ErrorCode.INVALID_ARGS

    def test_set_accent_color_invalid_value(self, dispatcher):
        result = dispatcher.dispatch("set_accent_color", args={"value": "magenta"})
        assert result.success is False
        assert result.error_code == ErrorCode.INVALID_ARGS

    def test_set_accent_color_missing_value(self, dispatcher):
        result = dispatcher.dispatch("set_accent_color", args={})
        assert result.success is False
        assert result.error_code == ErrorCode.INVALID_ARGS


class TestThresholdRange:
    def test_below_minimum(self, dispatcher, ec_msi_state):
        result = dispatcher.dispatch(
            "apply_threshold", args={"threshold": THRESHOLD_MIN - 1}, state=ec_msi_state
        )
        assert result.success is False
        assert result.error_code == ErrorCode.THRESHOLD_OUT_OF_RANGE

    def test_above_maximum(self, dispatcher, ec_msi_state):
        result = dispatcher.dispatch(
            "apply_threshold", args={"threshold": THRESHOLD_MAX + 1}, state=ec_msi_state
        )
        assert result.success is False
        assert result.error_code == ErrorCode.THRESHOLD_OUT_OF_RANGE

    def test_at_minimum_boundary(self, dispatcher, ec_msi_state):
        with patch("threshold.commands.write_threshold", return_value=(True, "direct")):
            result = dispatcher.dispatch(
                "apply_threshold", args={"threshold": THRESHOLD_MIN}, state=ec_msi_state
            )
            assert result.success is True

    def test_at_maximum_boundary(self, dispatcher, ec_msi_state):
        with patch("threshold.commands.write_threshold", return_value=(True, "direct")):
            result = dispatcher.dispatch(
                "apply_threshold", args={"threshold": THRESHOLD_MAX}, state=ec_msi_state
            )
            assert result.success is True


# ── No battery ───────────────────────────────────────────────────────────────


class TestNoBattery:
    def test_apply_threshold_no_battery(self, dispatcher, no_battery_state):
        result = dispatcher.dispatch(
            "apply_threshold", args={"threshold": 80}, state=no_battery_state
        )
        assert result.success is False
        assert result.error_code == ErrorCode.NO_BATTERY

    def test_restore_threshold_no_battery(self, dispatcher, no_battery_state):
        result = dispatcher.dispatch("restore_threshold", state=no_battery_state)
        assert result.success is False
        assert result.error_code == ErrorCode.NO_BATTERY

    def test_get_state_none(self, dispatcher):
        result = dispatcher.dispatch("get_state", state=None)
        assert result.success is False
        assert result.error_code == ErrorCode.NO_BATTERY


# ── Charge threshold success ─────────────────────────────────────────────────


class TestApplyThresholdSuccess:
    def test_ec_msi_direct_write(self, dispatcher, ec_msi_state, mock_config):
        with patch("threshold.commands.write_threshold", return_value=(True, "direct")),              patch("threshold.commands.read_sysfs", return_value="80"):
            result = dispatcher.dispatch(
                "apply_threshold", args={"threshold": 80}, state=ec_msi_state
            )
            assert result.success is True
            assert result.data["threshold"] == 80
            assert result.data["method"] == "direct"
            assert result.data["ec_mismatch"] is False
            mock_config.set_charge_threshold.assert_called_once_with(80)

    def test_sysfs_vendor_write(self, dispatcher, sysfs_vendor_state, mock_config):
        with patch("threshold.commands.write_threshold", return_value=(True, "direct")),              patch("threshold.commands.read_sysfs", return_value="70"):
            result = dispatcher.dispatch(
                "apply_threshold", args={"threshold": 70}, state=sysfs_vendor_state
            )
            assert result.success is True
            assert result.data["method"] == "direct"
            mock_config.set_charge_threshold.assert_called_once_with(70)


# ── EC mismatch ──────────────────────────────────────────────────────────────


class TestECMismatch:
    def test_ec_stores_different_value(self, dispatcher, ec_msi_state, mock_config):
        with patch("threshold.commands.write_threshold", return_value=(True, "direct")),              patch("threshold.commands.read_sysfs", return_value="78"):
            result = dispatcher.dispatch(
                "apply_threshold", args={"threshold": 80}, state=ec_msi_state
            )
            assert result.success is True
            assert result.data["ec_mismatch"] is True
            assert "EC stored 78%" in result.data["method"]

    def test_ec_matches_requested(self, dispatcher, ec_msi_state, mock_config):
        with patch("threshold.commands.write_threshold", return_value=(True, "direct")),              patch("threshold.commands.read_sysfs", return_value="80"):
            result = dispatcher.dispatch(
                "apply_threshold", args={"threshold": 80}, state=ec_msi_state
            )
            assert result.success is True
            assert result.data["ec_mismatch"] is False


# ── Write failures ───────────────────────────────────────────────────────────


class TestWriteFailures:
    def test_write_permission_denied(self, dispatcher, ec_msi_state):
        with patch("threshold.commands.write_threshold", return_value=(False, "Permission denied")):
            result = dispatcher.dispatch(
                "apply_threshold", args={"threshold": 80}, state=ec_msi_state
            )
            assert result.success is False
            assert result.error_code == ErrorCode.PERMISSION_DENIED

    def test_write_os_error(self, dispatcher, ec_msi_state):
        with patch("threshold.commands.write_threshold", return_value=(False, "Input/output error")):
            result = dispatcher.dispatch(
                "apply_threshold", args={"threshold": 80}, state=ec_msi_state
            )
            assert result.success is False
            assert result.error_code == ErrorCode.WRITE_FAILED
            assert "Input/output error" in result.message


# ── Notification-only mode ──────────────────────────────────────────────────


class TestNotificationOnly:
    def test_alarm_write_no_sysfs(self, dispatcher, notify_only_state, mock_config):
        result = dispatcher.dispatch(
            "apply_threshold", args={"threshold": 80}, state=notify_only_state
        )
        assert result.success is True
        assert result.data["method"] == "alarm"
        assert result.data["threshold"] == 80
        mock_config.set_charge_threshold.assert_called_once_with(80)

    def test_restore_alarm_disarm(self, dispatcher, notify_only_state, mock_config):
        result = dispatcher.dispatch("restore_threshold", state=notify_only_state)
        assert result.success is True
        assert result.data["method"] == "alarm"
        assert result.data["threshold"] == THRESHOLD_MAX
        mock_config.set_charge_threshold.assert_called_once_with(THRESHOLD_MAX)


# ── Restore threshold ────────────────────────────────────────────────────────


class TestRestoreThreshold:
    def test_restore_sets_100(self, dispatcher, ec_msi_state, mock_config):
        with patch("threshold.commands.write_threshold", return_value=(True, "direct")),              patch("threshold.commands.read_sysfs", return_value="100"):
            result = dispatcher.dispatch("restore_threshold", state=ec_msi_state)
            assert result.success is True
            assert result.data["threshold"] == THRESHOLD_MAX
            mock_config.set_charge_threshold.assert_called_once_with(THRESHOLD_MAX)


# ── Preference commands ──────────────────────────────────────────────────────


class TestPreferences:
    def test_set_dark_mode_true(self, dispatcher, mock_config):
        result = dispatcher.dispatch("set_dark_mode", args={"value": True})
        assert result.success is True
        assert result.data["dark_mode"] is True
        mock_config.set_dark_mode.assert_called_once_with(True)

    def test_set_dark_mode_false(self, dispatcher, mock_config):
        result = dispatcher.dispatch("set_dark_mode", args={"value": False})
        assert result.success is True
        mock_config.set_dark_mode.assert_called_once_with(False)

    def test_set_accent_color(self, dispatcher, mock_config):
        for color in VALID_ACCENT_COLORS:
            mock_config.reset_mock()
            result = dispatcher.dispatch("set_accent_color", args={"value": color})
            assert result.success is True
            assert result.data["accent_color"] == color
            mock_config.set_accent_color.assert_called_once_with(color)

    def test_set_compact_mode(self, dispatcher, mock_config):
        result = dispatcher.dispatch("set_compact_mode", args={"value": True})
        assert result.success is True
        mock_config.set_compact_mode.assert_called_once_with(True)

    def test_set_title_percentage(self, dispatcher, mock_config):
        result = dispatcher.dispatch("set_title_percentage", args={"value": False})
        assert result.success is True
        mock_config.set_title_percentage.assert_called_once_with(False)

    def test_set_show_notifications(self, dispatcher, mock_config):
        result = dispatcher.dispatch("set_show_notifications", args={"value": False})
        assert result.success is True
        mock_config.set_show_notifications.assert_called_once_with(False)

    def test_set_minimize_to_tray(self, dispatcher, mock_config):
        result = dispatcher.dispatch("set_minimize_to_tray", args={"value": False})
        assert result.success is True
        mock_config.set_minimize_to_tray.assert_called_once_with(False)


# ── Get state ────────────────────────────────────────────────────────────────


class TestGetState:
    def test_get_state_returns_snapshot(self, dispatcher, populated_state):
        result = dispatcher.dispatch("get_state", state=populated_state)
        assert result.success is True
        assert result.data["state"] is populated_state

    def test_get_state_with_none(self, dispatcher):
        result = dispatcher.dispatch("get_state", state=None)
        assert result.success is False
        assert result.error_code == ErrorCode.NO_BATTERY


# ── Result dataclass ─────────────────────────────────────────────────────────


class TestCommandResult:
    def test_success_defaults(self):
        r = CommandResult(success=True)
        assert r.data == {}
        assert r.error_code is None
        assert r.message is None

    def test_failure_with_error(self):
        r = CommandResult(
            success=False, error_code="x", message="bad"
        )
        assert r.success is False
        assert r.error_code == "x"
