# Threshold – Installation Guide

## Target Hardware

**MSI Thin A15 B7UCX** (AMD Ryzen 7000 series), EC firmware **`16RKIMS1.111`**.

Other MSI machines supported by upstream `msi-ec` may work; verify the
threshold sysfs path after loading the module.

Devices with vendor sysfs threshold support (thinkpad-acpi, asus-wmi, …) are
also supported — the app detects the appropriate control mode automatically.
When no EC/sysfs charge control is available, Threshold falls back to a
notification alarm.

## Supported Ubuntu versions

Packages are built and tested on **Ubuntu 24.04 LTS (noble)** and
**Ubuntu 26.04 LTS (resolute)**.  The package is built for `amd64`.

---

## Install from a GitHub Release (recommended)

1. Open the
   [Releases page](https://github.com/Bongbetic/MSI-batteryguard-for-Thin-A15-B7UCX/releases)
   and download the latest release's `.deb` file:

   - `threshold_*.deb` — the GTK4 app + msi-ec DKMS source (single package)

2. Install the package:

   ```bash
   sudo apt install ./threshold_1.3.0-1_amd64.deb
   ```

   DKMS builds the msi-ec module for the running kernel automatically. If
   kernel headers are missing, install them first:

   ```bash
   sudo apt install -y linux-headers-$(uname -r)
   ```

3. Add yourself to `plugdev` (needed for passwordless threshold writes) and
   reload the udev rules:

   ```bash
   sudo usermod -aG plugdev $USER
   # log out and back in for the group to take effect
   sudo udevadm control --reload-rules
   sudo udevadm trigger
   ```

4. Launch from the app menu (**Threshold**) or:

   ```bash
   threshold
   ```

### What gets installed

| Component | Location |
|---|---|
| Launcher | `/usr/bin/threshold` |
| Python package + GResource | `/usr/share/com.bongbetic.threshold/` |
| Desktop entry | `/usr/share/applications/` |
| AppStream metainfo | `/usr/share/metainfo/` |
| GSettings schema | `/usr/share/glib-2.0/schemas/` |
| udev rule (`plugdev` writes) | `/usr/lib/udev/rules.d/99-msi-battery.rules` |
| `msi-ec` DKMS source | `/usr/src/msi-ec-0.13/` |
| Built kernel module | `/lib/modules/$(uname -r)/updates/dkms/msi-ec.ko` |

### Control modes

The app automatically detects which control mode applies:

- **EC control — msi-ec**: msi-ec module loaded, threshold attr present.
- **Vendor sysfs control**: threshold attr present from another driver.
- **Notification only**: no threshold attr; charge monitoring with alarm.

---

## Verify the module

After installing `msi-ec-dkms`, load and check:

```bash
sudo modprobe msi-ec
dkms status                     # msi-ec/0.13 should be built + installed
modinfo msi-ec | grep filename # should point at updates/dkms, not the built-in path
ls /sys/class/power_supply/BAT*/charge_control_end_threshold
```

If the threshold file exists, you're ready to use the app.

---

## Manual DKMS fallback (developers / upstream latest)

If you prefer the latest upstream module instead of the packaged snapshot:

```bash
sudo apt install -y git dkms linux-headers-$(uname -r)

git clone https://github.com/BeardOverflow/msi-ec.git
cd msi-ec
sudo make dkms-install
```

Autoload on boot:

```bash
echo "msi-ec" | sudo tee /etc/modules-load.d/msi-ec.conf
```

### EC ID (MSI Thin A15 B7UCX)

Firmware ID **`16RKIMS1.111`** is supported upstream (CONF_G2_6, charge
register `0xd7`). The vendored source in `msi-ec-src/` includes this config.

---

## Manual build (developers)

Build dependencies (Ubuntu 24.04+):

```bash
sudo apt install -y \
  meson ninja-build pkg-config desktop-file-utils gettext \
  gobject-introspection python3 python3-gi python3-pytest \
  blueprint-compiler libgtk-4-dev libadwaita-1-dev \
  gir1.2-gtk-4.0 gir1.2-adw-1
```

Configure, test, install:

```bash
meson setup builddir
meson compile -C builddir
meson test -C builddir --print-errorlogs
sudo meson install -C builddir
sudo udevadm control --reload-rules
sudo udevadm trigger
```

Default prefix is `/usr/local`. For a layout closer to the `.deb`, use:

```bash
meson setup builddir --prefix=/usr --sysconfdir=/etc
```

### Build the .deb locally

```bash
sudo apt install -y dpkg-dev debhelper dh-python
sudo apt-get build-dep -y .
dpkg-buildpackage -us -uc -b
```

A single `.deb` lands in the parent directory:

- `../threshold_1.3.0-1_amd64.deb`

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `lsmod` shows no `msi_ec` | `sudo modprobe msi-ec` and check `dmesg` |
| `dkms status` shows build failure | Install `linux-headers-$(uname -r)` and reinstall the package |
| Threshold file not found | Module loaded but EC not supported — app switches to notification mode |
| Permission denied writing threshold | udev rule / `plugdev` membership — reload rules, re-login |
| App missing from GNOME Software | Ensure metainfo installed; refresh Software / AppStream cache |
| App shows "Notification only" mode | No EC/sysfs threshold control — alarm monitors charge and notifies at threshold |
