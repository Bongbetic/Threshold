# Appearance and adaptive layout observations for issue #119 (partial)

Observed `2026-10-01T06:05Z` (UTC, approx.) on the physical MSI Thin A15 B7UCX, Void Linux,
niri 26.04, DankMaterialShell 1.6.2, single user session on Wayland.

Candidate: installed `threshold-2.0.4_1`, XBPS SHA-256
`62d55b0b7814472fdf2effb3efbe2c85eb1f90278b23777941e187af01af74f6`
(matches the baseline; signed source `3682e414b40918ff7c1a8071ae26830e1dd858c4`).
Runtime: GTK 4.22.4, WebKitGTK 2.50.4, libadwaita 1.9.1.
Outputs: eDP-1 1920x1080 @ scale 1, HDMI-A-1 1920x1080 @ scale 1.

## Actual observations

- Launched the installed `threshold` command (no source checkout). Compositor
  app ID `com.bongbetic.threshold`; process environment `GDK_BACKEND=wayland`,
  `WAYLAND_DISPLAY=wayland-1`: native Wayland toplevel.
- The dashboard rendered with live EC values (charge 67%, limit 60%, BAT1,
  EC control) and no network dependency visible.
- System theme followed the current DMS palette (light surface). Accent orange.
- Window allocations were set with `niri msg action set-window-width/height`
  and captured with `niri msg action screenshot-window` (Threshold only):
  - [954x1028](normal-954.png): all three rows, footer ("Connected") visible,
    no clipping.
  - [640x1028](w640.png), [480x1028](w480-full.png): cards stack into one
    column; a vertical scrollbar appears; final rows lie below the fold.
  - [480x400](w480h400.png), [640x400](w640h400.png): header and first cards
    readable, vertical scrollbar present, no horizontal overflow seen.

## Not done (acceptance criteria still open)

- No input injection tool was available, so scrolling to the final row and
  footer at 480x400 was not exercised, and pointer/keyboard control was not
  tried at small sizes.
- Light/Dark explicit modes, live DMS palette change, retained explicit
  preference, and absent/invalid palette fallback were not exercised: the
  first needs in-app interaction; the last two change desktop state.
- Display scale was left at 1 on both outputs; 125%/150%/200% were not tested.
- No old architecture description was reconciled.

This is partial evidence only. It does not satisfy #119 and does not change
`release-acceptance.json`. Screenshots contain only the Threshold window.
