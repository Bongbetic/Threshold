# Physical Release Gate: MSI Thin A15 B7UCX

## Overview

The MSI Thin A15 B7UCX is the mandatory physical validation system for
Threshold v2.0.0. This gate ensures that live EC control, reboot
reconciliation, Secure Boot/MOK behavior, kernel recovery, notification-area
integration, and removal are proven on real hardware before any release
candidate is promoted to public.

**No automated simulation can satisfy this gate.** Fake-system tests, container
probes, and virtual-display sessions cover different verification dimensions
but cannot replace physical hardware evidence.

## Prerequisites

- MSI Thin A15 B7UCX with accessible battery sysfs interface
- Exact release candidate SHA-256 (from the immutable build artifacts)
- Both KDE Plasma Wayland and XFCE sessions available
- Secure Boot state documented (enabled or disabled)
- Root access for EC lifecycle operations

## Evidence Requirements

Every result in this protocol must:

1. **Name the exact candidate SHA-256** — evidence is bound to immutable
   artifacts; transferring results between builds is not permitted.
2. **Use ISO 8601 UTC timestamps** — format: `YYYY-MM-DDTHH:MM:SSZ`.
3. **Contain only sanitized content** — no usernames, home paths, hardware
   serials, UUIDs, private keys, or unrelated logs.
4. **Be no older than seven days** at promotion time — stale evidence must
   be refreshed against the unchanged candidates.

Evidence older than 7 days is rejected by the release workflow. If the
candidates have not changed, the physical gate may be refreshed by repeating
the relevant sections against the same SHA-256.

## Protocol Sections

### 1. Installation

Install the exact release candidate on the MSI Thin A15 B7UCX:

```bash
# Record candidate identity
echo "Candidate: threshold_<version>_amd64.deb"
echo "SHA-256: <exact-sha-256>"

# Install
sudo dpkg -i threshold_<version>_amd64.deb

# Verify installation layout
test -x /usr/bin/threshold
test -x /usr/sbin/threshold-ec-lifecycle
test -f /usr/lib/systemd/system/threshold-boot-reconcile.service
test -d /usr/src/msi-ec-0.13.112
```

Record: installation success, package ownership, file layout.

### 2. Live msi-ec Threshold Write and Readback

Verify that the msi-ec module exposes a writable threshold interface:

```bash
# Confirm EC setup is available
/usr/sbin/threshold-ec-lifecycle diagnostics

# Write a test threshold
echo 75 | sudo tee /sys/class/power_supply/BAT0/charge_control_end_threshold

# Read back and verify
cat /sys/class/power_supply/BAT0/charge_control_end_threshold
# Expected: 75

# Restore preferred threshold
echo 80 | sudo tee /sys/class/power_supply/BAT0/charge_control_end_threshold
```

Record: write success, readback value, sysfs path, threshold value.

### 3. Ordinary Reboot Reconciliation

Reboot the system and verify that the charge threshold is reconciled:

```bash
# Before reboot: record the desired threshold
echo "Desired threshold: 80"

# Reboot
sudo reboot

# After reboot: verify reconciliation
cat /sys/class/power_supply/BAT0/charge_control_end_threshold
# Expected: 80 (matches desired)

# Check lifecycle state
/usr/sbin/threshold-ec-lifecycle diagnostics
# setup_state should be "available"
```

Record: boot ID, reconciliation outcome, active threshold, setup state.

### 4. Persisted Machine Policy

Verify that the charge threshold persists across sessions and is treated
as machine-wide policy:

```bash
# Check persisted policy
cat /var/lib/threshold/ec/charge-threshold
# Expected: 80

# Verify different user sessions see the same policy
# (switch user or re-login)
cat /var/lib/threshold/ec/charge-threshold
# Expected: 80 (unchanged)
```

Record: persisted threshold value, policy consistency across sessions.

### 5. Secure Boot / MOK Behavior

If Secure Boot is enabled on the MSI Thin A15 B7UCX:

```bash
# Check Secure Boot state
mokutil --sb-state
# Expected: SecureBoot enabled

# Verify module loading with Secure Boot
lsmod | grep msi_ec
# Expected: msi_ec module loaded

# Test pending-reboot consumption (if MOK enrollment was required)
# After a reboot following MOK enrollment:
/usr/sbin/threshold-ec-lifecycle diagnostics
# pending-reboot should be consumed
# setup_state should be "available"
```

If Secure Boot is disabled, record the state and note that MOK-related
checks are not applicable.

Record: Secure Boot state, module load status, MOK enrollment outcome,
pending-reboot consumption.

### 6. Failed New-Kernel Build

Simulate a failed new-kernel build and verify recovery:

```bash
# Record current known-good kernel
/usr/sbin/threshold-ec-lifecycle diagnostics
# Note the kernel version with known-good status

# Trigger a build for a non-existent kernel (simulates failure)
# The lifecycle must preserve the older known-good kernel
sudo /usr/sbin/threshold-ec-lifecycle install-or-upgrade

# Verify older known-good kernel is preserved
/usr/sbin/threshold-ec-lifecycle diagnostics
# The previous kernel must still show known-good
```

Record: pre-failure known-good kernel, build failure outcome,
preservation of older kernel records.

### 7. Known-Good Kernel Boot

Verify that a kernel is only marked known-good after real boot with
live capability verification:

```bash
# Boot into the target kernel
# After boot, verify live EC capability:
cat /sys/class/power_supply/BAT0/charge_control_end_threshold
# Must return a valid threshold value

# Verify reconciliation ran
/usr/sbin/threshold-ec-lifecycle diagnostics
# setup_state: available
# The kernel should now be marked known-good
```

Record: kernel version, live capability verification, reconciliation
outcome, known-good status.

### 8. Named-Kernel Repair

Repair EC setup targeting a specific failing kernel:

```bash
# Explicit repair for the named kernel
sudo /usr/sbin/threshold-ec-lifecycle repair

# Verify repair outcome
/usr/sbin/threshold-ec-lifecycle diagnostics
# setup_state: available
# maintenance: ok

# Verify live control is not disturbed
cat /sys/class/power_supply/BAT0/charge_control_end_threshold
# Must return the current threshold
```

Record: repair verb, target kernel, repair outcome, live control status.

### 9. Subsequent Verification

After repair, verify the complete EC control chain:

```bash
# Write a new threshold
echo 65 | sudo tee /sys/class/power_supply/BAT0/charge_control_end_threshold

# Read back
cat /sys/class/power_supply/BAT0/charge_control_end_threshold
# Expected: 65

# Verify state is still available
/usr/sbin/threshold-ec-lifecycle diagnostics
# setup_state: available

# Restore preferred threshold
echo 80 | sudo tee /sys/class/power_supply/BAT0/charge_control_end_threshold
```

Record: write/readback success, state persistence, threshold restoration.

### 10. Safe Removal

Remove Threshold while preserving the charge threshold and not unloading
a working module:

```bash
# Record current state
echo "Threshold before removal: $(cat /var/lib/threshold/ec/charge-threshold)"
echo "Module before removal: $(lsmod | grep msi_ec)"

# Remove (not purge)
sudo dpkg --remove threshold

# Verify charge threshold persists
cat /var/lib/threshold/ec/charge-threshold
# Expected: same value as before removal

# Verify working module is NOT unloaded
lsmod | grep msi_ec
# Expected: module still loaded (if it was loaded before removal)

# Verify EC state is cleaned up
test ! -f /var/lib/threshold/ec/state
```

Record: removal success, threshold preservation, module status,
state cleanup.

### 11. KDE Plasma Wayland Desktop Checks

In a KDE Plasma Wayland session:

```bash
# Verify session type
echo $XDG_SESSION_TYPE
# Expected: wayland

# Launch Threshold
threshold &

# Record platform versions
echo "Plasma: $(plasmashell --version | head -1)"
echo "Qt: $(qmake --version | head -2)"
```

**Visual verification** (screenshots required):

- [ ] Icon painting in panel (battery state icon visible)
- [ ] Tooltip on hover (shows threshold and status)
- [ ] Left-click activation (opens main window)
- [ ] Right-click context menu (shows presets, Open, Quit)
- [ ] Context menu placement (menu appears near cursor)
- [ ] Preset success (selecting a preset updates threshold)
- [ ] Preset failure (failed preset shows error, preserves previous)
- [ ] Safe close (window hides, icon remains in panel)
- [ ] Panel restart recovery (restart plasmashell, icon reappears)
- [ ] Quit from context menu (Threshold exits cleanly)

Record: screenshots, watcher evidence, all visual checks.

### 12. XFCE Desktop Checks

In an XFCE session:

```bash
# Verify session type
echo $XDG_SESSION_TYPE
# Expected: x11

# Launch Threshold
threshold &

# Record platform versions
echo "XFCE: $(xfce4-session --version)"
echo "Panel: $(xfce4-panel --version)"
```

**Visual verification** (screenshots required):

- [ ] Icon painting in panel (battery state icon visible)
- [ ] Tooltip on hover (shows threshold and status)
- [ ] Left-click activation (opens main window)
- [ ] Right-click context menu (shows presets, Open, Quit)
- [ ] Context menu placement (menu appears near cursor)
- [ ] Preset success (selecting a preset updates threshold)
- [ ] Preset failure (failed preset shows error, preserves previous)
- [ ] Safe close (window hides, icon remains in panel)
- [ ] Panel restart recovery (restart xfce4-panel, icon reappears)
- [ ] Quit from context menu (Threshold exits cleanly)

Record: screenshots, watcher evidence, all visual checks.

## Evidence Recording Template

For each section, record results in a file named:

`physical-gate-<section>-<YYYY-MM-DDTHH:MM:SSZ>.txt`

```
=== Physical Gate: <Section Name> ===
Candidate: <candidate-filename>
SHA-256: <exact-sha-256>
System: MSI Thin A15 B7UCX
Date: <ISO-8601-UTC>
Secure Boot: <enabled|disabled>
Kernel: <kernel-version>

<Section-specific results>

Result: PASS | FAIL
```

## Privacy Sanitization

Before retaining any evidence:

1. Replace `/home/<user>/` for all home directory paths
2. Replace `serial=<redacted>` for hardware serials
3. Replace `UUID=<redacted>` for device UUIDs
4. Remove private keys and enrollment passwords
5. Remove unrelated system logs
6. Sanitize screenshots (blur personal data, remove identifying info)

## Gate Enforcement

The release workflow enforces:

- **Evidence freshness**: All physical gate evidence must be ≤7 days old
  at promotion time. Stale evidence must be refreshed.
- **SHA-256 binding**: Evidence must reference the exact candidate SHA-256.
  Evidence bound to different candidates is rejected.
- **No simulation**: Automated fake-system tests, container probes, and
  virtual-display sessions do not satisfy this gate. Only real hardware
  evidence on the MSI Thin A15 B7UCX is accepted.
- **Sanitization**: Evidence containing privacy-sensitive patterns is
  rejected.
