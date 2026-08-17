# Debian Archive Submission Process — Research Notes

**Scope:** New package submission for a **Python 3 / GTK 4 + libadwaita desktop GUI**
(`msi-batteryguard`, `Architecture: all`) plus a **DKMS kernel module**
(`msi-ec-dkms`) that ships the upstream `msi-ec` C source in `/usr/src/`.

These notes were researched against the primary Debian sources cited inline
(`developer-reference`, `debian-policy`, `lintian.debian.org`, the DFSG NEW-queue
team, `manpages.debian.org`, and `mentors.debian.net`). Claims are tagged `[n]`
and mapped to URLs in **[Sources](#sources)** at the end.

---

## 1. ITP — Intent To Package

**What it is.** An ITP is a bug filed in the Debian BTS to announce that someone
intends to package a piece of software. It is filed **before** any upload so the
community can spot duplicates and give early feedback.

**Which bug tracker.** The Debian Bug Tracking System (BTS):
- Filing address: `submit@bugs.debian.org` (via the `reportbug` tool, or by hand).
- Filed against the pseudo-package **`wnpp`** (Work-Needing and Prohibited
  Packages) — **not** against a real package name. `reportbug wnpp` walks you
  through it.
- Check for collisions first on the **WNPP page** (`https://www.debian.org/devel/wnpp/`)
  and via `https://bugs.debian.org/<packagename>`.

**Required pseudo-headers / fields** (from `Reporting` + the BTS developer docs
plus Developer's Reference §5.1):

```
To: submit@bugs.debian.org
Subject: ITP: msi-batteryguard -- Battery charge threshold controller for MSI laptops
Package: wnpp
Severity: wishlist
Owner: <your-email@example.com>
X-Debbugs-CC: debian-devel@lists.debian.org
```

Body **must** contain (§5.1): the *description* of the package, the *license* of
the prospective package, and the *current URL where it can be downloaded from*
(the upstream source). Additional useful fields: Upstream Author, VCS, the binary
packages it builds, and a short rationale (why Debian needs it, who the
maintainer is).

**Severity.** Must be `wishlist`.

**Announcing on debian-devel.** Send a copy to `debian-devel@lists.debian.org`
using the **`X-Debbugs-CC`** pseudo-header (not a normal `CC:` — using `CC:`
breaks subject threading so the bug number is not attached). §5.1 explicitly
says: *"Please send a copy to debian-devel@lists.debian.org by using the
X-Debbugs-CC header."* For 10+ ITPs at once, post a summary to the list instead.

**Closing the ITP.** Put `Closes: #<ITP-bug-number>` in the **first** entry of
`debian/changelog` so the BTS auto-closes the bug once the package is installed
in the archive (§5.1, §5.9.4). `reportbug --template`/`dch` can help generate
the entry.

> Note: a lone author who is both upstream and packager may still file the ITP
> themselves — anyone can file a `wnpp` bug. The maintainer need not yet be a
> Debian Developer; what differs is the **upload** (see §6 sponsorship).

---

## 2. The NEW queue — what the FTP Masters / DFSG team check

**Where uploads land.** Source + binary packages are uploaded (signed with a key
in the **Debian Developers** or **Debian Maintainers** keyrings) to
`ftp.upload.debian.org` in `/pub/UploadQueue/` (or `ssh.upload.debian.org`);
`dput`/`dupload` automate this (§5.6.2).

**Who reviews new packages and why.** As of 2026 the licensing/NEW review was
split out from "Archive Operations (FTP)" into the **DFSG, Licensing & New
Packages Team**, which "ensures that new packages entering the Debian archive
comply with the Debian Free Software Guidelines and relevant licensing and legal
requirements" and reviews packages in the NEW queue
(`https://dfsg-new-queue.debian.org/`). Packages remain visible at
`https://ftp-master.debian.org/new.html`.

**When NEW review happens.** Any upload that introduces a *new source package*,
or that adds *new binary packages* to an existing source package, goes to NEW
(§5.6.1). The **first upload of a new source package must include binary
packages** so reviewers can inspect binaries — source-only uploads only happen
after the source is already accepted.

**What reviewers check** (the DFSG team checklist + the sponsor's checklist in
§7.6.1.1, adapted for the NEW gate):
1. **DFSG compliance / license verification.** Is the software actually free?
   Run `licensecheck`, `scancode`, or `fossology` *before* uploading; the DFSG
   team will do its own scan. Packages in `main`/`contrib` must be DFSG-free
   (Policy §2.1, §2.2.1). If the license is complex/non-standard, add a
   `debian/README.source` explaining why it complies (DFSG-team instruction).
2. **Required files present and well-formed:**
   - source package: `.dsc`, `.orig.tar.{gz,xz,...}` (if non-native),
     `.debian.tar.{xz}` (quilt) or `.tar.{xz}` (native);
   - `debian/changelog`, `debian/control`, `debian/copyright`,
     `debian/rules`, `debian/source/format` (Policy §4.4–4.9);
   - `debian/watch` (recommended, §4.11);
   - binary: the `.deb` (built) plus the `.changes`/`.buildinfo`.
3. **Copyright file** carries a verbatim copy of the distribution license(s)
   (Policy §12.5 / §4.5); for GPL/BSD/Apache/etc. it should *reference*
   `/usr/share/common-licenses/*` rather than re-quoting.
4. **Packaging quality:** completeness of `Build-Depends`/`Depends`,
   `debian/rules` non-interactive, correct `Architecture` fields, debhelper
   usage, lintian-clean (see §4), correct build in a clean chroot
   (`pbuilder`/`sbuild`).
5. **No embedded non-free or non-redistributable code** (Policy §4.13, §4.16).
6. **No non-free bits in `main`**; `Section`/`Priority` are hints the archive
   may override (§5.7 "disparity" email).

**Common outcomes.** Accepted → package appears on `tracker.debian.org`; rejected
→ you get a reply (the old `REJECT-FAQ` is now superseded by the DFSG team,
which commits to "every rejection will cite the specific DFSG clause"). You ping
via `dfsg-team@debian.org` with subject `[PING] <pkg>` (aim: status within 2
weeks), or `[URGENT] <pkg>` for RC/critical security fixes.

---

## 3. Debian Policy — sections that apply to a Python/GTK4 GUI + DKMS module

> **Correction on §10.9.** The task prompt lists "Policy §10.9 (GUI
> applications / desktop entries / AppStream)". In Debian Policy Manual **v4.7.x,
> §10.9 is "Locale files"** (ch-files.html §10.9: files in
> `/usr/share/locale/`) — it is about *i18n data*, **not** GUI/desktop. The GUI
> and desktop-entry guidance therefore lives elsewhere; the relevant sections are:

**A. GUI applications / desktop entries / AppStream**
- **Policy §11.8 "Programs for the X Window System"** (ch-customized-programs.html
  §11.8): GUI apps must be configured with X support and must declare runtime
  deps; §11.8.1 (priorities/X deps), §11.8.7 (install dirs — install in the
  normal `/usr` dirs, **not** `/usr/X11R6/`).
- **Policy §9.7.1 "Registration of media type handlers with desktop
  entries"** (ch-opersys.html) and §9.6 (Menus). The authoritative *format*
  spec for `.desktop` files is the **freedesktop.org Desktop Entry Specification**;
  Debian packaging guidance lives on the wiki (`DesktopFiles`, `AppStream/Guidelines`,
  referenced by `lintian`). For Debian archive purposes the file is validated by
  `desktop-file-validate` (from `desktop-file-utils`).
- **AppStream / metainfo** (`*.metainfo.xml` installed under
  `/usr/share/metainfo/`) is **not** in the main Policy Manual; it is governed
  by the **AppStream specification** and validated by `appstreamcli validate`
  (see §5). The existing project file is correctly named
  `com.bongbetic.batteryguard.metainfo.xml` and lives in `data/`.
- **Policy §2.2.1 (`main`):** no `main` package may `Depends`/`Recommends` a
  non-`main` package. (The project's `Recommends: gir1.2-ayatanaappindicatorglib-2.0`
  must itself be in `main` for `msi-batteryguard` to qualify for `main`.)
- **Policy §10.1** (binaries): program names on `PATH` must be ASCII; no two
  packages install conflicting filenames.

**B. Policy §12.5 — Copyright information** (ch-docs.html §12.5)
Every package must ship a verbatim copy of its distribution license(s) in
`/usr/share/doc/PACKAGE/copyright`, and a copy must live in `debian/copyright`
in the source. The file must also state where upstream sources were obtained and
name/contact upstream authors. Licenses in `/usr/share/common-licenses/*`
(GPL, BSD, Apache-2.0, MIT, MPL, etc.) may be referenced rather than quoted.
The **machine-readable DEP-5 format** (`https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/`)
is the modern choice. The existing `debian/copyright` already follows DEP-5 and
references `/usr/share/common-licenses/GPL-3` — correct.

**C. Module / DKMS packaging requirements**
The Debian Policy Manual itself has no kernel-module chapter; out-of-tree modules
are covered by the **Debian Kernel Handbook** (ch. 4.4 "Out-of-tree kernel
modules", §4.4.1 "Building modules with DKMS") and the `dkms(8)` / `dh_dkms(1)`
manpages. The hard, machine-checked rules are:
- Binary package name **must end in `-dkms`** (dh_dkms NOTE: "binary packages
  using dh_dkms must have a name that ends in '-dkms'").
- The module **source** is installed to `/usr/src/<module>-<version>/` together
  with a `dkms.conf` (dkms(8) `add`: "requires source in
  `/usr/src/<module>-<module-version>/` as well as a properly formatted
  dkms.conf file"). DKMS then **builds the module per running kernel/arch at
  install time** (dkms(8) `build`: "builds … for the currently running kernel and
  arch").
- Therefore the `-dkms` **source package is `Architecture: all`** — the source
  is plain text compiled on the target. (The `dkms` framework package itself is
  `Architecture: all`; `_all.deb` filenames confirm this.) The module is
  pulled in via a `postinst` doing `dkms add/build/install`, `prerm`/`postrm`
  doing `dkms remove -m … --all`, and a `triggers` file with
  `interest-noawait /etc/kernel/postinst.d` so it rebuilds on kernel package
  upgrades. The existing `msi-ec-dkms.{postinst,prerm,triggers,install}` follow
  this pattern.
- `Depends: dkms (>= 2.2), ${misc:Depends}`.

> ⚠️ The project declares `msi-ec-dkms` as `Architecture: amd64`. For a DKMS
> **source** package this is non-conventional — source packages that merely ship
> buildable source text are expected to be `Architecture: all`. If `msi-ec` is
> genuinely x86-only (it uses x86 I/O-port access), the correct restriction is
> `Architecture: any [amd64 i386]` (or `all` with `BUILD_EXCLUSIVE_ARCH` in
> `dkms.conf`), **not** bare `amd64`, which wrongly excludes i386.

**D. Architecture: `all` vs `any` for the GUI app**
- Pure-Python GUI with Meson-generated `.ui`, GSettings schemas, desktop/icon/
  metainfo data → no compiled language binaries → **`Architecture: all`** is
  correct (Policy §11.1 "Architecture specification strings"; dev-ref §5.12.1
  #2: "Don't set architecture to a value other than `all` or `any` unless you
  really mean it").
- Because the *source* package produces one `all` binary *and* one arch-specific
  (`amd64`) binary (`msi-ec-dkms`), `debian/rules` must keep working
  `binary-indep` (GUI) and `binary-arch` (DKMS) targets — debhelper's `dh` handles
  this automatically per binary-stanza `Architecture`, and §4.9 requires both
  `binary-*` targets to exist and succeed independently.

---

## 4. Lintian — checks for a Python/GTK4/DKMS package

Run on the `.changes` (covers source + binaries): `lintian -v -i package.dsc …`
or `lintian -i *.changes` (lintian manual §2.2; dev-ref §5.3 says errors
(`E:`) block upload — warnings/info may be acceptable).

**Checks a Python/GTK4/DKMS package must clear / common tags:**
- `python3`* family: correct shebangs (`dh_python3` rewrites env→`/usr/bin/python3`),
  `${python3:Depends}` present, byte-compilation, files in
  `/usr/lib/python3/dist-packages`.
- `appstream-metadata` / `appstream-*` (`wrong-name`, `missing-modalias-provide`,
  legacy path `.appdata.xml` vs `.metainfo.xml`, `/usr/share/appdata/` vs
  `/usr/share/metainfo/`): validate with `appstreamcli validate-tree`.
- `desktop-*` (`desktop-file-validate` errors, missing Icon/Categories/Name).
- `dh_dkms`-related: package name ends in `-dkms`; dkms.conf present.
- `no-manual-page`: fires when a binary lacks a man page (Policy §12.1). For
  `msi-ec-dkms` (a kernel module, not a command) this is a legitimate false
  positive — override it (see below).
- `missing-dependency-to-dkms`/`bad-dependency`: DKMS deps.
- `hardening-*` / `file-missing-in-md5sums`: general.

**How overrides work (lintian manual §2.4).** Place the file at
`/usr/share/lintian/overrides/<package>` inside the package (binary pkg) or at
`debian/source/lintian-overrides` (source pkg). Format:
`[package [arch] [type]:] tag [context]`; comments above an override are shown
next to the tag (§2.4.2). The project already uses this (e.g.
`debian/msi-batteryguard.lintian-overrides`).

**Handling the warnings named in the task:**

- **`extra-license-file`** — tag page "All license information should be
  collected in the `debian/copyright` file"; severity **`info`**; references
  Policy §12.5. It fires on license-named files (`LICENSE`, `COPYING`, …)
  shipped in the binary package. For `msi-ec-dkms` the upstream GPL-2 text is
  **legitimately** shipped inside the module source tree at
  `/usr/src/msi-ec-0.13/LICENSE` (DKMS convention: the source tree must be
  self-contained, and DFSG §2.3 / Policy §12.5 require the license to
  accompany the code). → **Recommended:** keep the license file in the source
  tree, ensure `debian/copyright` also carries the full GPL-2 text, and add an
  **override with a justification comment** (§2.4.2):
  ```
  # GPL-2 license text ships inside the DKMS module source tree as required
  # by DKMS (self-contained source) and DFSG §2.3 / Policy §12.5; it is also
  # summarised in debian/copyright.
  msi-ec-dkms: extra-license-file
  ```
  (Severity is only `info`, so it is non-blocking even if left alone, but an
  override documents the decision for reviewers.)

- **"wrong-section"** — there is **no** lintian tag literally named
  `wrong-section` (the tag-list page 404s). The intended tag is
  **`wrong-section-according-to-package-name`** (severity `info`: "This package
  has a name suggesting that it belongs to a section other than the one it is
  currently categorized in"), found via Debian bug #608554. It fires when the
  declared `Section:` disagrees with the name pattern. A `-dkms` package is
  conventionally `Section: kernel` (kernel modules); a GTK/libadwaita desktop
  app is conventionally `Section: gnome` (or `utils`/`python`). The project
  uses `Section: utils` for both — change `msi-ec-dkms` to `Section: kernel`
  and (optionally) `msi-batteryguard` to `gnome`/keep `utils`, or override
  (`msi-ec-dkms: wrong-section-according-to-package-name`) with a comment. Note
  the strict counterpart **`wrong-section-for-udeb`** (warning: udeb must be
  `Section: debian-installer`) — not applicable here since these are `.deb`s.

- The project's existing overrides (`appstream-metadata-missing-modalias-provide`,
  `initial-upload-closes-no-bugs`, `no-manual-page`) are all valid;
  `initial-upload-closes-no-bugs` is the reminder that the first upload should
  carry `Closes: #<ITP>` once an ITP exists (§1).

---

## 5. AppStream — what `appstreamcli validate` requires

The archive's software-center metadata is produced/validated by AppStream.
`appstreamcli` (manpage) provides:
- `validate <files>` — validate metainfo XML for spec compliance (auto-detects
  upstream vs distro XML);
- `validate-tree <dir>` — also checks `.desktop` file presence/validity together
  with the metainfo;
- `--pedantic` — turn on stricter/style checks;
- `check-license <LICENSE>` — tests a license string against FSF/OSI/**DFSG**
  lists ("AppStream will consider any license … marked as suitable by … the
  Debian Free Software Guidelines").

**Mandatory metadata fields** the file must have to pass validation (AppStream
spec `chap-Metadata.html`, summarised by the Flathub MetaInfo guidelines which
cross-reference the same spec sections):
| Field (tag) | Requirement |
|---|---|
| `<id>` | Required; must be the reverse-DNS app id; must NOT contain `.desktop`. Filename must be `<id>.metainfo.xml`. |
| `<metadata_license>` | **Required** (license of the metainfo XML itself; CC0-1.0 or FSFAP recommended for upstream-authored). |
| `<project_license>` | **Required** (Flathub); valid SPDX id/expression. `appstreamcli check-license` validates it. |
| `<name>` | Required (one per language). |
| `<summary>` | Required (short, ≤ one line). |
| `<description>` | Required; at least one non-empty `<p>`/`<ol>`/`<ul>`. |
| `<launchable type="desktop-id">` | Required for graphical apps; must match the installed `.desktop` filename. |
| `<developer>` | Required; must have an `id` attribute (reverse-DNS, e.g. `com.bongbetic`) **and** a `<name>` child. |
| `<url type="homepage">` | Required at minimum; bugtracker/contact/vcs-browser recommended. |
| `<categories>` | Required (from the freedesktop Menu spec); avoid generic categories (GTK/GNOME/Qt/KDE are filtered). |
| `<screenshots>` | Required for graphical apps; at least one `<screenshot type="default">` with an `<image>` (direct URL) and `<caption>`. Screenshots should be from a tag/commit, not a branch. |
| `<content_rating type="oars-1.1">` | Required; generate via the OARS website. |
| `<releases>` | Required; `appstreamcli validate` flags `missing-data`/errors without it. Dates must not be in the future; versions must order correctly. |
| `<icon>` | Recommended (stock icon = the app id). |

**Install location/namespace for Debian:** `/usr/share/metainfo/<id>.metainfo.xml`
(not the legacy `/usr/share/appdata/`). `validate-tree /usr/share/metainfo/` (after
install) is the end-to-end check that catches desktop-file linkage too. Run
`appstreamcli validate --pedantic data/com.bongbetic.batteryguard.metainfo.xml`
locally before upload.

**Debian-archive specifics:** the archive runs AppStream composition over the
`.deb`s; errors block inclusion, so fix all `E:`-level `validate` output. The
existing `data/com.bongbetic.batteryguard.metainfo.xml` already carries every
mandatory field above (`id`, `metadata_license=CC0-1.0`, `project_license=GPL-3.0-or-later`,
`name`, `summary`, `description`, `launchable`, `developer id=com.bongbetic`+`name`,
`url`, `categories`, `screenshots` default+`caption`, `content_rating type="oars-1.1"`,
`releases`). It is named/installed correctly via the `.install` file.

---

## 6. Sponsorship — for a maintainer who is NOT a Debian Developer

A non-DD cannot upload to `ftp.upload.debian.org` (signing keys must be in the
**Debian Developers** or **Debian Maintainers** keyrings — a DM who has been
granted upload permissions for the package can upload directly; a brand-new
contributor needs a DD sponsor). Process:

1. **Prepare & host the package.** Build a clean source package (`.dsc`+`.changes`,
   signed with your GPG key) and make it available — traditionally on
   `mentors.debian.net` via `dput` (HTTPS/FTP upload), or via a public VCS link
   (salsa.debian.org). `mentors.debian.net` runs QA checks on import and emails
   you when ready.
2. **Request sponsorship (RFS).** File a bug against the **`sponsorship-requests`
   pseudo-package** (not `submit@` directly to a person). Use the template from
   the mentors RFS howto, with `Subject: RFS: msi-batteryguard/1.1.0-1 [ITP]
   -- Battery charge threshold controller …`. Body lists package name, version,
   upstream contact, URL, license, VCS, Section, the built binaries + synopses,
   the mentors.d.n URL, and `dget` line, plus the latest changelog entry. CC the
   `debian-mentors@lists.debian.org` list by following the thread.
3. **What the sponsor reviews** (dev-ref §7.6.1.1, non-exhaustive):
   - upstream tarball matches what upstream distributes (reproduce yourself if
     repacked);
   - `lintian -i` output and that every override is justified;
   - `licensecheck` + DFSG scan of `debian/copyright` (look for "All rights
     reserved"/non-DFSG);
   - full clean-chroot build via `pbuilder`/`sbuild` proving `Build-Depends`
     completeness;
   - proofread `control`, `rules`, maintainer scripts (idempotent, no hard deps
     when deps absent);
   - review of `debian/patches` (DEP-3 headers, `Forwarded:`);
   - **install, run, remove, purge** the binaries, optionally `piuparts`.
   The sponsor signs and uploads with `dpkg-buildpackage -k<KEY-ID>`; the
   changelog `Maintainer`/`Uploaders` stays as **you** (the packager) so you
   get the BTS mail — the DD only adds their signature.

---

## 7. Source format — `3.0 (native)` vs `3.0 (quilt)`

Policy ch-source §4 defines the two kinds:
- **Native** ("3.0 (native)"): *no distinction* between upstream release and
  Debian packaging. A single tarball `pkg_version.tar.{xz}` (no `.orig`, no
  Debian revision in the version, e.g. `1.0.0`), contains upstream + `debian/`.
  "Normally … used for software that has no independent existence outside of
  Debian, such as software written specifically to be a Debian package."
- **Non-native** ("3.0 (quilt)"): upstream release separated from Debian changes.
  An `.orig.tar.*` (upstream, untouched) + a `.debian.tar.*` (the `debian/`
  dir, applied as quilt patches). Version is `upstream-rev` e.g. `1.0.0-1`.
  "Most source packages in Debian are non-native."

**Which is correct when packaging lives in the same repo as the source code?**
The deciding factor is **whether upstream is a distinct entity**, not whether the
`debian/` directory happens to be committed in the same VCS. The project is a
GitHub project (`github.com/Bongbetic/…`) that publishes version tags/releases —
it has a recognizable upstream. Policy §4.4 footnote [[4]] explicitly says:
"if the Debian and upstream maintainers become different people … it might be
better to maintain the package as a non-native package." The debmake-doc ch.6
states `3.0 (quilt)` "is the most normal Debian source package format";
Projects/DebSrc3.0 is the de-facto reference for the two formats.

→ For BatteryGuard the **correct** format is `3.0 (quilt)` with a pristine
`.orig.tar.*` (the GitHub release tarball, without the `debian/` dir) and the
packaging carried as `debian.tar.xz`.

**The project is currently inconsistent:** `debian/source/format` says
`3.0 (native)` while `debian/changelog` uses versions **`1.0.0-1` / `1.1.0-1`**
(i.e. with a Debian revision — the non-native convention). Native packages have
no Debian revision. This mismatch must be resolved before a real Debian upload:
switch to `3.0 (quilt)` and generate a real `.orig.tar.*` (e.g.
`gbp import-orig --uscan` or `dget` from the GitHub release), OR — only if the
maintainer insists upstream == Debian — keep `3.0 (native)` and drop the `-1`
revision so the version is just `1.1.0`. The former (quilt + orig) is strongly
recommended given the GitHub-upstream model.

**Watch + repacking tie-in (§8):** with `3.0 (quilt)`, `uscan` + `mk-origtargz`
can auto-repack a non-DFSG-free tarball into `pkg_version+dfsg.orig.tar.xz`
(debian-watch(5) "HTTP site (DFSG)" example).

---

## 8. `debian/watch` — monitoring upstream (GitHub releases)

**Is it needed?** Policy §4.11 says: "If the upstream source … is available via
a mechanism that `uscan` understands, including this configuration file is
**recommended**." For a GitHub-hosted project that publishes release tarballs,
**yes** — it enables `uscan` to detect new upstream versions automatically and
(fed to `mk-origtargz`) to keep the `.orig.tar.*` current. It is also used by
Debian QA tooling. (It is optional only if upstream publishes no scannable
tarballs/tags.)

**Write it (v5 format, `debian-watch(5)`).** The modern, recommended form for
GitHub releases uses the `Template: GitHub` shorthand, which expands to the
releases/tags API recipe:

```
Version: 5
Template: GitHub
Owner: Bongbetic
Project: MSI-batteryguard-for-Thin-A15-B7UCX
```

or, equivalently, the explicit API form (from the manpage):
```
Version: 5
Source: https://api.github.com/repos/Bongbetic/MSI-batteryguard-for-Thin-A15-B7UCX/git/matching-refs/tags/
Matching-Pattern: https://api.github.com/repos/[^/]+/[^/]+/git/refs/tags/@ANY_VERSION@
Download-Url-Mangle: s%(api.github.com/repos/[^/]+/[^/]+)/git/refs/%$1/tarball/refs/%g
Filename-Mangle: s%.*/(\@ANY_VERSION@)%msi-batteryguard-$1.tar.gz%
Search-Mode: plain
```
Add **signature verification** if upstream publishes `.asc`/`.sig` releases:
`Pgp-Mode: auto` plus a `debian/upstream/signing-key.asc` armored keyring
(uscan(1) "KEYRING FILE EXAMPLES"; `gpg --export --armor <fpr> >
debian/upstream/signing-key.asc`). If upstream does **not** sign releases, set
`Pgp-Mode: none` to silence the signature warning.

**Test it.** From the source root:
```
uscan --verbose            # dry-run report (no download)
uscan --verbose --debug    # internals + version extraction
uscan --download           # actually grab a newer tarball
uscan --safe               # no download/repack (security-conscious)
```
`uscan` reads the upstream version from the first `debian/changelog` line,
downloads newer candidate tarballs, and (for non-native) runs `mk-origtargz` to
produce `…_orig.tar.{xz}` linked from the parent dir. If the project is native,
`uscan` still produces the orig-named tarball via `--no-symlink`/`--copy`/`
--rename` as configured.

---

## Sources

[1] Developer's Reference §5.1 "New packages" (ITP/WNPP/severity/X-Debbugs-CC/Closes) — https://www.debian.org/doc/manuals/developers-reference/pkgs.en.html#new-packages
[2] WNPP (Work-Needing & Prospective Packages) — https://www.debian.org/devel/wnpp/
[3] Debian BTS — "How to report a bug … via email" (pseudo-headers: Package/Version/Severity/Tags/Owner/X-Debbugs-CC) — https://www.debian.org/Bugs/Reporting.en.html
[4] debian-devel mailing list — https://lists.debian.org/debian-devel/
[5] Developer's Reference §5.6.2 "Uploading to ftp-master" (upload queue, signing keys, dput/dupload) — https://www.debian.org/doc/manuals/developers-reference/pkgs.en.html#uploading-to-ftp-master
[6] DFSG, Licensing & New Packages Team (NEW-queue mandate, pre-upload scanning, ping policy) — https://dfsg-new-queue.debian.org/
[7] Debian NEW / BYHAND Packages (live NEW list) — https://ftp-master.debian.org/new.html
[8] Debian Free Software Guidelines (Social Contract) — https://www.debian.org/social_contract#guidelines
[9] Debian Policy Manual ch. 2 "The Debian Archive" (DFSG, archive areas, copyright considerations, sections, priorities) — https://www.debian.org/doc/debian-policy/ch-archive.html
[10] Debian Policy Manual ch. 4 "Source packages" (native vs non-native §4, §4.3 changes to upstream, §4.4 changelog format+version, §4.5 copyright, §4.6 error trapping, §4.9 rules targets incl. binary-arch/binary-indep, §4.11 debian/watch) — https://www.debian.org/doc/debian-policy/ch-source.html
[11] Debian Policy Manual ch. 10 "Files" (§10.1 binaries, §10.9 locale files, §10.10 permissions) — https://www.debian.org/doc/debian-policy/ch-files.html
[12] Debian Policy Manual ch. 11 "Customized programs" (§11.1 architecture specification strings, §11.8 programs for the X Window System) — https://www.debian.org/doc/debian-policy/ch-customized-programs.html
[13] Debian Policy Manual ch. 12 §12.5 "Copyright information" — https://www.debian.org/doc/debian-policy/ch-docs.html#copyright-information
[14] DEP-5 machine-readable copyright format 1.0 — https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
[15] Developer's Reference §7.6 "Sponsoring packages" / §7.6.1.1 "Sponsoring a new package" (review checklist, signing) — https://www.debian.org/doc/manuals/developers-reference/beyond-pkging.en.html#sponsoring-packages
[16] Lintian User's Manual §2 (running, tags, overrides) — https://lintian.debian.org/manual/
[17] Lintian tag `extra-license-file` (info, Policy §12.5) — https://lintian.debian.org/tags/extra-license-file.html
[18] Lintian tag `wrong-section-according-to-package-name` (info) — https://lintian.debian.org/tags/wrong-section-according-to-package-name.html
[19] Lintian tag `wrong-section-for-udeb` (warning) — https://udd.debian.org/lintian-tag/wrong-section-for-udeb
[20] `appstreamcli(1)` manpage (validate, validate-tree, --pedantic, check-license) — https://manpages.debian.org/unstable/appstream/appstreamcli.1.en.html
[21] AppStream specification — "Upstream Metadata" / Metadata quickstart (canonical field definitions; docs site returned 504 during research) — https://www.freedesktop.org/software/appstream/docs/chap-Metadata.html
[22] Flathub "MetaInfo guidelines" (summarises mandatory fields; cross-references AppStream spec) — https://docs.flathub.org/docs/for-app-authors/metainfo-guidelines
[23] mentors.debian.net — "Request for Sponsorship" (RFS) howto + template — https://mentors.debian.net/sponsors/rfs-howto/
[24] debian-mentors mailing list — https://lists.debian.org/debian-mentors
[25] Debian Maintainer (wiki; keyrings, DM upload permissions, dcut) — https://wiki.debian.org/DebianMaintainer
[26] Guide for Debian Maintainers (debmake-doc) ch. 6 "Basics for packaging" (3.0 (quilt) is the most normal format) — https://www.debian.org/doc/manuals/debmake-doc/ch06.en.html
[27] Debian Wiki "Projects/DebSrc3.0" (3.0 quilt vs native reference) — https://wiki.debian.org/Projects/DebSrc3.0
[28] `dpkg-source(1)` (source formats) — https://manpages.debian.org/unstable/dpkg/dpkg-source.1.en.html
[29] `debian-watch(5)` format spec v5 (substitutions, GitHub template/examples, PGP options, repack) — https://manpages.debian.org/unstable/devscripts/debian-watch.5.en.html
[30] `uscan(1)` — https://manpages.debian.org/unstable/devscripts/uscan.1.en.html
[31] `dh_dkms(1)` (name must end in -dkms; manages postinst/postrm) — https://manpages.debian.org/testing/dh-dkms/dh_dkms.1.en.html
[32] `dkms(8)` (source in /usr/src/<module>-<ver>/, dkms.conf, per-kernel/arch build) — https://manpages.debian.org/testing/dkms/dkms.8.en.html
[33] Debian Linux Kernel Handbook (distributions) ch. 4.4 "Out-of-tree kernel modules" / §4.4.1 DKMS — https://kernel-team.pages.debian.org/kernel-handbook/
[34] Debian Package Tracker — https://tracker.debian.org/ (replaces PTS; per-package pages, maintainer contact)
[35] Lintian tags index — https://lintian.debian.org/
[36] Debian BTS control/reference: bug #608554 (origin of `wrong-section-according-to-package-name`) — https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=608554

### Local project references (for context)
- `debian/control` — current Sections/Architecture/Depends.
- `debian/source/format` — currently `3.0 (native)` (see §7 inconsistency).
- `debian/{msi-batteryguard,msi-ec-dkms}.lintian-overrides` — existing overrides.
- `debian/msi-ec-dkms.{postinst,prerm,triggers,install}` + `msi-ec-src/dkms.conf` — DKMS plumbing.
- `data/com.bongbetic.batteryguard.metainfo.xml` + `data/com.bongbetic.batteryguard.desktop` — AppStream/desktop metadata.
- `data/`, `src/` — Python 3 + GTK4/libadwaita sources; `msi-ec-src/` — vendored kernel module C source.

### Note on unreachable primary sources
Several `wiki.debian.org` pages (IntentsToPackage, AppStream/Guidelines, Mentors,
Projects/DebSrc3.0) and the `freedesktop.org/software/appstream/docs/` reference
site returned HTTP 504 during this research session. Where possible the same
content was confirmed from mirror primary sources (Debian manuals on
`debian.org`, `manpages.debian.org`, `lintian.debian.org`, `mentors.debian.net`,
and the DFSG NEW-queue site) and is cited above.
