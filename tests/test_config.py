"""Tests for the GSettings wrapper (config.py)."""

import pytest
from threshold.config import Config


class FakeSettings:
    """In-memory Gio.Settings mock for testing."""

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
        self._signals = {}

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
        self._signals[signal] = callback
        return 42


@pytest.fixture
def config():
    return Config(settings=FakeSettings())


# ─── dark-mode ─────────────────────────────────────────────────────────────────


def test_get_dark_mode_default(config):
    assert config.get_dark_mode() is False


def test_set_dark_mode(config):
    config.set_dark_mode(True)
    assert config.get_dark_mode() is True


def test_set_dark_mode_toggle(config):
    config.set_dark_mode(True)
    config.set_dark_mode(False)
    assert config.get_dark_mode() is False


# ─── autostart ─────────────────────────────────────────────────────────────────


def test_get_autostart_default(config):
    assert config.get_autostart() is False


def test_set_autostart(config):
    config.set_autostart(True)
    assert config.get_autostart() is True


# ─── window-width ──────────────────────────────────────────────────────────────


def test_get_window_width_default(config):
    assert config.get_window_width() == 800


def test_set_window_width(config):
    config.set_window_width(1024)
    assert config.get_window_width() == 1024


# ─── window-height ─────────────────────────────────────────────────────────────


def test_get_window_height_default(config):
    assert config.get_window_height() == 600


def test_set_window_height(config):
    config.set_window_height(768)
    assert config.get_window_height() == 768


# ─── maximized ─────────────────────────────────────────────────────────────────


def test_get_maximized_default(config):
    assert config.get_maximized() is False


def test_set_maximized(config):
    config.set_maximized(True)
    assert config.get_maximized() is True


# ─── charge-threshold ──────────────────────────────────────────────────────────


def test_get_charge_threshold_default(config):
    assert config.get_charge_threshold() == 80


def test_set_charge_threshold(config):
    config.set_charge_threshold(60)
    assert config.get_charge_threshold() == 60


# ─── minimize-to-tray ──────────────────────────────────────────────────────────


def test_get_minimize_to_tray_default(config):
    assert config.get_minimize_to_tray() is True


def test_set_minimize_to_tray(config):
    config.set_minimize_to_tray(False)
    assert config.get_minimize_to_tray() is False


# ─── show-notifications ────────────────────────────────────────────────────────


def test_get_show_notifications_default(config):
    assert config.get_show_notifications() is True


def test_set_show_notifications(config):
    config.set_show_notifications(False)
    assert config.get_show_notifications() is False


# ─── accent-color ──────────────────────────────────────────────────────────────


def test_get_accent_color_default(config):
    assert config.get_accent_color() == 'orange'


def test_set_accent_color(config):
    config.set_accent_color('blue')
    assert config.get_accent_color() == 'blue'


# ─── compact-mode ──────────────────────────────────────────────────────────────


def test_get_compact_mode_default(config):
    assert config.get_compact_mode() is False


def test_set_compact_mode(config):
    config.set_compact_mode(True)
    assert config.get_compact_mode() is True


# ─── title-percentage ──────────────────────────────────────────────────────────


def test_get_title_percentage_default(config):
    assert config.get_title_percentage() is False


def test_set_title_percentage(config):
    config.set_title_percentage(True)
    assert config.get_title_percentage() is True


# ─── last-applied-time ─────────────────────────────────────────────────────────


def test_get_last_applied_time_default(config):
    assert config.get_last_applied_time() == 0


def test_set_last_applied_time(config):
    config.set_last_applied_time(1787000000)
    assert config.get_last_applied_time() == 1787000000


# ─── signal connection ─────────────────────────────────────────────────────────


def test_connect(config):
    def callback(*_a):
        return None
    conn_id = config.connect('changed::dark-mode', callback)
    assert conn_id == 42
