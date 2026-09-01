
"""Tests for ThresholdState adapter (builds state from sysfs/config)."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from threshold.adapter import build_state
from threshold.battery import ControlMode
from threshold.config import Config


class FakeSettings:
    """In-memory Gio.Settings mock."""

    def __init__(self):
        self._store = {
            'dark-mode': False,
            'autostart': False,
            'minimize-to-tray': True,
            'show-notifications': True,
            'accent-color': 'orange',
            'compact-mode': False,
            'title-percentage': False,
            'last-applied-time': 0,
            'window-width': 800,
            'window-height': 600,
            'maximized': False,
            'charge-threshold': 80,
        }

    def get_boolean(self, key):
        return self._store[key]

    def set_boolean(self, key, value):
        self._store[key] = value

    def get_int(self, key):
        return self._store[key]

    def set_int(self, key, value):
        self._store[key] = value

    def get_int64(self, key):
        return self._store[key]

    def set_int64(self, key, value):
        self._store[key] = value

    def get_string(self, key):
        return self._store[key]

    def set_string(self, key, value):
        self._store[key] = value

    def connect(self, signal, callback):
        return 42


@pytest.fixture
def config():
    return Config(settings=FakeSettings())


class TestBuildStateNoBattery:
    """Test state construction when no battery is present."""

    @patch('threshold.adapter.find_battery_path', return_value=None)
    def test_no_battery_path(self, mock_find, config):
        state = build_state(config)
        assert state.battery_available is False
        assert state.battery_path is None
        assert state.control_mode is None
        assert state.charge_percent is None
        assert state.charge_status is None

    @patch('threshold.adapter.find_battery_path', return_value=None)
    def test_preferences_captured(self, mock_find, config):
        config.set_dark_mode(True)
        config.set_accent_color('blue')
        state = build_state(config)
        assert state.dark_mode is True
        assert state.accent_color == 'blue'

    @patch('threshold.adapter.find_battery_path', return_value=None)
    def test_window_state_captured(self, mock_find, config):
        config.set_window_width(1024)
        config.set_window_height(768)
        state = build_state(config)
        assert state.window_width == 1024
        assert state.window_height == 768


class TestBuildStateWithBattery:
    """Test state construction with mocked sysfs readings."""

    @patch('threshold.adapter.read_power_source', return_value='AC Adapter')
    @patch('threshold.adapter.read_capacity_wh', return_value=(52.5, 56.0))
    @patch('threshold.adapter.read_cycle_count', return_value=142)
    @patch('threshold.adapter.read_charge_percent', return_value=85)
    @patch('threshold.adapter.battery_health_percent', return_value=92)
    @patch('threshold.adapter.detect_control_mode', return_value=ControlMode.EC_MSI)
    @patch('threshold.adapter.find_battery_path')
    def test_populated_state(
        self, mock_find, mock_mode, mock_health, mock_pct, mock_cycles,
        mock_capacity, mock_power, config
    ):
        bat_path = Path("/sys/class/power_supply/BAT0")
        mock_find.return_value = bat_path
        
        # Mock read_sysfs for status and threshold
        with patch('threshold.adapter.read_sysfs') as mock_sysfs:
            def sysfs_side_effect(path):
                if path.name == 'status':
                    return 'Charging'
                if path.name == 'charge_control_end_threshold':
                    return '80'
                return None
            mock_sysfs.side_effect = sysfs_side_effect
            
            state = build_state(config)
        
        assert state.battery_available is True
        assert state.control_mode == ControlMode.EC_MSI
        assert state.charge_percent == 85
        assert state.charge_status == 'Charging'
        assert state.active_threshold == 80
        assert state.cycle_count == 142
        assert state.capacity_full_wh == 52.5
        assert state.health_percent == 92
        assert state.health_grade == 'Good'


class TestBuildStateNotificationOnly:
    """Test state in notification-only mode."""

    @patch('threshold.adapter.read_power_source', return_value='Battery')
    @patch('threshold.adapter.read_capacity_wh', return_value=None)
    @patch('threshold.adapter.read_cycle_count', return_value=None)
    @patch('threshold.adapter.read_charge_percent', return_value=75)
    @patch('threshold.adapter.detect_control_mode', return_value=ControlMode.NOTIFY_ONLY)
    @patch('threshold.adapter.find_battery_path')
    def test_notify_only_alarm_state(
        self, mock_find, mock_mode, mock_pct, mock_cycles,
        mock_capacity, mock_power, config
    ):
        bat_path = Path("/sys/class/power_supply/BAT0")
        mock_find.return_value = bat_path
        
        with patch('threshold.adapter.read_sysfs') as mock_sysfs:
            mock_sysfs.return_value = None  # No threshold file
            
            state = build_state(
                config,
                pending_threshold=80,
                alarm_armed=True,
                alarm_fired=False,
            )
        
        assert state.control_mode == ControlMode.NOTIFY_ONLY
        assert state.active_threshold is None
        assert state.pending_threshold == 80
        assert state.alarm_armed is True
        assert state.capabilities.supports_alarm is True
