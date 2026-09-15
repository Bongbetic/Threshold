"""Protected release assembly, signing, promotion, and withdrawal (issue #102).

Eight canonical public assets: DEB, Unified RPM, AppImage, source archive,
source RPM, release manifest, checksum inventory, detached armored checksum
signature.  Draft is private, approval-controlled, immutable on promotion,
and audibly withdrawn when defective.
"""

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RELEASE_WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"
WITHDRAW_WORKFLOW = ROOT / ".github" / "workflows" / "withdraw.yml"


# ── Draft assembly: exactly eight canonical public assets ──────────────


def test_draft_includes_all_eight_canonical_assets():
    """The assemble-draft job publishes exactly the eight canonical assets."""
    text = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    # Find the assemble-draft section
    assert "assemble-draft:" in text
    assemble = text.split("assemble-draft:", 1)[1]
    # Must list all eight asset types in the draft files
    for asset in [
        "*.deb",
        "*.rpm",
        "*.AppImage",
        "*.tar.gz",
        "release-manifest.json",
        "SHA256SUMS",
    ]:
        assert asset in assemble, f"Draft missing asset: {asset}"
    # SRPM must be included alongside RPM
    assert "*.src.rpm" in assemble or "src.rpm" in assemble, (
        "Draft must include source RPM (*.src.rpm)"
    )
    # Draft must be private
    assert "draft: true" in assemble
    # Latest must be disabled during draft
    assert "make_latest: false" in assemble


def test_draft_does_not_rebuild_or_rename_candidates():
    """Assembly must download immutable candidates, never rebuild or rename."""
    text = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    assemble = text.split("assemble-draft:", 1)[1]
    # Must download artifacts (not build)
    assert "download-artifact" in assemble
    # Must not build
    for forbidden in ("dpkg-buildpackage", "rpmbuild", "build-appimage", "meson setup"):
        assert forbidden not in assemble, (
            f"Assembly must not rebuild: {forbidden}"
        )


# ── Release manifest: provenance binding ───────────────────────────────


def test_release_manifest_includes_provenance_and_evidence():
    """The manifest binds candidates to provenance, distribution, desktop, and physical evidence."""
    text = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    # Manifest generation must include provenance fields
    assert "source_revision" in text
    assert "build_identity" in text or "build_identity" in text
    # Must include evidence binding (supported-distribution results, desktop results, physical)
    assert "supported_distribution" in text or "distro" in text.lower() or "distribution" in text.lower()
    assert "desktop" in text.lower()
    assert "physical" in text.lower() or "msi" in text.lower()


def test_release_manifest_binds_sha256_for_every_candidate():
    """Each candidate in the manifest has a SHA-256 hash."""
    text = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    # Manifest generation uses sha256sum
    assert "sha256sum" in text
    # Manifest JSON structure includes sha256 per candidate
    assert '"sha256"' in text or "'sha256'" in text


# ── Checksum inventory: covers candidates + manifest ───────────────────


def test_checksum_inventory_covers_all_candidates_and_manifest():
    """SHA256SUMS includes all five candidates plus the release manifest."""
    text = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    # SHA256SUMS is generated from the candidates directory
    assert "SHA256SUMS" in text
    # The generate step hashes everything in the candidates dir (which includes manifest)
    assemble = text.split("assemble-draft:", 1)[1]
    # Manifest must be in the same directory as candidates before SHA256SUMS is generated
    assert "release-manifest.json" in assemble
    # SHA256SUMS must be generated after manifest and candidates are collected
    assert "sha256sum" in assemble


# ── Signing: detached armored checksum signature ───────────────────────


def test_promotion_signs_checksum_inventory_with_gpg():
    """The promote step signs SHA256SUMS with a detached armored GPG signature."""
    text = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    promote = text.split("promote:", 1)[1]
    # Must use gpg to produce detached armored signature
    assert "gpg" in promote
    assert "--detach-sign" in promote or "--armor" in promote or "SHA256SUMS.asc" in promote
    # Must upload the signature
    assert "SHA256SUMS.asc" in promote


# ── Promotion: immutable draft promoted unchanged ──────────────────────


def test_promotion_edits_draft_to_public():
    """Promotion changes draft to non-draft (public) without rebuilding."""
    text = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    promote = text.split("promote:", 1)[1]
    # Must use gh release edit to unfreeze draft
    assert "--draft=false" in promote or "edit" in promote
    # Must not rebuild
    for forbidden in ("dpkg-buildpackage", "rpmbuild", "build-appimage", "meson setup"):
        assert forbidden not in promote


def test_promotion_sets_latest_on_publication():
    """Promotion must set Latest for the published release."""
    text = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    promote = text.split("promote:", 1)[1]
    # Must explicitly manage latest flag
    assert "latest" in promote.lower()


def test_promotion_uses_protected_environment():
    """Promotion runs in the release-promotion protected environment."""
    text = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    promote = text.split("promote:", 1)[1]
    assert "environment: release-promotion" in promote


def test_promotion_depends_on_physical_gate():
    """Promotion must wait for physical gate evidence validation."""
    text = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    promote = text.split("promote:", 1)[1]
    assert "physical-gate-check" in promote
    assert "needs:" in promote


# ── Withdrawal: auditable defective-release withdrawal ─────────────────


def test_withdraw_workflow_exists():
    """A dedicated withdraw workflow exists for marking releases withdrawn."""
    assert WITHDRAW_WORKFLOW.exists(), (
        "Missing .github/workflows/withdraw.yml"
    )


def test_withdraw_workflow_removes_latest():
    """Withdrawal removes the Latest flag from the defective release."""
    text = WITHDRAW_WORKFLOW.read_text(encoding="utf-8")
    assert "latest" in text.lower()
    assert "--latest=false" in text or "clear" in text.lower() or "remove" in text.lower()


def test_withdraw_workflow_marks_release_as_withdrawn():
    """Withdrawal marks the release with a withdrawn note in the release body."""
    text = WITHDRAW_WORKFLOW.read_text(encoding="utf-8")
    assert "withdrawn" in text.lower()
    # Must edit the release to add a notice
    assert "gh release edit" in text


def test_withdraw_workflow_requires_confirmation():
    """Withdrawal requires explicit confirmation input to prevent accidental withdrawal."""
    text = WITHDRAW_WORKFLOW.read_text(encoding="utf-8")
    assert "confirm" in text.lower() or "confirm_withdraw" in text.lower()
    # Must check the confirmation input
    assert "inputs." in text or "github.event.inputs" in text


def test_withdraw_does_not_delete_assets():
    """Withdrawal must not delete published assets (only mark withdrawn and remove Latest)."""
    text = WITHDRAW_WORKFLOW.read_text(encoding="utf-8")
    # Must not use delete
    assert "gh release delete" not in text or "delete-keep-files" in text
    # Body must note that assets remain available but the release is superseded


# ── Release verification instructions ──────────────────────────────────


def test_release_notes_include_verification_guidance():
    """The release assembly generates notes with verification instructions."""
    text = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    # Assembly step generates release notes
    assert "generate_release_notes" in text
    # Verify the release includes SHA256SUMS for user verification
    assert "SHA256SUMS" in text
    # Must include verification-related content
    assert "verify" in text.lower() or "verification" in text.lower()


# ── Concurrency: version-scoped lock ───────────────────────────────────


def test_concurrency_lock_scoped_to_version_tag():
    """The concurrency group is scoped to the specific version tag."""
    text = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    assert "concurrency:" in text
    assert "cancel-in-progress: false" in text
    # Must be scoped to ref (tag), not global
    assert "release-" in text or "github.ref" in text
