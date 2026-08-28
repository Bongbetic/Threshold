# Tray + Notifications: Can the Web Layer Drive Them?

**Research ticket**: [#39](https://github.com/Bongbetic/Threshold/issues/39) (part of wayfinder map [#34](https://github.com/Bongbetic/Threshold/issues/34))

**Sources**: [WebKitGTK WebKitNotification](https://webkitgtk.org/reference/webkit2gtk/stable/class.Notification.html), [WebKitGTK NotificationPermissionRequest](https://webkitgtk.org/reference/webkit2gtk/stable/class.NotificationPermissionRequest.html), [WebKitGTK WebView::show-notification](https://webkitgtk.org/reference/webkit2gtk/stable/signal.WebView.show-notification.html), [WebKitGTK UserContentManager](https://webkitgtk.org/reference/webkit2gtk/stable/class.UserContentManager.html), [StatusNotifierItem spec (freedesktop.org)](https://www.freedesktop.org/wiki/Specifications/StatusNotifierItem/), [org.freedesktop.Notifications spec](https://specifications.freedesktop.org/notification/latest/), [Debian: libwebkit2gtk-4.1-0 dependencies](https://packages.debian.org/sid/libwebkit2gtk-4.1-0), [Epiphany source (GNOME GitLab)](https://gitlab.gnome.org/GNOME/epiphany), [tauri-apps/tray-icon](https://github.com/tauri-apps/tray-icon), [tauri-apps/plugins-workspace notification plugin](https://github.com/tauri-apps/plugins-workspace), [GNOME Shell AppIndicator extension](https://extensions.gnome.org/extension/615/appindicator-support-kstatusnotifieritemappindicator/), Threshold's own `src/threshold/tray.py` and `debian/control`

---

## Question

Can the tray menu and notifications be driven from the web layer (StatusNotifierItem D-Bus from JS, a libnotify bridge), or must they stay native (GTK/libnotify) with Carbon visual language applied to copy and icons? What do comparable WebKitGTK apps do? Recommend an approach per surface.

## TL;DR

| Surface | Recommendation | Why |
| --- | --- | --- |
| Tray menu + icon | **Stay native** — keep `tray.py` (SNI over Gio.DBusConnection + dbusmenu) | JS in a WebKitGTK WebView has **no D-Bus access at all**; the host shell, not the app, renders tray icon and menu pixels, so driving SNI from JS adds a bridge for zero visual control. |
| Notifications | **Stay native** — keep `Notify` (libnotify) calls in Python | Even the "web-driven" path (Web Notifications API) terminates in WebKitGTK's own default handler, which "will emit a notification using libnotify". The web layer never reaches the notification daemon directly. |
| Carbon application | Copy (labels, titles, bodies) + icon names only | Both surfaces are rendered by the desktop environment (tray host, notification daemon). Carbon cannot style their chrome regardless of which layer emits. |

## Findings

### 1. The web layer has no D-Bus access in WebKitGTK

The WebKitGTK API surface exposes **no D-Bus (or raw socket) capability to web content**. The only channels between JS in the WebView and the embedding process are the bridges the host app builds itself:

- `webkit_user_content_manager_register_script_message_handler()` + the `script-message-received` signal on `WebKitUserContentManager` (since 2.6), and `register_script_message_handler_with_reply` for round-trips.
- `WebKitWebView` user messages (`user-message-received`, since 2.38).

So "SNI D-Bus from JS" cannot exist as stated: JavaScript cannot own `org.kde.StatusNotifierItem` or `com.canonical.dbusmenu` objects. Any web-driven tray would still require the Python side to implement the D-Bus objects and proxy every property/signal/activation through a script-message bridge — exactly the code `src/threshold/tray.py` already is, plus a marshalling layer.

### 2. Tray: the host shell renders everything; the app only supplies data

The StatusNotifierItem spec is deliberately model-view: it "does not define what the aspect of the Notification Items will be, this is strictly implementation specific", and aims to give "more freedom to the workspace how to graphically represent the items coherent to its visual style language". In practice the tray host (KDE Plasma, XFCE, MATE, Budgie, GNOME + AppIndicator/KStatusNotifierItem extension) draws the icon, tooltip, and — via the `com.canonical.dbusmenu` tree the app exports — the menu itself, in the host's own toolkit and style.

Consequences:

- **No layer choice buys visual control.** Whether Python or JS "drives" the tray, the pixels belong to the tray host. Carbon styling of the tray menu is impossible *by design*; Carbon can only influence the copy (`"Open Threshold"`, `"80%"`, `"Quit"`) and the icon name/theme path.
- **GNOME needs an extension regardless.** Vanilla GNOME Shell has no StatusNotifierWatcher; the community AppIndicator/KStatusNotifierItem extension supplies it. That fact is orthogonal to the web-vs-native question.
- Threshold's existing implementation is already optimal: a self-contained SNI over `Gio.DBusConnection` with a `Dbusmenu.Server` (`src/threshold/tray.py`), with no widget code to migrate when the window swaps to WebKitGTK. Nothing in the redesign touches it.

### 3. Notifications: even the web path ends in libnotify

WebKitGTK *does* implement the Web Notifications API, but only as a marshalling layer:

- A page calling `new Notification(...)` first triggers a `WebKitNotificationPermissionRequest` (since 2.8); unhandled requests are **denied by default**, so the shell must actively grant permission.
- When a notification is shown, `WebKitWebView::show-notification` fires with a `WebKitNotification` (title/body/tag + `clicked`/`closed` signals). Per the API reference: *"The default handler will emit a notification using libnotify, if built with support for it."*
- Distro builds do have that support: Debian's `libwebkit2gtk-4.1-0` package declares a runtime dependency on `libnotify4`.

So a web-driven notification is: JS → WebKit notification manager → the embedding app (or WebKit's default handler) → libnotify → `org.freedesktop.Notifications` on the session bus. The spec's urgency levels, body text, and icon are all the app controls; layout, animation, and placement belong to the notification daemon. Driving notifications from the web layer therefore changes *who says the words*, not *who renders them* — and the words (title/body) are the only Carbon-relevant part in either case.

There is also an ownership argument: Threshold's notifications are mostly **backend events** — the notify-only-mode charge alarm, apply success/failure, mode-detection messages in `src/threshold/window.py`'s `Notify` calls. They originate from the Python monitor, not from UI interaction, so wiring them through the WebView would couple system alarms to the UI process lifetime for no gain. A small `notify(title, body, urgency)` script-message bridge is a reasonable *optional* addition later, only if the web UI itself ever needs to raise toasts; it would still call the same `Notify` code.

### 4. What comparable WebKitGTK apps do

- **GNOME Web (Epiphany)** — the reference WebKitGTK embedding. Its `meson.build` (GTK4 era) depends on `webkitgtk-6.0` and notably does *not* depend on libnotify itself. In `src/ephy-shell.c` it connects to `show-notification`, uses the signal only to hook `clicked` → focus the right tab, and returns `FALSE` — i.e. it deliberately lets WebKitGTK's **default libnotify handler** display web notifications. The shell marshals; it does not reimplement.
- **Tauri apps on Linux** — the largest ecosystem of "web UI in a native shell" using WebKitGTK (`webkit2gtk`/`webkitgtk-6.0`): both surfaces are native-side. The tray comes from the Rust `tray-icon` crate, whose `Cargo.toml` gates its GTK feature on `libappindicator` (the StatusNotifierItem bridge); notifications come from `tauri-plugin-notification`, whose Linux target dependency is `notify-rust` (a direct `org.freedesktop.Notifications` D-Bus client). JS only invokes a command; it never touches D-Bus.
- **Threshold today** — `debian/control` already ships `gir1.2-notify-0.7`; `tray.py` already implements SNI + dbusmenu without any widget dependency.

No surveyed WebKitGTK application drives SNI or the notification daemon from JavaScript; the pattern is *native surface, web content*.

## Recommendation

1. **Tray: keep native.** Keep `src/threshold/tray.py` (SNI + dbusmenu) unchanged in the redesign. Apply Carbon to the menu copy and to the exported icon names/theme path only; the tray host's rendering is out of the app's hands by spec.
2. **Notifications: keep native.** Keep `Notify` (libnotify) calls in Python where the events originate (battery monitor, apply results). Do not adopt the Web Notifications API — it adds a permission dance and a WebView dependency to reach the same libnotify endpoint with less control (no urgency mapping beyond what `WebKitNotification` exposes).
3. **Bridge: none required for these surfaces.** The script-message bridge exists for window-bound UI concerns (settings, threshold read/write). An optional `notify()` bridge method may be added later if the web UI itself needs to raise notifications, implemented as a thin wrapper over the existing `Notify` path.

## References

- WebKitGTK 4.1 reference: [WebKitNotification](https://webkitgtk.org/reference/webkit2gtk/stable/class.Notification.html) (since 2.8), [NotificationPermissionRequest](https://webkitgtk.org/reference/webkit2gtk/stable/class.NotificationPermissionRequest.html) ("denied by default"), [WebView::show-notification](https://webkitgtk.org/reference/webkit2gtk/stable/signal.WebView.show-notification.html) ("default handler will emit a notification using libnotify, if built with support for it"), [UserContentManager](https://webkitgtk.org/reference/webkit2gtk/stable/class.UserContentManager.html) (script message handlers)
- [StatusNotifierItem specification](https://www.freedesktop.org/wiki/Specifications/StatusNotifierItem/) — "does not define what the aspect of the Notification Items will be, this is strictly implementation specific"
- [org.freedesktop.Notifications specification](https://specifications.freedesktop.org/notification/latest/)
- [Debian package: libwebkit2gtk-4.1-0](https://packages.debian.org/sid/libwebkit2gtk-4.1-0) — Depends: libnotify4
- Epiphany source: [meson.build](https://gitlab.gnome.org/GNOME/epiphany/-/blob/main/meson.build) (no libnotify dep; `webkitgtk-6.0`), [ephy-shell.c](https://gitlab.gnome.org/GNOME/epiphany/-/blob/main/src/ephy-shell.c) (`show-notification` handler returns FALSE)
- Tauri: [tray-icon Cargo.toml](https://github.com/tauri-apps/tray-icon/blob/dev/Cargo.toml) (`libappindicator` behind the `gtk` feature), [plugins-workspace notification Cargo.toml](https://github.com/tauri-apps/plugins-workspace/blob/v2/plugins/notification/Cargo.toml) (`notify-rust` on Linux)
- [GNOME Shell extension: AppIndicator and KStatusNotifierItem Support](https://extensions.gnome.org/extension/615/appindicator-support-kstatusnotifieritemappindicator/)
- Threshold in-tree: `src/threshold/tray.py`, `src/threshold/window.py` (`Notify` usage), `debian/control` (`gir1.2-notify-0.7`)
