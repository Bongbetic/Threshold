# One Threshold RPM for Fedora and openSUSE

**Question:** Can one binary RPM containing Threshold and the vendored
`msi-ec` DKMS source be installed safely by `dnf` on Fedora 43/44 and by
`zypper` on openSUSE Tumbleweed?

**Research date:** 2026-09-02

## Decision

One identical, `noarch` RPM can carry the Threshold application, udev rule,
sysusers file, modules-load entry, and `/usr/src/msi-ec-0.13.112` tree on all
three targets. The common RPM/DKMS interfaces are sufficient, provided the
spec avoids build-host-only macros in the resulting dependency set and uses
portable or alternative runtime requirements.

It **cannot**, however, satisfy the stronger requirement “build and load
`msi-ec`, then roll back the application if that fails” as a single ordinary
RPM. The module source is not available until RPM unpacks the package, so the
build belongs in `%post`; RPM explicitly cannot undo a transaction after a
scriptlet failure. A `%pre` can reject known-incompatible hardware before the
payload is unpacked, but cannot build source that is still inside that same
payload. [RPM's scriptlet contract](https://rpm.org/docs/latest/manual/triggers.html)
states both facts: `%pre` runs before unpacking and can prevent installation,
while scriptlets should normally return zero because RPM cannot roll back a
transaction.

Therefore the supported one-RPM design must use this state model:

1. Non-MSI hardware installs normally and uses vendor-sysfs or notification
   fallback.
2. Recognized MSI hardware attempts DKMS add/build/install in `%post`.
3. A successful build followed by a Secure Boot rejection is **pending reboot
   and MOK enrollment**, not an install failure.
4. Any other DKMS or module-load failure leaves the application installed but
   records an explicit **EC setup failed** state with a repair command and log.
5. Release verification, not RPM rollback, is what prevents publishing an RPM
   that fails on the mandatory Thin A15 B7UCX validation machine.

If transactional rollback on DKMS failure remains non-negotiable, one RPM is
not a viable design. It would require a separately installed preflight/module
package, an external installer that runs before `dnf`/`zypper`, or duplicating
the complete module source into a pre-install scriptlet; the first two violate
the one-package constraint and the last is not a maintainable or auditable RPM
design.

## Compatibility matrix

| Concern | Fedora 43/44 | openSUSE Tumbleweed | One-RPM treatment |
|---|---|---|---|
| RPM boolean dependencies | Supported | Supported | Use rich `or` dependencies only where package names differ. RPM has supported boolean dependencies since 4.13 ([RPM manual](https://rpm.org/docs/latest/manual/more_dependencies.html#boolean-dependencies)). |
| DKMS package | `dkms` is in Fedora; its package installs `/usr/bin/dkms`, `40-dkms.install`, and `dkms.service` ([Fedora package data](https://packages.fedoraproject.org/pkgs/dkms/dkms/fedora-43.html)) | `dkms` is in current [Tumbleweed/Factory](https://build.opensuse.org/package/show/openSUSE%3AFactory/dkms) | `Requires: dkms` is portable. |
| Kernel build prerequisites | Fedora's `dkms` package does not itself require `kernel-devel`; Fedora kernel-devel RPMs expose versioned `kernel-devel-uname-r` capabilities | Tumbleweed's `dkms` requires `kernel-syms`, which pulls its kernel development stack | A static RPM dependency can ensure *a* build tree, but cannot encode `uname -r` at install time. The post-install helper must check `/lib/modules/$(uname -r)/build` before promising immediate EC availability. |
| DKMS source layout | `/usr/src/<module>-<version>` | Same | Ship `/usr/src/msi-ec-0.13.112`; this is an upstream-supported manual source layout ([DKMS README](https://github.com/dkms-project/dkms/blob/main/README.md#installation-of-dkms-tarballs)). |
| Runtime GTK/Adwaita packages | `gtk4`, `libadwaita`, `libnotify`, `python3-gobject` | The runtime RPM names differ internally, but Tumbleweed packages provide the Fedora-facing `gtk4`, `libadwaita`, and `python3-gobject` capabilities | Keep the shared capabilities, but require the GI typelib files explicitly because openSUSE splits some typelibs into separate RPMs. |
| WebKitGTK 6 for the new UI | Fedora package: `webkitgtk6.0` ([Fedora 43 file list](https://packages.fedoraproject.org/pkgs/webkitgtk/webkitgtk6.0/fedora-43.html)) | Tumbleweed typelib package: `typelib-1_0-WebKit-6_0` | Require `/usr/lib64/girepository-1.0/WebKit-6.0.typelib`. Both solvers can resolve a file requirement to their differently named provider, whereas neither repository exposes a common `typelib(WebKit)` capability. |
| sysusers | Fedora and Tumbleweed both consume `/usr/lib/sysusers.d` | Same path; current Tumbleweed systemd owns the file trigger | Ship `threshold.conf` and, before the immediate udev trigger, explicitly call `systemd-sysusers` for this file. Do not bake either distro's build-only sysusers macro into the shared artifact. |
| udev rules | `/usr/lib/udev/rules.d` | Same | Ship the same rule, reload with `udevadm control --reload`, then trigger `power_supply` only after the `threshold` group exists. |
| Module autoload | `/usr/lib/modules-load.d` | Same | Ship `msi-ec.conf`; `AUTOINSTALL="yes"` lets DKMS rebuild for later kernels. |
| Secure Boot | Signed DKMS module still needs its certificate enrolled | Same | Treat this as pending reboot. Modern DKMS generates and uses `/var/lib/dkms/mok.key` and `/var/lib/dkms/mok.pub`; enroll the latter, not Ubuntu's `/var/lib/shim-signed/...` path ([DKMS module-signing and Secure Boot guidance](https://github.com/dkms-project/dkms/blob/main/README.md#module-signing)). |
| KDE Plasma / XFCE / GNOME | No packaging distinction | No packaging distinction | Desktop choice does not require another RPM; GTK/WebKit runtime dependencies, the desktop entry, notifications, and polkit/udev access are system services rather than desktop-specific payloads. |

## Dependency design

### Shared requirements

The current application requirements that already have cross-distribution
capabilities can remain direct requirements:

```spec
Requires:       python3-gobject
Requires:       gtk4 >= 4.14
Requires:       libadwaita >= 1.5
Requires:       hicolor-icon-theme
Requires:       dkms
Requires:       kmod
Requires:       systemd
Requires:       /usr/lib64/girepository-1.0/Gtk-4.0.typelib
Requires:       /usr/lib64/girepository-1.0/Adw-1.typelib
Requires:       /usr/lib64/girepository-1.0/Notify-0.7.typelib
Requires:       /usr/lib64/girepository-1.0/WebKit-6.0.typelib
Recommends:     polkit
Recommends:     mokutil
```

The WebKit dependency is currently missing from `packaging/threshold.spec`
even though `src/threshold/carbon_shell.py` requires GI namespace `WebKit`
version 6.0. Fedora ships the namespace in `webkitgtk6.0`; Tumbleweed splits it
into `typelib-1_0-WebKit-6_0`. The same split affects Notify on Tumbleweed.
Because the accepted release scope is x86-64, direct `/usr/lib64` typelib file
requirements are the cleanest shared capability: RPM file dependencies let
each solver select its own owning package without ambiguous rich-dependency
branch selection.

Do not put `%{?dist}` in `Release` for the shared artifact. It would not
prevent installation, but it would produce Fedora-branded NEVR and different
artifacts per Fedora build root. Use a distribution-neutral release such as
`Release: 1` and build the artifact once.

### Kernel headers are the hard dependency seam

Fedora 43's published `dkms` dependency list includes the compiler/toolchain
but no kernel-devel package ([Fedora's package metadata](https://packages.fedoraproject.org/pkgs/dkms/dkms/fedora-43.html#dependencies)).
Current Tumbleweed's `dkms` RPM instead requires `kernel-syms`. This was also
verified locally on Tumbleweed 20260830 with:

```text
$ zypper --non-interactive info --requires dkms
...
kernel-syms
gcc
make
modutils
```

RPM rich dependencies can express an alternative such as
`(kernel-devel-uname-r or kernel-syms)`, but no static header can require the
version returned later by `uname -r`. The installer must test the running
kernel's build link directly:

```sh
test -e "/lib/modules/$(uname -r)/build"
```

If it is absent on detected MSI hardware, the one-RPM design must report EC
setup failure and an exact distro-specific repair command. A maintainer
scriptlet must not recursively invoke `dnf` or `zypper` from inside their own
locked transaction.

## DKMS and reboot persistence

The vendored `dkms.conf` already declares `PACKAGE_NAME`, `PACKAGE_VERSION`,
one built module, and `AUTOINSTALL="yes"`. The portable install sequence is:

```sh
dkms add -m msi-ec -v 0.13.112
dkms build -m msi-ec -v 0.13.112 -k "$(uname -r)"
dkms install -m msi-ec -v 0.13.112 -k "$(uname -r)"
depmod -a "$(uname -r)"
modprobe msi-ec
```

DKMS documents that `-k` selects the target kernel and that `autoinstall`
installs modules for later kernel revisions ([DKMS manual](https://github.com/dkms-project/dkms/blob/main/dkms.8.in)). The Fedora package also installs a
kernel-install hook and service, while Tumbleweed's DKMS package depends on its
kernel development stack. The shared RPM must nevertheless test both upgrade
paths in native CI because the distro integration around the shared DKMS CLI
is different.

`/usr/lib/modules-load.d/msi-ec.conf` makes the successfully installed module
eligible for loading on each boot. The application should verify both
`/sys/devices/platform/msi-ec` and the battery threshold attribute after boot,
then reapply the saved threshold only when the EC did not preserve it.

## Scriptlets, sysusers, and udev

The current RPM spec suppresses every DKMS and `modprobe` error with `|| :`.
That makes the transaction robust, but it also makes successful EC setup
indistinguishable from failure. Replace that with an explicit state file and
logs, while still ending `%post` successfully because RPM cannot roll back.

The order should be:

1. Payload installs the sysusers, udev, modules-load, and DKMS source files.
2. `%post` creates the `threshold` group with `systemd-sysusers`.
3. `%post` runs the hardware-aware DKMS state machine.
4. `%post` reloads udev and triggers the `power_supply` subsystem.
5. `%post` writes one of `not-required`, `ready`, `pending-mok-reboot`, or
   `failed` under `/var/lib/threshold/`.

The same static files work on both systems. The distro macro sets used while
building packages are not identical: openSUSE has historically generated a
`%pre` using `sysusers_generate_pre`, while newer systemd packages use file
triggers for `/usr/lib/sysusers.d` and `/usr/lib/udev/rules.d`
([openSUSE systemd change record](https://build.opensuse.org/projects/home%3Ajsulig%3Abranches%3Adevel%3ALoongArch%3AFactory%3Acache/packages/systemd/files/systemd.changes?expand=0)).
For a shared prebuilt RPM, an explicit portable `systemd-sysusers` call avoids
depending on whichever build-time macro happened to exist in the build root.

## Secure Boot boundary

DKMS signs modules at build time and creates its default key pair in
`/var/lib/dkms`; Secure Boot still requires the public certificate to be
enrolled before the kernel trusts the module. Enrollment uses
`mokutil --import /var/lib/dkms/mok.pub` and completes in the firmware UI after
a reboot ([upstream DKMS instructions](https://github.com/dkms-project/dkms/blob/main/README.md#secure-boot)).

RPM scriptlets are non-interactive and should not assume their output is seen
([RPM scriptlet manual](https://rpm.org/docs/latest/manual/triggers.html#scripts)).
Consequently, neither `dnf` nor `zypper` can make a Secure Boot machine fully
EC-ready in the install transaction. The accepted `pending-mok-reboot` state
is not merely preferable UX; it is the correct transaction boundary.

## Required validation before release

Build one neutral RPM once, then test that exact checksum in all environments:

- Fedora 43 container/VM: solver install, application import/start smoke test,
  DKMS negative path without hardware, and kernel-update rebuild.
- Fedora 44 container/VM: the same checks.
- openSUSE Tumbleweed KDE Plasma and XFCE: solver install and desktop launch.
- Thin A15 B7UCX physical machine: DKMS build, signed module, MOK pending flow,
  post-reboot `modprobe`, threshold write/read-back, another reboot, and a
  kernel update followed by rebuild verification.

Container tests establish packaging and dependency compatibility; they cannot
establish EC safety or reboot persistence. Publication should remain gated on
the physical-machine test, while a draft GitHub release may be produced after
the native package smoke matrix passes.

## Implementation consequences

- Merge the current RPM subpackage into the main `%files` list; keep the
  artifact `BuildArch: noarch` because it ships Python and module *source*, not
  a prebuilt kernel object.
- Replace `%{?dist}` and Fedora-only build-result naming with a neutral NEVR.
- Add explicit Gtk/Adw/Notify/WebKit typelib file dependencies and test their
  solver resolution with both `dnf` and `zypper`.
- Keep shared FHS/systemd paths; avoid distro-specific DKMS and MOK paths.
- Implement the four-state EC setup record and a repair/verification command.
- Treat post-unpack DKMS failure as an installed-but-failed setup, never as a
  successful EC installation and never as a transaction that RPM can roll
  back.
- Make the exact artifact checksum, not merely the same spec source, the CI
  invariant across Fedora 43, Fedora 44, and Tumbleweed.
