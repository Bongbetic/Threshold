# DKMS, Secure Boot, and reboot lifecycle

Research for [“Research transactional DKMS, Secure Boot, and reboot lifecycle”](https://github.com/Bongbetic/Threshold/issues/71), checked 2026-09-02.

## Decision summary

Threshold can ship the application and the `msi-ec` source in one DEB and one
RPM and let the distribution's `dkms` package supply its native compiler,
kernel-development-package, signing, and kernel-hook integration. It cannot,
however, promise the same transactional rollback semantics on APT/dpkg and
DNF/Zypper, and it cannot complete Secure Boot MOK enrollment inside any package
transaction.

The enforceable lifecycle is:

1. Before installing, classify the host as MSI or non-MSI from DMI sysfs. A
   non-MSI host is allowed to install in vendor-sysfs/notification-only mode.
2. On MSI, install the source, run DKMS `add`, `build`, and `install` for the
   running kernel, and persist a machine-readable result.
3. If DKMS build/install fails, dpkg can leave Threshold unpacked but
   unconfigured and return failure. RPM cannot reliably undo an already
   installed payload from `%post`; RPM packaging guidance requires scriptlets
   to finish successfully because nonzero exits can leave interrupted upgrades
   and duplicate RPM database entries. On RPM, report a degraded/failure state
   and provide an explicit repair/uninstall action rather than claiming atomic
   rollback.
4. If the built module is signed but its key is not trusted while Secure Boot is
   enforcing, queue MOK enrollment and record `pending-reboot`. This is not a
   build failure. A person must confirm enrollment in MokManager on the next
   boot.
5. After a successful load, require both `/sys/devices/platform/msi-ec` and a
   battery `charge_control_end_threshold` attribute before declaring EC control
   ready. Compilation alone proves no hardware compatibility.
6. Ship `/usr/lib/modules-load.d/msi-ec.conf`, keep `AUTOINSTALL="yes"`, and
   verify readiness at application/session startup. These provide reboot and
   kernel-update recovery; they do not guarantee a new kernel remains usable if
   its DKMS rebuild fails.
7. On final removal, run `dkms remove msi-ec/<version> --all`, remove the
   modules-load configuration and Threshold-owned state, but preserve user
   preferences on ordinary removal. Purge may remove preferences.

## What each mechanism permits

| Mechanism | Before payload | After payload / configuration | Failure meaning | Reboot / upgrade role |
|---|---|---|---|---|
| dpkg/APT | `preinst` can perform a cheap host classification and abort before unpacking | `postinst configure` can run DKMS and exit nonzero | dpkg stops, but this is **not rollback**: the package can remain unpacked and unconfigured, so scripts must be idempotent | Debian DKMS installs kernel hooks; `AUTOINSTALL=yes` makes the module eligible for future kernels |
| RPM via DNF | `%pre` runs before package files are installed | `%post` runs after the payload and can run DKMS | A nonzero `%post` is not transactional rollback and can break install/upgrade/erase ordering | Fedora's `dkms` package provides kernel-install integration and matching kernel-devel dependencies |
| RPM via Zypper | Same RPM `%pre`/`%post` phases | Same RPM database and scriptlet semantics | Same non-atomic result; Snapper rollback must not be assumed on every installation | openSUSE's `dkms` package depends on `kernel-syms` and installs a DKMS kernel-install hook and boot service |
| DKMS | Source registration may be prepared once package files exist | `build` and `install` are explicit, separately failing actions | Failure is per module/kernel; `autoinstall` reports failure but does not restore an application package | `AUTOINSTALL=yes`, kernel hooks, and the DKMS service rebuild/install for later kernels |
| `modules-load.d` | N/A | A one-line `msi-ec` file is static boot policy | Loading can still fail because the module is absent, untrusted, or incompatible | `systemd-modules-load.service` tries it on each boot |
| MOK | An enrollment request can be queued in the running OS | Enrollment itself occurs in MokManager before the next OS boot | Until confirmed, a correctly built and signed module can still be rejected | Once enrolled, modules signed by that key can load on subsequent boots |

Debian Policy requires maintainer scripts to return nonzero on error so package
processing stops, requires them to be idempotent, and warns that they are not
guaranteed a controlling terminal. Therefore a DEB may fail `postinst` on a real
DKMS failure and be repairable with a later `dpkg --configure`; it must not try
to conduct firmware UI or an interactive MOK conversation in the script.
[Debian Policy §6](https://www.debian.org/doc/debian-policy/ch-maintainerscripts.html).
Debian's DKMS source package installs explicit kernel pre/post-install and
pre-remove integration scripts.
[Debian DKMS 3.2.2 source](https://sources.debian.org/src/dkms/3.2.2-1~deb13u1/)

Fedora's RPM guidance says `%pre` precedes payload installation and `%post`
follows it. It also requires all scriptlets to exit zero: nonzero exits can stop
later actions for that package, leave the old version unerased during an
upgrade, and produce duplicate RPM database entries or stale files. This rules
out describing a failed RPM `%post` DKMS build as a safe rollback.
[Fedora Scriptlets guidelines](https://docs.fedoraproject.org/en-US/packaging-guidelines/Scriptlets/)

Zypper ultimately installs RPMs. SUSE's kernel-module packaging documentation
explicitly describes SUSE-based systems as using RPM and recommends Kernel
Module Packages for repository-grade external modules. A GitHub-distributed
DKMS RPM can still use the distro `dkms` framework, but it does not gain a
different transaction model merely because Zypper invoked RPM.
[SUSE Kernel Module Packages Manual](https://documentation.suse.com/sbp/systems-management/html/SBP-KMP-Manual-SLE12SP2/index.html)

## Cross-Fedora/openSUSE RPM boundary

A single RPM can avoid hard-coding either distribution's kernel-development
package name by requiring only `dkms`. The native DKMS packages expand that
dependency differently:

- Fedora 43/44 publishes DKMS and its spec requires matching `kernel-devel`
  variants when the corresponding kernel core is present.
  [Fedora DKMS package](https://packages.fedoraproject.org/pkgs/dkms/dkms/),
  [Fedora DKMS spec](https://src.fedoraproject.org/rpms/dkms/blob/rawhide/f/dkms.spec),
  [Fedora kernel-devel package](https://packages.fedoraproject.org/pkgs/kernel/kernel-devel/)
- openSUSE Tumbleweed's official `dkms` package requires `kernel-syms`; its spec
  installs `40-dkms.install` and a DKMS systemd service. The checked machine has
  official `dkms` 3.3.0, `kernel-default-devel`, and `mokutil` packages installed.
  [openSUSE Factory DKMS spec](https://build.opensuse.org/package/view_file/openSUSE:Factory/dkms/dkms.spec)

The Threshold RPM should consequently:

- use `Requires: dkms`, not a Fedora-only `kernel-devel-uname-r` or an
  openSUSE-only `kernel-syms` dependency;
- locate DKMS through the transaction environment or support both
  `/usr/bin/dkms` (Fedora's spec) and `/usr/sbin/dkms` (openSUSE's spec);
- use upstream's `--rpm_safe_upgrade` for DKMS add/remove operations, as the
  DKMS manual specifically requires this flag for module source carried by an
  RPM during upgrades;
- run removal only for a final erase (`$1 == 0`), not while an older RPM is
  being replaced; and
- keep all failure recording distribution-neutral. A path such as
  `/var/lib/threshold/ec-setup.json` is preferable to parsing package-manager
  logs.

This reconciles the DKMS lifecycle layer. It does not prove that every GUI
runtime dependency in a Fedora-built RPM has the same name and ABI on openSUSE;
that is a separate packaging-compatibility decision.

## DKMS build, install, signing, and cleanup

DKMS distinguishes source registration, build, and installation. Its manual
documents that `remove --all` first uninstalls every installed kernel instance
and then removes the module/version from the DKMS tree. It also documents:

- `AUTOINSTALL="yes"` opts the module into automatic installation on kernels;
- `autoinstall` installs the newest eligible module revision for kernels;
- a first build can automatically generate signing keys;
- `mok_signing_key` and `mok_certificate` select those files;
- `modprobe_on_install` may load a successfully installed module; and
- `--rpm_safe_upgrade` is required on RPM add/remove operations.

[Upstream DKMS manual](https://github.com/dell/dkms/blob/master/dkms.8.in),
[upstream framework configuration](https://github.com/dell/dkms/blob/master/dkms_framework.conf.in)

Threshold's vendored `dkms.conf` already declares `AUTOINSTALL="yes"`. The
current DEB and RPM scripts suppress several DKMS failures, while the accepted
policy calls for distinguishing actual build/install failure from Secure Boot
pending enrollment. Implementation must stop treating every `modprobe` error as
equivalent and stop advertising `/var/lib/shim-signed/mok/mok.pub` as a portable
key path: upstream DKMS defaults to configurable `mok_signing_key` and
`mok_certificate`, commonly under `/var/lib/dkms`, while Ubuntu integration can
use shim-signed paths.

For a new kernel, DKMS may fail because matching build files are absent or the
module no longer compiles. Upstream DKMS exposes nonzero statuses for missing
headers, build failure, install failure, and aggregate autoinstall failure.
That failure should be recorded against the specific kernel release. It must
not delete the successfully installed module for an older kernel. The boot
loader can still boot that older kernel; Threshold should show the current
kernel as EC-unavailable and give the relevant DKMS build log path.
[upstream DKMS implementation and exit statuses](https://github.com/dell/dkms/blob/master/dkms.in)

## Secure Boot and MOK are a deferred state

The kernel module-signing facility validates module signatures at load time. In
restrictive mode it rejects modules whose signatures cannot be validated by a
trusted key; signing a `.ko` file is therefore necessary but not sufficient.
[Linux kernel module-signing documentation](https://www.kernel.org/doc/html/latest/admin-guide/module-signing.html)

Ubuntu documents the supported third-party-driver sequence: generate a
machine-specific MOK, sign modules during package installation, ask the user to
authenticate enrollment, present MokManager after restart, enroll, and reboot
again. SUSE likewise documents that `mokutil` writes an enrollment request to
the `MokNew` UEFI variable and MokManager consumes it on the next boot. Both
flows require a human with console access.
[Ubuntu Secure Boot documentation](https://documentation.ubuntu.com/security/docs/security-features/platform-protections/secure-boot/),
[SUSE UEFI and MOK documentation](https://documentation.suse.com/sles/15-SP7/html/SLES-all/cha-uefi.html),
[mokutil manual](https://manpages.ubuntu.com/manpages/noble/en/man1/mokutil.1.html)

Therefore:

- DKMS/package installation may generate and sign with a MOK, but a portable
  noninteractive package script cannot complete or reliably initiate the
  password-authenticated enrollment flow; a post-transaction setup helper must
  guide the user through queuing `mokutil --import`;
- the package must not fail solely because the module is signed by a key that
  is queued but not yet trusted;
- `pending-reboot` must include the certificate fingerprint/path and enough
  information to test enrollment later (`mokutil --test-key` where available);
- after reboot, verify the enrolled key, `modprobe msi-ec`, the platform device,
  and the battery threshold attribute before changing state to `ready`; and
- cancellation or missed enrollment remains a visible, retryable pending state.

## Hardware preflight: what is and is not knowable

A package script can cheaply read DMI identity from
`/sys/class/dmi/id/sys_vendor`, `product_name`, and related files. That is enough
to avoid making `msi-ec` mandatory on a clearly non-MSI machine. It is **not** a
compatibility proof.

The vendored driver explicitly states that it does not use DMI to identify
compatibility. During module initialization it reads the EC firmware version,
selects an exact configuration from its `allowed_fw` tables, returns
`-EOPNOTSUPP` when no configuration matches, and only registers the battery hook
when the configured charge-control capability bit is present. See
[`msi-ec-src/msi-ec.c`](../../msi-ec-src/msi-ec.c) and the upstream source
snapshot it vendors: [BeardOverflow/msi-ec](https://github.com/BeardOverflow/msi-ec).

That yields three progressively stronger checks:

1. **DMI vendor**: determines whether MSI-specific setup is relevant.
2. **Successful module load**: proves the running driver recognizes the EC
   firmware, unless an override/debug mode was used.
3. **Threshold sysfs attribute present**: proves the capability Threshold needs
   is actually exposed.

Secure Boot creates one unavoidable ambiguity: if the signing key is not yet
trusted, `modprobe` is rejected before `msi-ec` can inspect firmware. Such a
machine cannot be classified as supported or unsupported until MOK enrollment
and reboot. It is `pending-reboot`, not `unsupported`.

## Persistent state and boot behavior

`systemd-modules-load.service` reads newline-separated module names from
`modules-load.d` at boot. The systemd documentation recommends automatic device
ID aliases over static lists where drivers support them. `msi-ec` currently has
no DMI alias-based compatibility mechanism, so a package-owned
`/usr/lib/modules-load.d/msi-ec.conf` is the appropriate explicit fallback.
[systemd modules-load.d documentation](https://www.freedesktop.org/software/systemd/man/latest/modules-load.d.html)

Use a small explicit state model rather than a free-form warning file:

| State | Required evidence | Installer result |
|---|---|---|
| `non-msi` | DMI is clearly not MSI | Install app; no EC requirement |
| `build-failed` | MSI and DKMS add/build/install failed | DEB configuration fails; RPM records hard degraded state and finishes safely |
| `pending-reboot` | Build/install succeeded; Secure Boot enabled; signing key is queued/not trusted | Install succeeds with guided enrollment |
| `unsupported` | Trusted module reached init but rejected firmware, or loaded without required threshold capability | Accepted policy says fail initial MSI setup; later kernel/firmware regressions become actionable degraded state |
| `ready` | DKMS installed for running kernel, module loaded, platform and threshold sysfs nodes present | Install succeeds |

On every application start, and preferably through a boot-time helper, recompute
the runtime half of this state. If `ready`, read the actual threshold first and
reapply the saved user value only when it differs. This makes the selected
threshold survive EC/firmware resets without unnecessary EC writes.

## Upgrade and uninstall rules

1. **Package upgrade:** register the new DKMS module version, build/install it,
   and remove the old version only after the new version succeeds. On RPM use
   `--rpm_safe_upgrade`; never remove from an upgrade `%preun`.
2. **Kernel upgrade:** let the distro DKMS kernel hook/autoinstaller build the
   registered `AUTOINSTALL=yes` module. Record results by kernel. Preserve older
   successful builds.
3. **Final uninstall:** attempt to unload `msi-ec` when safe, run `dkms remove
   msi-ec/<version> --all`, remove the package-owned modules-load file, run
   `depmod` as DKMS requires, and remove Threshold's system setup-state file.
4. **Ordinary remove versus purge:** ordinary removal keeps per-user settings;
   Debian purge may remove system residue and preferences where package policy
   permits. RPM has no standard dpkg-style purge distinction, so user settings
   should remain unless the user explicitly requests reset.
5. **Shared ownership:** do not delete a signing key merely because Threshold is
   removed. A DKMS MOK may sign other modules. MOK deletion is a separate,
   explicit administrator action followed by MokManager confirmation.

## Accepted requirements: enforceability verdict

| Accepted behavior | Verdict |
|---|---|
| One app+module DEB and one app+module RPM | Enforceable |
| One RPM lifecycle for DNF and Zypper | Enforceable through distro-native `Requires: dkms`, portable paths, and RPM-safe upgrade handling |
| Fail and roll back on MSI DKMS build failure | Only partially enforceable: dpkg can fail configuration but does not restore a pristine preinstall filesystem; RPM `%post` cannot safely promise rollback |
| Secure Boot setup completes as pending reboot | Enforceable, provided a user completes MokManager enrollment |
| Unsupported MSI firmware is rejected | Enforceable only after a trusted module can execute; impossible to prove while MOK is pending |
| Module and threshold survive reboot | Enforceable through DKMS registration, modules-load policy, boot/startup verification, and conditional threshold reapplication |
| Kernel rebuild failure preserves older working kernel/module | Enforceable; record failure per new kernel and do not remove older DKMS instances |
| Uninstall removes DKMS and autoload setup | Enforceable; do not remove shared MOK keys or ordinary user preferences |

The implementation specification should explicitly replace the word
“transactional” with these observable state transitions. That gives users and
CI truthful success criteria across dpkg, DNF, and Zypper without weakening
Secure Boot or risking RPM database integrity.
