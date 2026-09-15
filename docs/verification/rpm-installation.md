
# Verification Procedure: Unified RPM on Fedora 43/44 and openSUSE Tumbleweed

## Prerequisites
- Clean Fedora 43/44 or openSUSE Tumbleweed system
- Network access for package dependencies
- SHA-256 of the exact RPM candidate: `threshold-2.0.0-1.noarch.rpm`

## Verification Steps

### 1. Candidate Integrity
```bash
# Verify the exact candidate SHA-256
sha256sum threshold-2.0.0-1.noarch.rpm
# Expected: <exact-sha-256-from-release-manifest>
```

### 2. Installation (Fedora - dnf)
```bash
# Install on clean system
sudo dnf install ./threshold-2.0.0-1.noarch.rpm

# Verify installation success
rpm -q threshold
```

### 3. Installation (openSUSE - zypper)
```bash
# Install on clean system
sudo zypper install ./threshold-2.0.0-1.noarch.rpm

# Verify installation success
rpm -q threshold
```

### 4. File Verification
```bash
# Verify installed files
rpm -ql threshold | head -20

# Verify desktop entry
desktop-file-validate /usr/share/applications/com.bongbetic.threshold.desktop

# Verify icon installation
ls -la /usr/share/icons/hicolor/scalable/apps/com.bongbetic.threshold.svg
```

### 5. EC Lifecycle Verification
```bash
# Check EC lifecycle script
ls -la /usr/share/com.bongbetic.threshold/threshold-ec-lifecycle

# Check sysusers configuration
getent group threshold

# Check udev rules
grep threshold /usr/lib/udev/rules.d/99-msi-battery.rules
```

### 6. Application Startup
```bash
# Launch application
threshold &

# Verify window appears
xdotool search --name "Threshold"

# Kill application
kill %1
```

### 7. Removal Verification
```bash
# Remove package
sudo dnf remove threshold  # or sudo zypper remove threshold

# Verify clean removal
rpm -q threshold || echo "Package removed successfully"

# Verify EC assets removed (if applicable)
ls /usr/share/com.bongbetic.threshold/ 2>/dev/null || echo "EC assets cleaned"
```

### 8. Evidence Recording
```bash
# Record all evidence with SHA-256 binding
echo "Candidate: threshold-2.0.0-1.noarch.rpm" > evidence.txt
echo "SHA-256: <exact-sha-256>" >> evidence.txt
echo "Distribution: Fedora 43/44 or openSUSE Tumbleweed" >> evidence.txt
echo "Package Manager: dnf/zypper" >> evidence.txt
echo "Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> evidence.txt
echo "Kernel: $(uname -r)" >> evidence.txt
echo "Desktop: $(echo $XDG_CURRENT_DESKTOP)" >> evidence.txt
```

## Privacy Sanitization
- Remove usernames, home paths, serial numbers, UUIDs
- Remove private keys, enrollment passwords
- Remove unrelated logs
- Keep only Threshold-specific evidence
