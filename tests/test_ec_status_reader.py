"""Tests for the sanitized EC status reader (issue #89).

Verifies that the Python reader correctly parses the world-readable
status file written by the lifecycle script and constructs ECStatus
values, and that absent or malformed files produce None.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from threshold.ec_status import read_ec_status
from threshold.ec_state import (
    ECSetupState,
    ECMaintenanceStatus,
    ECSetupReason,
)


def test_reads_available_status(tmp_path):
    status_file = tmp_path / "status"
    status_file.write_text(
        "setup_state=available\n"
        "maintenance=ok\n"
        "charge_threshold=80\n"
    )
    ec = read_ec_status(status_file)
    assert ec is not None
    assert ec.state == ECSetupState.AVAILABLE
    assert ec.reason is None
    assert ec.maintenance == ECMaintenanceStatus.OK


def test_reads_unavailable_with_reason(tmp_path):
    status_file = tmp_path / "status"
    status_file.write_text(
        "setup_state=unavailable\n"
        "reason=not_msi_hardware\n"
        "maintenance=ok\n"
        "charge_threshold=70\n"
    )
    ec = read_ec_status(status_file)
    assert ec is not None
    assert ec.state == ECSetupState.UNAVAILABLE
    assert ec.reason == ECSetupReason.NOT_MSI_HARDWARE


def test_reads_pending_reboot(tmp_path):
    status_file = tmp_path / "status"
    status_file.write_text(
        "setup_state=pending_reboot\n"
        "maintenance=ok\n"
        "charge_threshold=\n"
    )
    ec = read_ec_status(status_file)
    assert ec is not None
    assert ec.state == ECSetupState.PENDING_REBOOT
    assert ec.reason is None


def test_reads_maintenance_failed(tmp_path):
    status_file = tmp_path / "status"
    status_file.write_text(
        "setup_state=unavailable\n"
        "reason=build_failed\n"
        "maintenance=failed\n"
        "charge_threshold=80\n"
    )
    ec = read_ec_status(status_file)
    assert ec is not None
    assert ec.maintenance == ECMaintenanceStatus.FAILED
    assert ec.reason == ECSetupReason.BUILD_FAILED


def test_missing_file_returns_none(tmp_path):
    status_file = tmp_path / "nonexistent"
    ec = read_ec_status(status_file)
    assert ec is None


def test_empty_file_returns_none(tmp_path):
    status_file = tmp_path / "status"
    status_file.write_text("")
    ec = read_ec_status(status_file)
    assert ec is None


def test_malformed_file_returns_none(tmp_path):
    status_file = tmp_path / "status"
    status_file.write_text("garbage data\nno equals sign\n")
    ec = read_ec_status(status_file)
    assert ec is None


def test_unknown_setup_state_returns_none(tmp_path):
    status_file = tmp_path / "status"
    status_file.write_text(
        "setup_state=bogus\n"
        "maintenance=ok\n"
    )
    ec = read_ec_status(status_file)
    assert ec is None


def test_empty_charge_threshold_is_handled(tmp_path):
    status_file = tmp_path / "status"
    status_file.write_text(
        "setup_state=unavailable\n"
        "reason=not_msi_hardware\n"
        "maintenance=ok\n"
        "charge_threshold=\n"
    )
    ec = read_ec_status(status_file)
    assert ec is not None
    assert ec.state == ECSetupState.UNAVAILABLE


def test_omits_privileged_fields(tmp_path):
    status_file = tmp_path / "status"
    status_file.write_text(
        "setup_state=available\n"
        "maintenance=ok\n"
        "charge_threshold=80\n"
    )
    text = status_file.read_text()
    assert "boot_id" not in text
    assert "kernel=" not in text
    assert "sys_vendor" not in text
