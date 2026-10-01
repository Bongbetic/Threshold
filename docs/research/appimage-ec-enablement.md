# Safe AppImage EC-enablement boundary

Resolution asset for **Research a safe AppImage EC-enablement boundary**
([Wayfinder ticket](https://github.com/Bongbetic/Threshold/issues/72)). Research
was checked on 2026-09-02 against the current upstream documentation and source
linked below.

## Decision

Keep the AppImage unprivileged and fully usable without `msi-ec`. Add an
explicit **Enable MSI EC control** flow which performs one administrator-approved
bootstrap, then install a small, root-owned, command-limited helper. Use that
installed helper for every later install, update, repair, and removal operation.
Do **not** run a helper out of the user-writable AppImage as root on every update,
and do not install an always-running privileged daemon.

This preserves the useful AppImage contract: downloading or replacing the one
AppImage file never silently mutates the host. Enabling EC control is a separate,
clearly disclosed system change. The unavoidable caveat is that deleting an
AppImage cannot uninstall persistent system state; the application must expose
an explicit **Remove MSI EC support** operation and document it beside the
download.

The boundary should be:

```text
unprivileged AppImage UI
    |
    | explicit request + Polkit authentication
    v
/usr/libexec/threshold/threshold-ec-helper  (root-owned, fixed path)
    |
    | verifies a signed, versioned EC bundle; accepts fixed verbs only
    v
DKMS source/state + modules-load config + installed kernel module
```

Polkit's own architecture expects the privileged *mechanism* to treat the
unprivileged subject as untrusted and to check every request. Actions are
installed system-wide, while authentication agents are supplied by the desktop
session, which fits KDE Plasma and XFCE without putting privileged UI in the
AppImage.[1] `pkexec` deliberately does not validate arguments, and its manual
warns that privileged programs must not trust user input.[2]

## Why this design

| Design | Ownership and updates | Security boundary | Result |
| --- | --- | --- | --- |
| Run an embedded helper with `pkexec` on first run **and every update** | AppImage owner can replace the root-executed program at any time; each application update also changes privileged code | Polkit authenticates the administrator but does not establish artifact provenance or validate helper arguments. The displayed executable path is useful consent UI, not code verification.[2] | **Reject** after bootstrap. It makes a user-owned release artifact a recurring root-code entry point. |
| One-time AppImage bootstrap, then a root-owned helper at a fixed path | Bootstrap installs an immutable copy, action policy, versioned module payload, and state. Later AppImages negotiate a versioned protocol and request an explicit helper update. | One unavoidable initial trust decision, followed by a small stable boundary. Custom Polkit actions can bind to the installed full executable path.[2] | **Recommend.** Lowest persistent complexity while meeting the one-download AppImage requirement. |
| Separately distributed privileged service/package | Native package manager owns files, dependencies, rollback, signatures, and removal | Strongest conventional supply-chain and ownership model; a D-Bus mechanism must authorize every method because subjects are untrusted.[1] | **Security baseline, but not the primary UX.** It creates a second separately installed deliverable, contrary to the accepted one-artifact experience. |
| Root system D-Bus service installed from the AppImage | Stable root-owned endpoint; can report asynchronous progress and service multiple clients | Larger permanent API and parser surface. It must authenticate every request and should be on-demand and systemd-hardened.[1][3] | **Reserve for later.** DKMS lifecycle operations are rare enough for a short-lived helper. Add a service only if cancellable/progress-rich jobs cannot be handled safely by the helper protocol. |
| Embed local `.deb`/`.rpm` companions and ask PackageKit to install the matching one | Package manager owns lifecycle; PackageKit has a local-file transaction and a trusted-files flag.[7] | Good native transaction boundary, but still requires distro-specific embedded artifacts, PackageKit backend availability, and separate package identity/state | **Viable fallback**, especially on immutable hosts, but weakens the portable single-payload design and duplicates packaging work. |
| `systemd-sysext` image | Read-only extension can add files to `/usr` and `/opt` and activate at boot | It does not merge `/etc` or `/var`, has no dependency scheme, and is explicitly not a generic packaging framework.[8] DKMS necessarily maintains `/var/lib/dkms` and per-kernel modules. | **Reject** as the general Fedora/openSUSE/Debian solution. |

## Bootstrap and trust model

No code contained inside an AppImage can prove its own trustworthiness: the
AppImage documentation explicitly says signature validation requires an
**external** tool, not the AppImage being validated.[4] Therefore:

1. GitHub Releases must publish the signed AppImage, its detached checksum or
   provenance, and verification instructions. The enable dialog must identify
   the application version, embedded `msi-ec` version, and host changes before
   invoking Polkit. Running an unverified AppImage and approving root access is
   an administrator trust decision that software cannot repair internally.
2. The first bootstrap is the only time executable code from the read-only
   AppImage mount is elevated. It installs the helper atomically to a fixed
   root-owned path, plus its Polkit action. It must be a compiled/single-purpose
   installer, not `pkexec sh -c ...`, and accept no destination path or command
   string from the caller.
3. The installed helper becomes the trust anchor for future EC payloads. Embed a
   release public key in it and require a detached signature over a canonical
   manifest containing every file digest, payload version, minimum helper
   protocol, and supported architecture. Copy verified regular files into a
   root-owned staging directory before running DKMS; reject symlinks, devices,
   path traversal, unexpected files, oversize payloads, and a manifest/digest
   mismatch.
4. Never authorize an update implicitly. The UI compares the AppImage's embedded
   bundle/protocol version with root-owned state and offers **Update EC support**.
   Refuse downgrades unless the administrator chooses a separately named
   rollback operation.

AppImage itself supports one-app/one-file distribution and permits desktop
integration only with explicit user permission.[5] The same explicit-consent
principle should govern the much more consequential EC system integration.

## Installed helper contract

Use a fixed executable such as
`/usr/libexec/threshold/threshold-ec-helper`. Its public interface should contain
only these verbs, with no arbitrary paths or shell fragments:

- `status`: unprivileged/read-only status, or a separately safe query path;
- `install <staged-bundle-fd-or-token>`: verify, stage, register, build, install,
  configure autoload, and attempt load;
- `update <staged-bundle-fd-or-token>`: same validation with atomic version
  switch and rollback;
- `repair`: rebuild the already installed, root-owned source for the current
  kernel;
- `remove`: unload when safe, remove DKMS registration and Threshold-owned
  autoload/state files, preserving unrelated DKMS keys and configuration.

Prefer passing an already-open file descriptor or a helper-created opaque staging
token over accepting a caller-selected pathname. If a path is unavoidable, open
with no-follow semantics, verify ownership/type, pin the inode, and perform all
verification on that same descriptor before copying. Never invoke a shell and
use constant absolute paths for `dkms`, `modprobe`, and `depmod`.

Define separate Polkit actions for install/update, repair, and remove, all
defaulting to administrator authentication on an active local session. Do not use
`auth_admin_keep`: Polkit documents that cached authorization is keyed only by
action and subject, not request variables, so changed arguments can inherit the
authorization window.[1] Bind actions to the root-owned executable's full path,
not the AppImage's transient mount path.[2]

The helper should emit bounded machine-readable progress and a final state, but
must not accept environment-derived tool paths. `pkexec` already supplies a
minimal safe environment; retain that property rather than enabling GUI
environment forwarding, which its manual discourages.[2]

## Files and lifecycle ownership

The privileged companion, not the AppImage file, owns:

- `/usr/libexec/threshold/threshold-ec-helper`;
- `/usr/share/polkit-1/actions/com.bongbetic.threshold.ec.policy`;
- `/usr/src/msi-ec-<version>/` and DKMS registration;
- `/usr/lib/modules-load.d/msi-ec.conf` (or the host's canonical vendor path);
- `/var/lib/threshold/ec-state.json`, verified bundle metadata, and bounded logs.

State must record helper protocol, payload version/digest, DKMS status per kernel,
Secure Boot/MOK state, last operation, and whether a reboot is pending. It must
not contain signing private keys or a MOK password.

DKMS supports source under `/usr/src/<module>-<version>` and automatically signs
built modules with its configured key. With Secure Boot, the corresponding public
certificate still has to be known to firmware, and upstream documents the
`mokutil --import` plus reboot enrollment flow.[6] The helper may initiate and
report that workflow, but must model it as **pending reboot**, never claim the
module is usable before post-boot load and sysfs verification.

Because the vendored `dkms.conf` has `AUTOINSTALL="yes"`, kernel updates remain
DKMS-owned after initial registration. The AppImage helper should inspect and
repair DKMS state, not create a competing kernel-update daemon.

## Transaction and rollback rules

1. Detect host support and prerequisites without privilege where possible.
2. Authenticate only when the user presses the explicit enable/update/remove
   control.
3. Verify the bundle before changing installed state; then copy to a fresh,
   root-owned versioned directory.
4. Run DKMS add/build/install and preserve logs. Do not switch the active source
   marker or autoload configuration until the build/install succeeds.
5. If build/install fails, remove only the newly staged DKMS version and restore
   the prior version/state. Never remove an older working module as the first
   step.
6. If signing succeeds but Secure Boot prevents load, commit the install as
   **pending reboot/MOK enrollment**, not failure. After reboot, verify module
   load and `charge_control_end_threshold` before reporting EC-ready.
7. If firmware is unsupported or load fails for another reason, report a precise
   non-ready state and leave the unprivileged application functional.

If a system service is later introduced for progress/cancellation, make it
D-Bus-activated and short-lived. systemd supports `Type=dbus`/`BusName=`, while
its execution controls can make the filesystem read-only except explicitly
allowed DKMS/module/state paths and can hide home directories.[3] Start from
`ProtectSystem=strict`, `ProtectHome=yes`, `PrivateTmp=yes`,
`NoNewPrivileges=yes`, and no network address families, then validate the
minimum exceptions with `systemd-analyze security` and real builds on each
target distribution. Do not apply `DynamicUser=yes`: the operation genuinely
requires controlled root writes and module loading.

## Release acceptance criteria

- The AppImage starts on supported systems without prompting and remains useful
  in vendor-sysfs or notification-only mode.
- EC enablement occurs only after a human selects it and accepts the native
  Polkit prompt.
- The first bootstrap installs a fixed-path, root-owned helper; all subsequent
  privileged operations execute that copy, never a helper from the AppImage.
- Tampered, unsigned, wrong-architecture, downgraded, symlinked, or malformed EC
  bundles are rejected before DKMS runs.
- Replacing/deleting the AppImage neither updates nor removes system state.
  Update and removal are explicit and idempotent.
- KDE Plasma and XFCE authentication-agent flows are tested, plus cancellation,
  no-agent/TTY fallback, wrong-password, and concurrent-operation locking.
- A real Secure Boot install is tested through MOK enrollment, reboot, module
  autoload, sysfs reappearance, and saved-threshold restoration.

## Primary sources

1. [polkit manual: architecture, actions, authentication agents, and authorization caching](https://polkit.pages.freedesktop.org/polkit/polkit.8.html)
2. [`pkexec` manual: safe environment, executable-path actions, and unvalidated arguments](https://polkit.pages.freedesktop.org/polkit/pkexec.1.html)
3. [systemd service and execution manuals](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html), including [sandboxing controls](https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html)
4. [AppImage signature documentation](https://docs.appimage.org/packaging-guide/optional/signatures.html)
5. [AppImage concepts](https://docs.appimage.org/introduction/concepts.html) and [AppImage specification](https://github.com/AppImage/AppImageSpec/blob/master/draft.md)
6. [upstream DKMS README: source layout, module signing, and Secure Boot/MOK](https://github.com/dell/dkms/blob/master/README.md)
7. [PackageKit `InstallFiles` transaction API](https://github.com/PackageKit/PackageKit/blob/main/src/org.freedesktop.PackageKit.Transaction.xml)
8. [`systemd-sysext` manual](https://www.freedesktop.org/software/systemd/man/latest/systemd-sysext.html)
