"""Dispatcher EC recovery actions + guidance contract (issue #86).

Recovery guidance is presentation-neutral: state carries recovery actions
mapped from EC setup/maintenance state, and the dispatcher exposes
explicit gestures (setup/repair/diagnostics) with structured failures.
"""

import os
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from threshold.battery import ControlMode
from threshold.commands import CommandDispatcher, ErrorCode
from threshold.config import Config
from threshold.ec_state import (
    ECStatus,
    ECSetupState,
    ECSetupReason,
    ECMaintenanceStatus,
)
from threshold.state import ThresholdState

from test_state_ec_fields import FakeGSettings


def make_dispatcher(tmp_path, marker=False):
    config = Config(settings=FakeGSettings())
    dispatcher = CommandDispatcher(config)
    if marker:
        ec_state_dir = tmp_path / "ec"
        ec_state_dir.mkdir(exist_ok=True)
        (ec_state_dir / "package-owned").write_text("")
    return dispatcher


class TestRecoveryActionsMappedFromState:
    def test_repairable_unavailable_offers_repair_and_diagnostics(self):
        ec = ECStatus(
            state=ECSetupState.UNAVAILABLE,
            reason=ECSetupReason.KERNEL_HEADERS_MISSING,
        )
        assert ec.recovery_actions == ("repair", "diagnostics")

    def test_neutral_unavailable_offers_diagnostics_only(self):
        ec = ECStatus(
            state=ECSetupState.UNAVAILABLE,
            reason=ECSetupReason.NOT_MSI_HARDWARE,
        )
        assert ec.recovery_actions == ("diagnostics",)

    def test_pending_reboot_offers_reboot_only(self):
        ec = ECStatus(state=ECSetupState.PENDING_REBOOT)
        assert ec.recovery_actions == ("reboot",)

    def test_available_with_failed_maintenance_offers_repair(self):
        ec = ECStatus(
            state=ECSetupState.AVAILABLE,
            maintenance=ECMaintenanceStatus.FAILED,
        )
        assert ec.recovery_actions == ("repair", "diagnostics")

    def test_adapter_surfaces_recovery_actions(self):
        from threshold.adapter import build_state

        config = Config(settings=FakeGSettings())
        ec = ECStatus(
            state=ECSetupState.UNAVAILABLE,
            reason=ECSetupReason.BUILD_FAILED,
        )
        state = build_state(battery_path=None, config=config, ec_status=ec)
        assert state.ec_recovery_actions == ("repair", "diagnostics")


class TestECActionCommands:
    def test_unknown_action_rejected(self, tmp_path, monkeypatch):
        d = make_dispatcher(tmp_path)
        r = d.dispatch("ec_action", {"action": "reboot"})
        assert r.success is False
        assert r.error_code == ErrorCode.INVALID_ARGS

    def test_no_authority_is_structured_failure(self, tmp_path, monkeypatch):
        monkeypatch.delenv("THRESHOLD_APPIMAGE", raising=False)
        d = make_dispatcher(tmp_path)
        with patch("pathlib.Path.exists", return_value=False):
            r = d.dispatch("ec_action", {"action": "setup"})
        assert r.success is False
        assert r.error_code == ErrorCode.EC_NOT_AVAILABLE

    def test_package_setup_uses_fresh_pkexec(self, tmp_path, monkeypatch):
        monkeypatch.delenv("THRESHOLD_APPIMAGE", raising=False)
        d = make_dispatcher(tmp_path)
        calls = {}

        def fake_run(cmd, **kw):
            calls["cmd"] = cmd
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        with patch.object(Path, "exists", return_value=True), \
             patch("subprocess.run", side_effect=fake_run), \
             patch.object(CommandDispatcher, "PACKAGE_OWNED_MARKER", str(tmp_path / "m")):
            r = d.dispatch("ec_action", {"action": "setup"})
        assert r.success is True
        assert r.data["exit_class"] == "success"
        assert calls["cmd"][:2] == ["pkexec", CommandDispatcher.PACKAGE_LIFECYCLE]
        assert calls["cmd"][2] == "install-or-upgrade"

    def test_appimage_setup_uses_bootstrap(self, tmp_path, monkeypatch):
        monkeypatch.setenv("THRESHOLD_APPIMAGE", "1")
        d = make_dispatcher(tmp_path)
        calls = {}

        def fake_run(cmd, **kw):
            calls["cmd"] = cmd
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        with patch.object(Path, "exists", return_value=False), \
             patch("subprocess.run", side_effect=fake_run):
            r = d.dispatch("ec_action", {"action": "repair"})
        assert r.success is True
        assert "threshold-appimage-bootstrap" in calls["cmd"]
        assert calls["cmd"][-1] == "repair"

    def test_failed_operation_is_structured(self, tmp_path, monkeypatch):
        monkeypatch.setenv("THRESHOLD_APPIMAGE", "1")
        d = make_dispatcher(tmp_path)

        def fake_run(cmd, **kw):
            return subprocess.CompletedProcess(cmd, 4, stdout="", stderr="boom")

        with patch.object(Path, "exists", return_value=False), \
             patch("subprocess.run", side_effect=fake_run):
            r = d.dispatch("ec_action", {"action": "setup"})
        assert r.success is False
        assert r.error_code == ErrorCode.EC_OPERATION_FAILED
        assert r.data["exit_code"] == 4

    def test_diagnostics_unprivileged(self, tmp_path, monkeypatch):
        d = make_dispatcher(tmp_path)

        def fake_run(cmd, **kw):
            assert "pkexec" not in cmd
            return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")

        with patch.object(Path, "exists", return_value=True), \
             patch("subprocess.run", side_effect=fake_run):
            r = d.dispatch("ec_diagnostics", {})
        assert r.success is True
        assert r.data["diagnostics"] == "ok"

    def test_repair_never_triggers_from_passive_poll(self, tmp_path, monkeypatch):
        """The repair command is only reachable via explicit ec_action dispatch,
        never from get_state or other passive commands."""
        monkeypatch.delenv("THRESHOLD_APPIMAGE", raising=False)
        d = make_dispatcher(tmp_path)
        calls = {}

        def fake_run(cmd, **kw):
            calls["cmd"] = cmd
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        # get_state should not trigger any subprocess
        config = Config(settings=FakeGSettings())
        r = d.dispatch("get_state", state=None)
        assert r.success is False  # no state available
        assert "subprocess" not in str(calls)

        # Only ec_action with action="repair" triggers the lifecycle
        with patch.object(Path, "exists", return_value=True), \
             patch("subprocess.run", side_effect=fake_run):
            r = d.dispatch("ec_action", {"action": "repair"})
        assert r.success is True
        assert calls["cmd"][-1] == "repair"
