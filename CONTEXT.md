# Threshold

A battery charge-threshold controller: reads and writes the kernel's battery charge limit via sysfs so the EC stops charging at a user-set percentage.

## Language

**Threshold-capable battery**:
A battery whose sysfs directory has `type == Battery`. The app discovers
batteries by enumerating `/sys/class/power_supply/` dynamically.
_Avoid_: supported battery, EC-compatible device, MSI battery

**Charge threshold**:
The machine-wide, user-confirmed charge limit (20–100%); the most recent
confirmation becomes the device policy regardless of which user made it. It
remains the desired threshold in every control mode, including while EC setup
is pending or unavailable.
_Avoid_: charge cap, battery limit

**Active threshold**:
The charge threshold currently enforced by the battery's live sysfs interface.
It may differ temporarily from the desired threshold while EC control is being
set up, repaired, or reconciled.
_Avoid_: desired threshold, pending threshold

**Control mode**:
How the application communicates charge thresholds to the battery.
Three modes detected automatically at runtime:
- **EC msi-ec**: the msi-ec kernel module is loaded and exposes
  `charge_control_end_threshold` on the battery sysfs device.
- **Vendor sysfs**: a native vendor driver (thinkpad-acpi, asus-wmi, …)
  exposes the threshold file without msi-ec.
- **Notification only**: no threshold control is available; the app monitors
  capacity and notifies the user once the charge reaches the threshold.
_Avoid_: driver, firmware

**EC module**:
The kernel module (msi-ec, thinkpad-acpi, asus-wmi, …) that exposes the
battery's charge-threshold sysfs interface.  The app detects mode based on
whether the msi-ec platform device is present alongside the threshold file.
_Avoid_: driver, firmware

**EC setup state**:
The MSI EC module's readiness for control, determined by live capability
evidence: available now, pending completion after a reboot, or unavailable.
Persisted setup records explain history and recovery but cannot override live
verification. This is distinct from the active control mode.
_Avoid_: installation status, driver status

**EC setup reason**:
The explanation attached to an EC setup state, such as MOK enrollment required,
build failure, unsupported firmware, or MSI EC setup not applying to non-MSI
hardware. It determines the user-visible outcome and available recovery action.
_Avoid_: error code, setup state

**EC maintenance status**:
The health of an EC module update or repair independently of present EC control.
A working existing module can keep EC setup available while a replacement is
pending reboot or has failed.
_Avoid_: EC setup state, control mode

**Boot reconciliation**:
The bounded, non-boot-critical pre-login verification that discovers live
control, compares the active threshold with the charge threshold, and applies
the charge threshold once when they differ. It is available to native packages
and to an AppImage after its EC setup authority has been installed.
_Avoid_: startup retry, background repair, login restore

**Kernel lifecycle record**:
The durable, structured evidence for EC module preparation, trust, loading,
live capability, and boot reconciliation for one kernel release.
_Avoid_: install log, setup state, diagnostics dump

**Known-good kernel**:
An installed kernel on which live EC capability and boot reconciliation have
both succeeded during an actual boot. A successful DKMS build alone does not
make a kernel known-good.
_Avoid_: previous kernel, built kernel, fallback kernel

**AppImage EC bootstrap**:
The one-time, explicitly authorized setup that establishes Threshold's
system-owned EC maintenance capability for an otherwise unprivileged AppImage.
_Avoid_: AppImage installation, automatic setup

**EC setup authority**:
The system-owned authority that performs explicitly approved EC setup changes
for an AppImage; the AppImage can request an operation but retains no privilege.
_Avoid_: privileged AppImage, background updater

**EC setup bundle**:
A versioned, authenticated set of EC module and maintenance inputs presented by
Threshold for an explicit setup, update, or repair operation.
_Avoid_: AppImage update, driver download

**EC setup removal**:
The explicit administrative operation that removes Threshold-managed EC setup
without being implied by moving or deleting the AppImage file.
_Avoid_: AppImage deletion, uninstalling the AppImage

**Unified RPM**:
The single distribution-neutral RPM that contains Threshold, its vendored
msi-ec DKMS source, and the supporting system integration files. The exact
same artifact is installed through both dnf and zypper on supported x86-64
systems.
_Avoid_: RPM bundle, RPM pair, DKMS subpackage

**Unified RPM ownership handoff**:
The supported migration that transfers Threshold-managed EC setup assets from
the paired RPMs to the Unified RPM while preserving any live EC capability. It
adopts only assets traceable to official Threshold packages.
_Avoid_: package rename, module takeover, DKMS cleanup

**Threshold-managed EC asset**:
An EC setup asset whose provenance is recorded by Threshold through an
authorized package or bootstrap operation. Unrecorded module sources and DKMS
registrations are foreign assets and are never adopted or removed.
_Avoid_: owned file, installed module, DKMS artifact

**Native package integration layer**:
The shared system-integration payload used by both the DEB and Unified RPM,
including EC lifecycle behavior, boot reconciliation, service definitions, and
ownership manifests. Distribution-specific package hooks invoke this layer but
do not reimplement it.
_Avoid_: maintainer scripts, distro helper, packaging glue

**Release candidate**:
An immutable, canonically named release artifact built once from the tagged
source revision and carried unchanged through verification and publication.
_Avoid_: build output, release build, repacked artifact

**Release manifest**:
The machine-readable inventory that binds every release candidate to its
SHA-256, source revision, build identity, and provenance evidence.
_Avoid_: candidate inventory, checksum list, build metadata

**Release promotion**:
The explicitly authorized transition of a fully verified draft release to
public visibility without changing any candidate or release metadata asset.
_Avoid_: release upload, deployment, rebuild

**Withdrawn release**:
A previously public release retained as an auditable record but clearly marked
unsafe or unsuitable for use and superseded by a later release.
_Avoid_: deleted release, rolled-back release, replaced release

**EC lifecycle command**:
The private, idempotent system command that performs hardware preflight,
provenance checks, setup, repair, reconciliation, diagnostics, and removal for
Threshold-managed EC assets. Native package hooks and explicit recovery actions
invoke the same command.
_Avoid_: post-install script, DKMS wrapper, privileged application

**Notification-area item**:
Threshold's visible desktop-panel presence for opening the application and
using its threshold menu. It is usable only while its StatusNotifierItem is
registered with a live notification-area host.
_Avoid_: tray icon, system tray icon

**StatusNotifierItem**:
The D-Bus protocol object through which Threshold exposes its notification-area
item, icon, tooltip, activation methods, and dbusmenu to a compatible host.
_Avoid_: notification-area item, AppIndicator, XEmbed icon

**Notification-area readiness**:
Whether Threshold can safely hide its window behind a usable notification-area
item. It progresses through unavailable, registering, ready, or lost based on
live watcher registration evidence; only ready permits close-to-notification-area.
_Avoid_: tray existence, StatusNotifierItem status, desktop notification status

### Appearance

**Dark mode**:
The appearance setting that forces the dark theme when on; when off, the UI
follows the system's light/dark preference instead.
_Avoid_: night mode, force dark

**Theme scheme**:
Which of the light or dark themes the UI renders right now: dark when Dark
mode is on, otherwise whatever the system currently prefers.
_Avoid_: color scheme, theme

**Accent color**:
The highlight hue applied across the UI, chosen from five presets
(orange, blue, green, purple, red); orange is the default.
_Avoid_: theme color, highlight color
