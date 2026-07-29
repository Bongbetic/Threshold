"""BatteryGuard GTK4 application package."""

import os
import sys
import pathlib

import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gio


def _register_builtin_resources():
    """Register the compiled GResource bundle if available.

    The .gresource file lives in different locations depending on whether the
    app is installed system-wide or running from a meson build directory.
    """
    src_root = pathlib.Path(__file__).resolve().parent.parent  # src/
    project_root = src_root.parent  # repo root

    candidates = [
        # Installed: pkgdatadir / batteryguard.gresource
        pathlib.Path(sys.argv[0]).resolve().parent
        / '..' / 'share' / 'com.bongbetic.batteryguard'
        / 'batteryguard.gresource',
    ]

    meson_build = os.environ.get('MESON_BUILD_ROOT')
    if meson_build:
        candidates.append(
            pathlib.Path(meson_build) / 'data' / 'batteryguard.gresource'
        )

    # Common local / Debian dh meson build dirs
    candidates.append(project_root / 'builddir' / 'data' / 'batteryguard.gresource')
    candidates.extend(project_root.glob('obj-*/data/batteryguard.gresource'))

    for path in candidates:
        resolved = path.resolve()
        if resolved.exists():
            resource = Gio.Resource.load(str(resolved))
            Gio.resources_register(resource)
            return


_register_builtin_resources()
