"""Register the compiled GResource bundle for UI templates and CSS."""

from __future__ import annotations

import os
import pathlib
import sys

import gi

gi.require_version('Gio', '2.0')

from gi.repository import Gio  # noqa: E402


def register_resources() -> bool:
    """Locate and register ``batteryguard.gresource``.

    Returns True if a resource bundle was found and registered.
    """
    src_root = pathlib.Path(__file__).resolve().parent.parent  # src/
    project_root = src_root.parent

    candidates = [
        # Installed: near the launcher under share/<app_id>/
        pathlib.Path(sys.argv[0]).resolve().parent
        / '..' / 'share' / 'com.bongbetic.batteryguard'
        / 'batteryguard.gresource',
    ]

    meson_build = os.environ.get('MESON_BUILD_ROOT')
    if meson_build:
        candidates.append(
            pathlib.Path(meson_build) / 'data' / 'batteryguard.gresource'
        )

    pkgdatadir = os.environ.get('BATTERYGUARD_PKGDATADIR')
    if pkgdatadir:
        candidates.append(pathlib.Path(pkgdatadir) / 'batteryguard.gresource')

    candidates.append(project_root / 'builddir' / 'data' / 'batteryguard.gresource')
    candidates.extend(project_root.glob('obj-*/data/batteryguard.gresource'))

    for path in candidates:
        resolved = path.resolve()
        if resolved.exists():
            resource = Gio.Resource.load(str(resolved))
            Gio.resources_register(resource)
            return True
    return False
