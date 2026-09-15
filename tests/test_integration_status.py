from pathlib import Path

from threshold.integration_status import (
    RUNIT_ENABLE_COMMAND,
    detect_boot_reconciliation,
)


def test_reconciliation_absent_off_void(tmp_path):
    assert detect_boot_reconciliation(tmp_path / "missing", ()) == (None, None)


def test_reconciliation_installed_but_disabled(tmp_path):
    service = tmp_path / "etc" / "sv" / "threshold-boot-reconcile"
    service.mkdir(parents=True)
    assert detect_boot_reconciliation(service, ()) == (
        False,
        RUNIT_ENABLE_COMMAND,
    )


def test_reconciliation_enabled_by_service_link(tmp_path):
    service = tmp_path / "etc" / "sv" / "threshold-boot-reconcile"
    service.mkdir(parents=True)
    enabled = tmp_path / "var" / "service" / "threshold-boot-reconcile"
    enabled.parent.mkdir(parents=True)
    enabled.symlink_to(service)
    assert detect_boot_reconciliation(service, (enabled,)) == (True, None)
