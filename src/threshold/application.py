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


TIGHT_WINDOW_WIDTH = 760
TIGHT_WINDOW_HEIGHT = 365


def _carbon_requested() -> bool:
    """Check if the Carbon shell was requested via flag or env."""
    if '--carbon' in sys.argv:
        return True
    import os
    return os.environ.get('THRESHOLD_CARBON', '0') == '1'


class ThresholdApplication(Adw.Application):

    def __init__(self):
        super().__init__(
            application_id='com.bongbetic.threshold',
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        self._config = Config()
        self._use_carbon = False

    def do_startup(self):
        Adw.Application.do_startup(self)

        # Check for Carbon opt-in before loading GTK CSS
        self._use_carbon = _carbon_requested()

        if not self._use_carbon:
            from threshold.window import load_css_from_resource
            load_css_from_resource()

        migrate_if_needed()
        Notify.init('com.bongbetic.threshold')

    def do_activate(self):
        win = self.props.active_window
        if not win:
            if self._use_carbon:
                try:
                    from threshold.carbon_shell import create_carbon_window
                    win = create_carbon_window(self, self._config)
                except ImportError as e:
                    print(
                        f'error: Carbon shell requires WebKitGTK 6.0: {e}',
                        file=sys.stderr,
                    )
                    # Fall back to GTK
                    self._use_carbon = False
                    from threshold.window import ThresholdWindow
                    win = ThresholdWindow(application=self, config=self._config)
                    win.set_resizable(False)
                    win.set_default_size(TIGHT_WINDOW_WIDTH, TIGHT_WINDOW_HEIGHT)
                except FileNotFoundError as e:
                    print(f'error: {e}', file=sys.stderr)
                    sys.exit(1)
            else:
                from threshold.window import ThresholdWindow
                win = ThresholdWindow(application=self, config=self._config)
                # V3 UI is an instrument panel, not a document canvas. Older
                # releases persisted huge/maximized geometry (e.g. 1340x890),
                # leaving empty grid around the cards. Force the tight design
                # size and keep settings from re-expanding future launches.
                win.set_resizable(False)
                win.set_default_size(TIGHT_WINDOW_WIDTH, TIGHT_WINDOW_HEIGHT)
                self._config.set_maximized(False)
                self._config.set_window_width(TIGHT_WINDOW_WIDTH)
                self._config.set_window_height(TIGHT_WINDOW_HEIGHT)
        win.present()

    def do_shutdown(self):
        """Save window geometry and tear down notifications on shutdown."""
        win = self.props.active_window
        if win is not None:
            if hasattr(win, '_stop_polling'):
                win._stop_polling()
            if not self._use_carbon:
                self._config.set_maximized(False)
                self._config.set_window_width(TIGHT_WINDOW_WIDTH)
                self._config.set_window_height(TIGHT_WINDOW_HEIGHT)
        if Notify.is_initted():
            Notify.uninit()
        Adw.Application.do_shutdown(self)
