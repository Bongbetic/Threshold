
"""Tests for presentation-neutral Threshold state."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
from dataclasses import asdict

import pytest

# Ensure src is importable
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from threshold.state import ThresholdState, detect_capabilities
from threshold.battery import ControlMode


class TestThresholdStateConstruction:
    """Test ThresholdState can be constructed with domain values."""

    def test_minimal_state_requires_no_battery(self):
        """State can represent no-battery scenario."""
        state = ThresholdState(
            battery_available=False,
            battery_path=None,
            control_mode=None,
        )
        assert state.battery_available is False
        assert state.battery_path is None
        assert state.control_mode is None

    def test_populated_state_domain_values(self):
        """State uses domain values, not GTK widgets."""
        state = ThresholdState(
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
            power_source="AC Adapter",
        )
        assert state.charge_percent == 85
        assert state.charge_status == "Charging"
        assert state.control_mode == ControlMode.EC_MSI
        assert isinstance(state.control_mode, ControlMode)

    def test_capabilities_reflect_control_mode(self):
        """Capabilities derived from control mode."""
        caps = detect_capabilities(ControlMode.EC_MSI)
        assert caps.can_write_threshold is True
        assert caps.can_restore is True
        assert caps.supports_alarm is False

        caps_notify = detect_capabilities(ControlMode.NOTIFY_ONLY)
        assert caps_notify.can_write_threshold is False
        assert caps_notify.supports_alarm is True

    def test_preferences_snapshot(self):
        """Preferences captured as domain values."""
        state = ThresholdState(
            battery_available=False,
            dark_mode=True,
            accent_color="blue",
            compact_mode=True,
            title_percentage=True,
            show_notifications=False,
            minimize_to_tray=True,
        )
        assert state.dark_mode is True
        assert state.accent_color == "blue"
        assert state.compact_mode is True

    def test_window_state_captured(self):
        """Window geometry captured as domain values."""
        state = ThresholdState(
            battery_available=False,
            window_width=800,
            window_height=600,
            window_maximized=False,
        )
        assert state.window_width == 800
        assert state.window_height == 600
        assert state.window_maximized is False

    def test_theme_scheme_resolves_dark_mode(self):
        """Effective theme scheme derived from dark_mode preference."""
        state_dark = ThresholdState(battery_available=False, dark_mode=True)
        assert state_dark.effective_theme_scheme == "dark"
        
        state_light = ThresholdState(battery_available=False, dark_mode=False)
        assert state_light.effective_theme_scheme == "light"


class TestThresholdStateUpdates:
    """Test state updates preserve immutability pattern."""

    def test_update_charge_data(self):
        """Update battery telemetry without affecting preferences."""
        state = ThresholdState(
            battery_available=True,
            charge_percent=50,
            dark_mode=True,
        )
        updated = state.with_updates(charge_percent=75)
        assert updated.charge_percent == 75
        assert updated.dark_mode is True  # preserved
        assert state.charge_percent == 50  # original unchanged

    def test_update_preserves_all_fields(self):
        """Updated state carries forward all existing values."""
        state = ThresholdState(
            battery_available=True,
            charge_percent=60,
            control_mode=ControlMode.SYSFS_VENDOR,
            dark_mode=False,
            accent_color="green",
        )
        updated = state.with_updates(charge_percent=80)
        assert updated.control_mode == ControlMode.SYSFS_VENDOR
        assert updated.accent_color == "green"


class TestDetectCapabilities:
    """Test capability detection from control mode."""

    def test_ec_msi_capabilities(self):
        caps = detect_capabilities(ControlMode.EC_MSI)
        assert caps.can_write_threshold is True
        assert caps.can_restore is True
        assert caps.supports_alarm is False
        assert caps.write_method in ("direct", "pkexec")

    def test_sysfs_vendor_capabilities(self):
        caps = detect_capabilities(ControlMode.SYSFS_VENDOR)
        assert caps.can_write_threshold is True
        assert caps.can_restore is True
        assert caps.supports_alarm is False

    def test_notify_only_capabilities(self):
        caps = detect_capabilities(ControlMode.NOTIFY_ONLY)
        assert caps.can_write_threshold is False
        assert caps.can_restore is False
        assert caps.supports_alarm is True

    def test_none_mode_capabilities(self):
        caps = detect_capabilities(None)
        assert caps.can_write_threshold is False
        assert caps.can_restore is False
        assert caps.supports_alarm is False


class TestThresholdStateFromSysfs:
    """Test state construction from sysfs readings (mocked)."""

    def test_populated_snapshot(self):
        """Full battery snapshot with all sysfs values."""
        state = ThresholdState(
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
            power_source="AC Adapter",
        )
        assert state.charge_percent == 85
        assert state.active_threshold == 80
        assert state.health_grade == "Good"

    def test_notification_only_alarm_state(self):
        """Notification-only mode tracks alarm state."""
        state = ThresholdState(
            battery_available=True,
            control_mode=ControlMode.NOTIFY_ONLY,
            charge_percent=75,
            active_threshold=80,
            alarm_armed=True,
            alarm_fired=False,
        )
        assert state.alarm_armed is True
        assert state.alarm_fired is False
        assert state.capabilities.supports_alarm is True

    def test_no_battery_error_state(self):
        """No battery produces error-state snapshot."""
        state = ThresholdState(
            battery_available=False,
            control_mode=None,
        )
        assert state.charge_percent is None
        assert state.charge_status is None
        assert state.active_threshold is None
        assert state.health_percent is None
