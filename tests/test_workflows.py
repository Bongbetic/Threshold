"""GitHub Actions workflow contracts for supported build environments."""

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
RELEASE_WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"
SOURCE_FORMAT = ROOT / "debian" / "source" / "format"
WATCH_FILE = ROOT / "debian" / "watch"


def test_debian_source_metadata_uses_quilt_and_github_watch():
    assert SOURCE_FORMAT.read_text(encoding="utf-8").strip() == "3.0 (quilt)"
    watch = WATCH_FILE.read_text(encoding="utf-8")
    assert watch.splitlines() == [
        "Version: 5",
        "Template: GitHub",
        "Owner: Bongbetic",
        "Project: MSI-batteryguard-for-Thin-A15-B7UCX",
    ]


def test_ci_keeps_ubuntu_matrix_and_adds_debian_13_container():
    text = CI_WORKFLOW.read_text(encoding="utf-8")

    assert "os: [ubuntu-24.04, ubuntu-26.04]" in text
    assert "gir1.2-ayatanaappindicatorglib-2.0" not in text
    assert "  debian-13:" in text
    assert "container: debian:trixie" in text
    assert "useradd --create-home ci" in text
    assert "runuser -u ci --" in text
    assert "runuser -u ci -- dpkg-buildpackage -us -uc -b" in text
    assert "meson setup builddir" in text
    assert "meson compile -C builddir" in text
    assert "meson test -C builddir --print-errorlogs" in text
    assert "threshold-deb-debian-13" in text


def test_ci_runs_on_feature_branch_pushes():
    text = CI_WORKFLOW.read_text(encoding="utf-8")
    push = re.search(
        r"\n  push:\n(?P<body>(?:    .*\n)*)  pull_request:",
        text,
    )
    assert push is not None
    assert "branches:" not in push.group("body")


def test_workflows_use_threshold_package_artifact_names():
    ci = CI_WORKFLOW.read_text(encoding="utf-8")
    release = RELEASE_WORKFLOW.read_text(encoding="utf-8")

    assert "batteryguard-build-" not in ci
    assert "msi-batteryguard-deb-" not in ci
    assert "threshold-build-" in ci
    assert "threshold-deb-" in ci
    assert "msi-batteryguard_*.deb" not in release
    assert "threshold_*_amd64.deb" in release
    assert "msi-ec-dkms" not in release


def test_release_workflow_is_concurrency_locked_and_tag_triggered():
    text = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    assert "concurrency:" in text
    assert "cancel-in-progress: false" in text
    assert "tags: ['v*']" in text


def test_release_workflow_builds_candidates_once_and_never_rebuilds():
    text = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    # Candidate jobs produce checksums bound to the build
    assert "candidate.sha256" in text
    # Promotion step must not rebuild any artifact
    promote = text.split("promote:", 1)[1]
    for forbidden in ("dpkg-buildpackage", "rpmbuild", "build-appimage"):
        assert forbidden not in promote
    assert "environment: release-promotion" in text


def test_release_workflow_generates_manifest_and_checksums():
    text = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    assert "release-manifest.json" in text
    assert "SHA256SUMS" in text
    assert "sha256sum" in text
    assert "source_revision" in text


def test_release_workflow_promotes_protected_draft_unchanged():
    text = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    assert "draft: true" in text
    assert "make_latest: false" in text
    assert "release-promotion" in text
    assert "--draft=false" in text
    assert "--clobber" in text or "clobber" in text


def test_release_workflow_verifies_rpm_through_dnf_and_zypper():
    text = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    assert "opensuse/tumbleweed" in text
    assert "zypper" in text
    assert "dnf" in text


def test_release_workflow_verifies_appimage_candidate_startup():
    text = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    assert "--appimage-extract" in text
    assert "ec-bundle/manifest.json" in text


def test_release_workflow_checks_appimage_reproducibility():
    text = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    assert "not reproducible" in text
    assert "SOURCE_DATE_EPOCH" in text


def test_ci_has_web_job():
    """CI must have a dedicated web job for TypeScript, lint, vitest, and build."""
    text = CI_WORKFLOW.read_text(encoding="utf-8")
    assert "  web:" in text
    assert "npm ci" in text
    assert "tsc --noEmit" in text
    assert "vitest run" in text
    assert "npm run build" in text


def test_ci_installs_dbusmenu_for_notification_area_probe():
    """CI must install Dbusmenu 0.4 + dbus so the dbus-run-session probe runs."""
    text = CI_WORKFLOW.read_text(encoding="utf-8")
    assert "gir1.2-dbusmenu-glib-0.4" in text
    assert "dbus" in text


def test_ci_has_bundle_verify_job():
    """CI must have a bundle-verify job for offline safety and freshness."""
    text = CI_WORKFLOW.read_text(encoding="utf-8")
    assert "  bundle-verify:" in text
    assert "test_web_bundle.py" in text
    assert "test_carbon_xvfb.py" in text


def test_ci_web_job_rejects_http_references():
    """Web CI job must reject runtime HTTP/HTTPS references in the bundle."""
    text = CI_WORKFLOW.read_text(encoding="utf-8")
    assert "Reject runtime HTTP references" in text
    assert "grep -rn" in text


def test_ci_web_job_verifies_bundle_freshness():
    """Web CI job must verify the committed bundle matches the build output."""
    text = CI_WORKFLOW.read_text(encoding="utf-8")
    assert "Verify bundle is committed" in text
    assert "git status" in text
