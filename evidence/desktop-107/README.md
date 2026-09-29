# DMS appearance and Wayland verification

Work for [Implement and verify DMS appearance and Wayland tiling behavior](https://github.com/Bongbetic/Threshold/issues/107), 2026-09-29. This is desktop implementation evidence, not immutable release-candidate or physical EC acceptance.

## Implemented contract

- Theme now offers System, Light, and Dark. Untouched installations select System. A persisted legacy `dark-mode` boolean preserves explicit Light or Dark, including persisted false. The legacy value remains available for rollback. Selecting System does not erase the saved accent preset.
- System uses the appearance portal's light/dark preference first, then a valid DMS palette's inferred scheme, then the existing guarded GNOME/light fallback. Explicit Light/Dark exclude desktop palette overrides. A palette conflicting with the portal's scheme is excluded.
- DMS's XDG `gtk-4.0/dank-colors.css` is treated as bounded data, never executable CSS. Only allowed hex colors and cycle-checked role aliases are accepted. Foreground/background and accent contrast must meet 4.5:1. Missing card roles use window roles. Invalid palettes are rejected atomically.
- A one-second GLib timer observes replacement, late directory creation, and removal. One failed read retains the previous palette; the second clears it. This deliberately uses bounded polling instead of directory monitoring, avoiding separate parent-directory monitors and debounce/retry machinery. Idle cost is one bounded palette read per second. Portal initialization, changes, and owner changes use asynchronous D-Bus calls; shutdown cancels pending calls and disconnects listeners.
- Notification-area icons prefer the GTK-selected theme's standard symbolic/battery names and retain shipped namespaced fallback artwork. Inline web artwork continues to inherit its surrounding text color. SNI tooltip and status signatures now match the protocol, and pixmaps serialize alpha/red/green/blue in network order.
- A successful watcher registration alone no longer permits hiding: a live host must also be reported. Host or watcher loss restores an already hidden window. Owner/revision checks reject stale host replies. Activation tokens are accepted when provided.
- A native GTK header bar owns titlebar gestures and window controls; the web header's duplicate controls are hidden only inside the native application. Legacy asynchronous `begin_drag` requests report `dragging: false` and never call GTK3's removed method.

## Verification

- Focused Python suite: 200 passed, eight install checks initially skipped because Meson was not on PATH. With the configured build and PATH supplied, all 44 install-layout checks passed, including those eight.
- Repository Python lint: `flake8 src/threshold tests` passed.
- Web: TypeScript/Vite production build, ESLint, and all 114 Vitest tests passed. Existing build warnings about large chunks and font URLs remain; install/bundle checks verify the font payload.
- All 11 browser layout cases passed, including 480×400, long content, and 125%/150% text sizes: no horizontal overflow, overlapping rows, or unreachable final content.
- Private D-Bus integration passed with both a live host and a watcher without a host. It exercises actual exported tooltip properties, watcher loss/re-registration, and cleanup. Additional regression tests cover hidden-window recovery, ARGB byte order, palette validation/replacement/removal, scheme precedence, and real GSettings migration.
- X11 WebKitGTK handshake passed under Xvfb. Void provides Xvfb without the `xvfb-run` script, so a temporary wrapper used Xvfb's `-displayfd` and forced `GDK_BACKEND=x11` for the existing smoke test.
- Meson compiled and installed the application into a temporary DESTDIR. The actual `ThresholdApplication` and its web bundle were imported from that staged installation, using an isolated configuration directory and memory GSettings backend. No Threshold package was installed and no charge-threshold/EC command was invoked.

## Native niri/DMS observations

[Native probe results](native-result.json) record the staged application under forced `GDK_BACKEND=wayland`:

- GTK 4.22.4, WebKitGTK 2.50.4, libadwaita 1.9.1, niri 26.04, DMS 1.6.2, Quickshell 0.3.1, portal frontend 1.22.1.
- Backend/surface: `GdkWaylandDisplay` / `GdkWaylandToplevel`. Compositor app ID: `com.bongbetic.threshold`.
- Actual tiled allocations: 954×1028, 640×1028, and 480×1028. Web document width equals allocated width; no horizontal overflow at these sizes.
- DMS dark palette appears as `rgb(20, 18, 24)` with accent `#d0bcff`. Explicit Light switches to the bundled light palette and saved orange accent. Replacing the isolated palette propagates accent `#aaffcc`; removal restores bundled tokens after bounded retry.
- The live DMS watcher reports readiness `ready`. The selected icon resolves to `battery-good-symbolic`.
- Close hides the window; a real D-Bus SNI `Activate` restores it. Reopening receives a fresh compositor window ID and its default tile width. Focus is not guaranteed: niri leaves focus with the user's existing window.

The host initially lacked WebKitGTK and GTK development dependencies. Verification installed 19 runtime/build dependency packages and two Xvfb/Xauth packages through XBPS. No existing packages were upgraded or removed. Meson reported WebKit's development pkg-config file absent (the runtime typelib works); this application does not compile against WebKit. Missing gettext skipped translation compilation in this local verification build.

## Remaining release acceptance

The release task still owns immutable XBPS construction, real package installation/lifecycle tests, and physical EC evidence. Also retain these desktop limits in its acceptance record:

- Full DMS process restart, wallpaper-driven palette generation, portal restart, interactive notification-area menu/preset use, native pointer dragging, and activation-token focus transfer were not tested live. Watcher recovery and host absence/loss are covered by private-bus/regression tests.
- Native compositor scaling at 125%, 150%, and 200%, and a second Wayland compositor remain untested. Browser enlarged-text checks and an X11 WebKit smoke test do not establish those combinations.
- The palette probe changed only an isolated copy of DMS's generated file; the user's wallpaper and desktop preferences remained unchanged.
- The preserved application identity and staged install are verified; they do not establish package or release support.
