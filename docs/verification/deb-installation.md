
# Verification Procedure: DEB on Ubuntu 24.04 and Debian 13

## Prerequisites
- Clean Ubuntu 24.04 or Debian 13 system
- Network access for package dependencies
- SHA-256 of the exact DEB candidate: `threshold_2.0.0-1_amd64.deb`

## Verification Steps

### 1. Candidate Integrity
```bash
# Verify the exact candidate SHA-256
sha256sum threshold_2.0.0-1_amd64.deb
# Expected: <exact-sha-256-from-release-manifest>
```

### 2. Installation
```bash
# Install on clean system
sudo apt update
sudo apt install ./threshold_2.0.0-1_amd64.deb

# Verify installation success
dpkg -l threshold | grep ^ii
```

### 3. File Verification
```bash
# Verify installed files
dpkg -L threshold | head -20

# Verify desktop entry
desktop-file-validate /usr/share/applications/com.bongbetic.threshold.desktop

# Verify icon installation
ls -la /usr/share/icons/hicolor/scalable/apps/com.bongbetic.threshold.svg
```

### 4. EC Lifecycle Verification
```bash
# Check EC lifecycle script
ls -la /usr/share/com.bongbetic.threshold/threshold-ec-lifecycle

# Check sysusers configuration
getent group threshold

# Check udev rules
grep threshold /usr/lib/udev/rules.d/99-msi-battery.rules
```

### 5. Application Startup
```bash
# Launch application
threshold &

# Verify window appears (check with xdotool or wmctrl)
xdotool search --name "Threshold"

# Kill application
kill %1
```

### 6. Removal Verification
```bash
# Remove package
sudo apt remove threshold

# Verify clean removal
dpkg -l threshold | grep ^ii || echo "Package removed successfully"

# Verify EC assets removed (if applicable)
ls /usr/share/com.bongbetic.threshold/ 2>/dev/null || echo "EC assets cleaned"
```

### 7. Evidence Recording
```bash
# Record all evidence with SHA-256 binding
echo "Candidate: threshold_2.0.0-1_amd64.deb" > evidence.txt
echo "SHA-256: <exact-sha-256>" >> evidence.txt
echo "Distribution: Ubuntu 24.04/Debian 13" >> evidence.txt
echo "Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> evidence.txt
echo "Kernel: $(uname -r)" >> evidence.txt
echo "Desktop: $(echo $XDG_CURRENT_DESKTOP)" >> evidence.txt
```

## Privacy Sanitization
- Remove usernames, home paths, serial numbers, UUIDs
- Remove private keys, enrollment passwords
- Remove unrelated logs
- Keep only Threshold-specific evidence
