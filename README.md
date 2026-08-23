<p align="center">
  <img src="docs/brand/wordmark-light@2x.png" width="400" alt="Threshold by Bongbetic">
</p>

<p align="center">
  <strong>Battery charge threshold controller for MSI laptops on Linux</strong>
</p>

<p align="center">
  <a href="https://github.com/Bongbetic/Threshold/releases/latest">
    <img src="https://img.shields.io/github/v/release/Bongbetic/Threshold?label=latest&color=ff6b35" alt="Latest release">
  </a>
  <img src="https://img.shields.io/github/actions/workflow/status/Bongbetic/Threshold/ci.yml?branch=main&label=CI" alt="CI status">
  <img src="https://img.shields.io/badge/platform-amd64-blue" alt="Platform">
</p>

---

## What it does

Threshold sets the maximum charge level your battery will reach. Keeping it at
60–80% significantly extends long-term battery lifespan. The setting is written
directly to the **EC microcontroller** via the `msi-ec` kernel module and
**persists across reboots** — the same idea as MSI Center on Windows.

When no EC/sysfs charge control is available on the device, Threshold falls
back to a **notification alarm** — it monitors battery percentage and notifies
you once the charge reaches your set threshold.

## Control modes

Threshold automatically detects the best control mode at startup:

| Mode | Condition | Behaviour |
|---|---|---|
| **EC control** — msi-ec | msi-ec module loaded + threshold attr present | Writes directly to EC firmware, persists across reboots |
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

## Install

Download the latest `.deb` from
**[Releases](https://github.com/Bongbetic/Threshold/releases/latest)**
and install:

```bash
sudo apt install ./threshold_1.4.0-1_amd64.deb
```

The package includes:
- The Threshold GTK4 app
- Desktop entry and icons
- A udev rule for passwordless threshold writes (`plugdev` group)
- The `msi-ec` DKMS source tree (built automatically on install)

Add your user to the `plugdev` group (log out and back in):

```bash
sudo usermod -aG plugdev $USER
```

Launch from the app menu or run `threshold`.

> **Supported:** Ubuntu 24.04 LTS, 26.04 LTS, Debian Trixie — `amd64` only.

## Usage

| Control | Action |
|---|---|
| Slider | Select your desired charge limit |
| **Apply Threshold** | Write the value to EC/sysfs, or arm the notification alarm |
| **Restore to 100%** | Remove the limit / disarm the alarm |

### Recommended thresholds

| Use case | Threshold |
|---|---|
| Daily desktop use (plugged in often) | **60–70%** |
| Mixed use | **80%** |
| Travel / away from power | **100%** |

## System tray

Threshold sits in the system tray when running. The tray menu provides:

- **Current status** — threshold percentage and EC mode
- **Save** — persist current threshold to preferences
- **Restore** — reload saved threshold
- **Quit** — close the app

Settings are also saved automatically when you click **Apply Threshold**.

## Building from source

See **[INSTALL.md](INSTALL.md)** for the Meson build setup and local `.deb`
packaging.

---

<p align="center">
  <img src="docs/brand/icon-light-192.png" width="48" alt="Bongbetic">
  <br>
  <sub>Bongbetic — making Linux laptop battery management simple</sub>
</p>
