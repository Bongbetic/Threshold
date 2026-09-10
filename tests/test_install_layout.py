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
    # Allow rebuild so Blueprint/UI changes are picked up; stale --no-rebuild fails hard after source-tree moves.
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


def test_debian_package_installs_gsettings_convert_file():
    convert_file = ROOT / "data" / "com.bongbetic.batteryguard.convert"
    install_file = ROOT / "debian" / "threshold.install"

    assert convert_file.is_file()
    assert "usr/share/GConf/gsettings/" in install_file.read_text(
        encoding="utf-8"
    )

    lines = convert_file.read_text(encoding="utf-8").splitlines()
    assert "[com.bongbetic.threshold]" in lines
    mappings = {
        line.split(" = ", 1)[0]: line.split(" = ", 1)[1]
        for line in lines
        if " = " in line and not line.lstrip().startswith("#")
    }
    expected_keys = {
        "dark-mode",
        "autostart",
        "window-width",
        "window-height",
        "maximized",
        "charge-threshold",
    }
    assert set(mappings) == expected_keys
    assert all(
        value.startswith("/com/bongbetic/batteryguard/")
        for value in mappings.values()
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


# ── DEB packaging completeness (issue #93) ────────────────────────────────

_DEB_INSTALL = ROOT / "debian" / "threshold.install"
_DEB_POSTINST = ROOT / "debian" / "threshold.postinst"
_DEB_PRERM = ROOT / "debian" / "threshold.prerm"
_DEB_POSTRM = ROOT / "debian" / "threshold.postrm"
_DEB_CONTROL = ROOT / "debian" / "control"
_DEB_RULES = ROOT / "debian" / "rules"
_SYSUSERS = ROOT / "debian" / "threshold.sysusers"
_LIFECYCLE = ROOT / "packaging" / "threshold-ec-lifecycle"


def _install_manifest() -> str:
    return _DEB_INSTALL.read_text(encoding="utf-8")


def test_deb_installs_lifecycle_authority():
    assert "usr/sbin/threshold-ec-lifecycle" in _install_manifest()


def test_deb_installs_systemd_unit():
    assert (
        "usr/lib/systemd/system/threshold-boot-reconcile.service"
        in _install_manifest()
    )


def test_deb_installs_ec_dkms_source():
    manifest = _install_manifest()
    assert "msi-ec-src" in manifest
    assert "usr/src/msi-ec-0.13.112" in manifest


def test_deb_installs_udev_rule():
    assert "usr/lib/udev/rules.d/99-msi-battery.rules" in _install_manifest()


def test_deb_installs_notification_area_icons():
    manifest = _install_manifest()
    assert "icons/hicolor/scalable/apps/" in manifest
    assert "icons/hicolor/symbolic/apps/" in manifest


def test_deb_installs_dbusmenu_typelib():
    control = _DEB_CONTROL.read_text(encoding="utf-8")
    assert "gir1.2-dbusmenu-glib-0.4" in control


def test_deb_installs_web_ui():
    assert "usr/share/com.bongbetic.threshold/web/" in _install_manifest()


def test_deb_sysusers_file_exists():
    assert _SYSUSERS.is_file(), "debian/threshold.sysusers must exist"
    text = _SYSUSERS.read_text(encoding="utf-8")
    assert "threshold" in text


def test_deb_rules_enable_sysusers_and_systemd():
    rules = _DEB_RULES.read_text(encoding="utf-8")
    assert "--with sysusers" in rules
    assert "--with systemd" in rules


def test_deb_postinst_has_debhelper_token():
    text = _DEB_POSTINST.read_text(encoding="utf-8")
    assert "#DEBHELPER#" in text


def test_deb_postinst_invokes_lifecycle():
    text = _DEB_POSTINST.read_text(encoding="utf-8")
    assert "threshold-ec-lifecycle" in text
    assert "install-or-upgrade" in text


def test_deb_postinst_no_manual_systemctl():
    text = _DEB_POSTINST.read_text(encoding="utf-8")
    assert "systemctl" not in text, (
        "postinst must not call systemctl — dh_installsystemd handles this"
    )


def test_deb_prerm_has_debhelper_token():
    text = _DEB_PRERM.read_text(encoding="utf-8")
    assert "#DEBHELPER#" in text


def test_deb_prerm_invokes_lifecycle_on_remove():
    text = _DEB_PRERM.read_text(encoding="utf-8")
    assert "threshold-ec-lifecycle remove" in text


def test_deb_prerm_no_manual_systemctl():
    text = _DEB_PRERM.read_text(encoding="utf-8")
    assert "systemctl" not in text, (
        "prerm must not call systemctl — dh_installsystemd handles this"
    )


def test_deb_postrm_has_debhelper_token():
    text = _DEB_POSTRM.read_text(encoding="utf-8")
    assert "#DEBHELPER#" in text


def test_deb_postrm_purges_lifecycle_and_state():
    text = _DEB_POSTRM.read_text(encoding="utf-8")
    assert "threshold-ec-lifecycle remove" in text
    assert "rm -rf /var/lib/threshold" in text


def test_deb_control_has_runtime_deps():
    control = _DEB_CONTROL.read_text(encoding="utf-8")
    for dep in (
        "gir1.2-gtk-4.0",
        "gir1.2-adw-1",
        "gir1.2-notify-0.7",
        "gir1.2-webkit-6.0",
        "gir1.2-dbusmenu-glib-0.4",
        "dkms",
        "kmod",
        "systemd",
    ):
        assert dep in control, f"missing runtime dependency: {dep}"


def test_deb_control_recommends_not_depends():
    control = _DEB_CONTROL.read_text(encoding="utf-8")
    depends_section = control.split("Recommends:")[0]
    assert "policykit-1" not in depends_section, (
        "policykit-1 must be Recommends, not Depends"
    )
    assert "mokutil" not in depends_section, (
        "mokutil must be Recommends, not Depends"
    )
    recommends = control.split("Recommends:")[1]
    assert "policykit-1" in recommends
    assert "mokutil" in recommends


def test_deb_lifecycle_authority_source_exists():
    assert _LIFECYCLE.is_file(), "packaging/threshold-ec-lifecycle must exist"
