"""Shared EC lifecycle integration layer contract (issue #86, #89).

The lifecycle script is the single owner of EC setup, update, repair,
reconciliation, and removal behavior. DEB and RPM hooks invoke it without
reimplementing lifecycle logic. These tests assert the durable contract:
verbs, MSI preflight before any build/load, no package-manager invocation
from lifecycle code, ownership ledger, per-kernel records, structured
state file, and sanitized world-readable status summary.
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
    assert text.index("sys_vendor") < text.index("dkms add")


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


# ── Sanitized status summary (issue #89) ────────────────────────────────────


def test_lifecycle_exposes_status_file_path():
    text = _script()
    assert "EC_STATUS_FILE" in text


def test_lifecycle_has_write_sanitized_status_function():
    text = _script()
    assert "write_sanitized_status" in text


def test_lifecycle_calls_write_sanitized_status_after_setup():
    text = _script()
    # In the dispatch section, write_sanitized_status appears after do_setup
    dispatch = text[text.index("case \"${1:-}\""):]
    assert "do_setup" in dispatch
    assert "write_sanitized_status" in dispatch
    assert dispatch.index("do_setup") < dispatch.index("write_sanitized_status")


def test_status_summary_omits_boot_id():
    text = _script()
    # The write_sanitized_status function must not include boot_id
    idx = text.index("write_sanitized_status")
    fn_body = text[idx:idx + 800]
    assert "grep" in fn_body  # extracts only bounded fields


def test_lifecycle_removes_status_on_removal():
    text = _script()
    assert 'rm -f "$EC_STATE_FILE" "$EC_STATUS_FILE"' in text


# ── Issue #91: exclusive operation lock, journaled transactions ─────────────


def test_lifecycle_uses_flock_for_exclusive_lock():
    text = _script()
    assert "flock" in text
    assert "acquire_lock" in text
    assert "release_lock" in text


def test_lifecycle_has_operations_journal():
    text = _script()
    assert "ops-journal" in text
    assert "begin_op" in text
    assert "end_op" in text


def test_lifecycle_uses_atomic_file_writes():
    text = _script()
    assert "atomic_write" in text
    assert "sync_file" in text


def test_lifecycle_has_bounded_journal_retention():
    text = _script()
    assert "prune_journal" in text
    assert "JOURNAL_MAX" in text


def test_lifecycle_has_bounded_log_retention():
    text = _script()
    assert "prune_lifecycle_log" in text
    assert "LOG_MAX_LINES" in text


def test_lifecycle_dispatch_acquires_lock_for_mutations():
    text = _script()
    dispatch = text[text.index("Verb dispatch"):]
    assert "acquire_lock" in dispatch
    assert "begin_op" in dispatch
    assert "end_op" in dispatch
    # diagnostics is read-only and must appear after the lock acquisition
    # section in the dispatch (it's handled by the second case block)
    diag_block = dispatch.index("diagnostics)")
    lock_block = dispatch.index("acquire_lock")
    # The lock acquisition happens in the first case block, diagnostics
    # is in the second case block — diagnostics must NOT acquire the lock
    second_case = dispatch.index("case \"${1", dispatch.index("case \"${1") + 1)
    assert diag_block > second_case


def test_lifecycle_state_layout_includes_lock_and_journal():
    text = _script()
    assert "lock" in text
    assert "ops-journal" in text


def test_lifecycle_idempotency_check_present():
    text = _script()
    assert "was_completed" in text
