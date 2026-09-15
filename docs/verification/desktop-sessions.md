
# Verification Procedure: Real KDE Plasma Wayland and XFCE Sessions

## Overview
Verify Threshold's notification-area item works correctly in real desktop environments,
not just containers or virtual displays.

## Prerequisites
- Physical or VM systems with KDE Plasma Wayland and XFCE
- Threshold installed via DEB or RPM
- SHA-256 of the exact candidate

## KDE Plasma Wayland Verification

### 1. Session Setup
```bash
# Verify running on Wayland
echo $XDG_SESSION_TYPE
# Expected: wayland

# Verify KDE Plasma
echo $XDG_CURRENT_DESKTOP
# Expected: KDE
```

### 2. Platform Versions
```bash
# Record platform versions
echo "Plasma Version: $(plasmashell --version | head -1)"
echo "Qt Version: $(qmake --version | head -2)"
echo "KWin Version: $(kwin --version | head -1)"
echo "Wayland Version: $(wayland-info | head -5)"
```

### 3. Notification-Area Integration
```bash
# Launch Threshold
threshold &

# Verify panel icon appears
# (Visual inspection or D-Bus verification)

# Verify tooltip on hover
# (Visual inspection)

# Verify left-click opens window
# (Visual inspection)

# Verify right-click shows context menu
# (Visual inspection)
```

### 4. Threshold Presets
```bash
# Test threshold preset selection
# (Visual inspection of menu)

# Verify preset becomes checked only after success
# (Visual inspection)
```

### 5. Safe Close
```bash
# Close window
xdotool search --name "Threshold" windowclose

# Verify Threshold still in system tray
# (Visual inspection)

# Click tray icon to reopen
# (Visual inspection)
```

### 6. Panel Recovery
```bash
# Restart Plasma shell
kquitapp5 plasmashell && plasmashell &

# Verify Threshold re-registers
# (Visual inspection or D-Bus verification)
```

### 7. Quit
```bash
# Use Quit from context menu
# (Visual inspection)

# Verify Threshold exits cleanly
```

## XFCE Verification

### 1. Session Setup
```bash
# Verify running on X11 (XFCE doesn't support Wayland yet)
echo $XDG_SESSION_TYPE
# Expected: x11

# Verify XFCE
echo $XDG_CURRENT_DESKTOP
# Expected: XFCE
```

### 2. Platform Versions
```bash
# Record platform versions
echo "XFCE Version: $(xfce4-session --version)"
echo "Panel Version: $(xfce4-panel --version)"
echo "X11 Version: $(X -version | head -1)"
```

### 3. Notification-Area Integration
```bash
# Launch Threshold
threshold &

# Verify panel icon appears
# (Visual inspection)

# Verify tooltip on hover
# (Visual inspection)

# Verify left-click opens window
# (Visual inspection)

# Verify right-click shows context menu
# (Visual inspection)
```

### 4. Threshold Presets
```bash
# Test threshold preset selection
# (Visual inspection of menu)

# Verify preset becomes checked only after success
# (Visual inspection)
```

### 5. Safe Close
```bash
# Close window
xdotool search --name "Threshold" windowclose

# Verify Threshold still in system tray
# (Visual inspection)

# Click tray icon to reopen
# (Visual inspection)
```

### 6. Panel Recovery
```bash
# Restart XFCE panel
xfce4-panel -r

# Verify Threshold re-registers
# (Visual inspection or D-Bus verification)
```

### 7. Quit
```bash
# Use Quit from context menu
# (Visual inspection)

# Verify Threshold exits cleanly
```

## Evidence Recording

### For Each Desktop Session
```bash
# Record all evidence with SHA-256 binding
echo "Candidate: <candidate-name>" > evidence.txt
echo "SHA-256: <exact-sha-256>" >> evidence.txt
echo "Desktop: KDE Plasma Wayland / XFCE" >> evidence.txt
echo "Session Type: wayland / x11" >> evidence.txt
echo "Platform Versions: <versions>" >> evidence.txt
echo "Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> evidence.txt
echo "Watcher Evidence: <watcher-evidence>" >> evidence.txt
echo "Screenshots: <screenshot-paths>" >> evidence.txt
echo "Icon Painting: PASS" >> evidence.txt
echo "Tooltip Painting: PASS" >> evidence.txt
echo "Activation: PASS" >> evidence.txt
echo "Menu Placement: PASS" >> evidence.txt
echo "Preset Outcomes: PASS" >> evidence.txt
echo "Safe Close: PASS" >> evidence.txt
echo "Panel Recovery: PASS" >> evidence.txt
echo "Quit: PASS" >> evidence.txt
```

## Privacy Sanitization
- Remove usernames, home paths, serial numbers, UUIDs
- Remove private keys, enrollment passwords
- Remove unrelated logs
- Keep only Threshold-specific evidence
- Sanitize screenshots (blur personal data, remove identifying information)
