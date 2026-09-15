
# Verification Procedure: AppImage on All Five Distributions

## Prerequisites
- Clean systems for each distribution: Ubuntu 24.04, Debian 13, Fedora 43, Fedora 44, openSUSE Tumbleweed
- SHA-256 of the exact AppImage candidate: `threshold-2.0.0-x86_64.AppImage`
- FUSE support installed (for AppImage execution)

## Verification Steps

### 1. Candidate Integrity
```bash
# Verify the exact candidate SHA-256
sha256sum threshold-2.0.0-x86_64.AppImage
# Expected: <exact-sha-256-from-release-manifest>
```

### 2. Offline Startup Test
```bash
# Disconnect network (optional but recommended for offline test)
# sudo nmcli radio wifi off

# Make executable
chmod +x threshold-2.0.0-x86_64.AppImage

# Launch application
./threshold-2.0.0-x86_64.AppImage &

# Verify window appears
xdotool search --name "Threshold"

# Kill application
kill %1

# Reconnect network (if disconnected)
# sudo nmcli radio wifi on
```

### 3. Dependency Closure Verification
```bash
# Verify no build-host paths in AppImage
strings threshold-2.0.0-x86_64.AppImage | grep -E '/home/|/tmp/|/build/' | head -5
# Expected: no output or only benign references

# Verify embedded EC bundle
ls -la squashfs-root/usr/share/threshold/trust/ 2>/dev/null || echo "No trust directory"
```

### 4. Relocatability Test
```bash
# Copy to different location
cp threshold-2.0.0-x86_64.AppImage /tmp/test-threshold.AppImage

# Launch from new location
chmod +x /tmp/test-threshold.AppImage
/tmp/test-threshold.AppImage &

# Verify window appears
xdotool search --name "Threshold"

# Kill application
kill %1

# Clean up
rm /tmp/test-threshold.AppImage
```

### 5. Evidence Recording
```bash
# Record all evidence with SHA-256 binding
echo "Candidate: threshold-2.0.0-x86_64.AppImage" > evidence.txt
echo "SHA-256: <exact-sha-256>" >> evidence.txt
echo "Distribution: $(cat /etc/os-release | grep PRETTY_NAME | cut -d= -f2)" >> evidence.txt
echo "Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> evidence.txt
echo "Kernel: $(uname -r)" >> evidence.txt
echo "Desktop: $(echo $XDG_CURRENT_DESKTOP)" >> evidence.txt
echo "FUSE: $(which fusermount)" >> evidence.txt
```

## Privacy Sanitization
- Remove usernames, home paths, serial numbers, UUIDs
- Remove private keys, enrollment passwords
- Remove unrelated logs
- Keep only Threshold-specific evidence
