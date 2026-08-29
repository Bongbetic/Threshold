# prototype-carbon-ui

Throwaway layout prototype for wayfinder ticket
["Carbon UI: pick layout direction from prototype variants"](https://github.com/Bongbetic/Threshold/issues/36)
(map: [#34](https://github.com/Bongbetic/Threshold/issues/34)) — **not production code**.

Four structurally different translations of the `prototype-gtk4-ui` directions into
IBM Carbon (@carbon/web-components, g100 dark theme + provisional orange accent):

| Key | Variant | Source direction |
|-----|---------|------------------|
| `a` | Preferences form | `prototype-gtk4-ui/variant_a.ui` |
| `b` | Dashboard tiles | `prototype-gtk4-ui/variant_b.ui` |
| `c` | Side-nav shell | `prototype-gtk4-ui/variant_c.ui` |
| `d` | Industrial grid, scroll-free | `prototype-gtk4-ui/scroll-free/` (Industrial Grid UI Design Specification) |

## Run

Open `index.html` in any browser (double-click). Network is needed on first load for
the Carbon CDN; switch variants with `?variant=a|b|c|d`, the floating pill, or the
arrow keys. Default is `d`, the leading candidate.

The winning layout gets folded into the real implementation; the rest is discarded
(captured on a throwaway branch per the prototype skill).
