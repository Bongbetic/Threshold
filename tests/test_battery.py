"""Tests for the battery sysfs logic module."""

import stat
import subprocess
from pathlib import Path

import pytest

from batteryguard import battery


# ─── find_battery_path ─────────────────────────────────────────────────────────


def test_find_battery_path_found(tmp_path, monkeypatch):
    """Returns the path when BAT0 has charge_control_end_threshold."""
    bat0 = tmp_path / "BAT0"
    bat0.mkdir()
    (bat0 / "charge_control_end_threshold").write_text("80")
    monkeypatch.setattr(battery, "SYSFS_BASES", [str(bat0)])
    assert battery.find_battery_path() == bat0


def test_find_battery_path_first_wins(tmp_path, monkeypatch):
    """Returns the first battery path that has the threshold file."""
    bat0 = tmp_path / "BAT0"
    bat1 = tmp_path / "BAT1"
    bat0.mkdir()
    bat1.mkdir()
    (bat1 / "charge_control_end_threshold").write_text("80")
    monkeypatch.setattr(battery, "SYSFS_BASES", [str(bat0), str(bat1)])
    # BAT0 has no threshold file so it should return BAT1
    assert battery.find_battery_path() == bat1


def test_find_battery_path_nonexistent(tmp_path, monkeypatch):
    """Returns None when no battery path has the threshold file."""
    bat0 = tmp_path / "BAT0"
    bat0.mkdir()
    monkeypatch.setattr(battery, "SYSFS_BASES", [str(bat0)])
    assert battery.find_battery_path() is None


def test_find_battery_path_all_missing(tmp_path, monkeypatch):
    """Returns None when no battery directories exist at all."""
    monkeypatch.setattr(
        battery, "SYSFS_BASES",
        [str(tmp_path / "BAT0"), str(tmp_path / "BAT1")],
    )
    assert battery.find_battery_path() is None


# ─── read_sysfs ────────────────────────────────────────────────────────────────


def test_read_sysfs_returns_content(tmp_path):
    f = tmp_path / "test_file"
    f.write_text("  80\n")
    assert battery.read_sysfs(f) == "80"


def test_read_sysfs_nonexistent(tmp_path):
    assert battery.read_sysfs(tmp_path / "nope") is None


def test_read_sysfs_directory(tmp_path):
    """Returns None when path is a directory (cannot read)."""
    assert battery.read_sysfs(tmp_path) is None


# ─── write_threshold — direct write ────────────────────────────────────────────


def test_write_threshold_direct(tmp_path):
    """Direct write succeeds when the file is writable."""
    threshold = tmp_path / "charge_control_end_threshold"
    threshold.write_text("0")
    success, method = battery.write_threshold(tmp_path, 80)
    assert success is True
    assert method == "direct"
    assert threshold.read_text().strip() == "80"


# ─── write_threshold — PermissionError fallback ────────────────────────────────


def test_write_threshold_permission_error_pkexec_success(tmp_path, monkeypatch):
    """Falls back to pkexec when direct write gets PermissionError."""
    threshold = tmp_path / "charge_control_end_threshold"
    threshold.write_text("0")
    # Make the file read-only so direct write raises PermissionError
    threshold.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)

    calls = []

    def mock_subprocess_run(cmd, *args, **kwargs):
        calls.append(cmd)
        return type("Result", (), {"returncode": 0, "stdout": "", "stderr": ""})()

    monkeypatch.setattr(subprocess, "run", mock_subprocess_run)
    success, method = battery.write_threshold(tmp_path, 80)
    assert success is True
    assert method == "pkexec"
    assert "pkexec" in calls[0]


def test_write_threshold_permission_error_pkexec_fails(tmp_path, monkeypatch):
    """Returns failure with pkexec stderr when pkexec returns non-zero."""
    threshold = tmp_path / "charge_control_end_threshold"
    threshold.write_text("0")
    threshold.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)

    def mock_run(cmd, *args, **kwargs):
        return type("Result", (), {
            "returncode": 1, "stdout": "", "stderr": "pkexec: auth failed\n"
        })()

    monkeypatch.setattr(subprocess, "run", mock_run)
    success, method = battery.write_threshold(tmp_path, 80)
    assert success is False
    assert method == "pkexec: auth failed"


# ─── write_threshold — pkexec not found → sudo fallback ────────────────────────


def test_write_threshold_pkexec_missing_sudo_success(tmp_path, monkeypatch):
    """Falls back to sudo when pkexec is not installed."""
    threshold = tmp_path / "charge_control_end_threshold"
    threshold.write_text("0")
    threshold.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)

    calls = []

    def mock_run(cmd, *args, **kwargs):
        calls.append(cmd)
        if cmd[0] == "pkexec":
            raise FileNotFoundError("pkexec not found")
        return type("Result", (), {"returncode": 0, "stdout": "", "stderr": ""})()

    monkeypatch.setattr(subprocess, "run", mock_run)
    success, method = battery.write_threshold(tmp_path, 80)
    assert success is True
    assert method == "sudo"
    assert len(calls) == 2
    assert calls[0][0] == "pkexec"
    assert calls[1][0] == "sudo"


def test_write_threshold_pkexec_missing_sudo_fails(tmp_path, monkeypatch):
    """Returns failure message when both pkexec and sudo fail (no stderr)."""
    threshold = tmp_path / "charge_control_end_threshold"
    threshold.write_text("0")
    threshold.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)

    def mock_run(cmd, *args, **kwargs):
        if cmd[0] == "pkexec":
            raise FileNotFoundError("pkexec not found")
        return type("Result", (), {
            "returncode": 1, "stdout": "", "stderr": "",
        })()

    monkeypatch.setattr(subprocess, "run", mock_run)
    success, method = battery.write_threshold(tmp_path, 80)
    assert success is False
    assert "Permission denied" in method


def test_write_threshold_pkexec_missing_sudo_stderr(tmp_path, monkeypatch):
    """Returns sudo stderr when sudo fails with output."""
    threshold = tmp_path / "charge_control_end_threshold"
    threshold.write_text("0")
    threshold.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)

    def mock_run(cmd, *args, **kwargs):
        if cmd[0] == "pkexec":
            raise FileNotFoundError("pkexec not found")
        return type("Result", (), {
            "returncode": 1, "stdout": "", "stderr": "sudo: a password is required\n",
        })()

    monkeypatch.setattr(subprocess, "run", mock_run)
    success, method = battery.write_threshold(tmp_path, 80)
    assert success is False
    assert method == "sudo: a password is required"


def test_write_threshold_sudo_raises(tmp_path, monkeypatch):
    """Returns the exception message when sudo itself raises."""
    threshold = tmp_path / "charge_control_end_threshold"
    threshold.write_text("0")
    threshold.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)

    def mock_run(cmd, *args, **kwargs):
        if cmd[0] == "pkexec":
            raise FileNotFoundError("pkexec not found")
        raise OSError("sudo: not found")

    monkeypatch.setattr(subprocess, "run", mock_run)
    success, method = battery.write_threshold(tmp_path, 80)
    assert success is False
    assert method == "sudo: not found"


# ─── write_threshold — timeout ────────────────────────────────────────────────


def test_write_threshold_pkexec_timeout(tmp_path, monkeypatch):
    """Returns timeout message when pkexec times out."""
    threshold = tmp_path / "charge_control_end_threshold"
    threshold.write_text("0")
    threshold.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)

    def mock_run(cmd, *args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=30)

    monkeypatch.setattr(subprocess, "run", mock_run)
    success, method = battery.write_threshold(tmp_path, 80)
    assert success is False
    assert method == "Auth dialog timed out"


# ─── write_threshold — generic exception on direct write ───────────────────────


def test_write_threshold_direct_write_other_error_propagates(tmp_path, monkeypatch):
    """A non-PermissionError during direct write propagates (not caught)."""
    threshold = tmp_path / "charge_control_end_threshold"
    threshold.write_text("0")

    def broken_write(self, data):
        raise OSError("something else")

    monkeypatch.setattr(Path, "write_text", broken_write)
    with pytest.raises(OSError, match="something else"):
        battery.write_threshold(tmp_path, 80)


def test_write_threshold_generic_exception_in_pkexec(tmp_path, monkeypatch):
    """Any non-FileNotFoundError, non-TimeoutExpired raises in pkexec are caught."""
    threshold = tmp_path / "charge_control_end_threshold"
    threshold.write_text("0")
    threshold.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)

    def mock_run(cmd, *args, **kwargs):
        raise RuntimeError("unexpected crash")

    monkeypatch.setattr(subprocess, "run", mock_run)
    success, method = battery.write_threshold(tmp_path, 80)
    assert success is False
    assert method == "unexpected crash"
