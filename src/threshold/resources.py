"""Register the compiled GResource bundle for UI templates and CSS."""

from __future__ import annotations

import os
import pathlib
import sys

import gi

gi.require_version('Gio', '2.0')

from gi.repository import Gio  # noqa: E402


_registered = False


def register_resources() -> bool:
    """Locate and register ``threshold.gresource``.

    Returns True if a resource bundle was found and registered (or was
    already registered by an earlier call).
    """
    global _registered
    if _registered:
        return True

    src_root = pathlib.Path(__file__).resolve().parent.parent  # src/
    project_root = src_root.parent

    candidates = [
        # Explicit dev/test overrides first — a stale installed bundle must
        # never shadow a fresh build when running from a build directory.
        pathlib.Path(os.environ['MESON_BUILD_ROOT']) / 'data' / 'threshold.gresource'
        if os.environ.get('MESON_BUILD_ROOT') else None,
        pathlib.Path(os.environ['THRESHOLD_PKGDATADIR']) / 'threshold.gresource'
        if os.environ.get('THRESHOLD_PKGDATADIR') else None,
        # Installed: near the launcher under share/<app_id>/
        pathlib.Path(sys.argv[0]).resolve().parent
        / '..' / 'share' / 'com.bongbetic.threshold'
        / 'threshold.gresource',
        # Fallbacks: relative to the source tree.
        project_root / 'builddir' / 'data' / 'threshold.gresource',
    ]
    candidates.extend(project_root.glob('obj-*/data/threshold.gresource'))

    for path in candidates:
        if path is None:
            continue
        resolved = path.resolve()
        if resolved.exists():
            resource = Gio.Resource.load(str(resolved))
            Gio.resources_register(resource)
            _registered = True
            return True
    return False
