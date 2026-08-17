# Open Source Contribution Policies: Project vs. Debian

This document records the findings of an investigation into two things:

- **Part A — the repository's own contribution/licensing policies** (CLA, DCO,
  CONTRIBUTING guidelines, and the licenses that govern the app and the vendored
  `msi-ec` kernel module, including whether the two can be shipped together in a
  `.deb`).
- **Part B — Debian's requirements** for contributor agreements, copyright
  documentation (DEP-5), and DFSG compliance when submitting to the archive.

---

## Executive summary

| Question | Finding |
|---|---|
| Does the repo use a **CLA** (Contributor License Agreement)? | **No.** No `CLA.md`, `COPYING.*`, or contributor-agreement file exists anywhere in the tree. |
| Does the repo use the **DCO** (Developer Certificate of Origin)? | **No.** No `DCO`/`dco` file, no `Signed-off-by:` trailers in **27** commits across all refs (count = **0**), and no PR template or CI check enforcing sign-off. |
| Is there a **CONTRIBUTING.md** or contribution guide? | **No.** Only `AGENTS.md` (repo-agent skill config) and `README.md`/`INSTALL.md`. No `CODE_OF_CONDUCT`, no `PULL_REQUEST_TEMPLATE`. |
| **Main project license** | **GPL-3.0-or-later** (`meson.build` line 5; `data/com.bongbetic.batteryguard.metainfo.xml` line 5; `debian/copyright`). |
| **Vendored `msi-ec` kernel module license** | **GPL-2.0** text in `msi-ec-src/LICENSE`; the authoritative SPDX header in `msi-ec-src/msi-ec.c` line 1 reads `GPL-2.0-or-later`, and `MODULE_LICENSE("GPL")` appears at `msi-ec.c` line 3106. `msi-ec-src/README.md` line 9 labels it `GPL-2.0`. |
| **Compatible?** Can app (GPL-3) + module (GPL-2-or-later) ship in one `.deb`? | **Yes.** They are separate packages communicating across the kernel/userspace boundary (mere aggregation); and GPL-2.0-or-later + GPL-3.0-or-later combine to GPL-3.0-or-later (GNU: compatible). |
| Does **Debian require** an upstream CLA/DCO? | **No.** Debian requires accurate `debian/copyright`, DFSG freeness, and the right to distribute — **not** a contributor agreement. DFSG's "Distribution of License" clause *forbids* licenses that need extra agreement. |
| DFSG status of vendored `msi-ec` source | **OK for `main`.** GPL is DFSG-free; `msi-ec` is GPL, so it qualifies. |

---

## A) Repository analysis

Repository under test:
`/home/xavier/Documents/bongbetic/MSI-batteryguard-for-Thin-A15-B7UCX`

### A.1 Contributor License Agreement (CLA)

**Finding: No CLA exists.**

A recursive scan for `CLA*`, `COPYING*`, `COPYING`, `contributor-agreement`, and
any license-agreement document in the tree returned **no matches**:

```
find . -iname "license*" -o -iname "copying*" -o -iname "cla*" -o -iname "contributing*" -o -iname "dco*"
# (no output)
```

There is **no** `LICENSE` and **no** `COPYING` file at the repository root
(which contains only `AGENTS.md`, `INSTALL.md`, `README.md`, `meson.build`,
`data/`, `debian/`, `msi-ec-src/`, `po/`, `src/`, `tests/`, etc.). The upstream
GitHub repository is also not configured with a CLA bot (no
`.github/cla-assistant.yml`, no `FUNDING.yml` CLA gate, and `.github/` contains
only `workflows/ci.yml` and `workflows/release.yml`).

> **Implication:** Contributors do not sign any agreement; copyright is assumed
> to be granted under the project's license by virtue of submission. Debian does
> not require this file either (see §B.3), but its absence means there is no
> in-repo evidence of an upstream's intent to relicense, which downstream
> redistributors (Debian, in particular) usually obtain from the *copyright file*
> rather than a CLA.

### A.2 Developer Certificate of Origin (DCO)

**Finding: The DCO is not in use.**

- No `DCO` / `dco.txt` file exists in the repo.
- `git log --all --format='%(trailers:key=Signed-off-by)'` yields **0**
  `Signed-off-by:` trailers across all **27** commits and tags.
- No commit-template, no `.github/PULL_REQUEST_TEMPLATE` mentioning the DCO, and
  the CI workflow (`.github/workflows/ci.yml`) performs no sign-off check.

```
$ git log --all --format='%B' | grep -c "Signed-off-by:"
0
$ git rev-list --all --count
27
```

> **Implication:** There is no provenance/blessing trail for contributions. For a
> project seeking Debian inclusion, this is **not a blocker** (Debian does not
> mandate the DCO), but it does mean there is no lightweight, automated mechanism
> to certify that contributors have the right to submit the code they send.

### A.3 Contribution guidelines

**Finding: No `CONTRIBUTING.md` (or equivalent) is present.**

```
$ find . \( -iname "contributing*" -o -iname "code_of_conduct*" -o -iname "pull_request_template*" \)
# (no output)
```

The only quasi-documentation of "how to work here" is `AGENTS.md`
(`/home/xavier/.../AGENTS.md`), which is **not** a human contribution guide — it
configures an automated agent's git/CI behaviour:

```
AGENTS.md (lines 1-3): ## Agent skills
AGENTS.md (line 15-19): Use the existing local git config
   user.name = soubarnak / user.email = soubarna@live.in
AGENTS.md (line 23): Use the `gh` CLI for all git-related workflows
```

`README.md` documents *installation/usage* and building locally; `INSTALL.md`
documents the Meson build. Neither describes how an external person submits a
pull request or signs off on a change.

### A.4 Licenses present in the repository

#### Main project license — GPL-3.0-or-later

Declared in three authoritative places, consistently:

| File | Line | Declaration |
|---|---|---|
| `meson.build` | 5 | `license: 'GPL-3.0-or-later'` |
| `data/com.bongbetic.batteryguard.metainfo.xml` | 5 | `<project_license>GPL-3.0-or-later</project_license>` |
| `debian/copyright` | 8 | `License: GPL-3+` (with full GPL-3 text + pointer to `/usr/share/common-licenses/GPL-3`) |

**Note:** There is *no* root-level `LICENSE`/`COPYING` file shipped in the source
tarball-style repository. The GPL-3.0-or-later grant is therefore visible only
from machine-readable metadata (`meson.build`), the AppStream metainfo, and the
Debian copyright file. Debian Policy §12.5 is still satisfied for the *binary*
package (`/usr/share/doc/msi-batteryguard/copyright` carries the verbatim text),
but the *upstream source* lacks a human-readable top-level license file — a mild
open-source hygiene gap that makes it harder for contributors/reusers to see the
license at a glance.

#### Vendored `msi-ec` kernel module — GPL-2.0 / GPL-2.0-or-later

`msi-ec-src/` is a vendored snapshot of
`BeardOverflow/msi-ec` (per `msi-ec-src/README.md` line 3), snapshot commit
`050d4394a6747ebd106ae2f8ddb3a4eebe7c700f`, upstream version `0.13`.

- `msi-ec-src/LICENSE` — the full text of the **GNU General Public License v2.0**
  ("Version 2, June 1991").
- `msi-ec-src/msi-ec.c` line 1 — **`SPDX-License-Identifier: GPL-2.0-or-later`**
  (the authoritative SPDX expression embedded in the source).
- `msi-ec-src/msi-ec.c` line 3106 — `MODULE_LICENSE("GPL");` (the in-kernel
  macro declaring the module's license for the running kernel).
- `msi-ec-src/README.md` line 9 — "License: GPL-2.0 (see `LICENSE`)".

**Observed inconsistency:** the README says `GPL-2.0` (which reads as "GPL-2.0
*only*") while the source file's SPDX tag says `GPL-2.0-or-later`. The SPDX
identifier should be treated as authoritative (it is the modern standard and
explicitly grants the "or later" option). In practice the `LICENSE` file is just
the GPL-2 document; the "How to Apply" boilerplate inside it always contains the
"version 2 *or any later version*" wording, so the document text alone does not
distinguish "only" from "or-later". The SPDX tag does, and it says **or-later**.

### A.5 Debian packaging artifacts (licensing)

`debian/control` builds **two binary packages** from the one source tree
(`debian/rules` uses `--buildsystem=meson --with python3` and
`override_dh_dkms`):

- `msi-batteryguard` (Architecture: `all`) — the GTK4 Python app. **Section:
  utils**, **Recommends: msi-ec-dkms**, **Depends: python3-gi, libgtk, libadwaita,
  libnotify**.
- `msi-ec-dkms` (Architecture: `amd64`) — the vendored kernel module, built via
  DKMS (see `override_dh_dkms` → `dh_dkms -p msi-ec-dkms`;
  `debian/msi-ec-dkms.install` copies `msi-ec-src/* usr/src/msi-ec-0.13/`).

`debian/changelog` records the 1.1.0-1 release ("Add msi-ec-dkms package (vendored
msi-ec 0.13)").

### A.6 License compatibility & combined `.deb` distribution

**Conclusion: Yes, the GPL-3.0-or-later app and the GPL-2.0-or-later kernel
module can be distributed together in/through a `.deb` set.** Two independent
reasons support this:

**1) Mere aggregation (separate programs, separate packages).** The app and the
module never link to one another. Their only interaction is the userspace app
reading/writing `/sys/class/power_supply/BAT*/charge_control_*_threshold`, which
is a kernel-provided sysfs contract exposed by the *running kernel* through the
loaded module. That is the textbook "mere aggregation" case:

- GPL-2: section 2 allows distributing a work "based on the Program" alongside
  "a separate and independent work … which is not by its nature based on the
  Program" on the *same medium*.
- GPL-3: section 5 defines and permits "aggregates".
- The Linux kernel itself treats a module's `MODULE_LICENSE("GPL")` declaration
  as the basis for loading; this is a kernel-module boundary, not an
  app↔module linkage. (See the DFSG "License Must Not Contaminate Other
  Software" clause — the GPL's mere-aggregation carve-out is precisely what lets
  copyleft code sit next to other code on the same medium.)

**2) License-to-license compatibility (the intersection is non-empty).** Per the
FSF, combining code under "GPL 2 or later" with code under "GPL 3 or later" yields
a combined work licensable as "GPL 3 or later" — i.e. the two *are* compatible:

> "When you combine code under 'GPL 3 or later' with code under 'GPL 2 or
> later,' the license of the combination is their intersection, which is 'GPL 3
> or later.'" — GNU Project, *License Compatibility and Relicensing*

This resolves cleanly **because** the module is `GPL-2.0-or-later` (per
`msi-ec.c` SPDX), not `GPL-2.0-only`. Had upstream labeled it `GPL-2.0-only`,
then *merging the code* into a single program would be incompatible with
GPL-3.0 (FSF: "This is why GPL version 2 is incompatible with GPL version 3").
But even in that hypothetical, the **actual distribution here survives** because
the two remain separate programs (mere aggregation) and only *talk* across the
kernel boundary — exactly the scenario the GPL's aggregation clauses contemplate.

**DFSG angle:** both GPL-2 and GPL-3 are DFSG-free (Debian Legal lists "GNU GPL
(versions 1, 2, or 3)" as common/DFSG-free, and the FTP Masters license table
lists `gpl2` and `gpl3` as DFSG-free). A GPL-3 work packaged alongside a
GPL-2-or-later kernel module therefore meets the DFSG for Debian `main`.

### A.7 Empirical validation (lintian)

Running `lintian -I` (Lintian v2.122.0) on the rebuilt (xz) binary packages
produced by the project's own CI yields, for the **`msi-ec-dkms`** package:

```
I: msi-ec-dkms: extra-license-file                    [usr/src/msi-ec-0.13/LICENSE]
I: msi-ec-dkms: package-contains-documentation-outside-usr-share-doc [usr/src/msi-ec-0.13/LICENSE]
I: msi-ec-dkms: package-contains-documentation-outside-usr-share-doc [usr/src/msi-ec-0.13/README.md]
I: msi-ec-dkms: unused-override no-manual-page      [...]
W: msi-ec-dkms: wrong-section-according-to-package-name utils => kernel
```

(The many `wrong-file-owner-uid-or-gid`/`bad-owner-for-doc-file` lines are
artefacts of rebuilding the `.deb` rootlessly in `/tmp` for this check and do
**not** occur in the project's CI, which builds as root. They are disregarded.)

These are **informational (`I:`) / one warning (`W:`)** — **no `E:` failure**
attributable to licensing. The `extra-license-file` note is expected and
acceptable for a DKMS package: the upstream module source tree must be
self-contained under `/usr/src/<module>-<ver>/` so DKMS can compile it, which
necessitates shipping the `LICENSE` there. The `W:` `wrong-section-according-to-package-name`
suggests `Section: kernel` rather than `utils` for a kernel module — a minor
packer's-preference issue, not a license one.

**The one substantive packaging gap** (not auto-flagged by lintian, because
lintian does not semantically re-classify licenses) is in `debian/copyright`:

- The file uses a single `Files: *` stanza → `License: GPL-3+` and a
  `Files: debian/*` → `License: GPL-3+` stanza, with a `License: GPL-3+`
  stand-alone stanza that only quotes/refs GPL-3.
- It contains **no dedicated `Files: msi-ec-src/*` stanza** documenting that
  those files are under **GPL-2.0-or-later**, and it provides **no GPL-2 license
  text/stanza** even though the package ships the GPL-2 `LICENSE` under
  `/usr/src/msi-ec-0.13/LICENSE`.

Per DEP-5 (§5.2 example), the correct form is a more-specific `Files:` stanza that
overrides the general one:

```
Files: msi-ec-src/*
Copyright: 2022-2025 BeardOverflow/msi-ec contributors
           (see upstream msi-ec.c/MODULE_LICENSE)
License: GPL-2+

License: GPL-2+
 ...full GPL-2 text or pointer to /usr/share/common-licenses/GPL-2...
```

Because GPL-2.0-or-later is itself redistributable under GPL-3.0-or-later, the
current blanket `GPL-3+` declaration is **not a license violation** and the package
installs/builds fine. It is, however, an **imprecision** in the machine-readable
copyright: the file over-claims GPL-3+ for files the upstream licensed as
GPL-2.0-or-later. Automated license scanners (which is precisely what DEP-5 was
built for — the DEP-5 rationale explicitly cites the "GPL version 3 …
incompatibility with version 2" as motivation to "spot the software where the
incompatibility might be problematic") cannot reliably flag this from the
current file.

> **Action item / assumption:** I treated the SPDX tag `GPL-2.0-or-later` in
> `msi-ec.c` as authoritative over the README's `GPL-2.0` label, and I treated
`GPL-2.0-or-later` as license-compatible with the GPL-3 app (it is, per GNU).
If upstream actually intends `GPL-2.0-only`, the *only* change to the
compatibility conclusion is that the two licenses could no longer be _merged_
into one program — but distribution as a mere-aggregation bundle of two
separate packages would still be permitted.

---

## B) Debian contribution requirements

Sources for §B: Debian Policy Manual v4.7.4.1 §12.5 *Copyright information* / §12.5.1
(Machine-readable copyright); the DEP-5 spec at
`https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/`; Debian
Legal "License information" (`https://www.debian.org/legal/licenses/`); the FTP
Masters license table (`https://ftp-master.debian.org/licenses/`); and the FSF
*License Compatibility and Relicensing* page
(`https://www.gnu.org/licenses/license-compatibility.html`).

### B.1 DEP-5 copyright-format requirements

Debian's machine-readable copyright format (originally **DEP-5**, now
normatively part of `debian-policy`) requires, for `debian/copyright`:

- A **header stanza** with at least `Format:` (mandatory, must be the 1.0 URL),
  plus optionally `Upstream-Name`, `Upstream-Contact`, `Source`, `Comment`.
- One or more **`Files:` stanzas**, each with `Files:` (required),
  `Copyright:` (required), `License:` (required).
- **Short names** with a trailing `+` meaning "or any later version" — e.g.
  `GPL-2+` = GPL v2 or later, `GPL-3+` = GPL v3 or later. License names are
  **case-insensitive** and may not contain spaces.
- Multiple licenses on one file are joined by `or` (user may choose) or `and`
  (must satisfy both); `or` has *lower* precedence than `and` unless a comma
  separates them.
- **The last `Files:` stanza matching a path applies**; specific stanzas must
  come *after* the general `Files: *` stanza to override it. This is exactly how
  the vendored `msi-ec` files should be documented (a `Files: msi-ec-src/*`
  stanza placed after `Files: *`).
- Full license text may be supplied once via stand-alone `License:` stanzas, or
  by **pointer to `/usr/share/common-licenses/GPL-{2,3}`** (Debian Policy §12.5,
  footnote 9 — which lists `GPL-1`, `GPL-2`, `GPL-3` (and LGPL/GFDL/MPL variants)
  as the licenses that "should refer to the corresponding files under
  `/usr/share/common-licenses`").

The project's `debian/copyright` already follows DEP-5 (it has the `Format:`
header, header stanza, and per-files stanzas) and references
`/usr/share/common-licenses/GPL-3`. The **missing piece** is the dedicated
`Files: msi-ec-src/*` → `GPL-2+` stanza called for by §5.2's override pattern.

### B.2 How upstream copyright/licensing must be documented

Debian Policy Manual §12.5 *Copyright information* states the binding
requirements:

> "Every package must be accompanied by a verbatim copy of its distribution
> license(s) in the file `/usr/share/doc/PACKAGE/copyright`. This file must
> neither be compressed nor be a symbolic link. … the copyright file must say
> where the upstream sources (if any) were obtained, and should include a name or
> contact address for the upstream authors."

and §12.5.1 endorses the DEP-5 machine-readable format as the way to make this
information mechanically extractable.

Concretely, for this package Debian needs the copyright file to show:

1. **Copyright holder(s)** — e.g. `2025-2026 Soubarna <Soubarna@live.in>` for the
   app packaging (already present) and the **upstream msi-ec copyright** for the
   vendored files (currently *not* documented — `Files: *` attributes it all to
   the app author, which is inaccurate for the BeardOverflow/msi-ec code).
2. **Per-file license granularity** for files under a license *other than the
   dominant one* — i.e. the `msi-ec-src/*` GPL-2.0-or-later files (see §B.1).
3. A **verbatim copy / pointer** to each distribution license. The app's GPL-3
   is satisfied via a `/usr/share/common-licenses/GPL-3` pointer. The module's
   GPL-2 needs either the full text (or a `/usr/share/common-licenses/GPL-2`
   pointer) in the copyright file — neither is currently present.

> **Why "a name or contact address for the upstream authors" matters here:** the
> `msi-ec` files are a vendored upstream snapshot (`msi-ec-src/README.md`
> documents source `https://github.com/BeardOverflow/msi-ec`, commit
> `050d4394…`). Debian Policy wants *where the upstream source came from* stated
> in the `Source:` field (already done for the overall project) — and, ideally,
> credit for the vendored portion's copyright holder.

### B.3 Does Debian require an upstream contribution policy?

**No.** Debian does not require upstream projects to have a CLA, a DCO, a
Contributor Agreement, or even a `CONTRIBUTING.md`. Debian's licensing
requirements rest on two pillars, both of which are obligations on the
*redistributor* (the Debian maintainer), not on upstream's internal processes:

1. **DFSG compliance** — every file must be under a DFSG-free license and free
   to redistribute (see §B.4).
2. **Accurate copyright documentation** — the Debian `debian/copyright` must
   capture the true copyright/licensing of every file in the package, including
   vendored code (see §B.2). Debian obtains the *right to distribute* from the
   license grant on the code, not from a contributor agreement.

The most direct authoritative evidence is the **DFSG itself**, specifically the
"Distribution of License" guideline (from the Debian Social Contract):

> "The rights attached to the program must apply to all to whom the program is
> redistributed **without the need for execution of an additional license** by
> those parties."

That clause *prohibits* Debian's own licenses from conditioning redistribution
on signing anything — which is the flip side of "Debian does not impose a CLA
requirement on upstream." Debian Legal's own page confirms the practical stance:
maintainers are encouraged to use one of the common licenses (GPL/LGPL, modified
BSD, Artistic), and any licence *uncertainty* is resolved by emailing
`debian-legal` with the license text — **not** by demanding an upstream CLA.

This also explains why the project's *absence* of both a CLA (§A.1) and a DCO
(§A.2) is **not** a Debian blocker: Debian would simply need the maintainer's
`debian/copyright` to accurately record, for each file, who holds copyright and
under what license — and to confirm the GPL family licenses are present in
`/usr/share/common-licenses`. The maintainer, not upstream, carries that
burden.

### B.4 DFSG compliance check for the vendored `msi-ec` source

**Verdict: the vendored `msi-ec` kernel module source is DFSG-free and is
acceptable for Debian `main`.**

Checks against each DFSG criterion:

- **Free Redistribution** — GPL-2.0/GPL-3.0 impose no royalty or restriction on
  sale or on inclusion in an aggregate distribution. ✅
- **Source Code** — `msi-ec-src/` ships the source (`msi-ec.c`,
  `ec_memory_configuration.h`, `Makefile`, etc.) and the GPL license text. ✅
- **Derived Works** — GPL permits modification and redistribution of derivatives
  "under the same terms." ✅
- **Integrity of Author's Source Code** — GPL allows source distribution in
  modified form and requires patch/diff-based derivation; it does not forbid
  modification. ✅
- **No Discrimination Against Persons or Groups / Fields of Endeavor** — GPL is
  neutral. ✅
- **Distribution of License** — GPL grants apply automatically to everyone to
  whom the software is redistributed, without a separate agreement (satisfies the
  DFSG clause quoted in §B.3). ✅
- **License Must Not Be Specific to Debian** — GPL applies irrespective of Debian. ✅
- **License Must Not Contaminate Other Software** — GPL v2 §2's "mere
  aggregation" carve-out explicitly allows the GPL-covered work to be distributed
  "alongside … separate and independent work[s] … on a medium" without imposing
  the GPL on those other works. This is the exact mechanism that lets the
  GPL-2.0-or-later kernel module coexist in the same archive (and same `.deb`
  bundle) as the GPL-3.0-or-later app (see §A.6). ✅

Supporting authority: Debian Legal lists "GNU General Public License
(versions 1, 2, or 3)" among licenses considered free, and the FTP Masters license
table lists both `gpl2` and `gpl3` as DFSG-free. (The only residual
*compatibility* caveat in Debian is the GPL-2-only ↔ GPL-3 *merge*
incompatibility for code that is combined into a single program — the very
problem DEP-5 was created to help detect. Here it does not arise, because
`msi-ec` is `GPL-2.0-or-later`, and even if it were `GPL-2.0-only` the two
packages would only *aggregate*, not merge.)

**Caveat on the kernel-module angle (informational, not a DFSG blocker for this
package):** the upstream Linux kernel is `GPL-2.0-only` (its `COPYING` file).
That governs what the *kernel* will load, and the module declares
`MODULE_LICENSE("GPL")`, so loading is permitted. This kernel-side
GPL-2.0-only constraint is independent of the app↔module relationship analyzed
in §A.6.

---

## Actionable recommendations

1. **Fix `debian/copyright` granularity.** Add a dedicated, overriding stanza so
   the vendored files are documented at their true license:
   ```
   Files: msi-ec-src/*
   Copyright: <upstream msi-ec copyright holders; e.g. 2022-2025 BeardOverflow/msi-ec contributors>
   License: GPL-2+
   ```
   plus a stand-alone `License: GPL-2+` block that quotes the GPL-2 text or points
   to `/usr/share/common-licenses/GPL-2`. This satisfies DEP-5 §5.2 and Debian
   Policy §12.5, and lets automated license scanners correctly classify the module.
2. **Reconcile the `msi-ec` license label.** Align `msi-ec-src/README.md`
   ("GPL-2.0") with the `msi-ec.c` SPDX tag (`GPL-2.0-or-later`) so the
   "or-later" grant — which is what makes the module license-compatible with the
   GPL-3 app — is unambiguous.
3. **Add a top-level `LICENSE` (or `COPYING`) file** declaring GPL-3.0-or-later for
   the main project, so the upstream source (not just the machine metadata) shows
   the license at a glance. (Debian binary packaging already ships it via
   `/usr/share/doc/msi-batteryguard/copyright`.)
4. **Address the one lintian `W:` tag.** Consider `Section: kernel` for the
   `msi-ec-dkms` package (lintian: `wrong-section-according-to-package-name utils
   => kernel`), since it packages a kernel module.
5. **The `I: extra-license-file` / `package-contains-documentation-outside-usr-share-doc`
   notes for `usr/src/msi-ec-0.13/LICENSE|README.md` are benign for a DKMS
   package** — the source tree must be self-contained under `/usr/src/<mod>-<ver>/`
   for DKMS to build it. No action required, but an explicit `Comment:` in the
   copyright stanza explaining the DKMS layout aids reviewers.

---

## Sources

- Debian Policy Manual v4.7.4.1 — *§12.5 Copyright information* (verbatim license copy requirement, upstream source/contact, machine-readable format endorsement): https://www.debian.org/doc/debian-policy/ch-docs.html
- DEP-5 / machine-readable `debian/copyright` format, v1.0 (rationale re: GPL-2/GPL-3 incompatibility motivating the format; `Files:`/`Copyright:`/`License:` syntax; short names `GPL-2+`/`GPL-3+`; "last matching stanza applies" override rule; stand-alone License stanzas; `/usr/share/common-licenses` pointers): https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
- Debian Social Contract — *The Debian Free Software Guidelines (DFSG)* ("Distribution of License: … without the need for execution of an additional license"; "License Must Not Contaminate Other Software"): https://www.debian.org/social_contract
- Debian Legal — *License information* ("GNU GPL (versions 1, 2, or 3)" as DFSG-free/common): https://www.debian.org/legal/licenses/
- Debian FTP Masters — *License Information* (`gpl2`, `gpl3` listed DFSG-free; "Problematic license combinations" section): https://ftp-master.debian.org/licenses/
- GNU Project — *License Compatibility and Relicensing* ("This is why GPL version 2 is incompatible with GPL version 3"; "When you combine code under 'GPL 3 or later' with code under 'GPL 2 or later,' the license of the combination is their intersection, which is 'GPL 3 or later.'"): https://www.gnu.org/licenses/license-compatibility.html
- Repository evidence gathered directly from this working tree: `meson.build` (line 5), `msi-ec-src/msi-ec.c` (lines 1 and 3106), `msi-ec-src/README.md`, `msi-ec-src/LICENSE`, `data/com.bongbetic.batteryguard.metainfo.xml` (line 5), `debian/copyright`, `debian/control`, `debian/changelog`, `debian/rules`, `debian/msi-ec-dkms.install`, `.github/workflows/ci.yml`; and `git log`/`find` scans (27 commits, 0 `Signed-off-by:` trailers, no CLA/COPYING/CONTRIBUTING/DCO files). Lintian v2.122.0 run on rebuilt xz `.deb` artefacts.
