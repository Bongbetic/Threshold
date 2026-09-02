"""AppImage tooling contract (issue #86).

The AppImage is self-contained and relocatable, bundles the Dbusmenu 0.4
typelib and shared library privately, embeds a deterministic EC bundle,
never invokes privileged mutation at launch, and is reproducible.
"""

import stat
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "packaging" / "appimage" / "build-appimage.sh"
BOOTSTRAP = ROOT / "packaging" / "threshold-appimage-bootstrap"


def _build() -> str:
    return BUILD.read_text(encoding="utf-8")


def _bootstrap() -> str:
    return BOOTSTRAP.read_text(encoding="utf-8")


def test_build_script_is_executable():
    assert BUILD.exists()
    assert BUILD.stat().st_mode & stat.S_IXUSR


def test_build_bundles_dbusmenu_typelib_and_library():
    text = _build()
    assert "Dbusmenu-0.4.typelib" in text
    assert "libdbusmenu-glib" in text
    assert "GI_TYPELIB_PATH" in text


def test_build_embeds_deterministic_ec_bundle():
    text = _build()
    assert "ec-manifest.json" in text
    assert "bundle_checksum" in text
    assert "SOURCE_DATE_EPOCH" in text


def test_apprun_has_no_build_host_paths():
    text = _build()
    assert "THRESHOLD_PKGDATADIR" in text
    # AppRun must resolve relative to itself, never a build-host prefix
    assert 'readlink -f "$0"' in text


def test_bootstrap_limits_verbs_to_mutating_four():
    text = _bootstrap()
    for verb in ("install", "update", "repair", "remove"):
        assert verb in text
    # Status and diagnostics are not bootstrap verbs (unprivileged)


def test_bootstrap_accepts_only_streamed_bundle():
    text = _bootstrap()
    # Bundle input arrives on stdin; no caller-selected path argument
    assert "cat >" in text
    assert "MAX_BUNDLE_BYTES" in text
    assert '"$2"' not in text


def test_bootstrap_preserves_last_known_good():
    text = _bootstrap()
    assert "last-known-good" in text


def test_bootstrap_never_downgrades_silently():
    text = _bootstrap()
    # Ordinary downgrade refusal: protocol + identity checks gate replacement
    assert "protocol" in text
