# MSI BatteryGuard

A GTK4 + libadwaita desktop app for controlling the battery charge threshold on
**MSI Thin A15 B7UCX** (and other MSI laptops supported by `msi-ec`).

## What it does

Sets the maximum charge level your battery will reach. Keeping it at 60–80%
significantly extends long-term battery lifespan. The setting is written
directly to the **EC microcontroller** via the `msi-ec` kernel module and
**persists across reboots** — the same idea as MSI Center on Windows.

## Install (.deb)

Download the `.deb` from the latest CI artifacts or release, then:

```bash
sudo apt install ./msi-batteryguard_1.0.0-1_all.deb
```

The package installs the app, desktop entry, icons, AppStream metainfo, and
udev rule (passwordless threshold writes for the `plugdev` group).

You still need the `msi-ec` kernel module — see **INSTALL.md** (DKMS setup,
`.deb` details, and developer Meson builds).

## How it works

```
Slider → Apply → /sys/class/power_supply/BAT*/charge_control_end_threshold
                              ↓
                   msi-ec kernel module → EC microcontroller
```

## Usage

| Control | Action |
|---|---|
| Slider | Select your desired charge limit |
| **Apply Threshold** | Write the selected value to the EC |
| **Restore to 100%** | Remove the limit (full charging) |

## Recommended thresholds

| Use case | Threshold |
|---|---|
| Daily desktop use (plugged in often) | **60–70%** |
| Mixed use | **80%** |
| Travel / away from power | **100%** |

## Requirements

- Linux kernel module: `msi-ec` (DKMS recommended — see INSTALL.md)
- GTK4 ≥ 4.14, libadwaita ≥ 1.5 (pulled in by the `.deb`)
- Membership in the `plugdev` group for passwordless threshold writes
