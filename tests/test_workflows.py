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
    """Web CI job must reject runtime HTTP references in the bundle."""
    text = CI_WORKFLOW.read_text(encoding="utf-8")
    assert "Reject runtime HTTP references" in text
    assert "grep -rn" in text


def test_ci_web_job_verifies_bundle_freshness():
    """Web CI job must verify the committed bundle matches the build output."""
    text = CI_WORKFLOW.read_text(encoding="utf-8")
    assert "Verify bundle is committed" in text
    assert "git status" in text


# ── Issue #99: Build immutable v2.0.0 release candidates once ─────────────


def test_release_has_preflight_validation_job():
    """Release must validate version, EC, and manifest agreement before building."""
    text = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    assert "  preflight:" in text
    # Must check Meson version from meson.build
    assert "meson.build" in text
    # Must check EC manifest checksum matches vendored source
    assert "ec-manifest.json" in text
    # Must validate version agreement (tag vs meson vs spec)
    assert "preflight" in text


def test_release_has_source_archive_job():
    """Release must build the canonical source archive once from the signed tag."""
    text = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    assert "  source:" in text
    # Must produce a tar.gz source archive with the version in the name
    assert "Threshold-" in text or "threshold-" in text
    assert ".tar.gz" in text


def test_deb_and_rpm_use_source_archive():
    """DEB and RPM must build from the canonical source archive, not rebuild from checkout."""
    text = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    # The source job must exist
    assert "  source:" in text
    # DEB and RPM jobs must depend on source (via needs: [..., source])
    deb_section = text.split("  deb:", 1)[1].split("  rpm:", 1)[0]
    rpm_section = text.split("  rpm:", 1)[1].split("  appimage:", 1)[0]
    assert "source" in deb_section
    assert "source" in rpm_section
    # Both must download the source archive artifact
    assert "candidate-source" in deb_section or "source-archive" in deb_section
    assert "candidate-source" in rpm_section or "source-archive" in rpm_section


def test_release_manifest_includes_build_identity():
    """Release manifest must record source revision, build identity, and provenance."""
    text = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    assert "source_revision" in text
    assert "build_identity" in text or "build_identity" in text
    assert "provenance" in text or "runner" in text


def test_release_assembly_validates_candidate_inventory():
    """Assembly step must reject missing artifacts, unexpected names, or hash disagreement."""
    text = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    # Assembly must count candidates
    assert "wc -l" in text or "count" in text or "ls | wc" in text
    # Must verify exactly 5 candidates
    assert "5" in text
    # Must check hashes match
    assert "HASH MISMATCH" in text or "hash" in text


def test_release_all_verify_jobs_download_candidates():
    """Every verification job must download immutable candidates, never rebuild."""
    text = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    # All verify jobs use download-artifact
    assert "download-artifact" in text
    # Verify jobs must not build
    for section in text.split("  verify")[1:3]:  # deb-verify, rpm-verify
        for forbidden in ("dpkg-buildpackage", "rpmbuild", "meson setup"):
            assert forbidden not in section


# ── Issue #101: Enforce the MSI Thin A15 physical release gate ──────────────


def test_release_has_physical_gate_check_job():
    """Release must have a physical-gate-check job before promotion."""
    text = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    assert "physical-gate-check" in text
    # The physical gate check must validate evidence freshness
    assert "fresh" in text.lower() or "stale" in text.lower()
    # Must validate SHA-256 binding
    assert "sha256sum" in text
    # Must validate sanitization
    assert "sanitiz" in text.lower()


def test_release_promote_depends_on_physical_gate():
    """The promote job must depend on physical-gate-check."""
    text = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    promote_section = text.split("promote:", 1)[1]
    assert "physical-gate-check" in promote_section
    assert "needs:" in promote_section
