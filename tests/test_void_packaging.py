"""Contracts for the supported x86_64-glibc Void package."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VOID = ROOT / "packaging" / "void"


def test_void_template_is_unified_glibc_package():
    text = (VOID / "template").read_text()
    assert 'archs="x86_64"' in text
    assert "x86_64-musl" in text and "broken=" in text
    assert 'dkms_modules="msi-ec 0.13.112"' in text
    assert 'system_groups="threshold"' in text
    assert "vsv threshold-boot-reconcile" in text
    assert "usr/sbin" not in text


def test_runit_reconciliation_is_once_then_paused():
    text = (VOID / "files" / "threshold-boot-reconcile" / "run").read_text()
    assert "threshold-ec-lifecycle reconcile" in text
    assert "exec pause" in text


def test_void_install_does_not_enable_service():
    install = (VOID / "INSTALL").read_text()
    message = (VOID / "INSTALL.msg").read_text()
    assert "install-or-upgrade" in install
    assert "/var/service" not in install
    assert "ln -s /etc/sv/threshold-boot-reconcile /var/service/" in message


def test_void_removal_preserves_state_explicitly():
    text = (VOID / "REMOVE").read_text()
    assert "threshold-ec-lifecycle remove" in text
    assert "rm -rf /var/lib/threshold" not in text


def test_void_package_is_not_a_release_candidate():
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text()
    assert "candidate-xbps" not in workflow
