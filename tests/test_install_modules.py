"""Regression: every src/threshold/*.py module must ship in python_sources.

A module missing from ``src/meson.build`` installs fine for development
runs (PYTHONPATH=src) but is absent from the packaged .deb, producing a
ModuleNotFoundError at launch (see migration.py omission fixed in 1.2.1).
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_MESON = ROOT / "src" / "meson.build"


def _listed_modules() -> set[str]:
    text = SRC_MESON.read_text(encoding="utf-8")
    match = re.search(r"python_sources\s*=\s*\[(.*?)\]", text, re.DOTALL)
    assert match, "could not parse python_sources in src/meson.build"
    return set(re.findall(r"'(threshold/[^']+\.py)'", match.group(1)))


def test_all_threshold_modules_listed_in_python_sources():
    on_disk = {
        str(p.relative_to(ROOT / "src"))
        for p in (ROOT / "src" / "threshold").glob("*.py")
        if not p.name.startswith("__pycache__")
    }
    listed = _listed_modules()
    missing = on_disk - listed
    assert not missing, (
        f"modules present under src/threshold/ but missing from "
        f"src/meson.build python_sources: {sorted(missing)}"
    )
    stale = listed - on_disk
    assert not stale, (
        f"python_sources lists files that no longer exist: {sorted(stale)}"
    )


def test_migration_module_is_shipped():
    """migration.py is imported by application.py; it must be installed."""
    assert "threshold/migration.py" in _listed_modules()
