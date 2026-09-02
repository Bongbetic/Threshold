"""Packaging drift guard: integration manifest is the single version source.

Prevents the 0.13 vs 0.13.112 drift that shipped a stale msi-ec and
broke EC control on Thin A15 B7UCX (fix-v3 V3-1/V3-2). All packaging
inputs derive from packaging/ec-manifest.json or validate against it.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DKMS_CONF = ROOT / "msi-ec-src" / "dkms.conf"
INSTALL = ROOT / "debian" / "threshold.install"
POSTINST = ROOT / "debian" / "threshold.postinst"
PRERM = ROOT / "debian" / "threshold.prerm"
MAKE_VARS = ROOT / "msi-ec-src" / "Makefile.vars"
LIFECYCLE = ROOT / "packaging" / "threshold-ec-lifecycle"
MANIFEST = ROOT / "packaging" / "ec-manifest.json"
SPEC = ROOT / "packaging" / "threshold.spec"


def _manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def manifest_msi_ec_version() -> str:
    return _manifest()["msi_ec"]["version"]


def _dkms_version() -> str:
    text = DKMS_CONF.read_text(encoding="utf-8")
    m = re.search(r'PACKAGE_VERSION\s*=\s*"?([^"\n]+)"?', text)
    assert m, "PACKAGE_VERSION not found in msi-ec-src/dkms.conf"
    return m.group(1).strip().strip('"')


def _find_versions(text: str) -> list[str]:
    return re.findall(r"0\.13(?:\.\d+)?", text)


def _vendored_checksum() -> str:
    h = hashlib.sha256()
    files = sorted(
        p for p in (ROOT / _manifest()["msi_ec"]["source_dir"]).rglob("*")
        if p.is_file()
    )
    for p in files:
        h.update(f"{p.relative_to(ROOT)}\n".encode())
        h.update(p.read_bytes())
    return h.hexdigest()


def test_manifest_schema_and_required_keys():
    m = _manifest()
    assert m["schema"] == 1
    for key in ("msi_ec", "dkms", "lifecycle"):
        assert key in m
    assert m["dkms"]["name"] == "msi-ec"
    assert m["dkms"]["installed_source_path"].startswith("/usr/src/")
    assert m["lifecycle"]["command"] == "/usr/sbin/threshold-ec-lifecycle"


def test_manifest_checksum_matches_vendored_source():
    assert _manifest()["msi_ec"]["checksum"] == _vendored_checksum()


def test_dkms_version_matches_manifest():
    assert _dkms_version() == manifest_msi_ec_version()


def test_packaging_inputs_match_manifest_version():
    """Lifecycle authority + RPM spec pin the manifest version.

    DEB hooks intentionally contain no version: they delegate everything
    to the shared lifecycle command.
    """
    ver = manifest_msi_ec_version()
    for path in (LIFECYCLE, SPEC):
        text = path.read_text(encoding="utf-8")
        versions = _find_versions(text)
        assert versions, f"no msi-ec version found in {path.name}"
        for v in versions:
            assert v == ver, f"{path.name} has {v} but manifest is {ver}"


def test_deb_hooks_delegate_versions_to_lifecycle():
    """Hooks must not hardcode the msi-ec version (single source of truth)."""
    for path in (POSTINST, PRERM):
        versions = _find_versions(path.read_text(encoding="utf-8"))
        assert not versions, f"{path.name} hardcodes version; delegate to lifecycle"


def test_makefile_vars_matches_manifest():
    ver = manifest_msi_ec_version()
    text = MAKE_VARS.read_text(encoding="utf-8")
    m = re.search(r"VERSION\s*:=\s*(\S+)", text)
    assert m, "VERSION not found in msi-ec-src/Makefile.vars"
    assert m.group(1).strip() == ver, f"Makefile.vars VERSION {m.group(1)} != manifest {ver}"


def test_dkms_version_is_0_13_112():
    assert _dkms_version() == "0.13.112"
