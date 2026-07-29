# MSI BatteryGuard – Installation Guide

## Target Hardware

**MSI Thin A15 B7UCX** (AMD Ryzen 7000 series), EC firmware **`16RKIMS1.111`**.

Other MSI machines supported by upstream `msi-ec` may work; verify the
threshold sysfs path after loading the module.

---

## Recommended: install the `.deb`

```bash
sudo apt install ./msi-batteryguard_1.0.0-1_all.deb
```

This installs:

- The GTK4 app (`msi-batteryguard`)
- Desktop entry, icons, and AppStream metainfo (GNOME Software)
- The udev rule under `/etc/udev/rules.d/` for `plugdev` write access

Then install and load `msi-ec` (next section) if it is not already present.
The package **Recommends** `msi-ec-dkms` when that package is available.

Add yourself to `plugdev` if needed:

```bash
sudo usermod -aG plugdev $USER
# log out and back in
sudo udevadm control --reload-rules
sudo udevadm trigger
```

Launch from the app menu (**MSI BatteryGuard**) or:

```bash
msi-batteryguard
```

---

## msi-ec kernel module (DKMS)

```bash
sudo apt update
sudo apt install -y git dkms linux-headers-$(uname -r)

git clone https://github.com/BeardOverflow/msi-ec.git
cd msi-ec
sudo make dkms-install
```

Load without rebooting:

```bash
sudo modprobe -r msi_ec 2>/dev/null; sudo modprobe msi_ec
```

Verify:

```bash
dmesg | grep msi_ec | tail -5
ls /sys/class/power_supply/BAT*/charge_control_end_threshold
modinfo msi_ec | grep filename
# Prefer: .../updates/dkms/msi-ec.ko.xz  (not the built-in driver path)
```

Autoload on boot:

```bash
echo "msi-ec" | sudo tee /etc/modules-load.d/msi-ec.conf
```

### EC ID (MSI Thin A15 B7UCX)

Firmware ID **`16RKIMS1.111`** is supported upstream (CONF_G2_6, charge
register `0xd7`).

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

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `lsmod` shows no `msi_ec` | `sudo modprobe msi-ec` and check `dmesg` |
| Threshold file not found | Module loaded but EC not supported — check `dmesg` |
| Permission denied writing threshold | udev rule / `plugdev` membership — reload rules, re-login |
| App missing from GNOME Software | Ensure metainfo installed; refresh Software / AppStream cache |
| App shows battery path not found | `ls /sys/class/power_supply/` and report |
