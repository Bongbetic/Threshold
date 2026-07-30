"""AppStream metainfo: content contract and schema validation."""

from __future__ import annotations

import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
METAINFO = ROOT / "data" / "com.bongbetic.batteryguard.metainfo.xml"
APP_ID = "com.bongbetic.batteryguard"
REPO_URL = "https://github.com/Bongbetic/MSI-batteryguard-for-Thin-A15-B7UCX"
SCREENSHOT_PREFIX = f"{REPO_URL}/raw/main/data/screenshots/"


def _root() -> ET.Element:
    return ET.parse(METAINFO).getroot()


def test_metainfo_file_exists():
    assert METAINFO.is_file()


def test_metainfo_identifies_app():
    root = _root()
    assert root.findtext("id") == APP_ID
    assert root.findtext("name") == "MSI BatteryGuard"
    assert root.findtext("summary")
    assert root.find("description") is not None


def test_metainfo_categories_include_system_and_hardware_settings():
    cats = {c.text for c in _root().findall("categories/category")}
    assert cats >= {"System", "HardwareSettings"}


def test_metainfo_has_homepage_and_bugtracker_urls():
    urls = {u.get("type"): u.text for u in _root().findall("url")}
    assert urls.get("homepage") == REPO_URL
    assert urls.get("bugtracker") == f"{REPO_URL}/issues"


def test_metainfo_has_project_group_and_license():
    root = _root()
    assert root.findtext("project_group")
    assert root.findtext("project_license") == "GPL-3.0-or-later"


def test_metainfo_recommends_msi_ec_dkms():
    ids = {el.text for el in _root().findall("recommends/id")}
    assert "msi-ec-dkms" in ids


def test_metainfo_screenshots_point_at_github_hosted_images():
    images = [img.text for img in _root().findall("screenshots/screenshot/image")]
    assert images, "expected at least one screenshot image URL"
    for url in images:
        assert url.startswith(SCREENSHOT_PREFIX), url
        assert url.endswith((".png", ".jpg", ".jpeg", ".webp")), url
        local = ROOT / "data" / "screenshots" / Path(url).name
        assert local.is_file(), f"screenshot asset missing: {local}"


def test_metainfo_release_matches_meson_version():
    meson_build = ROOT / "meson.build"
    text = meson_build.read_text(encoding="utf-8")
    match = re.search(
        r"project\s*\(\s*'[^']+'\s*,\s*version:\s*'([^']+)'",
        text,
        re.DOTALL,
    )
    assert match, "could not parse meson.project version"
    meson_version = match.group(1)
    releases = [el.get("version") for el in _root().findall("releases/release")]
    assert releases, "metainfo has no <release> entries"
    assert meson_version in releases, (
        f"metainfo releases {releases} missing meson version {meson_version}"
    )


def test_metainfo_passes_appstreamcli_validate():
    appstreamcli = shutil.which("appstreamcli")
    if appstreamcli is None:
        pytest.skip("appstreamcli not installed")
    result = subprocess.run(
        [appstreamcli, "validate", "--no-net", str(METAINFO)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
