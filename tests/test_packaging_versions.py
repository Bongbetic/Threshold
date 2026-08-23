"""Packaging drift guard: msi-ec version must be consistent.

Prevents the 0.13 vs 0.13.112 drift that shipped a stale msi-ec and
broke EC control on Thin A15 B7UCX (fix-v3 V3-1/V3-2).
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DKMS_CONF = ROOT / "msi-ec-src" / "dkms.conf"
INSTALL = ROOT / "debian" / "threshold.install"
POSTINST = ROOT / "debian" / "threshold.postinst"
PRERM = ROOT / "debian" / "threshold.prerm"
MAKE_VARS = ROOT / "msi-ec-src" / "Makefile.vars"


def _dkms_version() -> str:
    text = DKMS_CONF.read_text(encoding="utf-8")
    m = re.search(r'PACKAGE_VERSION\s*=\s*"?([^"\n]+)"?', text)
    assert m, "PACKAGE_VERSION not found in msi-ec-src/dkms.conf"
    return m.group(1).strip().strip('"')


def _find_versions(text: str) -> list[str]:
    return re.findall(r"0\.13(?:\.\d+)?", text)


def test_dkms_version_matches_packaging():
    ver = _dkms_version()
    for path in (INSTALL, POSTINST, PRERM):
        text = path.read_text(encoding="utf-8")
        versions = _find_versions(text)
        assert versions, f"no msi-ec version found in {path.name}"
        # POSTINST may contain legacy cleanup for 0.13 → allow it if primary ver present
        if path == POSTINST:
            assert ver in versions, f"{path.name} missing current version {ver}"
            for v in versions:
                assert v in (ver, "0.13"), f"{path.name} has unexpected version {v}"
            continue
        for v in versions:
            assert v == ver, f"{path.name} has {v} but dkms.conf is {ver}"


def test_makefile_vars_matches_dkms():
    ver = _dkms_version()
    text = MAKE_VARS.read_text(encoding="utf-8")
    m = re.search(r"VERSION\s*:=\s*(\S+)", text)
    assert m, "VERSION not found in msi-ec-src/Makefile.vars"
    assert m.group(1).strip() == ver, f"Makefile.vars VERSION {m.group(1)} != dkms.conf {ver}"


def test_dkms_version_is_0_13_112():
    assert _dkms_version() == "0.13.112"
