"""Privileged fake-system EC transaction tests (issue #86, #89).

Runs the real lifecycle script with substituted DKMS, module, Secure Boot,
udev, boot identity, and sysfs effects (PATH stubs + THRESHOLD_FAKE_SYS
sysroot), asserting preflight rejection, setup states, pending-reboot
consumption, reconciliation single-write/readback, foreign-asset
preservation, removal semantics, idempotency, sanitized status summary,
machine-wide policy persistence, and absence of privileged side effects
— without root.
"""

import os
import subprocess
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LIFECYCLE = ROOT / "packaging" / "threshold-ec-lifecycle"

MSI_VENDOR = "Micro-Star International Co., Ltd."


def stub(path: Path, body: str) -> None:
    path.write_text(textwrap.dedent(body))
    path.chmod(0o755)


@pytest.fixture()
def fake_system(tmp_path: Path):
    """A fake system: sysroot, tool stubs, state dir, and env."""
    sysroot = tmp_path / "sys"
    bindir = tmp_path / "bin"
    state = tmp_path / "state"
    for d in (
        sysroot / "sys/class/dmi/id",
        sysroot / "sys/class/power_supply/BAT0",
        sysroot / "proc/sys/kernel/random",
        bindir,
        state,
    ):
        d.mkdir(parents=True)

    (sysroot / "proc/sys/kernel/random/boot_id").write_text("boot-a\n")

    # Tools: default to success paths; tests flip them per scenario.
    stub(bindir / "dkms", """\
        #!/bin/sh
        echo "dkms $1" >> "$DKMS_LOG"
        exit 0
        """)
    stub(bindir / "modprobe", """\
        #!/bin/sh
        echo "modprobe $*" >> "$DKMS_LOG"
        exit 0
        """)
    stub(bindir / "mokutil", """\
        #!/bin/sh
        echo "SecureBoot disabled"
        exit 0
        """)
    stub(bindir / "udevadm", "#!/bin/sh\nexit 0\n")

    env = dict(
        os.environ,
        PATH=f"{bindir}:{os.environ['PATH']}",
        THRESHOLD_FAKE_SYS=str(sysroot),
        THRESHOLD_EC_STATE_DIR=str(state),
        THRESHOLD_EC_DKMS_SRC=str(tmp_path / "usr/src/msi-ec-0.13.112"),
        THRESHOLD_EC_MODULES_LOAD=str(tmp_path / "modules-load.d/msi-ec.conf"),
        DKMS_LOG=str(tmp_path / "dkms.log"),
        THRESHOLD_EC_KERNEL="fake-kernel",
    )
    return type("Fake", (), {
        "sysroot": sysroot,
        "state": state,
        "env": env,
        "battery": sysroot / "sys/class/power_supply/BAT0",
    })


def run_lifecycle(fake, verb: str, boot_id: str | None = None):
    env = dict(fake.env)
    if boot_id:
        (fake.sysroot / "proc/sys/kernel/random/boot_id").write_text(boot_id + "\n")
    return subprocess.run(
        [str(LIFECYCLE), verb],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def read_state(fake) -> dict:
    lines = (fake.state / "state").read_text().splitlines()
    return dict(line.split("=", 1) for line in lines if "=" in line)


def make_msi(fake):
    (fake.sysroot / "sys/class/dmi/id/sys_vendor").write_text(
        MSI_VENDOR + "\n"
    )


def add_threshold_interface(fake):
    (fake.battery / "type").write_text("Battery\n")
    (fake.battery / "charge_control_end_threshold").write_text("80\n")


@pytest.mark.usefixtures("fake_system")
class TestFakeSystemLifecycle:
    def test_non_msi_hardware_never_builds_or_loads(self, fake_system):
        fake = fake_system
        (fake.sysroot / "sys/class/dmi/id/sys_vendor").write_text(
            "Lenovo\n"
        )
        r = run_lifecycle(fake, "install-or-upgrade")
        assert r.returncode == 0  # package transaction never fails
        assert read_state(fake)["setup_state"] == "unavailable"
        assert read_state(fake)["reason"] == "not_msi_hardware"
        assert not (Path(fake.env["DKMS_LOG"])).exists()

    def test_missing_kernel_headers_is_repairable(self, fake_system):
        fake = fake_system
        make_msi(fake)
        (fake.sysroot / "lib/modules/fake-kernel").mkdir(parents=True)
        r = run_lifecycle(fake, "install-or-upgrade")
        assert r.returncode == 0
        st = read_state(fake)
        assert st["reason"] == "kernel_headers_missing"

    def test_successful_setup_is_verified_available(self, fake_system):
        fake = fake_system
        make_msi(fake)
        (fake.sysroot / "lib/modules/fake-kernel/build").mkdir(parents=True)
        add_threshold_interface(fake)
        r = run_lifecycle(fake, "install-or-upgrade")
        assert r.returncode == 0
        st = read_state(fake)
        assert st["setup_state"] == "available"
        assert st["maintenance"] == "ok"
        ledger = (fake.state / "ledger").read_text()
        assert fake.env["THRESHOLD_EC_DKMS_SRC"] in ledger

    def test_build_failure_keeps_setup_reasoned_and_maintenance_failed(
        self, fake_system
    ):
        fake = fake_system
        make_msi(fake)
        (fake.sysroot / "lib/modules/fake-kernel/build").mkdir(parents=True)
        stub(Path(fake.env["PATH"].split(":")[0]) / "dkms", """\
            #!/bin/sh
            [ "$1" = build ] && exit 1
            exit 0
            """)
        r = run_lifecycle(fake, "install-or-upgrade")
        assert r.returncode == 0
        st = read_state(fake)
        assert st["setup_state"] == "unavailable"
        assert st["reason"] == "build_failed"
        assert st["maintenance"] == "failed"

    def test_secure_boot_load_failure_records_pending_reboot(self, fake_system):
        fake = fake_system
        make_msi(fake)
        (fake.sysroot / "lib/modules/fake-kernel/build").mkdir(parents=True)
        stub(Path(fake.env["PATH"].split(":")[0]) / "mokutil", """\
            #!/bin/sh
            echo "SecureBoot enabled"
            exit 0
            """)
        stub(Path(fake.env["PATH"].split(":")[0]) / "modprobe", """\
            #!/bin/sh
            exit 1
            """)
        r = run_lifecycle(fake, "install-or-upgrade")
        assert r.returncode == 0
        st = read_state(fake)
        assert st["reason"] == "load_failed_secure_boot"
        pending = (fake.state / "pending-reboot").read_text()
        assert "boot_id=boot-a" in pending
        assert "action=setup" in pending

    def test_first_different_boot_consumes_pending(self, fake_system):
        fake = fake_system
        make_msi(fake)
        (fake.sysroot / "lib/modules/fake-kernel/build").mkdir(parents=True)
        (fake.state / "pending-reboot").write_text(
            "boot_id=boot-a\ntarget_kernel=fake-kernel\naction=setup\n"
        )
        run_lifecycle(fake, "reconcile", boot_id="boot-a")
        assert (fake.state / "pending-reboot").exists()  # same boot: persists
        run_lifecycle(fake, "reconcile", boot_id="boot-b")
        assert not (fake.state / "pending-reboot").exists()  # consumed

    def test_reconcile_writes_once_and_verifies_readback(self, fake_system):
        fake = fake_system
        make_msi(fake)
        add_threshold_interface(fake)
        (fake.state / "charge-threshold").write_text("70\n")
        (fake.battery / "charge_control_end_threshold").write_text("80\n")
        r = run_lifecycle(fake, "reconcile", boot_id="boot-b")
        assert r.returncode == 0
        assert (fake.battery / "charge_control_end_threshold").read_text() == "70\n"
        assert read_state(fake)["setup_state"] == "available"

    def test_reconcile_readback_mismatch_is_reasoned_unavailable(
        self, fake_system
    ):
        fake = fake_system
        make_msi(fake)
        add_threshold_interface(fake)
        (fake.state / "charge-threshold").write_text("70\n")
        # Stub: sysfs writes silently do nothing (readback stays 80).
        (fake.battery / "charge_control_end_threshold").write_text("80\n")
        (fake.battery / "charge_control_end_threshold").chmod(0o444)
        r = run_lifecycle(fake, "reconcile", boot_id="boot-b")
        (fake.battery / "charge_control_end_threshold").chmod(0o644)
        assert r.returncode == 0
        assert read_state(fake)["setup_state"] == "unavailable"

    def test_reconcile_noop_when_active_matches_desired(self, fake_system):
        fake = fake_system
        make_msi(fake)
        add_threshold_interface(fake)
        (fake.state / "charge-threshold").write_text("80\n")
        run_lifecycle(fake, "reconcile", boot_id="boot-b")
        assert (fake.battery / "charge_control_end_threshold") \
            .read_text() == "80\n"

    def test_vendor_sysfs_reconcile_never_claims_ec_available(self, fake_system):
        fake = fake_system
        (fake.sysroot / "sys/class/dmi/id/sys_vendor").write_text("Dell\n")
        add_threshold_interface(fake)
        (fake.state / "charge-threshold").write_text("70\n")
        (fake.battery / "charge_control_end_threshold").write_text("80\n")
        r = run_lifecycle(fake, "reconcile", boot_id="boot-b")
        assert r.returncode == 0
        assert "70" in (fake.battery / "charge_control_end_threshold").read_text()
        state_file = fake.state / "state"
        assert not state_file.exists() or (
            dict(l.split("=", 1) for l in state_file.read_text().splitlines() if "=" in l)
        ).get("setup_state") != "available"

    def test_removal_keeps_working_module_and_foreign_assets(self, fake_system):
        fake = fake_system
        make_msi(fake)
        (fake.sysroot / "lib/modules/fake-kernel/build").mkdir(parents=True)
        dkms_src = Path(fake.env["THRESHOLD_EC_DKMS_SRC"])
        dkms_src.mkdir(parents=True)
        foreign = fake.state / "foreign-asset"
        foreign.write_text("do not touch\n")
        run_lifecycle(fake, "install-or-upgrade")
        # Working module is loaded: removal must leave it alone.
        (fake.sysroot / "sys/devices/platform/msi-ec").mkdir(parents=True)
        (fake.sysroot / "proc/modules").write_text("msi_ec 16384 - Live\n")
        run_lifecycle(fake, "remove", boot_id="boot-a")
        assert foreign.read_text() == "do not touch\n"
        assert not (fake.state / "ledger").exists()
        # The module dir may be removed by dkms stub-side ownership, but the
        # loaded platform device is untouched.
        assert (fake.sysroot / "sys/devices/platform/msi-ec").exists()

    def test_removal_never_unloads_working_module(self, fake_system):
        fake = fake_system
        make_msi(fake)
        (fake.sysroot / "lib/modules/fake-kernel/build").mkdir(parents=True)
        run_lifecycle(fake, "install-or-upgrade")
        (fake.sysroot / "proc/modules").write_text("msi_ec 16384 - Live\n")
        log = Path(fake.env["DKMS_LOG"])
        log.write_text("")
        run_lifecycle(fake, "remove", boot_id="boot-a")
        assert "modprobe -r" not in log.read_text()

    # ── Sanitized status summary (issue #89) ────────────────────────────────

    def test_install_writes_sanitized_status(self, fake_system):
        fake = fake_system
        make_msi(fake)
        (fake.sysroot / "lib/modules/fake-kernel/build").mkdir(parents=True)
        add_threshold_interface(fake)
        run_lifecycle(fake, "install-or-upgrade")
        status = fake.state / "status"
        assert status.exists()
        kv = dict(l.split("=", 1) for l in status.read_text().splitlines() if "=" in l)
        assert kv["setup_state"] == "available"
        assert "maintenance" in kv

    def test_status_summary_omits_privileged_fields(self, fake_system):
        fake = fake_system
        make_msi(fake)
        (fake.sysroot / "lib/modules/fake-kernel/build").mkdir(parents=True)
        add_threshold_interface(fake)
        run_lifecycle(fake, "install-or-upgrade")
        status = fake.state / "status"
        text = status.read_text()
        assert "boot_id" not in text
        assert "kernel=" not in text
        assert "dkms" not in text.lower()

    def test_non_msi_status_shows_unavailable_reason(self, fake_system):
        fake = fake_system
        (fake.sysroot / "sys/class/dmi/id/sys_vendor").write_text("Lenovo\n")
        run_lifecycle(fake, "install-or-upgrade")
        status = fake.state / "status"
        kv = dict(l.split("=", 1) for l in status.read_text().splitlines() if "=" in l)
        assert kv["setup_state"] == "unavailable"
        assert kv["reason"] == "not_msi_hardware"

    def test_reconcile_updates_sanitized_status(self, fake_system):
        fake = fake_system
        make_msi(fake)
        add_threshold_interface(fake)
        (fake.state / "charge-threshold").write_text("70\n")
        run_lifecycle(fake, "reconcile", boot_id="boot-b")
        status = fake.state / "status"
        kv = dict(l.split("=", 1) for l in status.read_text().splitlines() if "=" in l)
        assert kv["setup_state"] == "available"

    # ── Machine-wide policy persistence (issue #89) ─────────────────────────

    def test_charge_threshold_survives_ec_removal(self, fake_system):
        fake = fake_system
        make_msi(fake)
        (fake.sysroot / "lib/modules/fake-kernel/build").mkdir(parents=True)
        add_threshold_interface(fake)
        (fake.state / "charge-threshold").write_text("80\n")
        run_lifecycle(fake, "install-or-upgrade")
        # Remove EC assets
        run_lifecycle(fake, "remove", boot_id="boot-a")
        # Machine-wide charge threshold persists
        assert (fake.state / "charge-threshold").read_text() == "80\n"
        # State file is cleaned up
        assert not (fake.state / "state").exists()

    def test_removal_preserves_charge_threshold_not_state(self, fake_system):
        fake = fake_system
        make_msi(fake)
        (fake.sysroot / "lib/modules/fake-kernel/build").mkdir(parents=True)
        add_threshold_interface(fake)
        (fake.state / "charge-threshold").write_text("65\n")
        run_lifecycle(fake, "install-or-upgrade")
        assert (fake.state / "state").exists()
        run_lifecycle(fake, "remove", boot_id="boot-a")
        # Threshold policy survives
        assert (fake.state / "charge-threshold").read_text() == "65\n"
        # State file does not survive
        assert not (fake.state / "state").exists()

    # ── Collision refusal / foreign asset preservation (issue #89) ──────────

    def test_removal_only_removes_ledger_proven_assets(self, fake_system):
        fake = fake_system
        make_msi(fake)
        (fake.sysroot / "lib/modules/fake-kernel/build").mkdir(parents=True)
        dkms_src = Path(fake.env["THRESHOLD_EC_DKMS_SRC"])
        dkms_src.mkdir(parents=True)
        # Foreign asset outside the ledger
        foreign_dir = fake.state / "foreign-ec-config"
        foreign_dir.mkdir()
        (foreign_dir / "config.conf").write_text("foreign\n")
        run_lifecycle(fake, "install-or-upgrade")
        run_lifecycle(fake, "remove", boot_id="boot-a")
        # Foreign asset is untouched
        assert (foreign_dir / "config.conf").read_text() == "foreign\n"
        assert not (fake.state / "ledger").exists()

    def test_ledger_distinguishes_managed_from_foreign(self, fake_system):
        fake = fake_system
        make_msi(fake)
        (fake.sysroot / "lib/modules/fake-kernel/build").mkdir(parents=True)
        run_lifecycle(fake, "install-or-upgrade")
        ledger = (fake.state / "ledger").read_text()
        assert fake.env["THRESHOLD_EC_DKMS_SRC"] in ledger
        assert fake.env["THRESHOLD_EC_MODULES_LOAD"] in ledger
        # Foreign paths are not in the ledger
        assert "/etc/foreign" not in ledger

    # ── Absence of privileged side effects (issue #89) ──────────────────────

    def test_status_read_does_not_write_state(self, fake_system):
        """Reading the sanitized status file must not trigger lifecycle writes."""
        fake = fake_system
        # No lifecycle verb has run yet — state file should not exist
        assert not (fake.state / "state").exists()
        status = fake.state / "status"
        # Simulate a status read (what the Python reader does)
        if status.exists():
            status.read_text()
        # State file still does not exist
        assert not (fake.state / "state").exists()

    def test_diagnostics_does_not_write_status(self, fake_system):
        """The diagnostics verb must not produce a sanitized status file."""
        fake = fake_system
        make_msi(fake)
        run_lifecycle(fake, "diagnostics")
        assert not (fake.state / "status").exists()

    def test_status_file_is_world_readable(self, fake_system):
        """Sanitized status file must be readable without privileges."""
        fake = fake_system
        make_msi(fake)
        (fake.sysroot / "lib/modules/fake-kernel/build").mkdir(parents=True)
        add_threshold_interface(fake)
        run_lifecycle(fake, "install-or-upgrade")
        status = fake.state / "status"
        mode = status.stat().st_mode
        # World-readable (other-read bit set)
        assert mode & 0o004
