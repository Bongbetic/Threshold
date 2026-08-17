"""Meson install layout: icons, metainfo, udev, and ship-critical files."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
APP_ID = "com.bongbetic.threshold"


def _build_root() -> Path:
    env = os.environ.get("MESON_BUILD_ROOT")
    if env:
        return Path(env)
    candidate = ROOT / "builddir"
    if (candidate / "build.ninja").is_file():
        return candidate
    pytest.skip("no configured Meson build directory")


def _assert_builddir_matches_repo(build: Path) -> None:
    """Fail clearly when builddir was configured from a moved source tree."""
    meson_log = build / "meson-logs" / "meson-log.txt"
    if not meson_log.is_file():
        return
    text = meson_log.read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines()[:120]:
        if "Source dir:" in line:
            configured = line.split("Source dir:", 1)[1].strip()
            if configured and Path(configured).resolve() != ROOT.resolve():
                pytest.fail(
                    f"stale Meson builddir: configured source is {configured}, "
                    f"but tests run from {ROOT}. Re-run: "
                    f"meson setup --wipe {build.name}"
                )
            return


def _meson() -> str:
    meson = shutil.which("meson")
    if meson is None:
        pytest.skip("meson not installed")
    return meson


def _install_to_destdir() -> Path:
    build = _build_root()
    _assert_builddir_matches_repo(build)
    destdir = Path(tempfile.mkdtemp(prefix="threshold-destdir-"))
    # Allow rebuild so Blueprint/UI changes are picked up; stale --no-rebuild
    # fails hard after source-tree moves.
    result = subprocess.run(
        [_meson(), "install", "-C", str(build), f"--destdir={destdir}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.fail(result.stdout + result.stderr)
    return destdir


def _under_prefix(destdir: Path, *parts: str) -> list[Path]:
    """Return matching paths under /usr/local or /usr prefixes."""
    found = []
    for prefix in ("usr/local", "usr"):
        candidate = destdir.joinpath(prefix, *parts)
        if candidate.exists():
            found.append(candidate)
    return found


@pytest.fixture(scope="module")
def destdir():
    path = _install_to_destdir()
    yield path
    shutil.rmtree(path, ignore_errors=True)


def test_scalable_icon_installed(destdir: Path):
    icon = (
        destdir
        / "usr"
        / "local"
        / "share"
        / "icons"
        / "hicolor"
        / "scalable"
        / "apps"
        / f"{APP_ID}.svg"
    )
    alt = (
        destdir
        / "usr"
        / "share"
        / "icons"
        / "hicolor"
        / "scalable"
        / "apps"
        / f"{APP_ID}.svg"
    )
    assert icon.is_file() or alt.is_file(), f"missing scalable icon under {destdir}"


def test_symbolic_icon_installed(destdir: Path):
    candidates = list(
        destdir.glob(f"**/icons/hicolor/symbolic/apps/{APP_ID}-symbolic.svg")
    )
    assert candidates and candidates[0].is_file()


def test_metainfo_installed(destdir: Path):
    candidates = list(destdir.glob(f"**/metainfo/{APP_ID}.metainfo.xml"))
    assert candidates and candidates[0].is_file()


def test_udev_rule_installed_under_lib(destdir: Path):
    candidates = list(destdir.glob("**/lib/udev/rules.d/99-msi-battery.rules"))
    assert candidates and candidates[0].is_file(), (
        "udev rule must install to <prefix>/lib/udev/rules.d/ "
        f"(found={list(destdir.rglob('*.rules'))})"
    )
    text = candidates[0].read_text(encoding="utf-8")
    assert "charge_control_end_threshold" in text
    assert "plugdev" in text


def test_gresource_installed(destdir: Path):
    candidates = list(destdir.glob(f"**/{APP_ID}/threshold.gresource"))
    assert candidates and candidates[0].is_file(), (
        f"missing threshold.gresource under {destdir}"
    )


def test_gschema_installed(destdir: Path):
    candidates = list(destdir.glob(f"**/glib-2.0/schemas/{APP_ID}.gschema.xml"))
    assert candidates and candidates[0].is_file()


def test_desktop_file_installed(destdir: Path):
    candidates = list(destdir.glob(f"**/applications/{APP_ID}.desktop"))
    assert candidates and candidates[0].is_file()
    text = candidates[0].read_text(encoding="utf-8")
    assert "Exec=" in text


def test_launcher_installed(destdir: Path):
    found = _under_prefix(destdir, "bin", "threshold")
    assert found and found[0].is_file(), (
        f"missing threshold launcher under {destdir}"
    )


def test_debian_package_installs_compatibility_schema():
    install_file = ROOT / "debian" / "threshold.install"
    text = install_file.read_text(encoding="utf-8")
    assert (
        "usr/share/glib-2.0/schemas/"
        "com.bongbetic.batteryguard.gschema.xml" in text
    )


def test_source_icons_and_udev_live_under_data():
    assert (
        ROOT
        / "data"
        / "icons"
        / "hicolor"
        / "scalable"
        / "apps"
        / f"{APP_ID}.svg"
    ).is_file()
    assert (
        ROOT
        / "data"
        / "icons"
        / "hicolor"
        / "symbolic"
        / "apps"
        / f"{APP_ID}-symbolic.svg"
    ).is_file()
    assert (ROOT / "data" / "99-msi-battery.rules").is_file()
