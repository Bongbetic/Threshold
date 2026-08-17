"""Tests for the battery sysfs logic module."""

import stat
import subprocess
from pathlib import Path

from threshold import battery


# ─── find_battery_path ─────────────────────────────────────────────────────────


def test_find_battery_path_found(tmp_path, monkeypatch):
    """Returns the path when BAT0 has type Battery and charge_control_end_threshold."""
    bat0 = tmp_path / "BAT0"
    bat0.mkdir()
    (bat0 / "type").write_text("Battery")
    (bat0 / "charge_control_end_threshold").write_text("80")
    _mock_power_supply_root(monkeypatch, tmp_path)
    assert battery.find_battery_path() == bat0


def test_find_battery_path_first_wins(tmp_path, monkeypatch):
    """Returns the path that has both type and threshold when earlier ones lack them."""
    bat0 = tmp_path / "BAT0"
    bat1 = tmp_path / "BAT1"
    bat0.mkdir()
    (bat0 / "type").write_text("Battery")
    bat1.mkdir()
    (bat1 / "type").write_text("Battery")
    (bat1 / "charge_control_end_threshold").write_text("80")
    _mock_power_supply_root(monkeypatch, tmp_path)
    assert battery.find_battery_path() == bat1


def test_find_battery_path_nonexistent(tmp_path, monkeypatch):
    """Returns None when battery dir exists but lacks threshold file."""
    bat0 = tmp_path / "BAT0"
    bat0.mkdir()
    (bat0 / "type").write_text("Battery")
    _mock_power_supply_root(monkeypatch, tmp_path)
    assert battery.find_battery_path() is None


def test_find_battery_path_all_missing(tmp_path, monkeypatch):
    """Returns None when power_supply directory is empty."""
    _mock_power_supply_root(monkeypatch, tmp_path)
    assert battery.find_battery_path() is None


# ─── find_battery_path — dynamic enumeration ──────────────────────────────────


def _mock_power_supply_root(monkeypatch, tmp_path):
    """Monkeypatch Path.iterdir on /sys/class/power_supply to return items from tmp_path."""
    real_iterdir = Path.iterdir

    def fake_iterdir(self):
        if self.name == "power_supply":
            return list(tmp_path.iterdir())
        return real_iterdir(self)

    monkeypatch.setattr(Path, "iterdir", fake_iterdir)


def test_find_battery_path_dynamic_bat0_found(tmp_path, monkeypatch):
    """Finds BAT0 when it has type=Battery and threshold file."""
    bat0 = tmp_path / "BAT0"
    bat0.mkdir()
    (bat0 / "type").write_text("Battery")
    (bat0 / "charge_control_end_threshold").write_text("80")
    _mock_power_supply_root(monkeypatch, tmp_path)
    assert battery.find_battery_path() == bat0


def test_find_battery_path_filters_non_battery_type(tmp_path, monkeypatch):
    """Skips entries whose type file does not read Battery."""
    mains = tmp_path / "AC_ADAPTER"
    mains.mkdir()
    (mains / "type").write_text("Mains")
    (mains / "charge_control_end_threshold").write_text("90")  # would match if not filtered
    bat0 = tmp_path / "BAT0"
    bat0.mkdir()
    (bat0 / "type").write_text("Battery")
    (bat0 / "charge_control_end_threshold").write_text("80")
    _mock_power_supply_root(monkeypatch, tmp_path)
    result = battery.find_battery_path()
    assert result == bat0


def test_find_battery_path_skips_no_type_file(tmp_path, monkeypatch):
    """Skips entries without a type file."""
    unknown = tmp_path / "UNKNOWN"
    unknown.mkdir()
    (unknown / "charge_control_end_threshold").write_text("70")
    bat0 = tmp_path / "BAT0"
    bat0.mkdir()
    (bat0 / "type").write_text("Battery")
    (bat0 / "charge_control_end_threshold").write_text("80")
    _mock_power_supply_root(monkeypatch, tmp_path)
    assert battery.find_battery_path() == bat0


def test_find_battery_path_skips_no_threshold_file(tmp_path, monkeypatch):
    """Skips entries that have type Battery but lack threshold file."""
    cat1 = tmp_path / "BAT1"
    cat1.mkdir()
    (cat1 / "type").write_text("Battery")
    cat0 = tmp_path / "BAT0"
    cat0.mkdir()
    (cat0 / "type").write_text("Battery")
    (cat0 / "charge_control_end_threshold").write_text("80")
    _mock_power_supply_root(monkeypatch, tmp_path)
    assert battery.find_battery_path() == cat0


def test_find_battery_path_multi_battery_first_wins(tmp_path, monkeypatch):
    """When multiple batteries qualify, returns the first one found."""
    bat0 = tmp_path / "BAT0"
    bat0.mkdir()
    (bat0 / "type").write_text("Battery")
    (bat0 / "charge_control_end_threshold").write_text("60")
    bat1 = tmp_path / "BAT1"
    bat1.mkdir()
    (bat1 / "type").write_text("Battery")
    (bat1 / "charge_control_end_threshold").write_text("80")
    _mock_power_supply_root(monkeypatch, tmp_path)
    assert battery.find_battery_path() == bat0


def test_find_battery_path_no_matching_battery(tmp_path, monkeypatch):
    """Returns None when no battery has both type and threshold."""
    bat0 = tmp_path / "BAT0"
    bat0.mkdir()
    (bat0 / "type").write_text("Battery")
    # No threshold file
    _mock_power_supply_root(monkeypatch, tmp_path)
    assert battery.find_battery_path() is None


def test_find_battery_path_empty_directory(tmp_path, monkeypatch):
    """Returns None when power_supply directory is empty."""
    _mock_power_supply_root(monkeypatch, tmp_path)
    assert battery.find_battery_path() is None


def test_find_battery_path_mixed_devices(tmp_path, monkeypatch):
    """Properly filters through Mains, UPS, and finds Battery."""
    ac = tmp_path / "AC_ADAPTER"
    ac.mkdir()
    (ac / "type").write_text("Mains")
    ups = tmp_path / "UPS"
    ups.mkdir()
    (ups / "type").write_text("UPS")
    (ups / "charge_control_end_threshold").write_text("90")
    bat0 = tmp_path / "BAT0"
    bat0.mkdir()
    (bat0 / "type").write_text("Battery")
    (bat0 / "charge_control_end_threshold").write_text("80")
    _mock_power_supply_root(monkeypatch, tmp_path)
    result = battery.find_battery_path()
    assert result == bat0


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


# ─── read_charge_percent ───────────────────────────────────────────────────────


def test_read_charge_percent_prefers_capacity(tmp_path):
    (tmp_path / "capacity").write_text("53\n")
    (tmp_path / "charge_now").write_text("1000")
    (tmp_path / "charge_full").write_text("2000")
    (tmp_path / "charge_full_design").write_text("3000")
    assert battery.read_charge_percent(tmp_path) == 53


def test_read_charge_percent_falls_back_to_charge_full(tmp_path):
    (tmp_path / "charge_now").write_text("1600")
    (tmp_path / "charge_full").write_text("2000")
    (tmp_path / "charge_full_design").write_text("4000")
    assert battery.read_charge_percent(tmp_path) == 80


def test_read_charge_percent_falls_back_to_design(tmp_path):
    (tmp_path / "charge_now").write_text("2000")
    (tmp_path / "charge_full_design").write_text("4000")
    assert battery.read_charge_percent(tmp_path) == 50


def test_read_charge_percent_clamps_capacity(tmp_path):
    (tmp_path / "capacity").write_text("150")
    assert battery.read_charge_percent(tmp_path) == 100


def test_read_charge_percent_missing(tmp_path):
    assert battery.read_charge_percent(tmp_path) is None


# ─── write_threshold — direct write ────────────────────────────────────────────


def test_write_threshold_direct(tmp_path):
    """Direct write succeeds when the file is writable."""
    threshold = tmp_path / "charge_control_end_threshold"
    threshold.write_text("0")
    success, method = battery.write_threshold(tmp_path, 80)
    assert success is True
    assert method == "direct"
    assert threshold.read_text().strip() == "80"


def test_write_threshold_rejects_out_of_range(tmp_path):
    threshold = tmp_path / "charge_control_end_threshold"
    threshold.write_text("80")
    success, message = battery.write_threshold(tmp_path, 10)
    assert success is False
    assert "20" in message
    assert threshold.read_text().strip() == "80"


# ─── write_threshold — PermissionError fallback ────────────────────────────────


def test_write_threshold_permission_error_pkexec_success(tmp_path, monkeypatch):
    """Falls back to pkexec when direct write gets PermissionError."""
    threshold = tmp_path / "charge_control_end_threshold"
    threshold.write_text("0")
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


# ─── write_threshold — pkexec not found ────────────────────────────────────────


def test_write_threshold_pkexec_missing(tmp_path, monkeypatch):
    """Returns a clear install hint when pkexec is not installed."""
    threshold = tmp_path / "charge_control_end_threshold"
    threshold.write_text("0")
    threshold.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)

    def mock_run(cmd, *args, **kwargs):
        raise FileNotFoundError("pkexec not found")

    monkeypatch.setattr(subprocess, "run", mock_run)
    success, method = battery.write_threshold(tmp_path, 80)
    assert success is False
    assert "pkexec not found" in method
    assert "INSTALL.md" in method


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


# ─── write_threshold — OSError on direct write ─────────────────────────────────


def test_write_threshold_direct_write_other_error_returns_failure(tmp_path, monkeypatch):
    """A non-PermissionError during direct write returns a failure tuple."""
    threshold = tmp_path / "charge_control_end_threshold"
    threshold.write_text("0")

    def broken_write(self, data):
        raise OSError("something else")

    monkeypatch.setattr(Path, "write_text", broken_write)
    success, method = battery.write_threshold(tmp_path, 80)
    assert success is False
    assert method == "something else"


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
