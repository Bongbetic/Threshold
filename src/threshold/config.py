"""GSettings wrapper — typed access to application preferences."""

import gi

gi.require_version('Gio', '2.0')

from gi.repository import Gio  # noqa: E402

SCHEMA_ID = 'com.bongbetic.threshold'


class Config:
    """Typed wrapper around Gio.Settings for the threshold schema.

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

    # ── minimize-to-tray ───────────────────────────────────────────────────────

    def get_minimize_to_tray(self) -> bool:
        return self._settings.get_boolean('minimize-to-tray')

    def set_minimize_to_tray(self, value: bool) -> None:
        self._settings.set_boolean('minimize-to-tray', value)

    # ── show-notifications ─────────────────────────────────────────────────────

    def get_show_notifications(self) -> bool:
        return self._settings.get_boolean('show-notifications')

    def set_show_notifications(self, value: bool) -> None:
        self._settings.set_boolean('show-notifications', value)

    # ── accent-color ───────────────────────────────────────────────────────────

    def get_accent_color(self) -> str:
        return self._settings.get_string('accent-color')

    def set_accent_color(self, value: str) -> None:
        self._settings.set_string('accent-color', value)

    # ── compact-mode ───────────────────────────────────────────────────────────

    def get_compact_mode(self) -> bool:
        return self._settings.get_boolean('compact-mode')

    def set_compact_mode(self, value: bool) -> None:
        self._settings.set_boolean('compact-mode', value)

    # ── title-percentage ───────────────────────────────────────────────────────

    def get_title_percentage(self) -> bool:
        return self._settings.get_boolean('title-percentage')

    def set_title_percentage(self, value: bool) -> None:
        self._settings.set_boolean('title-percentage', value)

    # ── last-applied-time ──────────────────────────────────────────────────────

    def get_last_applied_time(self) -> int:
        return self._settings.get_int64('last-applied-time')

    def set_last_applied_time(self, value: int) -> None:
        self._settings.set_int64('last-applied-time', value)

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
