# Threshold

A GTK4 + libadwaita desktop app for controlling the battery charge threshold on
**MSI Thin A15 B7UCX** (and other MSI laptops supported by `msi-ec`).

## What it does

Sets the maximum charge level your battery will reach. Keeping it at 60–80%
significantly extends long-term battery lifespan. The setting is written
directly to the **EC microcontroller** via the `msi-ec` kernel module and
**persists across reboots** — the same idea as MSI Center on Windows.

When no EC or sysfs charge control is available on the device, Threshold falls
back to a **notification alarm** — it monitors battery percentage and notifies
you once the charge reaches your set threshold.

## Install on Ubuntu (24.04 LTS and newer)

Grab the latest release from the
**[Releases](https://github.com/Bongbetic/MSI-batteryguard-for-Thin-A15-B7UCX/releases)**
page and download the `.deb` file:

- `threshold_1.3.0-1_amd64.deb` — app + msi-ec DKMS source (single package)

Then install with apt:

```bash
sudo apt install ./threshold_1.3.0-1_amd64.deb
```

The package installs the app, desktop entry, icons, a udev rule that lets the
`plugdev` group write the charge threshold without a password, and the `msi-ec`
DKMS source tree. On install, DKMS builds the kernel module for the running
kernel automatically.

Make sure your user is in the `plugdev` group (log out and back in after
adding):

```bash
sudo usermod -aG plugdev $USER
```

Launch from the app menu (**Threshold**) or run `threshold`.

> **Ubuntu versions:** builds are tested on 24.04 LTS and 26.04 LTS.
> The package is built for `amd64`.

## Control modes

Threshold automatically detects the best control mode at startup:

| Mode | Condition | Behaviour |
|---|---|---|
| **EC control — msi-ec** | msi-ec module loaded + threshold attr present | Writes directly to EC firmware, persists across reboots |
| **Vendor sysfs control** | Threshold attr present from another driver (thinkpad-acpi, asus-wmi, …) | Writes via standard sysfs interface |
| **Notification only** | No threshold attr available | Monitors battery; notifies you when charge reaches threshold |

The current mode is shown in the UI under the "Active Threshold" card.

## How it works

```
Slider → Apply → /sys/class/power_supply/BAT*/charge_control_end_threshold
                              ↓
                   msi-ec kernel module → EC microcontroller
         — or —
         (Notification mode) → monitor capacity → libnotify alert at threshold
```

## Usage

| Control | Action |
|---|---|
| Slider | Select your desired charge limit |
| **Apply Threshold** | Write the value to EC/sysfs, or arm the notification alarm |
| **Restore to 100%** | Remove the limit / disarm the alarm |

## Recommended thresholds

| Use case | Threshold |
|---|---|
| Daily desktop use (plugged in often) | **60–70%** |
| Mixed use | **80%** |
| Travel / away from power | **100%** |

## Requirements

- Ubuntu 24.04 LTS or newer, `amd64`
- GTK4 ≥ 4.14, libadwaita ≥ 1.5 (pulled in by the package)
- Membership in the `plugdev` group for passwordless threshold writes (EC/sysfs modes)
- Close-to-tray or autostart recommended for notification mode background delivery

## Building from source

See **INSTALL.md** for the developer Meson build and for building the `.deb`
locally.
