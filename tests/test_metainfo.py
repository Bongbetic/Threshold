"""AppStream metainfo: content contract and schema validation."""

from __future__ import annotations

import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
METAINFO = ROOT / "data" / "com.bongbetic.threshold.metainfo.xml"
APP_ID = "com.bongbetic.threshold"
REPO_URL = "https://github.com/Bongbetic/MSI-batteryguard-for-Thin-A15-B7UCX"
SCREENSHOT_PREFIX = f"{REPO_URL}/raw/main/data/screenshots/"
SUMMARY = "Battery charge threshold controller"
OARS_CATEGORIES = {
    "violence-cartoon",
    "violence-fantasy",
    "violence-realistic",
    "violence-bloodshed",
    "violence-sexual",
    "violence-desecration",
    "violence-slavery",
    "violence-worship",
    "drugs-alcohol",
    "drugs-narcotics",
    "drugs-tobacco",
    "sex-nudity",
    "sex-themes",
    "sex-homosexuality",
    "sex-prostitution",
    "sex-adultery",
    "sex-appearance",
    "language-profanity",
    "language-humor",
    "language-discrimination",
    "social-chat",
    "social-info",
    "social-audio",
    "social-contacts",
    "social-location",
    "money-purchasing",
    "money-gambling",
    "money-advertising",
}


def _root() -> ET.Element:
    return ET.parse(METAINFO).getroot()


def test_metainfo_file_exists():
    assert METAINFO.is_file()


def test_metainfo_identifies_app():
    root = _root()
    assert root.findtext("id") == APP_ID
    assert root.findtext("name") == "Threshold"
    assert root.findtext("summary") == SUMMARY
    assert root.find("description") is not None


def test_metainfo_summary_is_generic():
    assert _root().findtext("summary") == SUMMARY


def _normalized_text(element: ET.Element) -> str:
    """Element text with XML whitespace/newlines collapsed."""
    return re.sub(r"\s+", " ", "".join(element.itertext())).strip()


def _description_text() -> str:
    return _normalized_text(_root().find("description"))


def test_metainfo_description_generalised_to_any_ec_laptop():
    desc = _description_text()
    assert "laptops with EC charge-threshold support" in desc
    assert "msi-ec" not in desc.lower()


def test_metainfo_content_rating_all_oars_categories_none():
    rating = _root().find("content_rating")
    assert rating is not None
    assert rating.get("type") == "oars-1.1"
    attrs = rating.findall("content_attribute")
    assert {a.get("id") for a in attrs} == OARS_CATEGORIES
    assert all(a.text == "none" for a in attrs)


def test_metainfo_release_120_describes_rename_generalisation_scroll_free():
    releases = _root().findall("releases/release")
    rel_120 = next(r for r in releases if r.get("version") == "1.2.0")
    text = _normalized_text(rel_120.find("description")).lower()
    assert "rename" in text
    assert "multi-device" in text
    assert "scroll-free" in text


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


def test_metainfo_no_recommends_msi_ec_dkms():
    """msi-ec-dkms is now bundled, not a recommends dependency."""
    ids = {el.text for el in _root().findall("recommends/id")}
    assert "msi-ec-dkms" not in ids


def test_metainfo_description_has_no_msi_only_language():
    assert "MSI" not in _description_text()


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
