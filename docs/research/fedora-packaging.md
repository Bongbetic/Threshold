# Fedora Packaging for Threshold — spec, deps, DKMS research notes

**Scope:** A Fedora `.spec` for the GTK4/Python meson-built Threshold 1.4.x app,
carried in a GitHub Release RPM (charter: *not* COPR, *not* official Fedora —
see map issue #35). Researched Aug 2026 against primary sources cited inline;
claims tagged `[n]` and mapped to URLs in **[Sources](#sources)**.

Ticket: #43. Answer summary up front:

1. **Deps:** runtime `python3-gobject gtk4 libadwaita libnotify hicolor-icon-theme`;
   build `meson ninja-build blueprint-compiler gtk4-devel libadwaita-devel python3-devel
   python3-gobject desktop-file-utils libappstream-glib gettext systemd-rpm-macros`.
2. **Permissions:** Fedora has no `plugdev`. The systemd `uaccess` tag cannot help
   (it manages ACLs on *device nodes*, not sysfs attributes like
   `charge_control_end_threshold`). Ship a `sysusers.d` group (`threshold`),
   `sed` the bundled rule from `plugdev` → `threshold`, and let the app's
   existing `pkexec` fallback cover everyone else.
3. **Matrix:** F40/41/42 are **EOL** (May 2025 / Dec 2025 / May 2026). Build for
   **F43 + F44** (both `current`), add F45 when it branches in Oct 2026.

---

## 1. Runtime and build dependencies (Fedora names)

The deb's `Build-Depends`/`Depends` map to Fedora as follows. Fedora package
naming differs from Debian: GIR typelibs live in the **main** library package,
not a separate `gir1.2-*` package — e.g. `gtk4` ships
`/usr/lib64/girepository-1.0/Gtk-4.0.typelib` while `.gir` + headers are in
`gtk4-devel` [6][7][8]. PyGObject's binary package is `python3-gobject`
(source package `pygobject3`) [9].

| Debian | Fedora runtime pkg | Fedora build pkg | Why / source |
|---|---|---|---|
| `python3-gi` | `python3-gobject` | `python3-gobject` | PyGI bindings [9] |
| `gir1.2-gtk-4.0` | `gtk4` | `gtk4-devel` | typelib in main pkg [6] |
| `gir1.2-adw-1` | `libadwaita` | `libadwaita-devel` | typelib in main pkg [7] |
| `gir1.2-notify-0.7` | `libnotify` | `libnotify-devel` (optional) | `Notify-0.7.typelib` in main pkg [8] |
| `gir1.2-dbusmenu-glib-0.4` | — none needed | — | tray.py implements SNI/dbusmenu over raw D-Bus (Gio), no gir import in `src/threshold/` |
| `libgtk-4-dev` etc. | — | covered above | |
| `gettext (>= 0.19.8)` | — | `gettext` | `i18n.gettext(preset: 'glib')` in `po/meson.build` |
| `meson`, `ninja-build` | — | `meson`, `ninja-build` | |
| `blueprint-compiler` | — | `blueprint-compiler` | meson falls back to committed `ui/window.ui` if absent, but require it so the `.blp` is the thing actually compiled; available since F41 [10] |
| `desktop-file-utils` | — | `desktop-file-utils` | `desktop-file-validate` in `%check` |
| — | — | `libappstream-glib` | `appstream-util validate-relax` in `%check` (Fedora AppData guideline) [11] |
| — | `hicolor-icon-theme` | — | installs into `%{_datadir}/icons/hicolor` (dir ownership) |
| — | — | `systemd-rpm-macros` | provides `%{_udevrulesdir}` macro [12] |
| — | — | `python3-devel` | provides `%py_byte_compile` macro [13] |
| `dkms (>= 2.2)` | `dkms` (subpackage `Requires:`) | — | Fedora ships dkms 3.x, same CLI as deb [14] |

Runtime also benefits from `polkit` (`pkexec`) — the app falls back to
`pkexec tee` when the direct sysfs write is denied (`src/threshold/battery.py`);
`pkexec` is in the default Fedora Workstation install (polkit is a base
dependency of systemd/logind era default install; explicit `Requires:` not
strictly needed but harmless as `Recommends:`).

## 2. Meson inside rpmbuild/mock

Standard Fedora macros, shipped by the `meson` package itself
(`data/macros.meson` in the meson source) [15]:

```spec
%build
%meson
%meson_build

%install
%meson_install
```

`%meson` runs `setup --buildtype=plain` with all Fedora dir paths
(`%{_prefix}`, `%{_datadir}`, …) against `%{_vpath_srcdir}`/`%{_vpath_builddir}`
(out-of-tree, matches Fedora's vpath convention). No `-Dprefix=` overrides
needed. The project's `gnome.post_install(...)` calls (schema compile, icon
cache, desktop db) run at `meson install` time inside the buildroot — they are
**no-ops for packaging** (the real system caches are refreshed by file
triggers, see §4) and safe.

Bytecode: Threshold's Python lives in
`%{_datadir}/com.bongbetic.threshold/threshold/`, **not** in
`%{python3_sitelib}`, so Fedora's automatic `brp-python-bytecompile` does not
touch it. Byte-compile manually in `%install` and own the `__pycache__` files,
otherwise Python writes untracked `.pyc` at first run (guidelines explicitly
recommend `%py_byte_compile` for exactly this layout) [13]:

```spec
%install
%meson_install
%py_byte_compile %{python3} %{buildroot}%{_datadir}/com.bongbetic.threshold/threshold/
```

```spec
%files
# …
%{_datadir}/com.bongbetic.threshold/threshold/          # includes __pycache__/*.pyc
```

Architecture: pure Python + data ⇒ `BuildArch: noarch` (same reasoning as the
deb's `Architecture: all`). The launcher `src/threshold.in` gets its shebang
from `find_program('python3')` at configure time — inside mock the buildroot
python3 path equals the installed path (`/usr/bin/python3`), so no
`%py3_shebang_fix` needed. Optionally set
`-Dpython-bytecompile=2` irrelevant to RPM (that meson option only affects
`meson install` dev installs; RPM path uses `%py_byte_compile` above).

`%check`: run `desktop-file-validate` on the desktop entry and
`appstream-util validate-relax` on the metainfo (guideline wording) [11].
The meson test suite needs a display for GTK imports — skip it (`%meson_test
|| :`) or gate it behind a bcond.

**Build flow:**

```bash
# SRPM (any Fedora machine / container)
rpmbuild -bs threshold.spec --define '_sourcedir .' --define '_srcrpmdir .'
# Rebuild reproducibly against a clean chroot
mock -r fedora-43-x86_64 --clean threshold-1.4.1-1.fc43.src.rpm
mock -r fedora-44-x86_64 --clean threshold-1.4.1-1.fc44.src.rpm
```

`mock` config names follow `fedora-<version>-<arch>.cfg`, generated per release
by `mock-core-configs` [16]. In CI (GitHub Actions) mock's systemd-nspawn
chroot needs a privileged runner; the pragmatic GH-Release pattern is
`container: fedora:43` + `dnf install -y rpm-build …` + `rpmbuild -ba`, with
mock kept for local/repro verification. (Charter only asks for a GitHub
Release RPM, not a Fedora-compliant build farm.)

## 3. Spec skeleton (recommended)

```spec
Name:           threshold
Version:        1.4.1
Release:        1%{?dist}
Summary:        Battery charge threshold controller for Linux laptops
License:        GPL-3.0-or-later
URL:            https://github.com/Bongbetic/Threshold
Source0:        %{url}/archive/v%{version}/%{name}-%{version}.tar.gz
BuildArch:      noarch

BuildRequires:  meson
BuildRequires:  ninja-build
BuildRequires:  pkgconf-pkg-config
BuildRequires:  gettext
BuildRequires:  blueprint-compiler
BuildRequires:  gtk4-devel >= 4.14
BuildRequires:  libadwaita-devel >= 1.5
BuildRequires:  python3-devel
BuildRequires:  python3-gobject
BuildRequires:  desktop-file-utils
BuildRequires:  libappstream-glib
BuildRequires:  systemd-rpm-macros

Requires:       python3-gobject
Requires:       gtk4 >= 4.14
Requires:       libadwaita >= 1.5
Requires:       libnotify
Requires:       hicolor-icon-theme
Recommends:     %{name}-msi-ec-dkms

%description
…(copy deb long description)…

%package msi-ec-dkms
Summary:        DKMS source for the msi-ec kernel module (bundled)
BuildArch:      noarch
Requires:       dkms
Requires(post): dkms
Requires(preun): dkms
# dkms itself pulls kernel-devel-matched for the running kernel (rich dep) [14]

%description msi-ec-dkms
Bundled msi-ec 0.13.112 kernel module source, built against the running
kernel at install time via DKMS. Mirrors the Debian package's /usr/src bundle.

%prep
%autosetup -p1 -n %{name}-%{version}
# plugdev is a Debian-ism; Fedora gets a dedicated system group (§5)
sed -i 's/\bplugdev\b/threshold/g' data/99-msi-battery.rules

%build
%meson
%meson_build

%install
%meson_install
%py_byte_compile %{python3} %{buildroot}%{_datadir}/com.bongbetic.threshold/threshold/

install -Dpm 0644 -t %{buildroot}%{_sysusersdir} %{SOURCE1}   # threshold sysusers.d file

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/com.bongbetic.threshold.desktop
appstream-util validate-relax %{buildroot}%{_metainfodir}/com.bongbetic.threshold.metainfo.xml

%post
# group already exists via sysusers.d; reload rules
udevadm control --reload-rules || :
udevadm trigger --subsystem-match=power_supply || :

%post msi-ec-dkms
msi_ec_ver=0.13.112
if command -v dkms >/dev/null 2>&1; then
    dkms add -m msi-ec -v ${msi_ec_ver} || :
    dkms build -m msi-ec -v ${msi_ec_ver} || :
    dkms install -m msi-ec -v ${msi_ec_ver} || :
fi
modprobe msi-ec || :

%preun msi-ec-dkms
if [ "$1" = "0" ]; then
    dkms remove -m msi-ec -v 0.13.112 --all || :
fi

%files
%license LICENSE
%doc README.md
%{_bindir}/threshold
%{_datadir}/com.bongbetic.threshold/
%{_datadir}/applications/com.bongbetic.threshold.desktop
%{_metainfodir}/com.bongbetic.threshold.metainfo.xml
%{_datadir}/glib-2.0/schemas/com.bongbetic.threshold.gschema.xml
%{_datadir}/glib-2.0/schemas/com.bongbetic.batteryguard.gschema.xml
%{_datadir}/GConf/gsettings/com.bongbetic.batteryguard.convert
%{_datadir}/icons/hicolor/*/apps/*.svg
%{_datadir}/locale/*/LC_MESSAGES/*.mo
%{_udevrulesdir}/99-msi-battery.rules
%{_sysusersdir}/threshold.conf

%files msi-ec-dkms
%{_usrsrc}/msi-ec-0.13.112/
%{_modulesloaddir}/msi-ec.conf   # created in %%install: "msi-ec" → autoload

%changelog
…
```

Notes:

- **No icon-cache / desktop-database / glib-schema scriptlets.** See §4 —
  RPM file triggers own those caches on every Fedora release this spec targets.
- `Source1` is a two-line sysusers.d file (§5).
- udev rule installs to `%{_udevrulesdir}` = `/usr/lib/udev/rules.d` (macro
  from `systemd-rpm-macros` [12]) — same non-`/etc` location lintian enforced
  on the deb side.
- `python-bytecompile-errors` brp pitfalls avoided by owning `__pycache__`
  via the directory entry in `%files`.

## 4. Icons / desktop / appstream / gschema — no scriptlets

Modern Fedora needs **zero `%post` cache-refresh scriptlets** for these. The
caches are refreshed by **RPM file triggers** owned by the base packages, which
fire when *any* package drops files into the watched directories:

| Cache | File trigger owner | Fires on |
|---|---|---|
| hicolor icon cache | `hicolor-icon-theme` (`%transfiletriggerin -- %{_datadir}/icons/hicolor` → `gtk-update-icon-cache --force`) | any icon added/removed under hicolor [17] |
| desktop database | `desktop-file-utils` (`%transfiletriggerin -- %{_datadir}/applications` → `update-desktop-database`) | any .desktop added/removed [18] |
| GSettings schemas | `glib2` (`%transfiletriggerin -- %{_datadir}/glib-2.0/schemas` → `glib-compile-schemas`) | any schema added/removed [19] |

So the spec's `%files` simply ships (all installed by meson already, no spec
`install` lines needed):

- icons: `%{_datadir}/icons/hicolor/{scalable,symbolic}/apps/*.svg`
- desktop: `%{_datadir}/applications/com.bongbetic.threshold.desktop`
- appstream metainfo: `%{_metainfodir}/com.bongbetic.threshold.metainfo.xml`
  — Fedora's AppData guideline: GUI apps SHOULD install a metainfo into
  `%{_metainfodir}`, and it MUST validate under
  `appstream-util validate-relax` [11] (run it in `%check`).
- gschema: both current + batteryguard-migration schemas + `.convert` map
  (migration path identical to deb).

`meson install` already runs `gnome.post_install` in the buildroot; its cache
writes there are discarded and the file triggers do the real work on the
user's machine.

## 5. udev rule + permissions on Fedora

### 5.1 `plugdev` does not exist

Fedora's system-group registry (`setup` package, `uidgid` file) has no
`plugdev` — the group is a Debian/Ubuntu-ism [5]. Shipping the deb rule
verbatim would leave a chgrp pointing at GID `plugdev` that never resolves.

### 5.2 `TAG+="uaccess"` cannot replace it

The systemd `uaccess` mechanism (recommended Fedora way to grant local-seat
users device access) works only on **device nodes**: the udev builtin opens the
device via `sd_device_open()` and sets a POSIX ACL on the node
("Manage device node user ACL") [4]. `charge_control_end_threshold` is a
**sysfs attribute**, not a device node — there is nothing to ACL. systemd
groups (there is no "systemd group" for this; logind's `uaccess`/seat ACLs are
node-only) don't apply either.

### 5.3 What works: dedicated system group (sysusers.d) + pkexec fallback

Recommended, mirroring the deb UX:

1. Create a group-only system account via **`sysusers.d`** — Fedora's blessed
   mechanism ("to create only a group without a user account … apply only the
   groupadd parts"; dynamic allocation via a
   `sysusers.d/<package-name>.conf` file) [3]. `Source1`:

   ```
   # Type Name ID GECOS
   g threshold -
   ```

2. `sed` the bundled rule `plugdev` → `threshold` (§3 `%prep`). The
   `RUN+="/bin/chgrp"` / `RUN+="/bin/chmod g+w"` pattern is generic udev and
   works identically on Fedora; only the group name was Debian-specific.
3. One-time user action, same as deb docs: `sudo usermod -aG threshold $USER`.
4. Users who don't join the group still work: `battery.py` falls back to
   `pkexec tee` (PolicyKit auth dialog) — `pkexec` ships in Fedora's default
   install. Passwordless-if-grouped, dialog-if-not: strictly better than deb.

Alternatives rejected:

- `wheel` group — conflates laptop battery tuning with full sudo. No.
- `users` group (GID 100, exists on Fedora [5]) — every human user is in it;
  granting all users EC write is broader than the deb behavior. No.
- Polkit-only (no udev rule) — would match where upstream GNOME extensions
  (e.g. Battery-Health-Charging) ended up [20], but requires app changes;
  keep as future option.

Follow-up app change (out of this ticket): the failure string at
`battery.py:243` says "join the plugdev group" — needs distro-aware wording.

## 6. DKMS source subpackage mirroring the deb msi-ec bundle

The deb (`debian/threshold.postinst`) bundles `msi-ec-src` (v0.13.112) under
`/usr/src`, runs `dkms add/build/install`, writes
`/usr/lib/modules-load.d/msi-ec.conf`, and falls back to notification-only
mode on failure (Secure Boot note via MOK). Mirror it as a `noarch`
subpackage:

- **Files:** `%{_usrsrc}/msi-ec-0.13.112/` = repo's `msi-ec-src/` tree
  (`msi-ec.c`, `ec_memory_configuration.h`, `Makefile`, `Makefile.vars`,
  `dkms.conf`, `LICENSE`). `dkms.conf` already has `AUTOINSTALL="yes"` and
  kernel-build-dir `MAKE[0]` — kernel-agnostic, works with Fedora's
  `/lib/modules/$(uname -r)/build` → `kernel-devel` layout.
- **Deps:** `Requires: dkms` only. Fedora's own `dkms` package carries the
  rich dependencies (`(kernel-devel-matched if kernel-core)` etc.) so headers
  track installed kernels automatically [14].
- **%post:** `dkms add/build/install` (same sequence as deb postinst). Kernel
  updates: Fedora dkms ships `dkms.service` (boot-time autoinstaller) **and**
  a `kernel-install.d/40-dkms.install` hook [14], so `AUTOINSTALL="yes"`
  rebuilds on each new kernel — same as deb.
- **%preun:** `dkms remove -m msi-ec -v 0.13.112 --all` on erase.
- **Autoload:** ship `%{_modulesloaddir}/msi-ec.conf` containing `msi-ec`
  (spec `%install` creates it; or a meson install_data — follow-up).
- **Secure Boot:** unsigned DKMS modules won't load with SB enabled; keep the
  deb's MOK guidance (`mokutil --import`) in `%post` output/docs. Akmods-style
  signing is out of charter scope.
- Failure tolerance: `|| :` on dkms steps; app degrades to notification mode
  (same contract as deb).

Fedora note: packaging kernel modules in the *official* Fedora collection is
restricted, but this RPM is a GitHub Release artifact (charter), where DKMS is
the standard third-party pattern and the `dkms` tool itself is in Fedora
repos [14].

## 7. Fedora release matrix

Release lifecycle (Bodhi release records) [2]:

| Fedora | State (Aug 2026) | EOL | gtk4 | libadwaita | pygobject3 | blueprint-compiler | dkms |
|---|---|---|---|---|---|---|---|
| F40 | archived | 2025-05-13 | 4.14.x | 1.5.x | 3.48 | 0.12 | 3.0.x |
| F41 | archived | 2025-12-15 | 4.16.x | 1.6.x | 3.50 | 0.16 | 3.1.x |
| F42 | archived | 2026-05-27 | 4.18.5 | 1.7.4 | 3.52 | 0.16 | 3.2.x |
| **F43** | **current** | 2026-12-02 | 4.20.x | 1.8.x | 3.56 | 0.20.x | 3.4.x |
| **F44** | **current** | 2027-06-02 | 4.22.x | 1.9.x | 3.56 | 0.20.4 | 3.4.3 |

(Version columns from koji build trees: gtk4 [6], libadwaita [7], pygobject3
[9], blueprint-compiler [10], dkms [14].)

- **Meson floor (`gtk4 >= 4.14`, `libadwaita >= 1.5`) is met by every release
  F40→F44**; only the EOL dates disqualify targets.
- The issue's proposed **F40/41/42 matrix is stale** — all three are archived.
  F42 went EOL 2026-05-27, three months before this research.
- **Recommendation: build F43 + F44** for the GH Release (two `fedora:43` /
  `fedora:44` container jobs, or one SRPM + two mock runs). Add **F45** when it
  branches (Oct 2026, `f45` dist tag already visible in koji tags). Any F40+
  RPM will *install* on newer Fedoras (noarch, no hard soname deps) — the
  matrix is about tested support, not installability.

## 8. Open follow-ups (for map #35, not this ticket)

- Upstream meson option for the udev group name (`-Dudev-group=`) to kill the
  spec-side `sed`.
- Distros-aware "join plugdev" string in `battery.py` failure path.
- Decide CI shape: two fedora containers vs one SRPM + mock per target.
- Release hygiene items already listed in map #35 "Not yet specified".

---

## Sources

1. Issue #43 question + map #35 charter (GitHub).
   https://github.com/Bongbetic/Threshold/issues/43
2. Bodhi release records, `releases/F40` … `releases/F44` (state/eol fields), fetched 2026-08-28.
   https://bodhi.fedoraproject.org/releases/F43
3. Fedora Packaging Guidelines — Users and Groups (dynamic allocation, sysusers.d, group-only accounts).
   https://docs.fedoraproject.org/en-US/packaging-guidelines/UsersAndGroups/
4. systemd source — `src/udev/udev-builtin-uaccess.c` ("Manage device node user ACL", opens device node, sets ACL).
   https://github.com/systemd/systemd/blob/main/src/udev/udev-builtin-uaccess.c
5. Fedora `setup` package `uidgid` file (group registry; no plugdev, users=100, wheel, video).
   https://src.fedoraproject.org/rpms/setup/blob/rawhide/f/uidgid
6. gtk4 package (spec %files: typelibs in main pkg, gir in -devel; koji version tree 4.14→4.22 by fc tag).
   https://src.fedoraproject.org/rpms/gtk4 and https://kojipkgs.fedoraproject.org/packages/gtk4/
7. libadwaita package (typelib in main pkg; koji tree).
   https://src.fedoraproject.org/rpms/libadwaita and https://kojipkgs.fedoraproject.org/packages/libadwaita/
8. libnotify spec (`Notify-0.7.typelib` in main pkg).
   https://src.fedoraproject.org/rpms/libnotify/blob/rawhide/f/libnotify.spec
9. pygobject3 package (binary pkgs `python3-gobject*`; koji tree 3.48→3.57 by fc tag).
   https://src.fedoraproject.org/rpms/pygobject3 and https://kojipkgs.fedoraproject.org/packages/pygobject3/
10. blueprint-compiler koji tree (0.12 fc40 → 0.20.4 fc44/fc45).
    https://kojipkgs.fedoraproject.org/packages/blueprint-compiler/
11. Fedora Packaging Guidelines — AppData (metainfo SHOULD go to `%{_metainfodir}`, MUST pass `appstream-util validate-relax`).
    https://docs.fedoraproject.org/en-US/packaging-guidelines/AppData/
12. systemd rpm macros (`%_udevrulesdir`, `%_udevhwdbdir`).
    https://github.com/systemd/systemd/blob/main/src/rpm/macros.systemd.in
13. Fedora Packaging Guidelines — Python (brp-python-bytecompile only covers sitelib/sitearch; `%py_byte_compile INTERPRETER PATH` for other dirs; `%py3_shebang_fix`).
    https://docs.fedoraproject.org/en-US/packaging-guidelines/Python/
14. Fedora dkms spec (Requires rich deps incl. `kernel-devel-matched if kernel-core`; ships `dkms.service` + `/usr/lib/kernel/install.d/40-dkms.install`; koji tree 3.0→3.4.3).
    https://src.fedoraproject.org/rpms/dkms and https://kojipkgs.fedoraproject.org/packages/dkms/
15. meson rpm macros (`%meson`, `%meson_build`, `%meson_install`, `%meson_test`).
    https://github.com/mesonbuild/meson/blob/master/data/macros.meson
16. mock-core-configs spec (generates `fedora-$ver-$mock_arch.cfg` per release).
    https://src.fedoraproject.org/rpms/mock-core-configs
17. hicolor-icon-theme spec (file triggers → `gtk-update-icon-cache --force` on `%{_datadir}/icons/hicolor`).
    https://src.fedoraproject.org/rpms/hicolor-icon-theme/blob/rawhide/f/hicolor-icon-theme.spec
18. desktop-file-utils spec (file triggers → `update-desktop-database` on `%{_datadir}/applications`).
    https://src.fedoraproject.org/rpms/desktop-file-utils/blob/rawhide/f/desktop-file-utils.spec
19. glib2 spec (file triggers → `glib-compile-schemas` on `%{_datadir}/glib-2.0/schemas`).
    https://src.fedoraproject.org/rpms/glib2/blob/rawhide/f/glib2.spec
20. Battery-Health-Charging extension (polkit-rules approach as the alternative endgame; `resources/10-dem.*.rules` are polkit.js rules).
    https://github.com/maniacx/Battery-Health-Charging
