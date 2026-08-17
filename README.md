# Threshold

A GTK4 + libadwaita desktop app for controlling the battery charge threshold on
**MSI Thin A15 B7UCX** (and other MSI laptops supported by `msi-ec`).

## What it does

Sets the maximum charge level your battery will reach. Keeping it at 60–80%
significantly extends long-term battery lifespan. The setting is written
directly to the **EC microcontroller** via the `msi-ec` kernel module and
**persists across reboots** — the same idea as MSI Center on Windows.

## Install on Ubuntu (24.04 LTS and newer)

Grab the latest release from the
**[Releases](https://github.com/Bongbetic/MSI-batteryguard-for-Thin-A15-B7UCX/releases)**
page and download **both** `.deb` files:

- `threshold_1.2.0-1_all.deb` — the app
- `msi-ec-dkms_0.13-1_amd64.deb` — the kernel module (built via DKMS)

Then install them with apt:

```bash
sudo apt install ./msi-ec-dkms_0.13-1_amd64.deb
sudo apt install ./threshold_1.2.0-1_all.deb
```

The `msi-ec-dkms` package builds and loads the `msi-ec` kernel module for the
running kernel automatically, and the app package installs the desktop entry,
icons, and a udev rule that lets the `plugdev` group write the charge threshold
without a password.

Make sure your user is in the `plugdev` group (log out and back in after
adding):

```bash
sudo usermod -aG plugdev $USER
```

Launch from the app menu (**Threshold**) or run `threshold`.

> **Ubuntu versions:** builds are tested on 24.04 LTS and 26.04 LTS. The app
> package is architecture-independent (`all`); the kernel module package is
> built for `amd64`.

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

- Ubuntu 24.04 LTS or newer, `amd64`
- The `msi-ec` kernel module — installed by the `msi-ec-dkms` package
- GTK4 ≥ 4.14, libadwaita ≥ 1.5 (pulled in by the app package)
- Membership in the `plugdev` group for passwordless threshold writes

## Building from source

See **INSTALL.md** for the developer Meson build and for building the `.deb`
locally.
