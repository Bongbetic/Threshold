"""Meson install layout: icons, metainfo, and udev rule destinations."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
APP_ID = "com.bongbetic.batteryguard"


def _build_root() -> Path:
    env = os.environ.get("MESON_BUILD_ROOT")
    if env:
        return Path(env)
    candidate = ROOT / "builddir"
    if (candidate / "build.ninja").is_file():
        return candidate
    pytest.skip("no configured Meson build directory")


def _meson() -> str:
    meson = shutil.which("meson")
    if meson is None:
        pytest.skip("meson not installed")
    return meson


def _install_to_destdir() -> Path:
    build = _build_root()
    destdir = Path(tempfile.mkdtemp(prefix="batteryguard-destdir-"))
    result = subprocess.run(
        [_meson(), "install", "-C", str(build), f"--destdir={destdir}", "--no-rebuild"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.fail(result.stdout + result.stderr)
    return destdir


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
    # Default meson prefix is /usr/local; packaged builds use /usr.
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
