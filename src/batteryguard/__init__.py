"""BatteryGuard GTK4 application package."""

import sys
import pathlib

import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gio


def _register_builtin_resources():
    """Register the compiled GResource bundle if available.

    The .gresource file lives in different locations depending on whether the
    app is installed system-wide or running from the meson builddir.  This
    function tries both and silently returns when neither exists (tests, CI
    without a display).
    """
    src_root = pathlib.Path(__file__).resolve().parent.parent  # src/
    project_root = src_root.parent  # repo root

    candidates = [
        # Installed: pkgdatadir / batteryguard.gresource
        pathlib.Path(sys.argv[0]).resolve().parent
        / '..' / 'share' / 'com.bongbetic.batteryguard'
        / 'batteryguard.gresource',
        # Meson builddir (development / CI)
        project_root / 'builddir' / 'data' / 'batteryguard.gresource',
    ]

    for path in candidates:
        resolved = path.resolve()
        if resolved.exists():
            resource = Gio.Resource.load(str(resolved))
            Gio.resources_register(resource)
            return


_register_builtin_resources()
