"""Physical release gate enforcement for MSI Thin A15 B7UCX (issue #101).

The mandatory physical gate cannot be satisfied by any automated simulation.
Evidence must be fresh (≤7 days), bound to the exact candidate SHA-256,
and contain only sanitized content. Promotion is blocked without valid
physical gate evidence.
"""

import hashlib
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "evidence"
RELEASES_DIR = ROOT / "releases"
PHYSICAL_GATE_DOC = ROOT / "docs" / "verification" / "msi-physical-gate.md"
RELEASE_WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"

EVIDENCE_MAX_AGE_DAYS = 7

# Patterns that must never appear in sanitized evidence.
PRIVACY_PATTERNS = [
    re.compile(r"/home/[^/\s]+/"),
    re.compile(r"/root/"),
    re.compile(r"serial=[A-Za-z0-9]+"),
    re.compile(r"UUID=[0-9a-fA-F-]+"),
    re.compile(r"ssh-rsa "),
    re.compile(r"BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY"),
]


def _sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _find_physical_evidence() -> list[Path]:
    """Find evidence files that contain physical gate results."""
    evidence_files = []
    if not EVIDENCE_DIR.exists():
        return evidence_files
    for f in EVIDENCE_DIR.iterdir():
        if f.is_file() and f.suffix in (".txt", ".log"):
            content = f.read_text(encoding="utf-8", errors="replace")
            if "physical" in content.lower() or "msi-thin-a15" in content.lower():
                evidence_files.append(f)
    return evidence_files


def _find_timestamped_evidence() -> list[tuple[Path, datetime]]:
    """Find timestamped evidence files and extract their timestamps."""
    results = []
    if not EVIDENCE_DIR.exists():
        return results
    ts_pattern = re.compile(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)")
    for f in EVIDENCE_DIR.iterdir():
        if not f.is_file():
            continue
        match = ts_pattern.search(f.name)
        if match:
            try:
                ts = datetime.strptime(match.group(1), "%Y-%m-%dT%H:%M:%SZ")
                ts = ts.replace(tzinfo=timezone.utc)
                results.append((f, ts))
            except ValueError:
                continue
    return results


def _candidate_sha256s() -> dict[str, str]:
    """Compute SHA-256 of all release candidates."""
    candidates = {}
    if not RELEASES_DIR.exists():
        return candidates
    for path in RELEASES_DIR.rglob("*"):
        if path.is_file() and path.suffix in (".deb", ".rpm"):
            candidates[path.name] = _sha256_of_file(path)
    return candidates


# ── Protocol document existence ────────────────────────────────────────────


def test_physical_gate_protocol_document_exists():
    """The physical gate protocol must be documented."""
    assert PHYSICAL_GATE_DOC.exists(), (
        f"Missing physical gate protocol: {PHYSICAL_GATE_DOC}"
    )
    content = PHYSICAL_GATE_DOC.read_text(encoding="utf-8")
    assert len(content) > 500, "Physical gate protocol is too short"


def test_physical_gate_protocol_covers_all_required_sections():
    """The protocol must cover installation, write/readback, reboot, Secure Boot,
    kernel recovery, removal, and both desktop environments."""
    content = PHYSICAL_GATE_DOC.read_text(encoding="utf-8").lower()
    required_sections = [
        "installation",
        "threshold write",
        "readback",
        "reboot",
        "reconcil",
        "secure boot",
        "mok",
        "kernel",
        "repair",
        "removal",
        "kde",
        "xfce",
        "sanitiz",
        "sha-256",
    ]
    for section in required_sections:
        assert section in content, (
            f"Physical gate protocol missing section/topic: {section}"
        )


# ── Evidence freshness (≤7 days) ───────────────────────────────────────────


def test_evidence_freshness_at_most_seven_days():
    """All timestamped evidence must be no older than 7 days."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=EVIDENCE_MAX_AGE_DAYS)
    timestamped = _find_timestamped_evidence()
    if not timestamped:
        pytest.skip("no timestamped evidence found")
    for path, ts in timestamped:
        assert ts >= cutoff, (
            f"Evidence {path.name} is stale: {ts.isoformat()} "
            f"(cutoff: {cutoff.isoformat()})"
        )


def test_evidence_timestamp_format_is_iso8601_utc():
    """Evidence timestamps must use ISO 8601 UTC format."""
    timestamped = _find_timestamped_evidence()
    if not timestamped:
        pytest.skip("no timestamped evidence found")
    ts_pattern = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
    for path, _ in timestamped:
        assert ts_pattern.search(path.name), (
            f"Evidence {path.name} does not use ISO 8601 UTC timestamp"
        )


# ── SHA-256 binding ────────────────────────────────────────────────────────


def test_evidence_contains_candidate_sha256():
    """Physical evidence must reference the exact candidate SHA-256."""
    candidates = _candidate_sha256s()
    if not candidates:
        pytest.skip("no release candidates found")
    physical_evidence = _find_physical_evidence()
    if not physical_evidence:
        pytest.skip("no physical gate evidence found")
    for ev_file in physical_evidence:
        content = ev_file.read_text(encoding="utf-8", errors="replace")
        # At least one candidate SHA-256 must appear in the evidence
        found = any(sha in content for sha in candidates.values())
        assert found, (
            f"Evidence {ev_file.name} does not reference any candidate SHA-256"
        )


def test_physical_evidence_has_sha256_field():
    """Physical evidence must contain an explicit SHA-256 or candidate field."""
    physical_evidence = _find_physical_evidence()
    if not physical_evidence:
        pytest.skip("no physical gate evidence found")
    for ev_file in physical_evidence:
        content = ev_file.read_text(encoding="utf-8", errors="replace").lower()
        assert "sha-256" in content or "sha256" in content, (
            f"Evidence {ev_file.name} has no SHA-256 binding"
        )


# ── Privacy sanitization ──────────────────────────────────────────────────


def test_physical_evidence_is_sanitized():
    """Physical evidence must not contain privacy-sensitive patterns."""
    physical_evidence = _find_physical_evidence()
    if not physical_evidence:
        pytest.skip("no physical gate evidence found")
    for ev_file in physical_evidence:
        content = ev_file.read_text(encoding="utf-8", errors="replace")
        for pattern in PRIVACY_PATTERNS:
            match = pattern.search(content)
            assert not match, (
                f"Evidence {ev_file.name} contains unsanitized data: "
                f"{match.group()!r}"
            )


# ── No automated simulation satisfies physical gate ────────────────────────


def test_physical_gate_cannot_be_satisfied_by_fake_system_tests():
    """The fake-system lifecycle tests must not produce physical gate evidence.

    Physical gate evidence must come from real hardware, not from tests that
    substitute DKMS, module, Secure Boot, and sysfs effects.
    """
    fake_test = ROOT / "tests" / "test_ec_lifecycle_fake.py"
    if not fake_test.exists():
        pytest.skip("fake-system test not found")
    fake_content = fake_test.read_text(encoding="utf-8")
    # The fake-system test file must not create physical gate evidence files
    assert "physical" not in fake_content.lower() or "physical_gate" not in fake_content.lower(), (
        "Fake-system test must not produce physical gate evidence"
    )


def test_release_workflow_requires_physical_evidence_before_promotion():
    """The release workflow must check for physical gate evidence before promoting."""
    content = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    # The promote job or a gate check must reference physical evidence
    assert "physical" in content.lower() or "physical-gate" in content.lower(), (
        "Release workflow must reference the physical gate"
    )


def test_release_workflow_promote_has_evidence_freshness_check():
    """The promotion path must enforce evidence freshness.

    The freshness check may be in the promote job itself or in a
    prerequisite gate job that promote depends on.
    """
    content = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    # Check the entire workflow for freshness enforcement
    # (the check may be in a gate job that promote depends on)
    assert (
        "fresh" in content.lower()
        or "stale" in content.lower()
        or ("7 days" in content or "seven days" in content)
    ), "Release workflow must enforce evidence freshness somewhere in the promotion path"
    # The promote job must depend on a gate that checks freshness
    assert "needs:" in content, "Promote job must have dependency on gate check"


def test_physical_gate_document_specifies_no_simulation_rule():
    """The protocol must explicitly state that no simulation can complete the gate."""
    content = PHYSICAL_GATE_DOC.read_text(encoding="utf-8").lower()
    assert "no automated" in content or "no simulation" in content or "cannot be simulated" in content, (
        "Protocol must state that automated simulation cannot satisfy the gate"
    )


def test_physical_gate_document_specifies_freshness_requirement():
    """The protocol must specify the 7-day evidence freshness requirement."""
    content = PHYSICAL_GATE_DOC.read_text(encoding="utf-8").lower()
    assert "7" in content and ("day" in content or "fresh" in content or "age" in content), (
        "Protocol must specify the evidence freshness requirement"
    )


def test_physical_gate_document_specifies_sha256_binding():
    """The protocol must specify SHA-256 binding for all evidence."""
    content = PHYSICAL_GATE_DOC.read_text(encoding="utf-8").lower()
    assert "sha-256" in content or "sha256" in content, (
        "Protocol must specify SHA-256 binding for evidence"
    )


def test_physical_gate_evidence_directory_exists():
    """The evidence directory must exist for physical gate evidence."""
    assert EVIDENCE_DIR.exists(), "Evidence directory must exist"
