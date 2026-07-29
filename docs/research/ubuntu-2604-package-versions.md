# Ubuntu 26.04 LTS ("Resolute") Package Version Research

**Date:** 2026-07-30
**Issue:** [#2](https://github.com/Bongbetic/MSI-batteryguard-for-Thin-A15-B7UCX/issues/2)
**Status:** Complete

## Methodology

Ubuntu 26.04 LTS is codenamed "Resolute Resplandor" and is actively under development (due April 2026). The `packages.ubuntu.com` site already serves the "resolute" suite with live package listings. Version data was collected directly from [packages.ubuntu.com/resolute/](https://packages.ubuntu.com/resolute/) for each requested package. Additionally, "questing" (Ubuntu 25.10 interim) and "noble" (Ubuntu 24.04 LTS) versions were collected to show the upgrade trajectory.

All version strings are verbatim from the package archive as of 2026-07-30.

## Key Package Versions

### GTK4

| Release | Package | Version |
|---------|---------|---------|
| Noble (24.04 LTS) | `libgtk-4-dev` | `4.14.2+ds-1ubuntu1` |
| Questing (25.10) | `libgtk-4-dev` | `4.20.1+ds-2` |
| **Resolute (26.04 LTS)** | **`libgtk-4-dev`** | **`4.22.2+ds-1ubuntu1`** |

> GTK 4.22 corresponds to GNOME 50 (March 2026 release).

### libadwaita

| Release | Package | Version |
|---------|---------|---------|
| Noble (24.04 LTS) | `libadwaita-1-dev` | `1.5.0-1ubuntu2` |
| **Resolute (26.04 LTS)** | **`libadwaita-1-dev`** | **`1.9.0-0ubuntu1`** |

> libadwaita 1.9 requires GTK >= 4.21.1 at build time, which the Resolute GTK 4.22 satisfies.

### Python 3

| Release | Package | Version |
|---------|---------|---------|
| Noble (24.04 LTS) | `python3` | `3.12.3-0ubuntu2.1` (Python 3.12) |
| **Resolute (26.04 LTS)** | **`python3`** | **`3.14.3-0ubuntu2` (Python 3.14)** |

> The default `python3` package provides Python 3.14.x. The `python3-gi` dependency range is `>= 3.14~, << 3.15`.

### PyGObject (python3-gi / GIR bindings)

| Release | Package | Version |
|---------|---------|---------|
| Noble (24.04 LTS) | `python3-gi` | `3.48.2-1` |
| **Resolute (26.04 LTS)** | **`python3-gi`** | **`3.56.2-1`** |

GIR introspection packages:

| Package | Resolute Version |
|---------|-----------------|
| `gir1.2-gtk-4.0` | `4.22.2+ds-1ubuntu1` |
| `gir1.2-adw-1` | `1.9.0-0ubuntu1` |
| `gir1.2-glib-2.0` | `2.88.0-1` |

> Note: Resolute uses GLib 2.88.0 and `libgirepository-2.0-0` (GIRepository API version 3.0), which is a significant bump from Noble's `libgirepository-1.0-1` (GLib 2.80.x).

### blueprint-compiler

| Release | Package | Version |
|---------|---------|---------|
| Noble (24.04 LTS) | `blueprint-compiler` | `0.12.0-1` |
| **Resolute (26.04 LTS)** | **`blueprint-compiler`** | **`0.19.0-2`** |

> Drops the `gir1.2-girepository-2.0` dependency that Noble required; now only depends on `python3` and `python3-gi`.

### Meson

| Release | Package | Version |
|---------|---------|---------|
| Noble (24.04 LTS) | `meson` | `1.3.2-1ubuntu1` |
| **Resolute (26.04 LTS)** | **`meson`** | **`1.10.1-1ubuntu2`** |

> Drops the `python3-pkg-resources` dependency (removed from setuptools 78+). Only depends on `ninja-build`, `python3`, and `python3-setuptools`.

### libnotify

| Release | Package | Version |
|---------|---------|---------|
| Noble (24.04 LTS) | `libnotify-dev` | `0.8.3-1build2` |
| **Resolute (26.04 LTS)** | **`libnotify-dev`** | **`0.8.8-1`** |

### GLib / GObject Introspection

| Release | Package | Version |
|---------|---------|---------|
| Noble (24.04 LTS) | `gir1.2-glib-2.0` | GLib 2.80.x (GIRepo 1.0) |
| **Resolute (26.04 LTS)** | **`gir1.2-glib-2.0`** | **`2.88.0-1`** |

> Resolute uses `libgirepository-2.0-0` (API version 3.0), which means PyGObject 3.56.2 is built against the newer GIRepository ABI. This is a transparent change for consumers but could matter for any C code linking directly to libgirepository.

## Summary Table: Minimum Dependency Versions for 26.04 LTS

| Dependency | Minimum Version in 26.04 | Debian Package Name |
|-----------|------------------------|-------------------|
| GTK4 | 4.22.2 | `libgtk-4-dev`, `gir1.2-gtk-4.0` |
| libadwaita | 1.9.0 | `libadwaita-1-dev`, `gir1.2-adw-1` |
| Python 3 | 3.14.3 | `python3` |
| PyGObject | 3.56.2 | `python3-gi` |
| GLib | 2.88.0 | `gir1.2-glib-2.0` |
| Blueprint Compiler | 0.19.0 | `blueprint-compiler` |
| Meson | 1.10.1 | `meson` |
| libnotify | 0.8.8 | `libnotify-dev` |

## Implications for This Project

### `meson.build`

- The minimum `dependency('gtk4')` version should be set to `>= 4.22`.
- The minimum `dependency('libadwaita-1')` version should be set to `>= 1.9`.
- Python 3.14 is available; ensure code is compatible.

### `debian/control`

- `Build-Depends` should reference `libgtk-4-dev (>= 4.22)`, `libadwaita-1-dev (>= 1.9)`.
- `Depends` for runtime GIR bindings: `gir1.2-gtk-4.0`, `gir1.2-adw-1`.
- Python 3.14 runtime is available; ensure `python3 (>= 3.12)` is compatible or tighten.

### API Considerations

- **GTK 4.22**: Part of GNOME 50. Check for deprecated symbols removed between 4.14 and 4.22.
- **libadwaita 1.9**: Requires GTK >= 4.21.1. Check widget/dialog API changes from 1.5.
- **Python 3.14**: Check for removed modules (PEP 594 cleanups continue). Verify `gi` module compatibility.
- **PyGObject 3.56**: Uses GIRepository API version 3.0 — transparent for Python consumers.
- **Blueprint 0.19**: Check for syntax changes from 0.12.

## Sources

- [packages.ubuntu.com - noble (24.04 LTS)](https://packages.ubuntu.com/noble/)
- [packages.ubuntu.com - questing (25.10)](https://packages.ubuntu.com/questing/)
- [packages.ubuntu.com - resolute (26.04 LTS)](https://packages.ubuntu.com/resolute/)
- GNOME release schedule: [release.gnome.org/calendar/](https://release.gnome.org/calendar/)
