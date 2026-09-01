"""Application class - startup, activation, shutdown, and autostart management."""

import sys

import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Notify', '0.7')

from gi.repository import Gio, Adw, Notify  # noqa: E402

from threshold.resources import register_resources  # noqa: E402

if not register_resources():
    print(
        'error: threshold.gresource not found. '
        'Build with Meson or set THRESHOLD_PKGDATADIR / MESON_BUILD_ROOT.',
        file=sys.stderr,
    )
    sys.exit(1)

from threshold.config import Config  # noqa: E402
from threshold.migration import migrate_if_needed  # noqa: E402


class ThresholdApplication(Adw.Application):

    def __init__(self):
        super().__init__(
            application_id='com.bongbetic.threshold',
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        self._config = Config()

    def do_startup(self):
        Adw.Application.do_startup(self)
        migrate_if_needed()
        Notify.init('com.bongbetic.threshold')

    def do_activate(self):
        win = self.props.active_window
        if not win:
            try:
                from threshold.carbon_shell import create_carbon_window
                win = create_carbon_window(self, self._config)
            except ImportError as e:
                print(
                    f'error: Carbon shell requires WebKitGTK 6.0: {e}',
                    file=sys.stderr,
                )
                sys.exit(1)
            except FileNotFoundError as e:
                print(f'error: {e}', file=sys.stderr)
                sys.exit(1)
        win.present()

    def do_shutdown(self):
        """Save window geometry and tear down notifications on shutdown."""
        win = self.props.active_window
        if win is not None:
            if hasattr(win, '_handler'):
                handler = win._handler
                handler.stop_polling()
                handler.stop_gsettings_listeners()
                handler._cleanup_tray()
        if Notify.is_initted():
            Notify.uninit()
        Adw.Application.do_shutdown(self)
