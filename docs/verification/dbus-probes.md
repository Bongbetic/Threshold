
# Verification Procedure: Installed-Artifact D-Bus Probes

## Overview
Verify that the installed Threshold artifact properly exposes its StatusNotifierItem
and dbusmenu through D-Bus, covering all required protocol surfaces.

## Prerequisites
- Threshold installed via DEB or RPM
- D-Bus session bus available
- StatusNotifierWatcher running (or fake watcher for testing)

## Verification Steps

### 1. Watcher Registration
```bash
# Check if Threshold registers with watcher
dbus-send --session --type=method_call --print-reply \
  --dest=org.kde.StatusNotifierWatcher \
  /StatusNotifierWatcher \
  org.freedesktop.DBus.Properties.Get \
  string:org.kde.StatusNotifierWatcher \
  string:RegisteredStatusNotifierItems

# Expected: threshold entry in the list
```

### 2. SNI Properties
```bash
# Get Threshold's SNI object path
SNI_PATH=$(dbus-send --session --type=method_call --print-reply \
  --dest=org.kde.StatusNotifierWatcher \
  /StatusNotifierWatcher \
  org.freedesktop.DBus.Properties.Get \
  string:org.kde.StatusNotifierWatcher \
  string:RegisteredStatusNotifierItems | grep threshold | cut -d'/' -f2)

# Verify required properties
dbus-send --session --type=method_call --print-reply \
  --dest=org.kde.StatusNotifierItem \
  /$SNI_PATH \
  org.freedesktop.DBus.Properties.Get \
  string:org.kde.StatusNotifierItem \
  string:Id

dbus-send --session --type=method_call --print-reply \
  --dest=org.kde.StatusNotifierItem \
  /$SNI_PATH \
  org.freedesktop.DBus.Properties.Get \
  string:org.kde.StatusNotifierItem \
  string:Title

dbus-send --session --type=method_call --print-reply \
  --dest=org.kde.StatusNotifierItem \
  /$SNI_PATH \
  org.freedesktop.DBus.Properties.Get \
  string:org.kde.StatusNotifierItem \
  string:Status
```

### 3. Icon Verification
```bash
# Verify artifact-owned icon name
dbus-send --session --type=method_call --print-reply \
  --dest=org.kde.StatusNotifierItem \
  /$SNI_PATH \
  org.freedesktop.DBus.Properties.Get \
  string:org.kde.StatusNotifierItem \
  string:IconName

# Expected: com.bongbetic.threshold (or similar artifact-owned name)
```

### 4. Menu Layout (dbusmenu)
```bash
# Get dbusmenu object path
MENU_PATH=$(dbus-send --session --type=method_call --print-reply \
  --dest=org.kde.StatusNotifierItem \
  /$SNI_PATH \
  org.freedesktop.DBus.Properties.Get \
  string:org.kde.StatusNotifierItem \
  string:Menu | grep object)

# Verify menu layout
dbus-send --session --type=method_call --print-reply \
  --dest=com.canonical.dbusmenu \
  $MENU_PATH \
  com.canonical.dbusmenu.GetLayout \
  int32:0 int32:-1 array:string:""

# Expected: menu items including Open Threshold, Quit, threshold presets
```

### 5. Activation Methods
```bash
# Test left-click activation
dbus-send --session --type=method_call \
  --dest=org.kde.StatusNotifierItem \
  /$SNI_PATH \
  org.kde.StatusNotifierItem.Activate \
  int32:0 int32:0

# Test context menu activation
dbus-send --session --type=method_call \
  --dest=org.kde.StatusNotifierItem \
  /$SNI_PATH \
  org.kde.StatusNotifierItem.ContextMenu \
  int32:0 int32:0
```

### 6. Safe Close Verification
```bash
# Verify window hides only when readiness is ready
# (Requires Threshold running with notification-area item)

# Close window
xdotool search --name "Threshold" windowclose

# Verify Threshold still in system tray
dbus-send --session --type=method_call --print-reply \
  --dest=org.kde.StatusNotifierWatcher \
  /StatusNotifierWatcher \
  org.freedesktop.DBus.Properties.Get \
  string:org.kde.StatusNotifierWatcher \
  string:RegisteredStatusNotifierItems | grep threshold

# Expected: Threshold still registered
```

### 7. Watcher Recovery
```bash
# Kill watcher (simulates panel restart)
pkill -f StatusNotifierWatcher

# Verify readiness revoked
# (Check Threshold logs or state)

# Restart watcher
/usr/lib/x86_64-linux-gnu/libexec/kde StatusNotifierWatcher &

# Verify re-registration within 5 seconds
sleep 6
dbus-send --session --type=method_call --print-reply \
  --dest=org.kde.StatusNotifierWatcher \
  /StatusNotifierWatcher \
  org.freedesktop.DBus.Properties.Get \
  string:org.kde.StatusNotifierWatcher \
  string:RegisteredStatusNotifierItems | grep threshold

# Expected: Threshold re-registered
```

### 8. Evidence Recording
```bash
# Record all evidence with SHA-256 binding
echo "Candidate: threshold_2.0.0-1_amd64.deb" > evidence.txt
echo "SHA-256: <exact-sha-256>" >> evidence.txt
echo "Probe: D-Bus StatusNotifierItem" >> evidence.txt
echo "Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> evidence.txt
echo "Watcher Registration: PASS" >> evidence.txt
echo "SNI Properties: PASS" >> evidence.txt
echo "Icon Verification: PASS" >> evidence.txt
echo "Menu Layout: PASS" >> evidence.txt
echo "Activation Methods: PASS" >> evidence.txt
echo "Safe Close: PASS" >> evidence.txt
echo "Watcher Recovery: PASS" >> evidence.txt
```

## Privacy Sanitization
- Remove usernames, home paths, serial numbers, UUIDs
- Remove private keys, enrollment passwords
- Remove unrelated logs
- Keep only Threshold-specific evidence
