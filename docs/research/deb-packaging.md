# Debian Packaging for Meson-built Python GTK4 + libadwaita App

**Target**: Ubuntu 24.04 LTS (`noble`), forward-compatible with 25.04 (`plucky`)

---

## 1. Architecture Decision

**`Architecture: all`** — The application is pure Python. Meson's `blueprint-compiler` produces architecture-independent `.ui` XML files from `.blp` sources. No compiled C/C++/Rust binaries are shipped. GSettings XML schemas, desktop entries, icons, and udev rules are all architecture-independent.

`all` packages are built once by the autobuilder and reused across all architectures. This simplifies the build dependency split: `Build-Depends-Indep` can list the bulk of dependencies, with only `debhelper` in `Build-Depends` (required for the `clean` target per Debian Policy).

---

## 2. debian/control

### 2.1 Source package stanzas

| Field | Value | Rationale |
|-------|-------|-----------|
| `Source` | `msi-batteryguard` | Source package name |
| `Section` | `utils` | Fits "Miscellaneous system utilities" |
| `Priority` | `optional` | Default for new packages |
| `Maintainer` | Project maintainer + email | Required |
| `Standards-Version` | `4.7.0` | Latest as of Ubuntu 24.04 era |
| `Homepage` | GitHub repo URL | |
| `Vcs-Browser` / `Vcs-Git` | GitHub repo URL | Optional but recommended |
| `Rules-Requires-Root` | `no` | Pure Python, no root needed for build |

### 2.2 Binary package stanza

| Field | Value | Rationale |
|-------|-------|-----------|
| `Package` | `msi-batteryguard` | Binary package name |
| `Architecture` | `all` | Pure Python |
| `Depends` | `${python3:Depends}, ${misc:Depends}, python3-gi, gir1.2-gtk-4.0, gir1.2-adw-1` | Runtime deps |
| `Recommends` | `msi-ec-dkms` | Kernel module is required at runtime but not a hard dependency (user may build from source) |
| `Suggests` | — | Nothing additional |

- `msi-ec-dkms` goes in `Recommends` (not `Depends`) because: (a) the kernel module source package may not exist yet in Debian/Ubuntu archives — the user may install it manually from GitHub; (b) `Recommends` installs by default with `apt`/`aptitude` but can be explicitly skipped, which is friendlier to users who build `msi-ec` from source.

### 2.3 Build-Depends / Build-Depends-Indep

Since the package is `Architecture: all` only, `Build-Depends-Indep` is the correct place for non-`clean`-target build tools. However, for maximum compatibility with all build environments (including schroot/sbuild), putting everything in `Build-Depends` is simpler and common practice.

```
Build-Depends: debhelper-compat (= 13),
               meson (>= 1.0),
               ninja-build,
               pkg-config,
               desktop-file-utils,
               gettext (>= 0.19.8),
               gobject-introspection,
               python3,
               python3-gi,
               blueprint-compiler,
               libgtk-4-dev,
               libadwaita-1-dev
```

| Package | Purpose |
|---------|---------|
| `debhelper-compat (= 13)` | debhelper version 13 (replaces `debian/compat`) |
| `meson (>= 1.0)` | Build system |
| `ninja-build` | Meson backend |
| `pkg-config` | Finds library paths for meson dependencies |
| `desktop-file-utils` | Validates `.desktop` files during build |
| `gettext (>= 0.19.8)` | i18n message catalog compilation |
| `gobject-introspection` | GI typelib tools; also adds `dh_girepository` support |
| `python3` | Python interpreter for build |
| `python3-gi` | PyGObject bindings (needed for build-time introspection checks, also `gi.repository` module for meson's post-install scripts) |
| `blueprint-compiler` | Compiles `.blp` UI description files to GTK `.ui` XML |
| `libgtk-4-dev` | `gtk4.pc` for pkg-config; pulls in `gir1.2-gtk-4.0` |
| `libadwaita-1-dev` | `libadwaita-1.pc` for pkg-config; pulls in `gir1.2-adw-1` |

### 2.4 Full template

```
Source: msi-batteryguard
Section: utils
Priority: optional
Maintainer: Bongbetic <your-email@example.com>
Build-Depends: debhelper-compat (= 13),
               meson (>= 1.0),
               ninja-build,
               pkg-config,
               desktop-file-utils,
               gettext (>= 0.19.8),
               gobject-introspection,
               python3,
               python3-gi,
               blueprint-compiler,
               libgtk-4-dev,
               libadwaita-1-dev
Standards-Version: 4.7.0
Homepage: https://github.com/Bongbetic/MSI-batteryguard-for-Thin-A15-B7UCX
Vcs-Browser: https://github.com/Bongbetic/MSI-batteryguard-for-Thin-A15-B7UCX
Vcs-Git: https://github.com/Bongbetic/MSI-batteryguard-for-Thin-A15-B7UCX.git
Rules-Requires-Root: no

Package: msi-batteryguard
Architecture: all
Depends: ${python3:Depends},
         ${misc:Depends},
         python3-gi,
         gir1.2-gtk-4.0,
         gir1.2-adw-1
Recommends: msi-ec-dkms
Description: Battery charge threshold controller for MSI laptops
 MSI BatteryGuard provides a GTK4 graphical interface for setting the
 battery charge threshold on MSI laptops. The charge limit is written
 directly to the EC microcontroller via the msi-ec kernel module and
 persists across reboots.
 .
 Typical use cases include setting a 60–80% charge ceiling to extend
 long-term battery lifespan when the laptop is primarily used plugged in.
```

---

## 3. debian/changelog

Format per Debian Policy 4.4:

```
msi-batteryguard (1.0.0-1) noble; urgency=medium

  * Initial release. (Closes: #XXXXXX)

 -- Maintainer Name <email@example.com>  Thu, 30 Jul 2026 12:00:00 +0000
```

**Version convention**: `UPSTREAM_VERSION-DEBIAN_REVISION`:
- `1.0.0-1` — upstream 1.0.0, first Debian packaging revision.
- `1.0.0-1ubuntu1` — Ubuntu-specific rebuild/change on the same Debian revision.

**Distribution**: `noble` for 24.04 LTS; change to `plucky` for 25.04 when targeting that release.

Use `dch(1)` from `devscripts` to create/edit changelog entries. Before release, change `UNRELEASED` to the target distribution.

---

## 4. debian/compat

Do **not** create a standalone `debian/compat` file. Use `debhelper-compat (= 13)` in `Build-Depends` instead. This is the modern approach since debhelper 12+.

**Compat level 13** gives:
- Meson build system auto-detection by `dh_auto_configure`
- Parallel builds enabled by default
- `dh_missing --fail-missing` by default (catches uninstalled files)
- `Rules-Requires-Root: no` support

---

## 5. debian/rules

### 5.1 Minimal rules with `dh` + meson

```makefile
#!/usr/bin/make -f

export DH_VERBOSE = 1

%:
	dh $@ --buildsystem=meson --with python3
```

What happens:
1. `dh_auto_configure` detects `meson.build` and runs:
   ```
   meson setup build --prefix=/usr --sysconfdir=/etc --localstatedir=/var --buildtype=plain
   ```
   (These options are set automatically by dh's meson buildsystem plugin.)

2. `dh_auto_build` runs `meson compile -C build -jN`.

3. `dh_auto_install` runs `DESTDIR=debian/tmp meson install -C build --no-rebuild`.

4. `dh_python3` (from `--with python3`): byte-compiles Python files, fixes shebangs (e.g., `#!/usr/bin/env python3` → `#!/usr/bin/python3`), computes `${python3:Depends}`, installs files into correct `/usr/lib/python3/dist-packages/` if needed.

5. `dh_girepository` (auto-invoked when `gobject-introspection` is in Build-Depends): computes `${gir:Depends}` for packages shipping GI typelib data.

### 5.2 Setting meson options

To override or add meson configure options, use `override_dh_auto_configure`:

```makefile
override_dh_auto_configure:
	dh_auto_configure -- -Dprefix=/usr -Dpython.bytecompile=2
```

The `--` separator passes options directly to `meson setup`. Common overrides:
- `-Dprefix=/usr` (default; explicit for clarity)
- `-Dsysconfdir=/etc` (default; explicit for clarity)
- `-Dpython.bytecompile=2` — optimization level 2 for `.pyc` files

### 5.3 GSettings schema compilation

Since Ubuntu 20.04+, `libglib2.0-0` installs a dpkg trigger on `/usr/share/glib-2.0/schemas/`. When any package places a `.gschema.xml` file there and the dpkg trigger fires, `glib-compile-schemas /usr/share/glib-2.0/schemas` runs automatically. **No explicit postinst handling is required.**

If you want to be explicit (defense-in-depth), add a trigger file:

**`debian/msi-batteryguard.triggers`**:
```
interest-noawait /usr/share/glib-2.0/schemas
```

And optionally add an explicit call in maintainer scripts, though this is redundant with the glib2.0 trigger. The modern GNOME packaging approach relies entirely on the glib2.0 trigger.

### 5.4 Python-specific concerns

| Concern | How it's handled |
|---------|-----------------|
| **Byte-compilation** | `dh_python3` (from `--with python3`) compiles `.py` → `.pyc` with `py_compile` at package build time. Post-install byte-compilation on the target system is handled by Python's import machinery. |
| **Shebang fixing** | `dh_python3` rewrites `#!/usr/bin/env python3` → `#!/usr/bin/python3` for scripts in `/usr/bin/`. |
| **PyGObject `gi` imports** | Works because `python3-gi` is in `Depends`. The `gi.repository` module uses GI typelibs (`gir1.2-gtk-4.0`, `gir1.2-adw-1`) resolved at runtime via the GObject introspection system. No special build-time configuration needed beyond the `-dev` packages providing the `.pc` files. |
| **Architecture-independent package** | `Architecture: all` means the `.deb` is not architecture-specific. `dh_python3` installs to `/usr/lib/python3/dist-packages/` (not the multiarch `lib/python3.X/site-packages`). `dh_strip` and `dh_shlibdeps` are automatically skipped for `all` packages. |
| **Upstream install layout via meson** | Meson's `install_dir` in `meson.build` maps to the package root. With `DESTDIR=debian/tmp`, dh files end up in `debian/tmp/usr/...` and dh copies to the binary package under `debian/msi-batteryguard/`. |

### 5.5 Complete rules template with overrides

```makefile
#!/usr/bin/make -f

export DH_VERBOSE = 1

%:
	dh $@ --buildsystem=meson --with python3

override_dh_auto_configure:
	dh_auto_configure -- -Dprefix=/usr -Dpython.bytecompile=2

override_dh_auto_test:
	@echo "Skipping tests (none defined)"
```

---

## 6. debian/copyright

Use the machine-readable DEP-5 format. Minimal template for a project licensed under e.g., GPL-3+:

```
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: msi-batteryguard
Upstream-Contact: Your Name <your-email@example.com>
Source: https://github.com/Bongbetic/MSI-batteryguard-for-Thin-A15-B7UCX

Files: *
Copyright: 2025-2026 Your Name <your-email@example.com>
License: GPL-3+

Files: debian/*
Copyright: 2026 Your Name <your-email@example.com>
License: GPL-3+

License: GPL-3+
 This program is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.
 .
 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.
 .
 You should have received a copy of the GNU General Public License
 along with this program.  If not, see <https://www.gnu.org/licenses/>.
 .
 On Debian systems, the complete text of the GNU General Public
 License version 3 can be found in `/usr/share/common-licenses/GPL-3`.
```

---

## 7. debian/install (optional)

If meson's `install` target places all files in the correct locations, no `debian/install` file is needed — `dh_auto_install` + `dh_install` handle it automatically.

Use `debian/msi-batteryguard.install` only if you need to move or rename files installed by meson, or install files that meson doesn't handle (e.g., an extra README or man page not in the meson build). Example:

```
debian/extra/some-file  usr/share/msi-batteryguard/
```

For this project, Meson will handle:
- Python script → `/usr/bin/msi-batteryguard`
- Desktop entry → `/usr/share/applications/org.bongbetic.msi-batteryguard.desktop`
- GSettings schema → `/usr/share/glib-2.0/schemas/org.bongbetic.msi-batteryguard.gschema.xml`
- Icons → `/usr/share/icons/hicolor/...`
- Metainfo → `/usr/share/metainfo/org.bongbetic.msi-batteryguard.metainfo.xml`

So no `debian/install` should be necessary.

---

## 8. GSettings Schema Handling

### 8.1 Schema installation in Meson

```meson
# In meson.build:
install_data(
  'data/org.bongbetic.msi-batteryguard.gschema.xml',
  install_dir: get_option('datadir') / 'glib-2.0' / 'schemas',
)
```

### 8.2 Schema XML compilation

The `gschemas.compiled` binary file is **not** shipped in the package. It is generated at install/upgrade time by the `glib-compile-schemas` tool.

Since `libglib2.0-0` (>= 2.48) ships a dpkg trigger on `/usr/share/glib-2.0/schemas/`, any package dropping `.gschema.xml` files there automatically triggers recompilation. The trigger is:

```
$ cat /usr/share/dpkg/triggers/libglib2.0-0
interest-noawait /usr/share/glib-2.0/schemas
```

This means **no explicit postinst or triggers file is required**. The glib package handles it.

### 8.3 Verification

After package installation, verify:

```bash
ls /usr/share/glib-2.0/schemas/gschemas.compiled  # should exist
gsettings list-schemas | grep msi-batteryguard     # should list the schema
```

---

## 9. debian/ Files Summary

| File | Required? | Purpose |
|------|-----------|---------|
| `debian/control` | Yes | Package metadata, dependencies |
| `debian/changelog` | Yes | Version history |
| `debian/copyright` | Yes | License and copyright info |
| `debian/rules` | Yes | Build recipe |
| `debian/compat` | **No** | Use `debhelper-compat (= 13)` in Build-Depends instead |
| `debian/source/format` | Yes | Source format: `3.0 (quilt)` or `3.0 (native)` |
| `debian/install` | No | Only if meson doesn't place all files correctly |
| `debian/msi-batteryguard.install` | No | Per-package install file (rarely needed) |
| `debian/msi-batteryguard.triggers` | No | Not needed; glib2.0 trigger handles schemas |
| `debian/msi-batteryguard.postinst` | No | Not needed; dh_python3 + glib trigger handle everything |
| `debian/msi-batteryguard.prerm` | No | Not needed |
| `debian/watch` | Optional | Upstream release monitoring |

### debian/source/format

Create `debian/source/format` with:
```
3.0 (native)
```
If the packaging lives in the same repo as the source (no separate upstream tarball). Or `3.0 (quilt)` for non-native packages.

For this project (packaging in same repo as upstream source), `3.0 (native)` is appropriate.

---

## 10. Build and Test Commands

```bash
# Install build dependencies
sudo apt build-dep .

# Build the package
dpkg-buildpackage -us -uc -b

# Or with debuild (from devscripts):
debuild -us -uc -b

# Lint the result
lintian ../msi-batteryguard_1.0.0-1_all.deb

# Install and test
sudo apt install ../msi-batteryguard_1.0.0-1_all.deb
msi-batteryguard
```

---

## 11. References

- [Debian Policy Manual](https://www.debian.org/doc/debian-policy/)
- [Debian New Maintainers' Guide](https://www.debian.org/doc/manuals/maint-guide/)
- [Meson Build System documentation](https://mesonbuild.com/)
- [debhelper manpage — dh(1)](https://manpages.debian.org/dh)
- [dh_python3 manpage](https://manpages.debian.org/dh_python3)
- [DEP-5: Machine-readable debian/copyright](https://dep-team.pages.debian.net/deps/dep5/)
- [Ubuntu packaging guide](https://packaging.ubuntu.com/)
- [GLib GSettings documentation](https://docs.gtk.org/gio/class.Settings.html)
