# DankMaterialShell appearance and native Wayland contract

Research for [Research DankMaterialShell appearance and native Wayland window contracts](https://github.com/Bongbetic/Threshold/issues/105), 2026-09-29. Threshold source inspected at `5348921`; no application or session configuration was changed and no runtime compatibility test was performed.

## Conclusion

Keep the dashboard layout, introduce an explicit system appearance mode with a validated DMS palette bridge, repair the StatusNotifierItem wire contract, and use GTK4 native window interactions. Make dashboard contents adapt to the compositor's allocation. Documentation establishes the APIs; native Wayland/DMS compatibility remains a release acceptance exercise.

## Repository evidence

- [Application](../../src/threshold/application.py) uses `Adw.Application` with `com.bongbetic.threshold`; [desktop entry](../../data/com.bongbetic.threshold.desktop) uses the matching icon name. Keep this identity stable.
- [Carbon shell](../../src/threshold/carbon_shell.py) embeds WebKitGTK 6.0, loads the web bundle, and requests a minimum of 960×700. [Commands](../../src/threshold/commands.py) calls `self._window.begin_move_drag(1, -1, -1, -1)`.
- [State](../../src/threshold/state.py) currently returns dark only when `dark_mode` is true; false explicitly returns light. [CONTEXT](../../CONTEXT.md) instead describes false as following the system. Resolve this inconsistency while adding automatic appearance; do not silently treat an existing explicit light preference as automatic.
- [Adapter](../../src/threshold/adapter.py) only probes GNOME appearance settings. Its missing-schema guard is valuable and should remain as a fallback.
- [Tray](../../src/threshold/tray.py) already watches the watcher owner and asynchronously re-registers with generation checks. It does not check whether a notification-area host is registered. It also declares the wrong tooltip signature and writes pixmap channels in the wrong order; details below.

## Palette and scheme

DMS documents generation of `~/.config/gtk-4.0/dank-colors.css` whenever Matugen is enabled, including when its GTK application toggle is off. The toggle controls applying the generated files. Wallpaper and theme changes regenerate application themes. Custom Matugen templates are supported but would add user configuration, so reading the existing GTK output is the smallest initial integration. [DMS application theming](https://danklinux.com/docs/dankmaterialshell/application-themes)

At DMS revision `33bc0a0dff319a9483fa40a367108ef1cfab01f0`, the GTK template exposes concrete semantic pairs: `window_bg_color`/`window_fg_color`, `card_bg_color`/`card_fg_color`, `accent_bg_color`/`accent_fg_color`, and `error_bg_color`/`error_fg_color`. Some values are aliases to another defined color. The light template differs and has fewer roles; never assume every role exists. [GTK template](https://github.com/AvengeMedia/DankMaterialShell/blob/33bc0a0dff319a9483fa40a367108ef1cfab01f0/quickshell/matugen/templates/gtk-colors.css), [light template](https://github.com/AvengeMedia/DankMaterialShell/blob/33bc0a0dff319a9483fa40a367108ef1cfab01f0/quickshell/matugen/templates/gtk-light-colors.css)

Implementation recommendation: add a small Python appearance adapter that reads this generated output, maps an allowlist of semantic colors into the existing web theme tokens, and sends only validated color data through the current JSON bridge. The dashboard is an HTML document, so GTK CSS alone does not theme it; this follows directly from the repository's separate WebKit content and CSS tokens.

Parsing policy: bound file size; accept hex colors and bounded, cycle-checked references among allowlisted `@define-color` entries; reject other CSS expressions. Do not import arbitrary CSS, execute a generator, or interpolate file contents into JavaScript. Validate an entire usable foreground/background palette before applying it atomically. Keep existing fallback tokens for missing roles. Read the XDG configuration location, with the documented home location as the conventional default. Merely finding an old DMS file must not override a user's explicit application preference.

For live reload, monitor the containing directory and filter changes for the color file so rename-based replacements are seen. Debounce reads; retain the previous valid palette during partial writes, then fall back after a bounded retry or removal. Handle a missing directory at startup, monitor setup failure, and cancellation at application shutdown. These are recommended application behaviors; `Gio.File.monitor_directory` provides a directory monitor but can fail. [GIO directory monitoring](https://docs.gtk.org/gio/method.File.monitor_directory.html)

The standardized portal exposes `org.freedesktop.appearance` `color-scheme`: 0 is no preference, 1 dark, 2 light; unknown values mean no preference. Its optional accent tuple contains sRGB channels in [0,1]. `ReadAll` and `SettingChanged` allow initialization and live updates across older portal implementations; `ReadOne` is version 2 and must not be assumed everywhere. [Settings portal](https://flatpak.github.io/xdg-desktop-portal/docs/doc-org.freedesktop.portal.Settings.html)

Recommended precedence: explicit app light/dark and custom appearance remain overrides; automatic mode reads the portal scheme first, guarded GNOME/GTK settings second, and a documented light fallback last. In automatic mode use a valid DMS palette when it agrees with the resolved scheme; if the portal has no preference, the palette's background luminance can be a documented inference. Avoid applying a light palette while forcing dark. Use the current bundled palette when external colors are unavailable. An explicit three-way System/Light/Dark setting avoids the existing boolean ambiguity; the implementation ticket must record its migration policy. DMS palette colors should take precedence over preset accent only in system appearance mode, with the saved preset retained for manual mode.

## Icons and StatusNotifierItem

DMS respects the icon theme selected through Qt's platform integration or `QS_ICON_THEME`; it does not require a particular theme. Its notification-area widget can tint icons itself. Therefore publish theme icon names and ship a complete hicolor fallback; avoid forcing Papirus or modifying desktop theme settings. Use symbolic application/status artwork where appropriate, and recolorable `currentColor` SVGs inside the HTML document. GTK icon theme selection cannot automatically replace inline HTML SVGs. [DMS icon theming](https://danklinux.com/docs/dankmaterialshell/icon-theming), [DMS icon rendering](https://github.com/AvengeMedia/DankMaterialShell/blob/33bc0a0dff319a9483fa40a367108ef1cfab01f0/quickshell/Modules/DankBar/Widgets/TrayItemIcon.qml)

The KDE interface source confirms three concrete mismatches:

| Contract | Existing Threshold | Required correction |
| --- | --- | --- |
| `ToolTip` is `(sa(iiay)ss)` | `(sa(iiay)sbs)`, five fields and a string supplied for the boolean slot | Export four fields: icon name, pixmaps, title, body |
| `NewStatus` contains a string argument | Signal has no argument | Match the interface and emit the current status when it changes |
| Icon pixmaps are ARGB32 in network byte order | Filled pixels serialized as B,G,R,A | Serialize A,R,G,B and retain transparent pixels |

The signature discrepancies are confirmed by the [KDE SNI interface](https://github.com/KDE/kstatusnotifieritem/blob/538db5224873a719c4ba50eb3d32367de1e54fbd/src/org.kde.StatusNotifierItem.xml). Byte order follows [KDE's reference image conversion](https://github.com/KDE/kstatusnotifieritem/blob/538db5224873a719c4ba50eb3d32367de1e54fbd/src/kstatusnotifieritem.cpp#L1209). Runtime consequences have not been exercised here.

Do not assume an advertised pixmap automatically rescues a missing named icon in every host. Quickshell's current item implementation selects a nonempty name before pixmap rendering. Ship resolvable names and explicitly test fallback paths. [Quickshell SNI implementation](https://github.com/quickshell-mirror/quickshell/blob/master/src/services/status_notifier/item.cpp)

Preserve asynchronous registration and generation checks. Strengthen notification-area readiness to require both successful item registration and a live host; track `IsStatusNotifierHostRegistered` and host registration/unregistration signals. A watcher existing alone is insufficient evidence that the user can retrieve a hidden window. Revoke readiness on either host or watcher loss, re-register after owner changes, and ignore stale replies. Decide how an already hidden window becomes reachable when the host disappears; showing it again is the conservative recommendation. [Watcher interface](https://github.com/KDE/kstatusnotifieritem/blob/538db5224873a719c4ba50eb3d32367de1e54fbd/src/org.kde.StatusNotifierWatcher.xml)

## Native Wayland, niri and activation

GTK4 removed `gtk_window_begin_move_drag`; Threshold's current call is invalid for its toolkit. Prefer a native `Gtk.WindowHandle` for a dedicated titlebar region, since it already implements dragging and titlebar gestures. If retaining a web titlebar, capture real GTK input and call `Gdk.Toplevel.begin_move` on the native surface with the initiating device, button, surface coordinates and event time. The asynchronous web command's invented `-1` values are not a substitute for an input event. Do not wrap interactive dashboard contents in an unrestricted drag handle. [GTK4 migration](https://docs.gtk.org/gtk4/migrating-3to4.html), [WindowHandle](https://docs.gtk.org/gtk4/class.WindowHandle.html), [begin_move](https://docs.gtk.org/gdk4/method.Toplevel.begin_move.html)

GTK's Wayland backend is native; `GDK_BACKEND=wayland` is useful for acceptance testing, not a launcher requirement that should disable X11 fallback. Retain the stable app ID and confirm the actual surface ID in niri. [GTK Wayland support](https://docs.gtk.org/gtk4/wayland.html), [niri window identification and rules](https://niri-wm.github.io/niri/Configuration%3A-Window-Rules.html)

Remove the 960×700 hard minimum after responsive content is implemented. Keep a comfortable default size, but use only the smallest demonstrated usable minimum. GTK explicitly distinguishes a default size from a forced minimum and warns against fixed dimensions across fonts and themes. Honor compositor allocations through wrapping, grid stacking and vertical scrolling; no application-generated niri rules should be necessary. [GTK size requests](https://docs.gtk.org/gtk4/method.Widget.set_size_request.html)

`Gtk.Window.present()` makes hidden windows visible, but focusing and placement depend on the window manager. Wayland activation is token based and the compositor may reject a token. KDE's SNI extension includes `ProvideXdgActivationToken`; current Quickshell `activate()` source inspected here directly invokes `Activate(0,0)` without obtaining a token. Do not claim guaranteed focus transfer from DMS. Support tokens when provided, apply the startup ID before presentation, and verify DMS activation in the actual release session. [GTK present](https://docs.gtk.org/gtk4/method.Window.present.html), [GTK startup ID](https://docs.gtk.org/gtk4/method.Window.set_startup_id.html), [Wayland protocol source](https://gitlab.freedesktop.org/wayland/wayland-protocols/-/blob/main/staging/xdg-activation/xdg-activation-v1.xml), [Quickshell activation](https://github.com/quickshell-mirror/quickshell/blob/master/src/services/status_notifier/item.cpp#L221)

niri documents GTK portal integration as part of desktop setup. Threshold must degrade cleanly if a portal is absent and must not install session-specific portal overrides. [niri required desktop components](https://github.com/niri-wm/niri/blob/main/docs/wiki/Important-Software.md)

## Bounded acceptance for the implementation/release ticket

1. Record actual GTK, WebKitGTK, DMS, niri, portal and icon-theme versions. Launch with native Wayland forced and verify the reported surface app ID and absence of XWayland dependence.
2. At the normal initial size, all final-row text is fully visible. Also inspect 960×700, 640×600, and 480×600 logical allocations; 100%, 125%, 150%, and 200% scaling; long device strings; enlarged text; all control modes and EC messages. Smaller allocations may scroll vertically; no label overlap or unreachable controls is acceptable. These sizes are a proposed bounded matrix, not established support.
3. Change DMS wallpaper and light/dark mode while Threshold is open. Verify palette propagation, contrast and SVG colors, plus explicit app overrides. Exercise absent, removed, malformed and atomically replaced palette files and portal restart. Verify fallback without GNOME schemas or DMS.
4. Verify the notification-area icon in the configured theme and with bundled fallback; inspect tooltip, menu presets, opening and closing. Restart the watcher and DMS separately; host loss must not strand an inaccessible window. Check D-Bus signatures and channel order directly.
5. Tile, resize, float, drag the titlebar, maximize/unmaximize where supported, switch workspace and reopen from DMS. Sliders and buttons must not start a move. Record compositor-controlled behavior rather than assuming identical geometry/focus on every compositor.
6. Repeat a focused smoke check on one other Wayland tiling compositor and an X11 session. Report tested combinations only; broader seamless compatibility remains an aspiration until measured.

## Research provenance and remaining decisions

Context7 was resolved before querying GTK (`/gnome/gtk`), DMS (`/websites/danklinux`), and the portal (`/flatpak/xdg-desktop-portal`). GTK and DMS returned relevant current material. The portal docs query returned no matching snippets; the official portal API page supplied the contract instead. No quota failure occurred. Freedesktop wiki SNI pages were unavailable; KDE's maintained interface XML and implementation supplied the primary wire-contract evidence.

The existing implementation ticket can settle the remaining product choices: System/Light/Dark migration and accent override semantics; dedicated native titlebar versus native event handling for the current web header; and the minimum usable dimensions demonstrated by the clipping fix. No additional map ticket is necessary for the confirmed defects. Live compositor rendering, activation behavior, and package integration have not been verified by this research.
