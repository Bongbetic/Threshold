"""Shared EC lifecycle integration layer contract (issue #86).

The lifecycle script is the single owner of EC setup, update, repair,
reconciliation, and removal behavior. DEB and RPM hooks invoke it without
reimplementing lifecycle logic. These tests assert the durable contract:
verbs, MSI preflight before any build/load, no package-manager invocation
from lifecycle code, ownership ledger, per-kernel records, and structured
state file.
"""

import stat
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIFECYCLE = ROOT / "packaging" / "threshold-ec-lifecycle"
UNIT = ROOT / "data" / "threshold-boot-reconcile.service"


def _script() -> str:
    return LIFECYCLE.read_text(encoding="utf-8")


def test_lifecycle_script_exists_and_is_executable():
    assert LIFECYCLE.exists()
    mode = LIFECYCLE.stat().st_mode
    assert mode & stat.S_IXUSR


def test_lifecycle_exposes_required_verbs():
    text = _script()
    for verb in ("install-or-upgrade", "repair", "reconcile", "remove", "diagnostics"):
        assert f'{verb})' in text, f"missing case for verb {verb}"


def test_lifecycle_preflights_msi_dmi_before_building():
    text = _script()
    assert "dmi/id/sys_vendor" in text
    # Preflight must appear before the first dkms invocation
    assert text.index("sys_vendor") < text.index("dkms")


def test_lifecycle_never_invokes_package_managers():
    text = _script()
    for forbidden in ("apt-get", "apt ", "dnf ", "zypper", "dpkg "):
        assert forbidden not in text, f"lifecycle must not invoke {forbidden}"


def test_lifecycle_uses_ownership_ledger():
    text = _script()
    assert "/var/lib/threshold/ec/ledger" in text


def test_lifecycle_records_per_kernel_evidence():
    text = _script()
    assert "kernels" in text
    assert "boot_id" in text


def test_lifecycle_writes_structured_setup_state():
    text = _script()
    assert "setup_state" in text
    for state in ("available", "pending_reboot", "unavailable"):
        assert state in text


def test_lifecycle_preserves_charge_threshold_on_remove():
    text = _script()
    # removal must not touch GSettings / charge threshold
    assert "gsettings" not in text


def test_lifecycle_never_unloads_working_module_on_removal():
    text = _script()
    assert "modprobe -r" not in text


def test_boot_reconcile_unit_is_oneshot_before_graphical():
    text = UNIT.read_text(encoding="utf-8")
    assert "Type=oneshot" in text
    assert "Before=graphical.target" in text
    assert "threshold-ec-lifecycle reconcile" in text
    assert "TimeoutStartSec" in text


def test_reconciliation_performs_single_write_and_readback():
    text = _script()
    assert "charge_control_end_threshold" in text
    # no retry loop markers
    assert "while true" not in text
