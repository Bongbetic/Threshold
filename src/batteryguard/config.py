"""GSettings wrapper — typed access to application preferences."""

import gi

gi.require_version('Gio', '2.0')

from gi.repository import Gio  # noqa: E402

SCHEMA_ID = 'com.bongbetic.batteryguard'


class Config:
    """Typed wrapper around Gio.Settings for the batteryguard schema.

    Usage::

        config = Config()
        config.get_dark_mode()       # bool
        config.set_dark_mode(True)
        config.connect('changed::dark-mode', callback)
    """

    def __init__(self, settings: Gio.Settings | None = None):
        self._settings = settings or Gio.Settings.new(SCHEMA_ID)

    # ── dark-mode ──────────────────────────────────────────────────────────────

    def get_dark_mode(self) -> bool:
        return self._settings.get_boolean('dark-mode')

    def set_dark_mode(self, value: bool) -> None:
        self._settings.set_boolean('dark-mode', value)

    # ── autostart ──────────────────────────────────────────────────────────────

    def get_autostart(self) -> bool:
        return self._settings.get_boolean('autostart')

    def set_autostart(self, value: bool) -> None:
        self._settings.set_boolean('autostart', value)

    # ── window-width ───────────────────────────────────────────────────────────

    def get_window_width(self) -> int:
        return self._settings.get_int('window-width')

    def set_window_width(self, value: int) -> None:
        self._settings.set_int('window-width', value)

    # ── window-height ──────────────────────────────────────────────────────────

    def get_window_height(self) -> int:
        return self._settings.get_int('window-height')

    def set_window_height(self, value: int) -> None:
        self._settings.set_int('window-height', value)

    # ── maximized ──────────────────────────────────────────────────────────────

    def get_maximized(self) -> bool:
        return self._settings.get_boolean('maximized')

    def set_maximized(self, value: bool) -> None:
        self._settings.set_boolean('maximized', value)

    # ── charge-threshold ───────────────────────────────────────────────────────

    def get_charge_threshold(self) -> int:
        return self._settings.get_int('charge-threshold')

    def set_charge_threshold(self, value: int) -> None:
        self._settings.set_int('charge-threshold', value)

    # ── signal connection ──────────────────────────────────────────────────────

    def connect(self, signal: str, callback) -> int:
        """Connect to a GSettings signal (e.g. ``changed::dark-mode``)."""
        return self._settings.connect(signal, callback)
