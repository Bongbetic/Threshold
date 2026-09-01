# ADR: Carbon Web UI Architecture

**Status:** Accepted
**Date:** 2025-08-31
**Part of:** [Wayfinder: Carbon web UI redesign](https://github.com/Bongbetic/Threshold/issues/34)
**Supersedes:** none (first architecture ADR for the web layer)

## Context

Threshold's UI is being rebuilt as an IBM Carbon Design System web UI (`@carbon/web-components`) hosted in a WebKitGTK WebView inside the existing Python/GTK shell. The Python backend (sysfs/EC IO, mode detection, GSettings) is unchanged; only the presentation layer swaps. This ADR locks the web-layer architecture so implementation can begin.

**Decisions recorded here** were resolved across nine wayfinder tickets (#36–#42, #54, #55), each holding the full detail and evidence. This ADR is the single place where they compose into a coherent architecture; it links, never restates.

### Reference documents

- `CONTEXT.md` — domain glossary, appearance terminology
- `docs/research/carbon-component-inventory.md` — full component mapping (F1–F8 sub-decisions)
- `docs/research/webkitgtk-python-bridge.md` — bridge research findings
- `docs/research/carbon-meson-buildchain.md` — build chain research findings
- `docs/research/tray-notifications-web-layer.md` — tray/notification research findings
- `prototype/carbon-ui-layout` — throwaway layout prototype (branch, will not merge)

## Decision

### 1. Layout: Industrial grid, scroll-free

One-screen control panel at target size (`~1180×860`, usable floor `960×700`). No page scroll at the floor. Resolved in [#36](https://github.com/Bongbetic/Threshold/issues/36).

Layout regions: header → top status grid (3 columns) → dominant charge limit panel → lower settings grid (3 columns) → footer device bar. CSS grid fills available space. Existing geometry-save logic carries over.

### 2. Window chrome: full web, no GTK HeaderBar

`decorated: false` on GtkWindow. The Carbon header is the sole header — no native CSD title bar.

- **Window controls:** minimize, maximize/restore, close as `cds-button` components in the header trailing edge, routed through the bridge to Python (`self.minimize()`, `self.maximize()`/`self.unmaximize()`, `_on_close_request`).
- **Title + live percentage:** header shows `"Threshold — {pct}%"`, updated live over the bridge.
- **Nav:** region focus anchors (Overview / Threshold / Settings / About). Active = orange underline. About opens a `cds-modal`. One-screen contract preserved — nav moves keyboard focus, not pages.
- **Menu button:** dropped for v1 (nothing to open in a one-screen design).
- **Drag:** JS mousedown on header drag zone → bridge `window.begin-drag` → Python `self.begin_move_drag()`. Double-click on drag zone → toggle maximize/restore.
- **Resizable.** Default `~1180×860`, minimum `960×700`, no maximum.

Resolved in [#55](https://github.com/Bongbetic/Threshold/issues/55).

### 3. Bridge: WebKitGTK script message handlers + UserScript shim

- **JS→Python:** script message handlers. One handler receiving JSON-stringified `{id, cmd, args}` requests.
- **Python→JS:** `evaluate_javascript` for pushes (acks + events), with `GLib.idle_add` for thread-safe dispatch.
- **Injected shim:** `~40`-line `UserScript` exposing `window.threshold.request()` (promise-based) and `window.threshold.on()` (event listener).
- **Sidecar rejected** — extra process/port/auth surface with zero added capability.
- **Apply threshold with ack:** `write_threshold` may block `~30s` on pkexec → handler returns fast, write on a `GLib.Thread` worker, ack pushed via `evaluate_javascript` with request-id correlation.
- **Battery polling:** keep the existing Python-owned 5s `GLib.timeout_add_seconds` tick; push `battery` events (single source of truth).
- **GSettings:** existing `Config` `changed::` signals fan out as events; JS writes go through the same setters.
- **Minimum WebKitGTK:** ≥ 2.40 for `evaluate_javascript` + world param. All target distros exceed it.

Resolved in [#37](https://github.com/Bongbetic/Threshold/issues/37).

### 4. Build chain: commit Vite dist to `web/dist`

- **Commit the Vite dist** to `web/dist` (`base:'./'`, self-hosted Plex). Debian Policy forbids network during package builds; the dist must be in the source tree.
- **Meson never runs npm:** `install_subdir('web/dist', install_dir: pkgdatadir/'web')`. A `custom_target` npm wrapper is dev-only (outputs can't own a dist tree).
- **Deb pickup:** one line in `debian/threshold.install` — `usr/share/com.bongbetic.threshold/web`.
- **Font bundling:** self-hosted IBM Plex woff2 (OFL-1.1). Prebuilt `@carbon/styles/css/styles.css` hardcodes IBM CDN — build from SCSS or declare own `@font-face`.
- **Offline rendering:** registered `threshold://` URI scheme (preferred) or `file://` + `allow-file-access-from-file-urls=true`.
- **CI drift-check:** re-builds and diffs `web/dist` to catch staleness.
- **CI enforcement:** grep dist for `https?://` to enforce no-CDN.

Resolved in [#38](https://github.com/Bongbetic/Threshold/issues/38).

### 5. Theme: White ↔ Gray 100, parity with system dark mode

- **Theme pair:** White (light) ↔ Gray 100 (dark). No Gray 10, no Gray 90.
- **Scheme policy:** `dark-mode` bool — ON forces dark (Adw `FORCE_DARK`), OFF follows system (Adw `DEFAULT`). No tri-state, no settings-key migration. Live flips while open.
- **Accent:** five accents (orange default, blue, green, purple, red). Per-theme tone pairs — a bright step for Gray 100, a deep step for White.
- **Python is single source of truth** for theme scheme. Adw.StyleManager computes effective scheme; web layer does not read `prefers-color-scheme` as authority.
- **Theme reaches the page over the bridge:** appearance (scheme + accent) in the state snapshot; changes as push events. Page swaps Carbon theme tokens (`cds--g100` ↔ `cds--white` root class) and accent custom properties — no reload.
- **First paint:** shell injects effective scheme at load (initial payload) so committed dist renders correctly offline in both schemes with no flash.

Resolved in [#42](https://github.com/Bongbetic/Threshold/issues/42).

### 6. Tray + notifications: stay native

- **Tray:** native SNI + dbusmenu (`src/threshold/tray.py`). WebKitGTK gives web content no D-Bus access; SNI leaves icon/menu rendering to the tray host.
- **Notifications:** native libnotify via Python. WebKitGTK's Web Notifications API is only a marshalling layer; Threshold's alarms originate in the Python backend.
- **Carbon applies to copy and icons only** on both surfaces.
- **No bridge needed** for these surfaces.

Resolved in [#39](https://github.com/Bongbetic/Threshold/issues/39).

### 7. i18n: English-only v1 with `t()` stub

- **v1:** English-only, every string routes through a `t()` module. No `po/` changes, no extraction, no bridge bundle. (`po/LINGUAS` is empty — existing gettext was scaffolding.)
- **Bridge convention:** semantic keys. Python pushes machine values; web layer renders display labels via `t()`.
- **Fallback:** English msgid, never a raw key. Unknown key renders English source string. Dev builds log on misses; release builds silent.
- **English-as-key:** `t('Battery status')` returns the English string — no catalog file; future xgettext reads calls directly.
- **Locale:** system locale only. No in-app switcher.
- **Future activation:** a fresh effort when a non-English locale is wanted.

Resolved in [#40](https://github.com/Bongbetic/Threshold/issues/40).

### 8. Test strategy: Vitest + mirrored contract fixtures + Xvfb smoke

- **JS unit:** Vitest + jsdom, logic only. Covers view-controller logic, state→DOM mapping, formatting, event wiring, bridge client against mocked `webkit.messageHandlers`. No Chromium component tests (wrong engine). Carbon components never re-tested.
- **Bridge contract:** mirrored pytest/vitest suites over shared `web/test/fixtures/messages.json` golden fixtures. Covers every message type: state snapshot, `set_threshold` ack (incl. pkexec errors), settings writes, push events, unknown-cmd error.
- **CI smoke:** Xvfb launch of real WebKitGTK shell on Ubuntu — loads committed `web/dist` via offline scheme, waits for JS `ready` ping, performs one request→ack round-trip. `gir1.2-webkit-6.0` + `xvfb` on the runner.
- **Gating:** separate required `web` CI job (`npm ci → tsc --noEmit → eslint → vitest run`). Meson/deb stay npm-free. No web-layer coverage gate in v1.

Resolved in [#41](https://github.com/Bongbetic/Threshold/issues/41).

### 9. Component inventory: eight sub-decisions locked

Full mapping in `docs/research/carbon-component-inventory.md`. The eight flagged sub-decisions resolved:

| Flag | Decision | Vehicle |
|------|----------|---------|
| **F1** | Header nav = focus/scroll-to region anchors; About = `cds-modal` | [C] `cds-header-nav` + `cds-header-nav-item` with `is-active` |
| **F2** | Menu button dropped for v1 | — |
| **F3** | Mode control = radio-button group styled as segments (content switcher acceptable if visual parity wins) | [C] `cds-radio-group` + styled radio buttons (or `cds-content-switcher`) |
| **F4** | Slider floating label = custom position from `cds-slider-changed`, unit-tested | [X] custom label |
| **F5** | Settings-row pattern = named [T] row pattern (geometry, separators, control alignment) | [T] style-only pattern |
| **F6** | Panel containers = style-only on layer tokens; Tile reserved for selectable content | [T] layer-01 surface + border-subtle + 8px radius |
| **F7** | Value-row picker = `cds-modal` | [C] `cds-modal` |
| **F8** | Dropdown style = boxed | [C] `cds-dropdown` |

Resolved in [#54](https://github.com/Bongbetic/Threshold/issues/54).

### 10. Component vehicles: shipped vs custom vs tokens

| Vehicle | Components |
|---------|-----------|
| **[C] shipped `@carbon/web-components`** | `cds-header`, `cds-header-menu-button` (if kept), `cds-header-name`, `cds-header-nav`, `cds-header-nav-item`, `cds-slider` + `cds-slider-input`, `cds-tile-group` + `cds-radio-tile`, `cds-button`, `cds-toggle`, `cds-dropdown`, `cds-modal`, `cds-toast-notification`, `@carbon/icons` |
| **[T] tokens + style-only** | Panel containers, panel titles, readout values, dividers, settings-row pattern, min/max labels, recommendation caption, metadata strip, accent swatches (styled radio group) |
| **[X] custom** | Floating slider label, accent swatch radio-group component |

## Consequences

### What this locks

- **Presentation only.** The Python backend is unchanged. This ADR governs the web layer exclusively.
- **Single-theme-pair scope.** White ↔ Gray 100; no Gray 10/90. Theme activation is a future effort.
- **English-only v1.** i18n is stubbed; activation is a future effort.
- **Tray and notifications are outside the web layer.** No bridge work needed for these surfaces.
- **Build chain is commit-based.** The Vite dist lives in the source tree; npm never runs in Meson/deb.
- **All dynamic values flow through the bridge.** No direct DOM manipulation from Python; no `prefers-color-scheme` authority in JS.

### What this does not lock

- **Exact accent tone per hue.** Implementation tuning under WCAG contrast checks.
- **Settings-row picker surface (resume-below, hysteresis).** `cds-modal` is recommended; implementation may validate `cds-popover` during build.
- **F3 mode control final shape.** Radio-button segments or content switcher — implementation picks during build.
- **`threshold://` URI scheme registration.** Implementation detail; the offline rendering requirement is locked, the mechanism is not.
- **CI runner matrix details.** Ubuntu smoke is locked; Debian/RPM specifics are CI plumbing.

### Implementation order

1. **Scaffold:** `web/` directory, Vite config, self-hosted Carbon build, `t()` stub, bridge client module.
2. **Shell:** `decorated: false` GtkWindow, WebKitGTK WebView, `UserScript` shim, message handler registration.
3. **Theme:** SCSS token sets, root-class switching, bridge appearance push.
4. **Layout:** CSS grid, header, status grid, charge panel, settings grid, footer.
5. **Components:** Carbon components wired to bridge state, F1–F8 decisions applied.
6. **Tests:** Vitest unit, contract fixtures, Xvfb smoke.
7. **Integration:** `meson.build` install, `debian/threshold.install` line, CI jobs.

## References

- Wayfinder map: [#34](https://github.com/Bongbetic/Threshold/issues/34)
- Layout: [#36](https://github.com/Bongbetic/Threshold/issues/36)
- Bridge: [#37](https://github.com/Bongbetic/Threshold/issues/37)
- Build chain: [#38](https://github.com/Bongbetic/Threshold/issues/38)
- Tray/notifications: [#39](https://github.com/Bongbetic/Threshold/issues/39)
- i18n: [#40](https://github.com/Bongbetic/Threshold/issues/40)
- Test strategy: [#41](https://github.com/Bongbetic/Threshold/issues/41)
- Theme mapping: [#42](https://github.com/Bongbetic/Threshold/issues/42)
- Component inventory: [#54](https://github.com/Bongbetic/Threshold/issues/54)
- Window chrome: [#55](https://github.com/Bongbetic/Threshold/issues/55)
