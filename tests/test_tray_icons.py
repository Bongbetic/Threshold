"""Artifact-owned notification-area battery icons (issue #86).

Every artifact ships namespaced empty/low/medium/good/full icons in
charging and non-charging forms so the SNI icon name always resolves
from the artifact, independent of the host icon theme.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATUS = ROOT / "data" / "icons" / "hicolor" / "scalable" / "status"
PREFIX = "com.bongbetic.threshold-battery-"
LEVELS = ("empty", "low", "medium", "good", "full")


def expected_names() -> set[str]:
    names = {f"{PREFIX}{level}.svg" for level in LEVELS}
    names |= {f"{PREFIX}{level}-charging.svg" for level in LEVELS}
    return names


def test_all_battery_icons_ship_in_every_artifact():
    actual = {p.name for p in STATUS.glob("*.svg")}
    assert actual == expected_names()


def test_battery_icons_are_valid_svg_with_viewbox():
    for path in STATUS.glob("*.svg"):
        text = path.read_text(encoding="utf-8")
        assert text.lstrip().startswith("<svg"), path.name
        assert 'viewBox="0 0 16 16"' in text, path.name
        assert "</svg>" in text, path.name


def test_charging_variants_differ_from_plain():
    for level in LEVELS:
        plain = (STATUS / f"{PREFIX}{level}.svg").read_text(encoding="utf-8")
        charging = (STATUS / f"{PREFIX}{level}-charging.svg").read_text(encoding="utf-8")
        assert plain != charging, level
