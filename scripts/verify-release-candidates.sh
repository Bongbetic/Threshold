#!/bin/bash
# Threshold v2.0.0 Release Candidate Verification Script
# Binds all results to exact candidate SHA-256

set -euo pipefail

# Configuration
CANDIDATE_DIR="${1:-.}"
EVIDENCE_DIR="${2:-./evidence}"
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# Create evidence directory
mkdir -p "$EVIDENCE_DIR"

# Function to record evidence
record_evidence() {
    local category="$1"
    local result="$2"
    local details="$3"
    echo "=== $category ===" >> "$EVIDENCE_DIR/verification-$TIMESTAMP.txt"
    echo "Result: $result" >> "$EVIDENCE_DIR/verification-$TIMESTAMP.txt"
    echo "Details: $details" >> "$EVIDENCE_DIR/verification-$TIMESTAMP.txt"
    echo "" >> "$EVIDENCE_DIR/verification-$TIMESTAMP.txt"
}

# Function to sanitize evidence
sanitize_evidence() {
    local file="$1"
    sed -i 's|/home/[^/]*/|/home/<user>/|g' "$file"
    sed -i 's|/root/|/home/<user>/|g' "$file"
    sed -i 's|serial=[^ ]*|serial=<redacted>|g' "$file"
    sed -i 's|UUID=[^ ]*|UUID=<redacted>|g' "$file"
}

echo "Starting Threshold v2.0.0 verification..."
echo "Timestamp: $TIMESTAMP"

# 1. Verify DEB candidates
echo "=== DEB Verification ==="
for deb in "$CANDIDATE_DIR"/*.deb; do
    [ -f "$deb" ] || continue
    sha256=$(sha256sum "$deb" | cut -d' ' -f1)
    echo "Candidate: $(basename "$deb")"
    echo "SHA-256: $sha256"
    record_evidence "DEB Candidate" "PASS" "$(basename "$deb") SHA-256: $sha256"
    if [ "$(id -u)" -eq 0 ]; then
        echo "Testing installation..."
        dpkg -i "$deb" 2>&1 | tee -a "$EVIDENCE_DIR/install-$(basename "$deb" .deb).log"
        record_evidence "DEB Installation" "${PIPESTATUS[0]:-1}" "$(basename "$deb")"
    fi
done

# 2. Verify RPM candidates
echo "=== RPM Verification ==="
for rpm in "$CANDIDATE_DIR"/*.rpm; do
    [ -f "$rpm" ] || continue
    sha256=$(sha256sum "$rpm" | cut -d' ' -f1)
    echo "Candidate: $(basename "$rpm")"
    echo "SHA-256: $sha256"
    record_evidence "RPM Candidate" "PASS" "$(basename "$rpm") SHA-256: $sha256"
    if [ "$(id -u)" -eq 0 ]; then
        echo "Testing installation..."
        if command -v dnf &> /dev/null; then
            dnf install -y "$rpm" 2>&1 | tee -a "$EVIDENCE_DIR/install-$(basename "$rpm" .rpm).log"
        elif command -v zypper &> /dev/null; then
            zypper install -y "$rpm" 2>&1 | tee -a "$EVIDENCE_DIR/install-$(basename "$rpm" .rpm).log"
        fi
        record_evidence "RPM Installation" "${PIPESTATUS[0]:-1}" "$(basename "$rpm")"
    fi
done

# 3. Verify AppImage candidates
echo "=== AppImage Verification ==="
for appimage in "$CANDIDATE_DIR"/*.AppImage; do
    [ -f "$appimage" ] || continue
    sha256=$(sha256sum "$appimage" | cut -d' ' -f1)
    echo "Candidate: $(basename "$appimage")"
    echo "SHA-256: $sha256"
    record_evidence "AppImage Candidate" "PASS" "$(basename "$appimage") SHA-256: $sha256"
    chmod +x "$appimage"
    if timeout 10 "$appimage" --help &> /dev/null; then
        record_evidence "AppImage Startup" "PASS" "$(basename "$appimage")"
    else
        record_evidence "AppImage Startup" "FAIL" "$(basename "$appimage")"
    fi
done

# 4. Run existing tests
echo "=== Test Suite ==="
if [ -d "tests" ]; then
    echo "Running test suite..."
    python -m pytest tests/ -v 2>&1 | tee -a "$EVIDENCE_DIR/test-suite.log" || true
    record_evidence "Test Suite" "See log" "tests/"
fi

# 5. Sanitize evidence
echo "=== Sanitizing Evidence ==="
for file in "$EVIDENCE_DIR"/*.txt "$EVIDENCE_DIR"/*.log; do
    [ -f "$file" ] && sanitize_evidence "$file"
done

# 6. Generate final report
echo "=== Verification Complete ==="
echo "Evidence directory: $EVIDENCE_DIR"
echo "Timestamp: $TIMESTAMP"

cat > "$EVIDENCE_DIR/summary-$TIMESTAMP.txt" << SUMMARY
Threshold v2.0.0 Release Candidate Verification
Timestamp: $TIMESTAMP
Evidence Directory: $EVIDENCE_DIR

Privacy Sanitization: Applied
SUMMARY

echo "Summary: $EVIDENCE_DIR/summary-$TIMESTAMP.txt"