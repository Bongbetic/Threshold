# Threshold – Installation Guide

## Target Hardware

**MSI Thin A15 B7UCX** (AMD Ryzen 7000 series), EC firmware **`16RKIMS1.111`**.

Other MSI machines supported by upstream `msi-ec` may work; verify the
threshold sysfs path after loading the module.

Devices with vendor sysfs threshold support (thinkpad-acpi, asus-wmi, …) are
also supported — the app detects the appropriate control mode automatically.
When no EC/sysfs charge control is available, Threshold falls back to a
notification alarm.

## Supported distributions

| Distribution | Package | Notes |
|---|---|---|
| Ubuntu 24.04 LTS (noble), 26.04 LTS (resolute), Debian trixie | `threshold_*.deb` | `amd64` |
| Fedora 43, Fedora 44 | `threshold-*.rpm` | `noarch` — app + DKMS subpackage |

---

## Install from a GitHub Release (recommended)

### Ubuntu / Debian (.deb)

1. Open the
   [Releases page](https://github.com/Bongbetic/MSI-batteryguard-for-Thin-A15-B7UCX/releases)
   and download the latest release's `.deb` file:

   - `threshold_*.deb` — the GTK4 app + msi-ec DKMS source (single package)

2. Install the package:

   ```bash
   sudo apt install ./threshold_1.4.1-1_amd64.deb
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

### Fedora (.rpm)

Two packages are attached to each release (built for Fedora 43 and 44):

- `threshold-<version>-1.fcXX.noarch.rpm` — the GTK4 app
- `threshold-msi-ec-dkms-<version>-1.fcXX.noarch.rpm` — the `msi-ec` DKMS
  source; pulled in automatically by `dnf` as a weak dependency (install
  it explicitly if you run with `--setopt=install_weak_deps=False`)

1. Install the kernel-module prerequisites, then the app (the DKMS
   subpackage comes with it and builds the `msi-ec` module for the
   running kernel at install time; DKMS also rebuilds it on kernel
   updates):

   ```bash
   sudo dnf install -y dkms "kernel-devel-uname-r == $(uname -r)"
   sudo dnf install ./threshold-1.4.1-1.fc44.noarch.rpm
   ```

2. The package creates a system group `threshold` (Fedora has no
   `plugdev`) and the udev rule grants that group write access to the
   charge threshold attribute. Add yourself and log back in:

   ```bash
   sudo usermod -aG threshold $USER
   # log out and back in for the group to take effect
   ```

   Users not in the `threshold` group can still apply thresholds through
   the app's `pkexec` (polkit) fallback.

3. **Secure Boot**: the unsigned DKMS module will not load until signed.
   Enroll a MOK key once (for example, if one was created during DKMS
   setup), then reboot:

   ```bash
   sudo mokutil --import /var/lib/shim-signed/mok/mok.pub
   ```

4. Launch from the app menu (**Threshold**) or:

   ```bash
   threshold
   ```

#### Fedora differences

- udev rule group: `threshold` (rewritten from the Debian `plugdev` at
  build time)
- group config: `/usr/lib/sysusers.d/threshold.conf`
- DKMS source: `/usr/src/msi-ec-0.13.112/`
- autoload hint: `/usr/lib/modules-load.d/msi-ec.conf`
- everything else matches the table below

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

## Verify downloads

Every release carries a `SHA256SUMS` file covering the `.deb` and `.rpm`
artifacts:

```bash
sha256sum -c SHA256SUMS --ignore-missing
```

A GPG-signed copy is attached to each release and maintained in the
repository at `output/SHA256SUMS.asc`. The release signing key is
ed25519, fingerprint:

```
0560467C 274F2A72 1007DDF6 E9B18DB9 8E43B738
```

Verify with `gpg --verify SHA256SUMS.asc SHA256SUMS`.

## Verify the module

After installing the DKMS package (`msi-ec-dkms` on Ubuntu/Debian,
`threshold-msi-ec-dkms` on Fedora), load and check:

```bash
sudo modprobe msi-ec
dkms status                     # msi-ec/0.13 (deb) or msi-ec/0.13.112 (rpm) built + installed
modinfo msi-ec | grep filename # should point at updates/dkms, not the built-in path
ls /sys/class/power_supply/BAT*/charge_control_end_threshold
```

If the threshold file exists, you're ready to use the app.

---

## Manual DKMS fallback (developers / upstream latest)

If you prefer the latest upstream module instead of the packaged snapshot:

```bash
sudo apt install -y git dkms linux-headers-$(uname -r)
# Fedora: sudo dnf install -y git dkms "kernel-devel-uname-r == $(uname -r)"

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

Fedora build dependencies:

```bash
sudo dnf install -y meson ninja-build gettext blueprint-compiler \
  gtk4-devel libadwaita-devel python3-gobject desktop-file-utils
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
| Permission denied writing threshold (Fedora) | `threshold` group membership (not `plugdev`) — `usermod -aG threshold $USER`, re-login |
| DKMS module won't load (Secure Boot) | Sign and enroll a MOK key — see "Fedora (.rpm)" above |
| App missing from GNOME Software | Ensure metainfo installed; refresh Software / AppStream cache |
| App shows "Notification only" mode | No EC/sysfs threshold control — alarm monitors charge and notifies at threshold |
