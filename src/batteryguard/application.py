"""Application class — startup, activation, shutdown, and autostart management."""

import sys

import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Notify', '0.7')

from gi.repository import Gio, Adw, Notify  # noqa: E402

from batteryguard.resources import register_resources  # noqa: E402

if not register_resources():
    print(
        'error: batteryguard.gresource not found. '
        'Build with Meson or set BATTERYGUARD_PKGDATADIR / MESON_BUILD_ROOT.',
        file=sys.stderr,
    )
    sys.exit(1)

from batteryguard.window import BatteryGuardWindow, load_css_from_resource  # noqa: E402
from batteryguard.config import Config  # noqa: E402


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
        Notify.init('com.bongbetic.batteryguard')

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = BatteryGuardWindow(application=self, config=self._config)
            if self._config.get_maximized():
                win.maximize()
            else:
                w = self._config.get_window_width()
                h = self._config.get_window_height()
                win.set_default_size(w, h)
        win.present()

    def do_shutdown(self):
        """Save window geometry and tear down notifications on shutdown."""
        win = self.props.active_window
        if win is not None:
            if hasattr(win, '_stop_polling'):
                win._stop_polling()
            self._config.set_maximized(win.props.maximized)
            if not win.props.maximized:
                self._config.set_window_width(win.get_width())
                self._config.set_window_height(win.get_height())
        if Notify.is_initted():
            Notify.uninit()
        Adw.Application.do_shutdown(self)
