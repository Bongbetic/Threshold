# Debian 13 ("trixie") Package Versions — Research Notes

This document records the package versions available in the **Debian 13 stable**
archive (codename **`trixie`**) for the packages relevant to the
`MSI-batteryguard-for-Thin-A15-B7UCX` project, and compares them against the
project's `meson.build` dependency constraints.

All package versions below were read directly from the live
`packages.debian.org` page for the **`trixie`** suite (each of the 23 package
pages returned HTTP 200 and is titled "Debian — Details of package `<pkg>` in
trixie"). Each package is cited inline as
`https://packages.debian.org/trixie/<pkg>`.

> Codename confirmation: the official Debian 13 codename is **`trixie`**
> (t-r-i-x-i-e), as printed on every Debian release / news page and in the
> `packages.debian.org` suite selector (which labels the suite "`trixie`
> (stable)"). The path `/releases/trixy/` returns a 404; the valid suite path is
> `trixie`.

---

## 1. Debian 13 (trixie) release status

| Item | Value | Source |
| --- | --- | --- |
| Official codename | **`trixie`** (codename for Debian 13) | <https://www.debian.org/News/2025/20250809> — "its new stable version 13 (code name trixie)" |
| Suite status | **stable** | <https://www.debian.org/releases/trixie/> (page title: "Debian — Debian "trixie" Release Information"); `packages.debian.org` suite selector labels it "`trixie` (stable)" |
| Initial release (13.0) date | **August 9, 2025** | <https://www.debian.org/releases/trixie/> ; <https://www.debian.org/News/2025/20250809> |
| Current point release | **13.6** | <https://www.debian.org/releases/trixie/> — "Debian 13.6 was released on July 11th, 2026" |
| Latest point-release date | **July 11, 2026** | <https://www.debian.org/News/2026/20260711> — "Updated Debian 13: 13.6 released ... July 11th, 2026" |
| Support lifecycle | 3 years full support (until Aug 9, 2028) + 2 years LTS (until Jun 30, 2030) | <https://www.debian.org/releases/trixie/> |

For reference, Debian 13 "trixie" ships with **GNOME 48**
(<https://www.debian.org/News/2025/20250809>), which is consistent with the
GTK 4.18 / libadwaita 1.7 versions found below (GNOME 48 was built against
GTK 4.18 and libadwaita 1.7).

### Supported architectures (initial release)
amd64, arm64, armhf, ppc64el, riscv64, s390x — plus i386 (co-architecture only)
and armel (upgrade-only). Source: <https://www.debian.org/releases/trixie/>

---

## 2. Package versions in Debian 13 (trixie)

Each row cites the per-package `packages.debian.org` page fetched from the
`trixie` suite. The version shown is the version currently published in the
`trixie` suite — i.e. including the 13.6 point-release/security updates (which
is why several packages carry a `~deb13u*` Debian revision suffix on top of the
base `trixie` version).

### GTK 4

| Package | Debian version (trixie) | Upstream version | Source URL |
| --- | --- | --- | --- |
| `libgtk-4-dev` | `4.18.6+ds-2` | GTK **4.18.6** | <https://packages.debian.org/trixie/libgtk-4-dev> |
| `gir1.2-gtk-4.0` | `4.18.6+ds-2` | GTK **4.18.6** | <https://packages.debian.org/trixie/gir1.2-gtk-4.0> |

(`+ds-2` = DFSG-repacked source; the underlying upstream GTK version is 4.18.6.)

### libadwaita

| Package | Debian version (trixie) | Upstream version | Source URL |
| --- | --- | --- | --- |
| `libadwaita-1-dev` | `1.7.6-1~deb13u1` | libadwaita **1.7.6** | <https://packages.debian.org/trixie/libadwaita-1-dev> |
| `gir1.2-adw-1` | `1.7.6-1~deb13u1` | libadwaita **1.7.6** | <https://packages.debian.org/trixie/gir1.2-adw-1> |

(`~deb13u1` = first Debian 13 point-release/security update; upstream 1.7.6.)

### Python 3

| Package | Debian version (trixie) | Upstream version | Source URL |
| --- | --- | --- | --- |
| `python3` | `3.13.5-1` | Python **3.13.5** | <https://packages.debian.org/trixie/python3> |

### PyGObject

| Package | Debian version (trixie) | Upstream version | Source URL |
| --- | --- | --- | --- |
| `python3-gi` (PyGObject) | `3.50.0-4` | PyGObject **3.50.0** | <https://packages.debian.org/trixie/python3-gi> |

### Tooling and bindings

| Package | Debian version (trixie) | Upstream version | Source URL |
| --- | --- | --- | --- |
| `blueprint-compiler` | `0.16.0-3` | **0.16.0** | <https://packages.debian.org/trixie/blueprint-compiler> |
| `meson` | `1.7.0-1` | **1.7.0** | <https://packages.debian.org/trixie/meson> |
| `ninja-build` | `1.12.1-1` | **1.12.1** | <https://packages.debian.org/trixie/ninja-build> |
| `pkg-config` | `1.8.1-4` | **1.8.1** (pkgconf-based) | <https://packages.debian.org/trixie/pkg-config> |
| `gobject-introspection` | `1.84.0-1` | **1.84.0** | <https://packages.debian.org/trixie/gobject-introspection> |

### libnotify

| Package | Debian version (trixie) | Upstream version | Source URL |
| --- | --- | --- | --- |
| `libnotify-dev` | `0.8.6-1` | libnotify **0.8.6** | <https://packages.debian.org/trixie/libnotify-dev> |
| `gir1.2-notify-0.7` | `0.8.6-1` | libnotify **0.8.6** | <https://packages.debian.org/trixie/gir1.2-notify-0.7> |

### GLib

| Package | Debian version (trixie) | Upstream version | Source URL |
| --- | --- | --- | --- |
| `libglib2.0-dev` | `2.84.4-3~deb13u3` | GLib **2.84.4** | <https://packages.debian.org/trixie/libglib2.0-dev> |
| `gir1.2-glib-2.0` | `2.84.4-3~deb13u3` | GLib **2.84.4** | <https://packages.debian.org/trixie/gir1.2-glib-2.0> |

(`~deb13u3` = third Debian 13 point-release/security update; upstream 2.84.4.)

### Utilities

| Package | Debian version (trixie) | Upstream version | Source URL |
| --- | --- | --- | --- |
| `desktop-file-utils` | `0.28-1` | **0.28** | <https://packages.debian.org/trixie/desktop-file-utils> |
| `gettext` | `0.23.1-2` | **0.23.1** | <https://packages.debian.org/trixie/gettext> |

### Packaging/build-infrastructure packages (part 4)

| Package | Debian version (trixie) | Status | Source URL |
| --- | --- | --- | --- |
| `dkms` | `3.2.2-1~deb13u1` | present | <https://packages.debian.org/trixie/dkms> |
| `debhelper` | `13.24.2` | present | <https://packages.debian.org/trixie/debhelper> |
| `dh-python` | `6.20250414` | present | <https://packages.debian.org/trixie/dh-python> |
| `dpkg-dev` | `1.22.22` | present | <https://packages.debian.org/trixie/dpkg-dev> |
| `lintian` | `2.122.0` | present | <https://packages.debian.org/trixie/lintian> |
| `appstream` | `1.0.5-1` | present | <https://packages.debian.org/trixie/appstream> |

---

## 3. Comparison with the project's `meson.build`

Project constraints (`meson.build`, lines 21–22):

```meson
dependency('gtk4', version: '>= 4.14')
dependency('libadwaita-1', version: '>= 1.5')
```

…and the project-level Meson floor (`meson.build`, line 4):

```meson
meson_version: '>= 1.0.0'
```

| Project constraint | Debian 13 (trixie) version | Comparison | Satisfied? |
| --- | --- | --- | --- |
| `gtk4` >= **4.14** | GTK **4.18.6** (`libgtk-4-dev` / `gir1.2-gtk-4.0`) | 4.18.6 ≥ 4.14 | ✅ Yes |
| `libadwaita-1` >= **1.5** | libadwaita **1.7.6** (`libadwaita-1-dev` / `gir1.2-adw-1`) | 1.7.6 ≥ 1.5 | ✅ Yes |
| Meson >= **1.0.0** | Meson **1.7.0** | 1.7.0 ≥ 1.0.0 | ✅ Yes |

### Conclusion: do the constraints need updating?

**No update is required for Debian 13 (trixie) compatibility.** Every dependency
floor in the project's `meson.build` is already satisfied by the stable
package versions shipped in trixie:

- GTK 4.18.6 is comfortably above the `>= 4.14` floor.
- libadwaita 1.7.6 is above the `>= 1.5` floor.
- Meson 1.7.0 is above the `>= 1.0.0` floor.

Because the trixie versions are *newer* than the declared minimums, the project
will configure and build against the stable Debian 13 packages with **no
`meson.build` changes**.

### Optional note (not required)

Since the shipped trixie versions exceed the minimums, the team *could* raise the
lower bounds (e.g. to `gtk4 >= 4.18` / `libadwaita-1 >= 1.7`) to pin to the
exact versions in current Debian stable and to gate on newer GTK/libadwaita API.
This is **optional** and would narrow compatibility with other distributions
that still ship the 4.14 / 1.5 era, so it is **not** recommended merely for trixie
support. The current constraints already build cleanly on Debian 13.

---

## 4. Summary table

| Category | Package | Debian 13 (trixie) version | >= requirement? |
| --- | --- | --- | --- |
| GTK 4 | `libgtk-4-dev` | 4.18.6+ds-2 (4.18.6) | ✅ >= 4.14 |
| GTK 4 | `gir1.2-gtk-4.0` | 4.18.6+ds-2 (4.18.6) | ✅ >= 4.14 |
| libadwaita | `libadwaita-1-dev` | 1.7.6-1~deb13u1 (1.7.6) | ✅ >= 1.5 |
| libadwaita | `gir1.2-adw-1` | 1.7.6-1~deb13u1 (1.7.6) | ✅ >= 1.5 |
| Python | `python3` | 3.13.5-1 (3.13.5) | — |
| PyGObject | `python3-gi` | 3.50.0-4 (3.50.0) | — |
| Blueprint | `blueprint-compiler` | 0.16.0-3 (0.16.0) | — |
| Build | `meson` | 1.7.0-1 (1.7.0) | ✅ >= 1.0.0 |
| Build | `ninja-build` | 1.12.1-1 (1.12.1) | — |
| Build | `pkg-config` | 1.8.1-4 (pkgconf 1.8.1) | — |
| Introspection | `gobject-introspection` | 1.84.0-1 (1.84.0) | — |
| libnotify | `libnotify-dev` | 0.8.6-1 (0.8.6) | — |
| libnotify | `gir1.2-notify-0.7` | 0.8.6-1 (0.8.6) | — |
| GLib | `libglib2.0-dev` | 2.84.4-3~deb13u3 (2.84.4) | — |
| GLib | `gir1.2-glib-2.0` | 2.84.4-3~deb13u3 (2.84.4) | — |
| Utilities | `desktop-file-utils` | 0.28-1 (0.28) | — |
| Utilities | `gettext` | 0.23.1-2 (0.23.1) | — |
| Infrastructure | `dkms` | 3.2.2-1~deb13u1 (3.2.2) | — |
| Infrastructure | `debhelper` | 13.24.2 | — |
| Infrastructure | `dh-python` | 6.20250414 | — |
| Infrastructure | `dpkg-dev` | 1.22.22 | — |
| Infrastructure | `lintian` | 2.122.0 | — |
| Infrastructure | `appstream` | 1.0.5-1 | — |

### Source index

Release information:
- <https://www.debian.org/releases/trixie/> (Debian 13 "trixie" release information)
- <https://www.debian.org/News/2025/20250809> (Debian 13.0 initial release, August 9, 2025)
- <https://www.debian.org/News/2026/20260711> (Debian 13.6 point release, July 11, 2026)

Package versions — all `https://packages.debian.org/trixie/<pkg>`:
`libgtk-4-dev`, `gir1.2-gtk-4.0`, `libadwaita-1-dev`, `gir1.2-adw-1`,
`python3`, `python3-gi`, `blueprint-compiler`, `meson`, `ninja-build`,
`pkg-config`, `gobject-introspection`, `libnotify-dev`, `gir1.2-notify-0.7`,
`libglib2.0-dev`, `gir1.2-glib-2.0`, `desktop-file-utils`, `gettext`,
`dkms`, `debhelper`, `dh-python`, `dpkg-dev`, `lintian`, `appstream`.

---

*Generated during a research task; see `meson.build` (project root) for the
authoritative source of the `gtk4` / `libadwaita-1` version constraints.*
