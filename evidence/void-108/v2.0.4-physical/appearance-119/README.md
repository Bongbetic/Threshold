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

## User-reported physical verification (2026-10-01T06:20Z)

After the observations above, the maintainer reported, in chat, that on the
same laptop and candidate they exercised System, Light and Dark modes, tested
display scales 1.25, 1.5 and 2, scrolled to the footer at the narrow/short
allocation, and restored appearance and scale afterwards. No screenshots were
taken of those runs. These are the maintainer's reports; I did not observe
them, and no per-step results or timestamps were recorded.

## Still open

- Live DMS palette change and absent/invalid palette fallback were not
  reported as exercised.
- The 1.25/1.5/2 results are not itemised (legibility, obscured content).

Old architecture text in `docs/adr/001-carbon-web-ui-architecture.md`
(boolean dark mode, JS drag) was reconciled with the accepted behavior.
This does not change `release-acceptance.json`. The screenshots above contain
only the Threshold window.
