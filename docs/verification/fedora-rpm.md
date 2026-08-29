# Fedora RPM verification checklist

Reusable procedure for verifying a Fedora RPM release. The bar was decided
on the map's checklist ticket; the release cut itself runs this and records
the evidence.

**Bar for "verified" (amended at the v1.4.2 cut, see #46): full coverage of
checks A–E on Fedora 44 bare metal, plus the CI smoke gate on Fedora 43 +
44 containers. A Fedora 43 VM run is optional, not required: the RPM is
noarch, so the fc43/fc44 packages carry an identical payload and the CI
smoke job already exercises install/lifecycle on F43. The interactive
checks (non-sudo group write, pkexec fallback, C) run on the F44 metal
environment.**

## Checks

### A — Package install

- `sudo dnf install ./threshold-<version>-1.fcXX.noarch.rpm` succeeds on a
  clean system (the `threshold-msi-ec-dkms` subpackage installs
  alongside).
- Files present under `/usr/share/com.bongbetic.threshold/`.
- `desktop-file-validate` passes on the installed desktop entry.

### B — Permissions

- sysusers group exists: `getent group threshold`.
- udev rule rewritten `plugdev` → `threshold` and applied:
  `grep threshold /usr/lib/udev/rules.d/99-msi-battery.rules`; the
  package `%post` already reloads rules — re-run
  `sudo udevadm control --reload-rules && sudo udevadm trigger` if in
  doubt.
- Threshold write works **without sudo** as a group member (after
  re-login).
- **pkexec fallback** works as a non-member.

### C — App

- Window launches (GTK4/libadwaita): run `threshold`.
- Tray icon appears (StatusNotifierItem). GNOME VMs need an AppIndicator
  extension for this check.
- Notification fires (arm an alarm above the current charge and let it
  trigger).

### D — Kernel (hardware-bound; needs the MSI EC)

- DKMS builds against the running kernel: `dkms status` shows
  `msi-ec/0.13.112` installed.
- Module loads (signed on Secure Boot systems): `sudo modprobe msi-ec`,
  `modinfo msi-ec | grep filename`.
- Attribute exists:
  `ls /sys/class/power_supply/BAT1/charge_control_end_threshold`.
- Write round-trip: `echo 80 | sudo tee .../charge_control_end_threshold`
  → readback 80.

### E — Lifecycle

- `sudo dnf remove threshold threshold-msi-ec-dkms` removes the files and
  the DKMS module cleanly (`dkms status` no longer lists msi-ec).
- Reinstall works.

## Environments (split)

| Environment | Checks | Notes |
|---|---|---|
| CI smoke job (`release.yml`, Fedora 43 + 44 containers) | most of A, parts of B/E | install, assert group/udev/files/`SHA256SUMS`, remove clean; runs on every release |
| Fedora 43 VM | A, B, C, E | Optional — not required by the bar. D skipped (hardware-bound). GNOME needs the AppIndicator extension for the tray check. |
| Fedora 44 bare metal (MSI Thin A15, Xfce, Secure Boot **on**) | A–E full | Includes the interactive checks: non-sudo group write after re-login, pkexec fallback, C (window/tray/notification). D needs one-time DKMS MOK signing setup. MOK enrollment keeps Secure Boot on — do not verify with SB off. |

## Evidence

Record run results in the "Cut the release and run verification" ticket
resolution and in the GitHub Release notes. A release page counts as
verified once the CI smoke gate is green and the Fedora 44 bare-metal
results (A–E, including the interactive checks) are recorded against it.