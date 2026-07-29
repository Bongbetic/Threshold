"""Application class — startup, activation, shutdown, and autostart management."""

import sys
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gio, Adw, GObject

from batteryguard.window import BatteryGuardWindow, load_css_from_resource
from batteryguard.config import Config


class BatteryGuardApplication(Adw.Application):

    def __init__(self):
        super().__init__(
            application_id='com.bongbetic.batteryguard',
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        self._config = Config()

    def do_startup(self):
        Adw.Application.do_startup(self)
        load_css_from_resource()

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = BatteryGuardWindow(application=self, config=self._config)
            # Restore window geometry
            if self._config.get_maximized():
                win.maximize()
            else:
                w = self._config.get_window_width()
                h = self._config.get_window_height()
                win.set_default_size(w, h)
        win.present()

    def do_shutdown(self):
        """Save window geometry on shutdown."""
        win = self.props.active_window
        if win is not None:
            self._config.set_maximized(win.props.maximized)
            if not win.props.maximized:
                self._config.set_window_width(win.get_width())
                self._config.set_window_height(win.get_height())
        Adw.Application.do_shutdown(self)