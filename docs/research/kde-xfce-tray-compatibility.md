# KDE and XFCE tray runtime compatibility

Research for [Research KDE and XFCE tray runtime compatibility](https://github.com/Bongbetic/Threshold/issues/79), captured on 2026-09-02.

## Decision summary

Threshold should keep its single StatusNotifierItem (SNI) plus `com.canonical.dbusmenu` implementation for both Plasma and XFCE. The KDE failure is not a Wayland or Plasma incompatibility: the RPM omits the `Dbusmenu` GObject Introspection runtime, and the application deliberately skips all SNI construction when that import fails.

Supported artifacts need a hard runtime guarantee for `Dbusmenu-0.4.typelib`: the existing Debian dependency is correct; the RPM needs a dependency satisfiable by Fedora's `libdbusmenu` and openSUSE's `typelib-1_0-Dbusmenu-0_4`; the AppImage must bundle the typelib and its `libdbusmenu-glib.so.4` library and set its private `GI_TYPELIB_PATH`. Do not add a second AppIndicator or legacy XEmbed implementation.

Dependency correctness is necessary but not sufficient for safe close-to-tray behavior. Threshold must consider the tray ready only after an SNI host exists and the watcher accepts this item. Until then, closing the window must not hide it. This is the required fallback; a second menu implementation is not required for the supported release matrix.

## Tight reproduction and causal proof

The host was openSUSE Tumbleweed 20260830, Plasma 6.7.4, KDE Wayland. Plasma owned `org.kde.StatusNotifierWatcher`, and `IsStatusNotifierHostRegistered` returned true. Neither `libdbusmenu-glib4` nor `typelib-1_0-Dbusmenu-0_4` was installed.

The minimal red signal was:

```console
$ python3 - <<'PY'
import gi
gi.require_version('Dbusmenu', '0.4')
from gi.repository import Dbusmenu
print('Dbusmenu 0.4 import: PASS')
PY
Traceback (most recent call last):
  ...
ValueError: Namespace Dbusmenu not available
```

This is the exact gate in `src/threshold/tray.py`: failure sets `HAS_DBUSMENU = False`, and `_setup_tray()` in `src/threshold/carbon_shell.py` returns without creating an SNI. No item can reach Plasma after that return.

For the one-variable green test, the official Tumbleweed `libdbusmenu-glib4` and `typelib-1_0-Dbusmenu-0_4` RPMs were extracted under `/tmp`; only `LD_LIBRARY_PATH` and `GI_TYPELIB_PATH` were changed for the test process. Nothing was installed on the host:

```console
$ GI_TYPELIB_PATH=/tmp/threshold-dbusmenu-runtime/usr/lib64/girepository-1.0 \
  LD_LIBRARY_PATH=/tmp/threshold-dbusmenu-runtime/usr/lib64 \
  PYTHONPATH=src python3 - <<'PY'
import threshold.tray
print(f'Threshold.tray.HAS_DBUSMENU={threshold.tray.HAS_DBUSMENU}')
PY
Threshold.tray.HAS_DBUSMENU=True
```

Instantiating `TrayIcon` with those same paths added the process to Plasma's `RegisteredStatusNotifierItems`. The exported `com.canonical.dbusmenu.GetLayout(0, -1, [])` call returned radio items for 60, 70, 80, 90, and 100 percent, followed by Open Threshold and Quit. This falsifies a Plasma/Wayland transport failure as the current cause and confirms that adding the missing runtime preserves the existing implementation.

The test also exposed a separate safety gap: `_tray is not None` currently means only that local objects were constructed. It does not mean a host exists or registration succeeded, yet `handle_close_request()` uses that value as permission to hide the window.

## Runtime package matrix

| Target | Package containing `Dbusmenu-0.4.typelib` | Library relationship | Threshold action |
|---|---|---|---|
| openSUSE Tumbleweed | `typelib-1_0-Dbusmenu-0_4` | Split package; its generated requirement pulls `libdbusmenu-glib4` | Add an RPM dependency that can select this package. The current RPM has none. |
| Fedora 43 | `libdbusmenu` 16.04.0-30.fc43 | The main package contains both the typelib and `libdbusmenu-glib.so.4` | Add an RPM dependency that can select `libdbusmenu`. |
| Fedora 44 | `libdbusmenu` 16.04.0-31.fc44 | Same layout as Fedora 43 | Same as Fedora 43. |
| Ubuntu 24.04 | `gir1.2-dbusmenu-glib-0.4` | Depends on the matching `libdbusmenu-glib4` | Keep the existing hard dependency in `debian/control`. |
| Debian 13 | `gir1.2-dbusmenu-glib-0.4` | Depends on the matching `libdbusmenu-glib4` | Keep the existing hard dependency in `debian/control`. |
| AppImage | No host package may be assumed | Bundle both the typelib and shared library inside the AppDir | Set AppRun's private `GI_TYPELIB_PATH` and library search path; verify the bundle with the same import probe. |

The package names and file ownership come from the distribution-owned sources: the [openSUSE Factory spec](https://build.opensuse.org/public/source/openSUSE:Factory/libdbusmenu/libdbusmenu.spec) defines the dedicated typelib package; the [Fedora source spec](https://src.fedoraproject.org/rpms/libdbusmenu/raw/rawhide/f/libdbusmenu.spec) places `Dbusmenu-0.4.typelib` in `libdbusmenu`; and the [Ubuntu 24.04](https://packages.ubuntu.com/noble/gir1.2-dbusmenu-glib-0.4) and [Debian 13](https://packages.debian.org/trixie/gir1.2-dbusmenu-glib-0.4) package records identify their GI packages and library dependencies. Fedora's official package index confirms availability in [Fedora 43 and 44](https://packages.fedoraproject.org/pkgs/libdbusmenu/libdbusmenu/).

The unified RPM design ticket should choose one of two mechanically verifiable expressions: a Boolean dependency such as `(libdbusmenu or typelib-1_0-Dbusmenu-0_4)`, or a dependency on the x86-64 typelib file owned by both distributions. Do not name only `libdbusmenu`: that succeeds on Fedora but does not install openSUSE's split typelib. The artifact's install test must prove resolution with both `dnf` and `zypper` rather than assuming the expression is portable.

AppImage explicitly requires bundling: AppImage's own [runtime dependency guidance](https://docs.appimage.org/introduction/concepts.html) says resources not reasonably present on every supported target must be included. Its GTK bundling example also demonstrates setting [`GI_TYPELIB_PATH` inside AppRun](https://github.com/AppImage/AppImageKit/wiki/Bundling-GTK3-apps).

## Compatibility and fallback contract

SNI is the correct common protocol. The freedesktop [StatusNotifierItem specification](https://specifications.freedesktop.org/status-notifier-item/latest-single/) defines watcher registration, icon and tooltip properties, activation methods, and the `Menu` object path to a `com.canonical.dbusmenu` object. XFCE documents that its [status tray supports status notifier items](https://docs.xfce.org/panel-plugins/xfce4-statusnotifier-plugin/start), with the functionality integrated into `xfce4-panel` since 4.15. Plasma on the live host exposes the same watcher contract.

Commit to these behaviors:

1. Importing `Dbusmenu 0.4` is a build/install acceptance gate for every supported artifact, not an optional enhancement.
2. `TrayIcon` has explicit states: `unavailable` (no watcher/host), `registering`, `ready` (registration succeeded and the item is listed), and `lost` (watcher disappeared). Merely constructing the object is not readiness.
3. Close-to-tray hides the window only in `ready`. In every other state, the application keeps the window available and explains that the notification-area host is unavailable. A later watcher appearance re-registers the item; watcher loss revokes readiness immediately.
4. Keep the current dbusmenu tree and actions. Do not silently downgrade to an icon with a dead right-click menu, and do not add AppIndicator/XEmbed. A missing typelib in a supported package is a packaging defect; a missing desktop host is a safe-degradation condition.
5. Keep desktop notifications independent from tray readiness. `org.freedesktop.Notifications` and SNI serve different purposes; losing a tray host must not disable threshold alarms.
6. Align the SNI surface with the protocol while implementing the fix: expose `ContextMenu`, acknowledge every method call, retain the valid `Menu` object, and only advertise `Status = Active` while the item is usable.

## Protocol-level release verification

Add one unattended probe that runs against the installed artifact in the real desktop session. Run the same probe on openSUSE Tumbleweed KDE Plasma Wayland and XFCE, Fedora 43/44 KDE and XFCE, Ubuntu 24.04 KDE and XFCE, and Debian 13 KDE and XFCE.

The probe must fail unless all of the following pass:

1. `gi.require_version('Dbusmenu', '0.4')` imports from the installed artifact's runtime environment.
2. `org.kde.StatusNotifierWatcher` exists, `IsStatusNotifierHostRegistered` is true, and the watcher adds Threshold to `RegisteredStatusNotifierItems` within a bounded timeout.
3. D-Bus introspection on the registered item exposes `org.kde.StatusNotifierItem`; `Title`, `Status`, `IconName`, `ToolTip`, and `Menu` return valid values; the advertised icon resolves in the target desktop theme.
4. `com.canonical.dbusmenu.GetLayout(0, -1, [])` returns all threshold presets plus Open Threshold and Quit. Sending an `Event(..., "clicked", ...)` to a preset reaches Threshold's command boundary and updates the checked radio state.
5. Calling `Activate(0, 0)` presents the existing window. A real left click does the same; a real right click opens the exported menu; Quit unregisters the item without leaving a ghost entry.
6. Closing the window while the item is `ready` hides it and it is recoverable from the tray. Stopping/removing the panel host first makes close-to-tray refuse to hide. Restarting the panel causes automatic re-registration without restarting Threshold.
7. A fresh DEB/RPM install on a machine without the distro's dbusmenu package pulls the correct dependency. Removing that dependency is refused by the package manager. The AppImage passes the import and protocol probes with the host package absent.
8. A notification-only threshold alarm still reaches `org.freedesktop.Notifications` with the tray host present and absent.

Use D-Bus properties and method calls as the automated assertions, then retain one short visual check per desktop for actual icon painting, tooltip, left click, and menu placement. The protocol checks localize failures; the visual check catches panel/theme behavior that D-Bus cannot prove.

## What this resolves

The immediate KDE defect is resolved at the specification level by making the Dbusmenu runtime mandatory in DEB/RPM and bundled in AppImage. The safe fallback is host-readiness gating for close-to-tray, not a second tray technology. This preserves XFCE behavior, makes Plasma Wayland use the already-working SNI path, and gives the release gate a deterministic way to prove both.
