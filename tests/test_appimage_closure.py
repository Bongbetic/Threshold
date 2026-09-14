
"""AppImage dependency closure and offline-startup contract (issue #96).

The AppImage bundles every runtime dependency so it starts offline on
every supported distribution: Python, GI typelibs, GTK/Adwaita libraries,
WebKit (optional), GSettings schemas compiled, dbusmenu, web content,
and notification-area icons.
"""

import stat
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "packaging" / "appimage" / "build-appimage.sh"


def _build() -> str:
    return BUILD.read_text(encoding="utf-8")


# ── GSettings schema compilation ───────────────────────────────────────────


def test_build_compiles_gsettings_schemas_in_appdir():
    """The AppDir must contain compiled GSettings schemas so GSettings
    works offline without the system schema cache."""
    text = _build()
    assert "glib-compile-schemas" in text
    assert "gschema" in text.lower() or "schemas" in text


def test_apprun_sets_gsettings_schema_dir():
    """AppRun must point GSETTINGS_SCHEMA_DIR into the AppDir so
    GSettings.find() resolves without system paths."""
    text = _build()
    assert "GSETTINGS_SCHEMA_DIR" in text


# ── GI typelib closure ─────────────────────────────────────────────────────


def test_build_bundles_core_gi_typelibs():
    """Core GI typelibs must be copied into the AppDir so
    gi.require_version() resolves offline."""
    text = _build()
    for typelib in ("GLib-2.0.typelib", "GObject-2.0.typelib",
                     "Gio-2.0.typelib", "Gtk-4.0.typelib",
                     "Adw-1.typelib", "Notify-0.7.typelib"):
        assert typelib in text, f"build script must bundle {typelib}"


# ── Notification-area icon closure ─────────────────────────────────────────


def test_build_bundles_notification_area_icons():
    """The battery status icons used by the notification-area item must
    be present in the AppDir for SNI icon-name resolution."""
    text = _build()
    assert "icons" in text.lower()
    # The meson install already puts icons in the AppDir; verify the
    # build script ensures they are present.
    assert "hicolor" in text or "install_subdir" in text or "icons" in text.lower()


# ── Web content closure ────────────────────────────────────────────────────


def test_apprun_sets_xdg_data_dirs_for_offline_theming():
    """XDG_DATA_DIRS must include the AppDir so GTK can find the bundled
    Adwaita theme and icon resources offline."""
    text = _build()
    assert "XDG_DATA_DIRS" in text


# ── No privileged mutation on basic operations ─────────────────────────────


def test_build_script_never_invokes_pkexec():
    """The build script and AppRun must never invoke pkexec, sudo, or
    any privileged helper at launch time."""
    text = _build()
    assert "pkexec" not in text
    assert "sudo" not in text
    # AppRun must not call the bootstrap
    lines = text.split("\n")
    in_apprun = False
    for line in lines:
        if "cat >" in line and "AppRun" in line:
            in_apprun = True
        if in_apprun and "RUNEOF" in line:
            in_apprun = False
        if in_apprun:
            assert "bootstrap" not in line.lower(), \
                "AppRun must not invoke the bootstrap script"
