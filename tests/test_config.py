"""Tests for the GSettings wrapper (config.py)."""

import pytest
from batteryguard.config import Config


class FakeSettings:
    """In-memory Gio.Settings mock for testing."""

    def __init__(self):
        self._store = {
            'dark-mode': False,
            'autostart': False,
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


# ─── signal connection ─────────────────────────────────────────────────────────


def test_connect(config):
    callback = lambda *a: None
    conn_id = config.connect('changed::dark-mode', callback)
    assert conn_id == 42