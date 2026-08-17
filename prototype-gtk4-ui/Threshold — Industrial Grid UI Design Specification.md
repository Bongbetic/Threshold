# Threshold — Industrial Grid UI Design Specification

> Target: **GTK 4 + libadwaita**
> 
> Purpose: Reproduce the dark industrial/grid-based interface shown in the reference image as closely as practical while keeping the implementation idiomatic to GTK4/libadwaita.
> 
> **Measurement note:** Pixel values below are inferred from the supplied reference image and should be treated as implementation targets, not source-extracted values. Where libadwaita's native widget metrics differ slightly, preserve the visual hierarchy, spacing rhythm, and proportions first.

---

## 1. Visual Direction

The interface should feel like a **compact industrial control panel** rather than a conventional settings page.

Core characteristics:

- Dark charcoal application surface.

- Repeated rectangular instrument panels arranged on a strict grid.

- Thin low-contrast borders instead of large drop shadows.

- Small corner radii: rounded, but not pill-heavy.

- Orange is the single active/accent color.

- Large numeric battery values act as instrument readouts.

- Secondary information stays quiet and gray.

- Controls are dense, aligned, and deliberately mechanical.

- The top-level layout is symmetric and modular.

- Avoid glassmorphism, gradients, oversized rounded cards, excessive whitespace, or floating mobile-style components.

---

# 2. Reference Canvas and Window

## 2.1 Reference proportions

The reference image is approximately:

- Width: **1365 px**

- Height: **1152 px**

- Aspect ratio: **1.185 : 1**

Recommended desktop window defaults:

```
default-width: 1180–1240 pxdefault-height: 860–920 pxminimum-width: 960 pxminimum-height: 700 px
```

The UI should remain usable down to approximately 900–960 px wide.

At narrower sizes, secondary cards may reflow vertically.

---

## 2.2 Window background

Main application background:

```
--app-bg: #171717;
```

Suggested GTK CSS:

```
window,.background {    background: #171717;    color: #F3F3F3;}
```

Avoid pure black.

---

# 3. Color System

Use a restrained neutral palette with one warm accent.

## 3.1 Core tokens

```
--app-bg:              #171717;--header-bg:           #202020;--panel-bg:            #222222;--panel-bg-raised:     #262626;--control-bg:          #2D2D2D;--control-bg-hover:    #353535;--border-subtle:       #3A3A3A;--border-strong:       #4A4A4A;--separator:           #383838;--text-primary:        #F4F4F4;--text-secondary:      #B7B7B7;--text-muted:          #8D8D8D;--text-disabled:       #676767;--accent:              #FF7800;--accent-hover:        #FF8B1A;--accent-pressed:      #E96D00;--accent-soft:         rgba(255, 120, 0, 0.18);--accent-border:       rgba(255, 120, 0, 0.70);--success:             #57C271;--warning:             #E9B949;--danger:              #EF5B5B;
```

The screenshot accent visually sits near GNOME/libadwaita orange.

---

## 3.2 Accent usage rules

Orange should appear only on:

- active navigation underline,

- current battery percentage readout,

- threshold percentage readout,

- selected threshold mode,

- selected preset,

- primary action button,

- slider filled section,

- active switches,

- selected accent color sample,

- small active state icons/checkmarks.

Do **not** use orange for regular headings, body text, separators, or inactive controls.

Target orange coverage: approximately **5–9% of the visible UI**.

---

# 4. Typography

Use the system GNOME/libadwaita font stack.

Recommended:

```
font-family: "Adwaita Sans", "Cantarell", sans-serif
```

If Adwaita Sans is available, prefer it.

---

## 4.1 Type scale

### Window title

```
20 px600 weightline-height ~ 26 px
```

### Top navigation labels

```
18 px400–500 weight
```

### Card title / section title

```
17–18 px600 weight
```

### Large instrument value

For values like `72%`, `80%`:

```
44–48 px400 weightline-height 1.0
```

Use medium/light visual weight rather than bold.

### Medium numeric value

```
28–32 px400–500 weight
```

### Main label / row label

```
16–17 px400–500 weight
```

### Secondary text

```
14–15 px400 weight
```

### Caption / metadata

```
12.5–14 px400 weight
```

---

## 4.2 Typography rules

- Avoid heavy bold text except panel titles.

- Large percentages should look like **readouts**, not headings.

- Secondary labels should use `--text-secondary`.

- Descriptions and helper text should use `--text-muted`.

- Prefer tabular numerals when available.

GTK/Pango option:

```
font-feature-settings: "tnum";
```

Particularly for:

- battery percentage,

- threshold value,

- cycle count,

- capacity,

- temperatures,

- time values.

---

# 5. Global Spacing System

Use a consistent 4 px base grid.

```
4 px   micro spacing8 px   icon/text gap12 px  compact internal gap16 px  normal internal gap20 px  card padding minimum24 px  standard card padding28 px  wide card padding32 px  major section gap
```

Recommended constants:

```
--space-1: 4px;--space-2: 8px;--space-3: 12px;--space-4: 16px;--space-5: 20px;--space-6: 24px;--space-7: 28px;--space-8: 32px;
```

---

# 6. Corner Radius System

Keep corners modest.

```
Window chrome/button:        10–14 pxMain cards:                  7–9 pxNested controls:             6–8 pxButtons:                     6–8 pxPreset tiles:                7–8 pxSwitches:                    native / libadwaitaColor swatches:              circular
```

Recommended token:

```
--radius-card: 8px;--radius-control: 7px;
```

Avoid 16–24 px "mobile card" radii.

---

# 7. Border and Elevation

The visual system should rely on borders rather than large shadows.

## Cards

```
background: #222222;border: 1px solid #3A3A3A;border-radius: 8px;
```

Optional extremely subtle shadow:

```
box-shadow: 0 1px 2px rgba(0,0,0,0.22);
```

Do not use visible floating shadows.

---

# 8. Main Layout

Use a vertical root layout:

```
┌────────────────────────────────────────────┐│ Header Bar / Navigation                    │├────────────────────────────────────────────┤│                                            ││ Top status grid: 3 columns                 ││                                            ││ Charge Limit panel                         ││                                            ││ Lower settings grid: 3 columns             ││                                            │├────────────────────────────────────────────┤│ Footer / device info + profile             │└────────────────────────────────────────────┘
```

Main content padding:

```
horizontal: 24 pxvertical:   22–24 px
```

Grid gap:

```
18 px horizontally18 px vertically
```

GTK recommendation:

- `GtkGrid` for top and bottom matrices.

- `GtkBox` for internal composition.

- `AdwClamp` only if a max width is necessary; do not make the center column excessively narrow.

- For responsiveness use `AdwBreakpoint`.

---

# 9. Header / Navigation

## 9.1 Height

Target:

```
72–76 px
```

Background:

```
#202020
```

Bottom divider:

```
1px solid #303030
```

---

## 9.2 Left section

Elements:

1. hamburger/menu button

2. app title `Threshold`

Measurements:

```
left margin: 22 pxmenu button: 46 x 46 pxgap menu → title: 26 px
```

Menu button:

```
background: #2B2B2B;border-radius: 9px;
```

Icon:

```
20–22 px
```

---

## 9.3 Center navigation

Items:

- Overview

- Threshold

- Settings

- About

Horizontal gap:

```
42–46 px
```

Active tab:

- white text

- orange underline

Underline:

```
height: 2 pxwidth: approximately label width + 24 pxbottom aligned to header edge
```

Inactive:

```
color: #C3C3C3;
```

Hover:

```
color: #FFFFFF;
```

---

## 9.4 Window controls

Right-aligned GNOME-style circular/rounded controls.

Approximate target:

```
button: 38 x 38 pxgap: 12 px
```

Use native `AdwHeaderBar` controls where practical.

Do not fake Windows-style controls.

---

# 10. Top Status Grid

Three cards:

```
Battery Status | Active Threshold | Threshold Mode
```

Columns should be approximately equal.

Reference proportions:

```
column width: ~31.5% eachgap: 18 pxcard height: ~200 px
```

All three cards:

```
padding: 24 px
```

---

# 11. Battery Status Card

Structure:

```
Battery Status----------------------------------------72%                Power Source                   AC Adapter⚡ Charging         Health                   Good                   Temperature                   34°C
```

The card should visually split into:

- left readout region,

- vertical divider,

- right diagnostics region.

Approximate divider location:

```
52–54% from card's left edge
```

Vertical separator:

```
width: 1px;background: #414141;
```

---

## 11.1 Large battery value

```
72%44–48 pxorangenormal weight
```

Position:

```
~28 px below card title
```

---

## 11.2 Charging label

Icon + text:

```
icon: 18–20 pxtext: 17 pxgap: 12 px
```

Use symbolic icon:

```
battery-level / power / bolt symbolic icon
```

Suggested GNOME icon names may vary by installed icon theme.

---

## 11.3 Right-side diagnostics

Use right alignment.

Each item:

```
caption:14 px#9C9C9Cvalue:16 px#EEEEEE
```

Vertical rhythm:

```
~12 px between caption and value groups
```

---

# 12. Active Threshold Card

Structure:

```
Active Threshold80%                           Last changed                              Today, 10:24 AMBAT1
```

Large value:

```
80%44–48 pxorange
```

Bottom battery ID:

```
16 px#B8B8B8
```

Timestamp area right-aligned.

---

# 13. Threshold Mode Card

Title:

```
Threshold Mode
```

Two horizontal segmented controls:

```
[ Automatic ] [ Manual ]
```

Each:

```
height: 54 pxradius: 7 px
```

Selected:

```
background: rgba(255,120,0,0.22);color: #FF7800;
```

Inactive:

```
background: #303030;color: #BDBDBD;
```

Selected icon:

```
18–20 pxorange
```

Inactive lock icon:

```
17–19 pxmuted gray
```

Gap:

```
8 px
```

---

# 14. Charge Limit Main Panel

This is the dominant panel.

Approximate height:

```
310–330 px
```

Padding:

```
26 px horizontal22–24 px vertical
```

---

## 14.1 Header row

Left:

```
Charge Limit18 px / 600
```

Right:

```
80%32 pxorange
```

Align to same top baseline.

---

# 15. Slider

Use GTK `GtkScale`.

Range:

```
minimum: 20maximum: 100step: 1
```

Reference:

```
20%                         80%         100%├────────────────────────────●────────────┤
```

Track:

```
height: 6 pxradius: 3 px
```

Filled track:

```
background: #FF7800;
```

Remaining track:

```
background: #4A4A4A;
```

Thumb:

```
24–28 px circle
```

Thumb:

```
background: #F1F1F1;border: 1px solid #D5D5D5;
```

Value label `80%` should float directly above thumb:

```
14–16 px#FFFFFF
```

Slider left/right labels:

```
20%100%
```

Use:

```
14 px#A6A6A6
```

---

# 16. Threshold Recommendation Caption

Centered underneath slider:

```
Recommended: 60–80% daily  •  100% for travel
```

Typography:

```
14 px#A4A4A4
```

Top margin:

```
10–12 px
```

Bottom margin:

```
20–22 px
```

---

# 17. Threshold Preset Tiles

Five equal tiles:

```
60%       70%       80%       90%       100%Daily     Balanced  Recommended Extended   TravelUse
```

Container:

```
display: 5 equal columnsgap: 10 px
```

Tile height:

```
68–74 px
```

Padding:

```
12 px
```

Default tile:

```
background: #272727;border: 1px solid #414141;border-radius: 7px;
```

Selected `80%`:

```
background: rgba(255,120,0,0.12);border: 1px solid #FF7800;
```

Selected percentage and subtitle:

```
color: #FF7800;
```

Main value:

```
18 px / 600
```

Subtitle:

```
14 px
```

Selection indicator:

- small orange outlined circle/check icon

- top-right inside tile

- about 18 px

---

# 18. Main Action Buttons

Two side-by-side buttons.

```
[ Apply Threshold              ] [ Restore to 100%            ]
```

Grid:

```
left width: ~49%right width: ~49%gap: 34–36 px
```

Height:

```
50 px
```

Radius:

```
7 px
```

Primary:

```
background: #FF7800;color: #FFFFFF;font-weight: 600;
```

Hover:

```
background: #FF8B1A;
```

Pressed:

```
background: #E96D00;
```

Secondary:

```
background: #353535;color: #F1F1F1;
```

Do not outline the secondary button unless focused.

---

# 19. Lower Settings Grid

Three panels:

```
General | Charging Behavior | Appearance
```

Card heights approximately equal.

Reference target:

```
height: 340–370 pxgap: 18 px
```

Padding:

```
22–24 px
```

---

# 20. Panel Section Title

All three panels:

```
17–18 px600#F3F3F3
```

Bottom margin:

```
18 px
```

---

# 21. Settings Row Pattern

Each row:

```
┌──────────────────────────────────────┐│ Row title                        [ ] ││ Description                          │└──────────────────────────────────────┘
```

Typical row minimum height:

```
66–72 px
```

Main label:

```
16 px#F1F1F1
```

Description:

```
13.5–14 px#8F8F8F
```

Rows separated by:

```
border-bottom: 1px solid #3A3A3A;
```

Last row has no separator.

---

# 22. General Panel

Rows:

1. Dark Mode
   
   - `Follow system preference`

2. Launch at login
   
   - `Start minimized in background`

3. Minimize to tray
   
   - `Keep app in system tray`

4. Show notifications
   
   - `Notify on threshold changes`

Switches align to far right.

---

# 23. Switch Styling

Prefer native libadwaita switches.

Target visual:

```
width: 58–62 pxheight: 30 px
```

Inactive:

```
background: #303030;border: 1px solid #4A4A4A;
```

Active:

```
background: rgba(255,120,0,0.18);border: 1px solid #FF7800;
```

Knob:

```
background: #F4F4F4;
```

Native GTK metrics may vary; use CSS only if necessary.

---

# 24. Charging Behavior Panel

Rows:

1. Resume charging below
   
   - `Start charging when below limit`
   
   - current value: `75%`
   
   - chevron right

2. Full charge reminder
   
   - `Notify when reaching 100%`
   
   - switch

3. Stop charging at limit
   
   - `Prevent overcharging`
   
   - switch

4. Charge hysteresis
   
   - `Avoid rapid charging toggles`
   
   - value: `5%`
   
   - chevron right

Rows 1 and 4 use a **nested row frame**.

Recommended nested frame:

```
background: #292929;border: 1px solid #3E3E3E;border-radius: 6px;padding: 10px 12px;
```

---

# 25. Appearance Panel

## 25.1 Accent color row

Label:

```
Accent ColorOrange
```

Right side contains 5 circular swatches.

Suggested colors:

```
Orange  #FF7800Blue    #4A91F2Green   #32D74BPurple  #A44BF4Red     #F04444
```

Swatch:

```
26–30 px diametergap: 14 px
```

Selected swatch:

- thin orange outer ring

- 3 px visual separation from inner disk

---

## 25.2 Compact Mode

Description:

```
Reduce spacing and padding
```

Switch right aligned.

---

## 25.3 Show percentage in title

Description:

```
Display battery % in window title
```

Switch right aligned.

---

# 26. Footer / Bottom Device Bar

Height:

```
74–78 px
```

Background:

```
#1B1B1B
```

Top border:

```
1px solid #323232
```

Horizontal padding:

```
30–32 px
```

---

## 26.1 Left metadata

Display inline:

```
Battery: BAT1    Cycle Count: 156    Design Capacity: 54.0 Wh
```

Text:

```
14–15 px#C6C6C6
```

Value may use:

```
#EEEEEE
```

Gaps:

```
36–40 px
```

---

## 26.2 Profile selector

Right side:

```
Profile     [ Daily             v ] [save]
```

Label:

```
15 px
```

Dropdown target:

```
250–260 px wide50 px high
```

Background:

```
#303030
```

Save button:

```
52 x 50 px
```

Icon:

```
18 px
```

---

# 27. Icon System

Use GNOME symbolic icons wherever possible.

Icon style:

- monochrome

- 16–20 px

- no filled emoji

- no colorful SVG icon set

- orange only for active/selected states

Suggested icon concepts:

```
menubolt / powertrend / automaticlockchevron-rightsavewindow-minimizewindow-maximizewindow-close
```

Preferred icon size:

```
16 px compact controls18 px row actions20 px primary status
```

---

# 28. GTK4 / libadwaita Widget Mapping

Recommended mapping:

| UI Element      | GTK/libadwaita                                            |
| --------------- | --------------------------------------------------------- |
| Main window     | `AdwApplicationWindow`                                    |
| Header          | `AdwHeaderBar` or custom `GtkBox` inside `AdwToolbarView` |
| Navigation      | `GtkToggleButton`/custom flat buttons                     |
| Top cards       | `GtkFrame` + CSS class                                    |
| Main grids      | `GtkGrid`                                                 |
| Text rows       | `GtkBox`                                                  |
| Settings row    | `AdwActionRow` where suitable                             |
| Switches        | `GtkSwitch`                                               |
| Slider          | `GtkScale`                                                |
| Preset buttons  | `GtkToggleButton`                                         |
| Dropdown        | `GtkDropDown`                                             |
| Icons           | `GtkImage`                                                |
| Adaptive layout | `AdwBreakpoint`                                           |
| Toasts          | `AdwToastOverlay`                                         |
| Dialogs         | `AdwAlertDialog`                                          |

Do not force `AdwPreferencesPage` if it causes the layout to become a conventional vertical preferences screen. The target layout is a dashboard/control panel.

---

# 29. Suggested CSS Class Architecture

Suggested names:

```
threshold-windowindustrial-headernav-itemnav-item-activepanelpanel-titlestatus-panelinstrument-valueinstrument-value-accentmetadata-labelmetadata-valuethreshold-panelthreshold-sliderpreset-gridpreset-buttonpreset-button-selectedprimary-actionsecondary-actionsettings-panelsettings-rowsettings-descriptionnested-settingfooter-barprofile-selectoraccent-orange
```

---

# 30. Example CSS Skeleton

```
.threshold-window {    background: #171717;    color: #F4F4F4;}.industrial-header {    background: #202020;    border-bottom: 1px solid #303030;}.panel {    background: #222222;    border: 1px solid #3A3A3A;    border-radius: 8px;}.panel-title {    color: #F4F4F4;    font-size: 18px;    font-weight: 600;}.instrument-value {    font-size: 46px;    font-weight: 400;    font-feature-settings: "tnum";}.instrument-value-accent {    color: #FF7800;}.metadata-label {    color: #8D8D8D;    font-size: 14px;}.metadata-value {    color: #EEEEEE;    font-size: 16px;}.preset-button {    background: #272727;    border: 1px solid #414141;    border-radius: 7px;    min-height: 70px;}.preset-button:hover {    background: #303030;}.preset-button-selected {    background: rgba(255, 120, 0, 0.12);    border-color: #FF7800;    color: #FF7800;}.primary-action {    background: #FF7800;    color: white;    border-radius: 7px;    min-height: 50px;    font-weight: 600;}.primary-action:hover {    background: #FF8B1A;}.secondary-action {    background: #353535;    color: #F1F1F1;    border-radius: 7px;    min-height: 50px;}.footer-bar {    background: #1B1B1B;    border-top: 1px solid #323232;}
```

GTK CSS support differs from web CSS. Treat the above as a visual token reference and translate unsupported properties into GTK-supported selectors and widget properties.

---

# 31. Grid Geometry

For a ~1200 px usable content width:

```
Main content left/right padding: 24 pxUsable width: ~1152 pxTop grid:3 columnscolumn gap: 18 pxeach card: ~372 pxBottom grid:same 3-column geometryVertical gaps:18 px between top grid and main panel18 px between main panel and bottom grid
```

The main `Charge Limit` panel spans all 3 columns.

---

# 32. Responsive Behavior

## >= 1100 px

Use exact 3-column layout.

```
[Status] [Threshold] [Mode][Charge Limit spans all][General] [Charging] [Appearance]
```

## 900–1099 px

Allow:

```
[Status] [Threshold][Mode spans / moves below][Charge Limit][General] [Charging][Appearance spans / moves below]
```

## < 900 px

Stack all cards vertically.

Do not shrink text excessively.

Large readout minimum:

```
36 px
```

Maintain minimum card padding:

```
16 px
```

---

# 33. Interaction States

Every interactive element must support:

```
normalhoveractive/pressedselecteddisabledkeyboard focus
```

## Focus

Use a visible thin focus ring:

```
outline equivalent: 2 pxaccent or light neutral
```

Do not remove GTK keyboard focus indication.

## Disabled

Reduce contrast but remain readable:

```
opacity equivalent: ~0.5–0.6
```

---

# 34. Functional Features Visible in the Reference

The replica should include the following behavior surface.

## Battery status

Display:

- battery percentage,

- charging/discharging state,

- power source,

- health,

- temperature.

## Active threshold

Display:

- active charging threshold,

- battery device ID,

- last change timestamp.

## Threshold mode

Modes:

- Automatic

- Manual

## Charge limit

Allow:

- slider between 20–100,

- presets: 60 / 70 / 80 / 90 / 100,

- apply threshold,

- restore to 100%.

## General

- dark mode/system theme behavior,

- launch at login,

- minimize to tray,

- notifications.

## Charging behavior

- resume charging below threshold,

- full-charge reminder,

- stop charging at limit,

- hysteresis.

## Appearance

- accent color,

- compact mode,

- percentage in title.

## Footer

- battery device,

- cycle count,

- design capacity,

- profile selector,

- profile save action.

---

# 35. Interaction Logic

## Presets

Selecting a preset:

1. updates the slider,

2. updates the large percentage in the charge-limit panel,

3. highlights only one preset,

4. does **not** commit the system threshold until `Apply Threshold` is pressed.

## Apply Threshold

On successful apply:

- active threshold card updates,

- selected threshold remains orange,

- show a brief `AdwToast`.

Example:

```
Charging threshold set to 80%
```

## Restore to 100%

Behavior:

- sets slider to 100,

- selects `100% Travel`,

- apply immediately only if intended by product behavior; otherwise update pending state and require Apply.

Prefer explicit behavior over hidden system changes.

---

# 36. Visual Density

The reference is moderately dense.

Target density:

```
Card title → first content: 20–24 pxRow spacing: 12–16 pxPanel padding: 22–24 pxGrid gap: 18 px
```

Compact Mode can reduce:

```
panel padding: 24 → 16 pxrow height: 68 → 54 pxgrid gap: 18 → 12 px
```

Do not reduce typography below readable desktop sizes.

---

# 37. Accessibility

Minimum goals:

- body text contrast >= WCAG AA where practical,

- control labels should never rely only on orange state,

- selected presets need border + icon + color,

- switches must expose accessible names,

- slider must expose min/max/current value,

- status values should have semantic accessible labels.

Example accessible slider name:

```
Charge limit, 80 percent
```

Automatic/manual mode should behave as an exclusive group.

---

# 38. Light Theme Policy

The reference is intentionally dark.

If light mode is implemented, preserve the same structure rather than redesigning it.

Suggested light tokens:

```
--app-bg:          #F3F3F3;--header-bg:       #EAEAEA;--panel-bg:        #FFFFFF;--control-bg:      #F0F0F0;--border-subtle:   #D6D6D6;--text-primary:    #1D1D1D;--text-secondary:  #5D5D5D;--text-muted:      #7A7A7A;--accent:          #E86700;
```

However, dark mode should be considered the canonical reference.

---

# 39. Do Not Deviate Into These Styles

Avoid:

- huge rounded cards,

- pill-shaped everything,

- blue/purple gradients,

- glass blur,

- glossy 3D switches,

- neon borders,

- oversized icons,

- mobile-first bottom navigation,

- large empty hero regions,

- centered settings rows,

- excessive shadow layers,

- pure black backgrounds,

- pure orange panels.

The result should feel like a **GNOME-native workstation utility** with a subtle industrial dashboard character.

---

# 40. Implementation Priority

When visual compromises are necessary, preserve these in order:

1. **3-column industrial grid structure**

2. **dark charcoal surfaces**

3. **orange instrument/readout accent**

4. **compact 18–24 px spacing rhythm**

5. **thin borders**

6. **large percentage readouts**

7. **preset tile row**

8. **two-button action row**

9. **three lower control panels**

10. **footer metadata strip**

---

# 41. Suggested GTK Component Hierarchy

```
AdwApplicationWindow└── AdwToolbarView    ├── top-bar    │   └── AdwHeaderBar / custom header GtkBox    │       ├── menu button    │       ├── app title    │       ├── navigation box    │       └── window controls    │    └── content        └── GtkBox vertical            ├── GtkGrid top-status-grid            │   ├── BatteryStatusPanel            │   ├── ActiveThresholdPanel            │   └── ThresholdModePanel            │            ├── ChargeLimitPanel            │   ├── title/value row            │   ├── GtkScale            │   ├── recommendation label            │   ├── presets GtkGrid            │   └── action buttons GtkBox/Grid            │            ├── GtkGrid settings-grid            │   ├── GeneralPanel            │   ├── ChargingBehaviorPanel            │   └── AppearancePanel            │            └── FooterBar                ├── metadata box                └── profile controls
```

---

# 42. Recommended Sizing Constants

Centralize these values.

```
WINDOW_DEFAULT_WIDTH      = 1220WINDOW_DEFAULT_HEIGHT     = 900HEADER_HEIGHT             = 74FOOTER_HEIGHT             = 76CONTENT_PAD_X             = 24CONTENT_PAD_Y             = 22GRID_GAP                  = 18CARD_PADDING              = 24CARD_RADIUS               = 8CONTROL_RADIUS            = 7TOP_CARD_MIN_HEIGHT       = 196CHARGE_PANEL_MIN_HEIGHT   = 310LOWER_CARD_MIN_HEIGHT     = 345ACTION_BUTTON_HEIGHT      = 50MODE_BUTTON_HEIGHT        = 54PRESET_HEIGHT             = 70LARGE_VALUE_FONT          = 46SECTION_TITLE_FONT        = 18BODY_FONT                 = 16SECONDARY_FONT            = 14CAPTION_FONT              = 13ICON_SMALL                = 16ICON_NORMAL               = 18ICON_STATUS               = 20
```

---

# 43. Accuracy Checklist for Coding Agents

Before considering the implementation visually complete, verify:

- Window defaults to approximately 1200 × 900.

- Header is ~74 px high.

- Main content uses ~24 px side padding.

- Top section contains exactly three visually equal cards on desktop.

- Cards use #222-ish dark surfaces.

- Card borders are thin and subtle.

- Card radius is approximately 8 px.

- Grid gaps are approximately 18 px.

- Battery `72%` is large and orange.

- Threshold `80%` is large and orange.

- Battery status card contains a vertical divider.

- Automatic mode is orange-selected.

- Charge Limit panel spans the full layout width.

- Slider fill is orange and remaining rail is gray.

- Slider thumb is light gray/white.

- Five preset tiles are shown.

- 80% preset has orange border and selected indicator.

- Apply Threshold button is orange.

- Restore to 100% button is dark neutral.

- Three lower settings panels align in one row at desktop widths.

- Settings rows use thin separators.

- Active switches use orange.

- Appearance panel includes five color swatches.

- Footer has battery/cycle/capacity metadata.

- Footer has a profile selector and save button.

- No large drop shadows are visible.

- No gradients are visible.

- No excessive pill-shaped controls are introduced.

- Native GNOME/libadwaita interaction behavior is preserved.

- Keyboard focus remains clearly visible.

- Responsive breakpoints do not compress text below readable sizes.

---

# 44. Final Visual Target

The finished app should read as:

> **A GNOME-native battery charging control utility presented like an industrial instrumentation dashboard: dark, modular, grid-aligned, compact, technically precise, and using orange only for active state and key numeric readouts.**

When choosing between strict libadwaita defaults and the reference image, preserve **libadwaita behavior** while using custom CSS classes for the panel geometry, color hierarchy, compact grid structure, and orange instrumentation aesthetic.
