# Carbon assets in a Meson/GTK repo: build chain research

**Ticket**: #38 · **Map**: #34 ("Offline asset bundling policy (waits on build-chain research)" — answered here)

**Question**: How should npm-built `@carbon/web-components` assets be built and shipped inside this Meson/GTK repo? Cover: a vite/esbuild step wired into Meson (`custom_target`?), dist committed vs built in CI, IBM Plex font bundling, strictly-offline rendering (no CDN), and how the deb packaging picks up the built bundle. Recommend one build+ship approach.

---

## TL;DR recommendation

1. **Build with Vite into a committed `web/dist`** (relative `base: './'`, Plex woff2 either inlined or with stable filenames). Debian Policy forbids network access during package builds, so `npm ci` can never run inside `dpkg-buildpackage` — the dist **must** already be in the source tree when the deb is built. Committing it keeps one source of truth for sbuild/buildd, the GitHub orig tarball, and `meson install`; a CI drift-check job re-builds and diffs to keep it honest.
2. **Meson never runs npm.** Install the committed tree with `install_subdir('web/dist', install_dir: pkgdatadir / 'web')`. A `custom_target` wrapping `npm run build` is provided only as a **dev convenience** behind a Meson option (it cannot declare a vite dist tree as outputs anyway — see §2), and is excluded from the install path used by the deb.
3. **Deb pickup is one line**: add `usr/share/com.bongbetic.threshold/web/` to `debian/threshold.install`. The repo already runs `dh --buildsystem=meson`, so `ninja install` lands the bundle in `debian/tmp` and `dh_install` packages it. Offline rendering: register a `threshold://` URI scheme in WebKitGTK (preferred) or load `file://` with `allow-file-access-from-file-urls=true`.

Details and citations below.

---

## 1. What we're shipping: `@carbon/web-components` facts

Verified against the npm registry and the upstream repo (GitHub `carbon-design-system/carbon`):

- `@carbon/web-components` latest is **2.62.0**, license **Apache-2.0**. Dependencies: `lit ^3.1.0`, `@carbon/styles ^1.114.0`, `@carbon/icons`, `flatpickr`, `lodash-es`, `@floating-ui/dom`, etc. (registry metadata for `@carbon/web-components`).
- Usage is per-component ESM imports, ideal for a bundler/tree-shaking:
  ```js
  import '@carbon/web-components/es/components/dropdown/dropdown.js';
  ```
  (README, `packages/web-components` on `main`).
- The README also offers CDN artifacts (`https://1.www.s81c.com/common/carbon/web-components/version/.../dropdown.min.js`). **Ruled out** — charter says strictly offline.

So the app is a small npm project (`web/`) that imports Carbon components + styles and is bundled by Vite into static `index.html` + JS/CSS/font assets.

## 2. Meson wiring: `custom_target` can't own a vite dist tree

From the Meson reference manual (`mesonbuild.com/Reference-manual_functions.html`, `custom_target` / `install_subdir` sections):

- `custom_target` **outputs cannot contain path separators** — `output:` is a flat list of filenames in the target dir. A Vite build emits a dynamic set of hashed files (`assets/index-Ab3xZ9.js`, `assets/index-C2fQ1.woff2`, …), which cannot be declared as Meson target outputs.
- Viable keywords if we still want a target: `command` (array, no shell — use a wrapper script), `build_by_default`, `build_always_stale`, `console: true` (shows npm output), `@PRIVATE_DIR@` / `@OUTDIR@` / `@SOURCE_ROOT@` substitutions.
- `install_subdir('web/dist', install_dir: pkgdatadir / 'web', exclude_files: [...])` installs an **entire source-tree subdirectory** — exactly the shape a committed dist has. (Doc note: creating install dirs that don't exist in the source tree is deprecated; another reason the dist belongs in the tree.)
- Meson has no npm/Node integration module (FAQ mentions neither npm nor node).

Consequences:

- **Install path**: `install_subdir` on the committed `web/dist` → deterministic, no node.js needed at build time.
- **Dev path** (optional): `custom_target('web-dist', console: true, build_by_default: false, input: package.json marker, output: 'web-dist.stamp', command: [find_program('node'), 'web/build.js'])` behind `-Dweb-ui-build=enabled`, writing straight into the source tree (`@SOURCE_ROOT@/web/dist`) and touching the stamp. It is a dev accelerator, never a dependency of `meson install`. CI drift-check (§3) uses the same script.

## 3. Committed dist vs built in CI — committed wins here

**Hard constraint first.** Debian Policy, ch. "Source packages" (`debian.org/doc/debian-policy/ch-source.html`, build targets):

> "…required targets **must not attempt network access to other hosts**. Only access via the loopback interface to services on the build host that have been started by the build is allowed."

`npm ci`/`npm install` hits registry.npmjs.org → forbidden inside `debian/rules` for anything built by Debian's buildds/sbuild (which is where this package aims after the #24 Debian-submission research). Node itself would also need to be a `Build-Depend` (currently absent, and gratuitous for an `Architecture: all` pure-Python package).

So there are only two shapes, both ending with the dist inside the source package:

| | **A. Commit `web/dist` to git** | **B. CI builds dist before deb build** |
|---|---|---|
| deb build | dist already in tree, zero extra steps | CI job runs `npm ci && npm run build`, copies into tree, then `dpkg-buildpackage` |
| source tarball (GitHub orig tarball for Debian) | correct by construction | release job must remember to inject; a maintainer running `dpkg-buildpackage` locally without node gets a broken or missing UI |
| repo noise | one reviewed directory of minified assets; no `node_modules` | clean tree, but dist exists only ephemerally |
| drift risk | source `web/src` can change without rebuild | none by construction |
| tooling | same `web/build.js` for devs + CI | CI-only build step |

**Recommendation: A (commit the dist), guarded by CI.**

- Single source of truth: what you tag is what ships, both in `.deb` and in the future Debian orig tarball — important because #24 targets ftp-master upload where the .dsc contents are what counts.
- No `nodejs`/`npm` in `Build-Depends`; `Architecture: all` story stays intact (see `docs/research/deb-packaging.md`).
- Drift guard: CI job "web-dist check" runs the Vite build and `git diff --exit-code web/dist`. Fails the PR, not the release.
- Licensing is compatible: Carbon packages are Apache-2.0, IBM Plex is OFL-1.1 (verified: `@ibm/plex@6.4.1` package.json license field; map #34 already settled this). The `debian/copyright` needs Apache-2.0 + OFL-1.1 entries for the vendored dist.

## 4. IBM Plex bundling (strictly offline)

Verified from the published `@carbon/styles@1.114.0` and `@ibm/plex@6.4.1` tarballs:

- **The prebuilt stylesheet is a trap.** `@carbon/styles/css/styles.css` hardcodes every IBM Plex `@font-face` to IBM's CDN:
  `https://1.www.s81c.com/common/carbon/plex/fonts/IBM-Plex-Sans/fonts/split/woff2/IBMPlexSans-Regular-Latin1.woff2` (verbatim from the tarball). Importing it ships a CDN dependency → violates offline charter.
- **The SCSS route is offline-clean.** In `scss/_config.scss`: `$use-akamai-cdn: false !default;` — the default. With CDN off, `scss/fonts/_src.scss` resolves each face to a **local path into the `@ibm/plex` package** (`#{config.$font-path}/IBM-Plex-Sans/fonts/...`), which a bundler can follow.
- **Fonts are self-hostable**: `@ibm/plex@6.4.1` (OFL-1.1) ships **4,059 woff2 files**; we only need a handful — IBM Plex Sans Regular/Medium/SemiBold (+ maybe Mono) Latin subsets.

Two workable bundling strategies inside `web/`:

1. **Own `@font-face` (recommended).** Skip Carbon's fonts module entirely (`@use '@carbon/styles/scss/reset'; @use '@carbon/styles/scss/components/...';` per-component), copy ~4 woff2 from `@ibm/plex` into `web/public/fonts/`, declare `@font-face` with `font-display: swap`. Total ~200–400 KB, full control, no sass url() plumbing.
2. **Carbon SCSS + bundler rewrite.** Import `@carbon/styles/scss/globals` + fonts with `$font-path` pointed at `@ibm/plex`; requires Vite to resolve and emit each referenced woff2 from `sass` output URLs. Works but brittle (per-family unicode splits pull dozens of files).

Vite behaviors that matter (vite.dev build/shared options):

- `base: './'` → relative asset URLs in built HTML/CSS. **Required** for `file://`/`threshold://` loading (default `base` is `/`).
- `build.assetsInlineLimit` (default 4096): assets under 4 KiB become base64 data URLs — fonts can be fully inlined by raising the limit, guaranteeing a near single-file bundle; or leave hashing on and accept multiple files (fine, since we commit the tree).
- `build.assetsDir` (default `assets`) controls the nesting dir; `rollupOptions` is now a deprecated alias for `rolldownOptions` in current Vite docs — don't cite `rollupOptions` in new code.

## 5. Strictly-offline rendering in WebKitGTK

Verified against upstream WebKit source and PyGObject API docs:

- If loading via `file://` (`web_view.load_uri('file://' + pkgdatadir + '/web/index.html')`), sibling loads (ES module imports, fetches) are subject to file-URL origin rules. `WebKitSettings` exposes exactly the toggles needed — from upstream `WebKitSettings.cpp`: `allow-file-access-from-file-urls` (~L1529) and `allow-universal-access-from-file-urls` (~L1548). Set the first `true` (PyGObject: `props.allow_file_access_from_file_urls = True`).
- **Preferred: custom URI scheme.** `WebKitWebContext.register_uri_scheme()` (PyGObject docs, `WebKit2-4.1`/`WebKit2-5.0` `WebContext`) serves app content from a handler — no file-URL CORS edge cases, works identically for `threshold://app/index.html`, and can stream straight out of the installed `pkgdatadir` (or even a GResource). This is the standard WebKitGTK embedding pattern.
- Either way, `base: './'` (§4) plus the Plex self-hosting (§4) closes the last external-URL holes. Add a CI grep over `web/dist` for `https?://` in JS/CSS/HTML to enforce "no CDN" mechanically (excluding sourcemap comments).

## 6. How the deb picks the bundle up

Current repo flow (verified in-tree): `debian/rules` runs `dh $@ --buildsystem=meson --with python3` with `override_dh_auto_install: cd obj-* && DESTDIR=... ninja install`, then `dh_install` maps `debian/tmp` paths via `debian/threshold.install` (already enumerates gresource, `.py`s, schemas, etc.).

- `dh`'s Meson support is the debhelper `Buildsystem/meson.pm` module (verified in the debhelper source tree on salsa: `lib/Debian/Debhelper/Buildsystem/` contains `meson.pm`); debhelper(7) documents `dh_auto_*` build-system autodetection, and this repo pins it explicitly with `--buildsystem=meson`.
- Therefore: meson `install_subdir('web/dist', install_dir: pkgdatadir / 'web')` lands in `debian/tmp/usr/share/com.bongbetic.threshold/web/`, and the **only packaging change** is one line in `debian/threshold.install`:
  ```
  usr/share/com.bongbetic.threshold/web
  ```
- No new `Build-Depends`, no rules changes, `Architecture: all` unchanged. Size impact: a Carbon-based UI bundle is roughly 0.5–2 MB depending on component count and font strategy — trivial vs. current package size.
- `debian/copyright` gains: Apache-2.0 (Carbon, Lit is BSD-3 — check tree per vendored file) and OFL-1.1 (Plex) sections for `web/dist`.

## Decision checklist (for the map)

- [x] Offline asset bundling policy: self-host everything; dist committed; CI asserts no `https://` refs (this doc).
- [ ] Architecture ADR: `threshold://` scheme vs `file://` + settings flag (ticket #37 bridge research).
- [ ] Vendoring policy footnote in `debian/copyright` when implementation lands.

## Sources

- npm registry: `registry.npmjs.org/@carbon/web-components` (2.62.0, Apache-2.0, deps) — fetched 2026-08-28
- `@carbon/styles@1.114.0` tarball: `css/styles.css` (CDN `@font-face` URLs), `scss/_config.scss` L62 (`$use-akamai-cdn: false !default`), `scss/fonts/_src.scss` (local `@ibm/plex` resolver)
- `@ibm/plex@6.4.1` tarball: license OFL-1.1, woff2 inventory
- Carbon web-components README: `github.com/carbon-design-system/carbon/tree/main/packages/web-components` (ESM imports, CDN artifacts)
- Vite docs: `vite.dev/config/shared-options/` (`base`), `vite.dev/config/build-options/` (`assetsDir`, `assetsInlineLimit`, `rolldownOptions` alias note)
- Meson reference: `mesonbuild.com/Reference-manual_functions.html` — `custom_target` (output path-separator rule, `install:`, `console:`, `@PRIVATE_DIR@`, `build_always_stale`) and `install_subdir`
- Debian Policy: `debian.org/doc/debian-policy/ch-source.html` — "required targets must not attempt network access to other hosts"
- debhelper source: `salsa.debian.org/debian/debhelper` → `lib/Debian/Debhelper/Buildsystem/meson.pm`; debhelper(7) build-system autodetection
- WebKit upstream: `WebKitSettings.cpp` (`allow-file-access-from-file-urls`, `allow-universal-access-from-file-urls`); PyGObject docs `WebKit2-4.1 WebContext` (`register_uri_scheme`)
- Repo: `debian/rules`, `debian/threshold.install`, `data/meson.build`, `src/meson.build` (current install layout), `docs/research/deb-packaging.md` (Architecture: all rationale)
