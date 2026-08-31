# Carbon component inventory — Industrial Grid layout

Resolution asset for **Screen + component inventory for the industrial grid layout** ([wayfinder ticket #54](https://github.com/Bongbetic/Threshold/issues/54)) on the [Wayfinder: Carbon web UI redesign map](https://github.com/Bongbetic/Threshold/issues/34).

Enumerates every region, component, and interaction state of the industrial-grid layout — contract locked in [#36's resolution](https://github.com/Bongbetic/Threshold/issues/36) — and maps each piece to its implementation vehicle. Primary sources: the variant-D mock on `prototype/carbon-ui-layout` (`prototype-carbon-ui/index.html`), the GTK design spec (`prototype-gtk4-ui/Threshold — Industrial Grid UI Design Specification.md`), and the upstream `@carbon/web-components` source tree (`carbon-design-system/carbon@main`, `packages/web-components`; package version **2.62.0**, current on npm when checked).

**Vehicle key**

- **[C]** shipped `@carbon/web-components` component — imported from the self-hosted build per #38, never the CDN
- **[T]** tokens + style-only — SCSS on Carbon layout/color/type/spacing tokens, no component
- **[X]** custom piece — our markup + JS styled on Carbon tokens (no upstream equivalent)

## Header

| Piece | Vehicle | Mapping & notes |
|---|---|---|
| App header bar | [C] `cds-header` | `aria-label="Threshold"` |
| Menu button | [C] `cds-header-menu-button` | Exists upstream (`ui-shell/header-menu-button.ts`); the #36 failure was a CDN module-graph artifact — re-verify on the self-hosted build. Flag **F2**: nothing to open in a one-screen design |
| App name | [C] `cds-header-name` | `prefix="Battery"` + name, as in mock |
| In-page nav | [C] `cds-header-nav` + `cds-header-nav-item` | Active item = `is-active` + `aria-current="page"` (both exist upstream). Flag **F1**: nav semantics in a scroll-free one-screen layout |
| Window controls | GTK shell | Not web components — owned by the shell; see the window-chrome ticket #55 |

## Top status grid (three equal panels)

The mock wraps every panel in `cds-tile`; upstream guidance scopes Tile to (inter)active content, and #36 hit tile grid-sizing breakage. Recommendation (flag **F6**): style-only panel containers.

| Piece | Vehicle | Mapping & notes |
|---|---|---|
| Panel container | [T] (rec.) or [C] `cds-tile` | layer-01 surface + 1px border-subtle + 8px radius on tokens — flag **F6** |
| Panel title | [T] | Carbon heading token + text-primary |
| Battery % / active-threshold readouts | [T] | "instrument value" class on Carbon type tokens (candidate `display-01` 42px vs custom 46px — pin at kickoff) + accent prop per #42; `font-variant-numeric: tabular-nums` |
| Charging state icon + label | [C] `@carbon/icons` + [T] | e.g. `battery--charging/20` es-import; `currentColor`; orange only when active |
| Status divider + diagnostics | [T] | 1px border-subtle divider; caption/value pairs right-aligned |
| Last changed / device id | [T] | plain text over the bridge |
| Threshold Mode control | [C] `cds-content-switcher` (mock) — flag **F3** | Upstream ships **no segmented control** (full component list checked). Guidance: a content switcher toggles *views* and "should not be used as a binary input control" — Automatic/Manual is an input, so a radio-button group styled as segments is the guidance-pure alternative |

## Charge Limit panel

| Piece | Vehicle | Mapping & notes |
|---|---|---|
| Header row (title + live %) | [T] | |
| Slider | [C] `cds-slider` **with `cds-slider-input` child** | `min=20 max=100 step=1 label-text hide-label`; the input child is required (source imports it; #36 gotcha) — add `hide-text-input`; value changes arrive as `cds-slider-changed` (user gesture) |
| Floating value label | [X] | No floating-label API upstream. Position a label over the thumb: percent = (value−min)/(max−min), updated on `cds-slider-changed` and on programmatic sets — flag **F4** |
| Min/max end labels | [T] | `20%` / `100%` |
| Recommendation caption | [T] | |
| Preset tiles ×5 | [C] `cds-tile-group` + `cds-radio-tile` | **Not the mock's `cds-selectable-tile`** — selectable tiles are checkbox-semantics (independent), presets are an exclusive choice. Radio tiles share a `name`, render the checked icon, and get keyboard navigation via tile-group's `<fieldset>` + legend slot; events: `cds-radio-tile-selected`, `cds-current-radio-tile-selection` |
| Apply Threshold | [C] `cds-button kind="primary"` | commits pending state to the system |
| Restore to 100% | [C] `cds-button kind="secondary"` | pending-until-apply behavior per spec §35 |
| Apply toast | [C] `cds-toast-notification` | caption "Charging threshold set to 80%"; `timeout` ≈ 4s; host wrapper positions it |

## Lower settings grid (three panels)

| Piece | Vehicle | Mapping & notes |
|---|---|---|
| Settings row pattern | [T] | title+desc left, control right, border-subtle separators; structured list rejected (read-only tabular data), contained list rejected (not control rows) — lock as a named pattern, flag **F5** |
| Switch rows | [C] `cds-toggle` | `toggled` (not the deprecated `checked`), `hide-label` + `aria-label`; `label-a`/`label-b` if on/off labels wanted |
| Value + chevron rows (resume-below, hysteresis) | [C] ghost `cds-button` row + [C] `cds-modal` (rec.) / `cds-side-panel` / `cds-popover` | the row itself is a button opening a picker — flag **F7** |
| Accent swatches ×5 | [X] | radio-group semantics (`role="radiogroup"`, roving radios) styled as circular swatches; selected ring per spec §25.1 |
| Compact mode / % in title rows | [C] `cds-toggle` | |

## Footer

| Piece | Vehicle | Mapping & notes |
|---|---|---|
| Metadata strip | [T] | BAT1 / cycle count / design capacity |
| Profile selector | [C] `cds-dropdown` | `type="inline"` (mock) vs boxed default (contract's ~250×50 geometry) — flag **F8** |
| Save | [C] `cds-button kind="tertiary" size="sm"` | or an icon button with `save/16` |

## Cross-cutting

- **States** (spec §33): shipped [C] components carry normal/hover/active/selected/disabled/focus on state tokens. The [T]/[X] pieces must wire `$layer-hover`, `$focus` (visible focus ring), and disabled opacity — include in the ADR checklist.
- **Theming** (#42): emit both theme token sets via SCSS (`theme.theme(themes.$white)` / `$g100`) and switch by root class; accent = per-theme `--cds-*` overrides, pushed from Python over the bridge (Python is the source of truth).
- **Icons**: `@carbon/icons` es imports (16/18/20), monochrome, `currentColor`.
- **i18n** (#40): every user-visible string passes the `t()` stub (English-as-key); bridge payloads carry semantic keys.
- **Bridge** (#37): all dynamic values flow via `window.threshold.request()/on()`; component events map onto `request()` calls; mirrored pytest/vitest suites over golden fixtures per #41.
- **Scroll-free fit**: fixed geometry per spec §42 (default 1220×900, usable floor 960×700); compact mode reduces spacing; the web layer must not scroll at the floor.

## Mock divergences — do not copy the prototype here

1. Preset tiles: mock's `cds-selectable-tile` → `cds-tile-group` + `cds-radio-tile` (exclusive-selection semantics).
2. Menu button: mock hand-rolls the hamburger → use `cds-header-menu-button` on the self-hosted build (flag F2 may drop it entirely).
3. Panels as `cds-tile` → style-only panel containers recommended (flag F6).
4. CDN loading → npm + SCSS build per #38.

## Flagged sub-decisions (input to the architecture ADR)

- **F1 — Header nav in a one-screen layout.** Overview / Threshold / Settings / About cannot navigate pages. Options: focus/scroll-to region anchors (the mock's decorative underline), or view-switching with About opening a `cds-modal`. Recommendation: region focus + About modal.
- **F2 — Menu button with nothing to open.** Drop it, or repurpose (About / profile menu). Recommendation: drop for v1.
- **F3 — Mode control: content switcher vs segmented radio.** No segmented control ships upstream; guidance bars content switcher as binary input. Recommendation: radio-button group styled as segments; content switcher acceptable if visual parity wins.
- **F4 — Slider floating label.** No upstream float. Recommendation: custom label positioned from `cds-slider-changed`, with the positioning math unit-tested; fallback is the built-in visually-hidden label.
- **F5 — Settings-row pattern.** Lock the [T] row pattern (geometry, separators, control alignment) as a named pattern so all 11 rows stay uniform.
- **F6 — Panel container: tile vs style-only.** Recommendation: style-only panels on layer tokens; Tile reserved for genuinely selectable content.
- **F7 — Value-row picker surface.** `cds-modal` vs `cds-side-panel` vs `cds-popover` for resume-below and hysteresis. Recommendation: `cds-modal`.
- **F8 — Dropdown style.** Inline (mock) vs boxed (contract geometry). Recommendation: boxed.

## Sources

- `@carbon/web-components` **2.62.0** (npm `dist-tags.latest`); source tree `carbon-design-system/carbon@main`, `packages/web-components/src/components/` — component list, `slider.ts`, `tile/{radio-tile,tile-group,selectable-tile}.ts`, `toggle.ts`, `dropdown.ts`, `ui-shell/*`, `notification/*`, `docs/styling.md` (paths cited inline above)
- Content switcher usage guidance: <https://carbondesignsystem.com/components/content-switcher/usage/>
- Variant-D mock: `prototype-carbon-ui/index.html`, branch `prototype/carbon-ui-layout`
- GTK design spec: `prototype-gtk4-ui/Threshold — Industrial Grid UI Design Specification.md`
- Map decisions this builds on: #36 (layout contract), #37 (bridge), #38 (build chain), #39 (tray/notifications stay native), #40 (i18n), #41 (test strategy), #42 (theme mapping)
