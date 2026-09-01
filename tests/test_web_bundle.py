"""Web bundle verification: completeness, offline safety, and freshness.

These tests verify that the committed production bundle under web/dist/
is complete, self-contained (no runtime HTTP dependencies), and
up-to-date with the current source.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = ROOT / "web"
DIST_DIR = WEB_DIR / "dist"
INDEX_HTML = DIST_DIR / "index.html"
FIXTURES = WEB_DIR / "test" / "fixtures" / "messages.json"


# ── Bundle existence ───────────────────────────────────────────────────────


def test_dist_directory_exists():
    assert DIST_DIR.is_dir(), "web/dist/ not found — run: cd web && npm run build"


def test_index_html_exists():
    assert INDEX_HTML.is_file(), "web/dist/index.html missing"


def test_dist_contains_js_assets():
    js_files = list(DIST_DIR.glob("assets/*.js"))
    assert js_files, "no JS assets in web/dist/assets/"


def test_dist_contains_css_assets():
    css_files = list(DIST_DIR.glob("assets/*.css"))
    assert css_files, "no CSS assets in web/dist/assets/"


def test_dist_contains_fonts():
    font_files = list(DIST_DIR.glob("fonts/*.woff2"))
    assert font_files, "no IBM Plex font files in web/dist/fonts/"


# ── Carbon components bundled ──────────────────────────────────────────────


def test_bundle_registers_carbon_components():
    """JS bundle must register at least one cds- custom element."""
    js_files = list(DIST_DIR.glob("assets/*.js"))
    assert js_files, "no JS bundle"
    content = js_files[0].read_text(encoding="utf-8")
    # Carbon web components register via customElements.define("cds-...")
    assert "cds-header" in content or "cds-button" in content, (
        "JS bundle does not contain Carbon component registrations"
    )


def test_bundle_contains_design_tokens():
    """CSS bundle must contain Carbon design token CSS custom properties."""
    css_files = list(DIST_DIR.glob("assets/*.css"))
    assert css_files, "no CSS bundle"
    content = css_files[0].read_text(encoding="utf-8")
    # Carbon tokens use --cds- prefix or standard Carbon tokens
    assert "--cds-" in content or "cds--" in content, (
        "CSS bundle does not contain Carbon design tokens"
    )


# ── Offline safety ─────────────────────────────────────────────────────────


def test_no_runtime_http_references():
    """Bundle must not contain fetchable HTTP/HTTPS URLs.

    SVG namespace URIs (w3.org) are identifiers, not network requests.
    """
    http_pattern = re.compile(r"https?://(?!www\.w3\.org)")
    for path in DIST_DIR.rglob("*"):
        if path.is_file() and not path.suffix == ".woff2":
            content = path.read_text(encoding="utf-8", errors="ignore")
            matches = http_pattern.findall(content)
            assert not matches, (
                f"{path.relative_to(DIST_DIR)} contains HTTP references: {matches[:3]}"
            )


# ── Source fixture: shared between Python and JS ──────────────────────────


def test_shared_fixture_exists():
    assert FIXTURES.is_file(), (
        "web/test/fixtures/messages.json missing — shared contract fixture"
    )


def test_shared_fixture_is_valid_json():
    data = json.loads(FIXTURES.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    # Must contain at least the core message types
    for key in ("ready_request", "ready_response", "get_state_request",
                "unknown_command_request"):
        assert key in data, f"fixture missing key: {key}"


# ── Bundle rebuild freshness ───────────────────────────────────────────────


def _compute_dist_fingerprint() -> str:
    """SHA-256 of all non-font dist files (sorted)."""
    h = hashlib.sha256()
    for path in sorted(DIST_DIR.rglob("*")):
        if path.is_file() and path.suffix != ".woff2":
            h.update(path.read_bytes())
    return h.hexdigest()


def _npm_build() -> subprocess.CompletedProcess:
    """Run npm ci + npm run build in the web directory."""
    return subprocess.run(
        ["npm", "ci"],
        cwd=str(WEB_DIR),
        capture_output=True,
        text=True,
        check=False,
    )


def test_committed_bundle_matches_source():
    """Rebuilding from source produces output identical to the committed bundle.

    This catches stale commits where source changed but the dist was not rebuilt.
    Skipped if Node.js is not available.
    """
    if not (WEB_DIR / "node_modules").is_dir():
        pytest.skip("web/node_modules not installed — run: cd web && npm ci")

    # Fingerprint the committed dist
    committed_hash = _compute_dist_fingerprint()

    # Rebuild from clean state
    build = subprocess.run(
        ["npm", "run", "build"],
        cwd=str(WEB_DIR),
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    if build.returncode != 0:
        pytest.fail(f"npm run build failed: {build.stderr}")

    rebuilt_hash = _compute_dist_fingerprint()

    assert committed_hash == rebuilt_hash, (
        "Committed web/dist/ is stale. Rebuild with: cd web && npm run build\n"
        f"Committed hash: {committed_hash}\n"
        f"Rebuilt hash:   {rebuilt_hash}"
    )


# ── Contract fixture: Python can read without Node ─────────────────────────


def test_python_contract_fixture_readable():
    """Python tests must be able to load the shared fixture without Node."""
    data = json.loads(FIXTURES.read_text(encoding="utf-8"))
    # Verify a few critical message shapes
    ready = data["ready_request"]
    assert ready["cmd"] == "ready"
    assert "id" in ready

    state = data["get_state_response"]
    assert state["ok"] is True
    assert "state" in state["data"]
    assert "appearance" in state["data"]
