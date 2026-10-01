# Reproducible Void XBPS downloads and release verification

Research date: 2026-09-29. Threshold source inspected: `534892138d93b832aa53ea0415c060b49bff9563`.

Resolution of [Research reproducible Void XBPS downloads and release verification](https://github.com/Bongbetic/Threshold/issues/104), child of [Deliver Void packages and adaptive Wayland desktop support](https://github.com/Bongbetic/Threshold/issues/103).

## Recommended contract

Publish one unified `x86_64` glibc XBPS and its local repository index as immutable GitHub release downloads. Build from the exact canonical source archive used by the release, verify those same bytes in a fresh Void environment, and include both downloads in the release manifest and signed checksum inventory. Users download and verify the files, then install from their local directory. This meets the accepted binary-release request without creating a permanent remote XBPS repository or a second signing key. Local XBPS repositories need no XBPS signature; remote repositories require one. [Void signing documentation](https://docs.voidlinux.org/xbps/repositories/signing.html), [custom repositories](https://docs.voidlinux.org/xbps/repositories/custom.html).

This recommendation supersedes only the source-template-only distribution restriction in [the existing Void ADR](../adr/002-void-linux-native-support.md). Retain the glibc-only target, administrator-controlled service enablement and Secure Boot, and physical acceptance requirement. The user explicitly accepted downloadable XBPS publication; no additional product decision is required to implement this contract.

## Current repository findings

- The [Void template](../../packaging/void/template) is version `2.0.1_1`. It supplies GTK4, libadwaita, WebKitGTK 6, Python GI, notification and DBusMenu dependencies, vendored MSI EC source, a dedicated `threshold` group, udev policy, and a runit service. Its `distfiles` fetches the `v2.0.1` GitHub tag archive with a fixed checksum.
- [Void CI](../../.github/workflows/ci.yml) copies the current template into a fresh `void-packages` clone but still fetches that tag archive. Consequently it can test current packaging against old application code. It checks only three payload paths and retains no downloadable XBPS artifact. Passing this job does not establish that checkout changes were built.
- [Release assembly](../../.github/workflows/release.yml) excludes `*.xbps` and repository metadata. [The Void test](../../tests/test_void_packaging.py) explicitly forbids `candidate-xbps`; update that obsolete restriction with the ADR and installation documentation.
- Existing [physical installation evidence](../../evidence/physical-gate-installation-2026-09-27T19:33:59Z.txt) and [live EC evidence](../../evidence/physical-gate-live-ec-write-readback-2026-09-27T19:33:59Z.txt) describe a DEB installed on a Debian kernel. They cannot prove Void installation, runit behavior, or the new XBPS. No `evidence/void-acceptance.md` exists at the inspected revision.

## Exact source and build identity

Use a fresh disposable Void glibc build environment with a recorded image digest and pinned `void-packages` commit. Record its resolved dependency versions too: a pinned template checkout alone cannot freeze the contents of rolling binary repositories. Existing `ethereal` mode is suitable only inside that disposable container; upstream explicitly says it operates on the host filesystem. [Upstream build README](https://github.com/void-linux/void-packages/blob/141bcf65ca6f96e557e42814e43107b90554fbcd/README.md#ethereal).

Recommended release and branch-CI source flow:

1. Create one canonical archive from the intended committed checkout. Include the committed rebuilt `web/dist` and vendored EC tree; verify their freshness and EC manifest checksum before archiving. Record archive SHA-256, resolved commit, tag if applicable, and template checksum.
2. Generate a build-local copy of the Void template that names the canonical archive, sets `wrksrc` to its exact top-level directory, and sets `checksum` to that archive's SHA-256. Preserve the normal upstream template for public source builds; do not disable checksum checks.
3. Place the archive at `hostdir/sources/threshold-<version>/<canonical-filename>`. The upstream fetch hook accepts already-present files only after comparing their digest with `checksum`; it returns without fetching when all cached files match. This avoids requiring publication of a source archive before draft creation. A local-source URL in the generated template should fail if the cache is absent rather than quietly selecting a different upstream archive. [Fetch-hook implementation](https://github.com/void-linux/void-packages/blob/141bcf65ca6f96e557e42814e43107b90554fbcd/common/hooks/do-fetch/00-distfiles.sh).
4. Build once through `xbps-src`; it emits `threshold-<version>_<revision>.x86_64.xbps` into `hostdir/binpkgs`. In a clean output directory, register only that XBPS and preserve the resulting `x86_64-repodata`. Do not copy dependency packages into the release. Use an explicit expected filename and fail on missing or additional Threshold candidates. [XBPS package manual](https://github.com/void-linux/void-packages/blob/141bcf65ca6f96e557e42814e43107b90554fbcd/Manual.md#package-build-phases), [xbps-rindex](https://man.voidlinux.org/xbps-rindex.1).
5. Record package and index digests with the source digest, source revision, package version/revision, architecture, image digest, `void-packages` commit, build tool/dependency versions, and verification evidence. All downstream jobs consume these exact files. A reproduction experiment may build a second copy for comparison; it must not replace the candidate silently.

Distinguish traceable construction from bit-for-bit reproducibility. The present recipe and rolling dependencies do not prove identical future binary bytes. Claim reproducibility only after independent matching builds with recorded inputs; otherwise claim exact-source provenance and immutable candidate verification. This is a research recommendation, not an observed successful build.

## Downloads, installation, and trust

Recommended release assets add two files: `threshold-<version>_<revision>.x86_64.xbps` and `x86_64-repodata`. Cover each in `release-manifest.json` and `SHA256SUMS`, then sign the inventory through the existing protected release key. Publish the release key fingerprint through the project's established trust channel. The existing AppImage EC Ed25519 key is a separate purpose and must not be reused implicitly. [Current release workflow](../../.github/workflows/release.yml), [EC trust model](../../packaging/trust/README.md).

After verifying the signed inventory and these downloaded files, install from a directory containing both:

```sh
sudo xbps-install --repository="$PWD" 'threshold-<version>_<revision>'
```

The package argument is a package expression, not the `.xbps` filename. `--repository` places the local directory first while retaining the configured Void repositories to obtain dependencies. Use the exact package version expression to bind installation to the selected release. A standalone XBPS can instead be indexed locally with `xbps-rindex -a "$PWD/threshold-<version>_<revision>.x86_64.xbps"`; shipping the index avoids that extra step. These are documentation examples with placeholders, not commands executed during research. [xbps-install](https://man.voidlinux.org/xbps-install.1), [xbps-rindex](https://man.voidlinux.org/xbps-rindex.1).

Do not instruct users to point XBPS directly at unsigned GitHub asset URLs. A remote repository needs XBPS RSA signing metadata and signed packages, with users accepting the corresponding trust key. Creating a permanent repository also brings ongoing index maintenance and updates. Downloading release files and installing locally needs neither a permanent repository setting nor that additional XBPS signing identity. [Void signing documentation](https://docs.voidlinux.org/xbps/repositories/signing.html).

## Lifecycle and package verification

The [runit service](../../packaging/void/files/threshold-boot-reconcile/run) runs reconciliation once, then executes `pause`; [installation instructions](../../packaging/void/INSTALL.msg) leave activation to the administrator. Preserve that model and verify both disabled and enabled cases. Void enables services with a symlink from `/etc/sv/<service>` into `/var/service`; merely installing its files does not establish successful boot reconciliation. [Void service documentation](https://docs.voidlinux.org/config/services/index.html).

There is a concrete integration risk to test before publication: `dkms_modules` activates Void's own install/removal trigger, while [Threshold INSTALL](../../packaging/void/INSTALL) and [REMOVE](../../packaging/void/REMOVE) also invoke the [shared lifecycle](../../packaging/threshold-ec-lifecycle). Void's trigger attempts builds for kernels with headers and removes matching module registrations without consulting Threshold's ledger. Threshold's setup separately checks hardware and source provenance and runs DKMS. Therefore do not assume that its ledger guard covers every operation performed by XBPS. Verify generated scripts and actual trigger ordering, then make package-manager ownership and shared lifecycle responsibilities consistent. This fits the package delivery work; it does not require another product decision. [Void DKMS trigger source](https://github.com/void-linux/void-packages/blob/141bcf65ca6f96e557e42814e43107b90554fbcd/srcpkgs/xbps-triggers/files/dkms).

Verify the candidate in a fresh Void environment, not only by inspecting its archive:

- Installation resolves runtime dependencies and produces the application, WebKit UI bundle, GSettings schemas, desktop entry, app/status icons, lifecycle executable at the Void path, EC source, udev group rule, and runit service. No systemd unit should remain in the Void payload.
- A package-installed launch resolves GI typelibs and schemas. A missing kernel/header or non-MSI environment must produce a truthful, bounded status rather than a claimed working EC setup.
- Upgrade preserves the configured threshold and user settings. Removal preserves machine policy and foreign assets according to the established lifecycle contract. Verify the native DKMS trigger's effects explicitly.
- Record package digest, OS/architecture, installed dependency versions, commands, results, and logs. CI must retain this evidence and fail on verification failure.

These are proposed acceptance checks grounded in the [Void ADR](../adr/002-void-linux-native-support.md), [installation contract](../../INSTALL.md#void-linux-x86_64-glibc), and existing lifecycle implementation; none was run in this research ticket.

## Protected release changes

Extend existing jobs rather than creating a second publication path. Add version preflight against the Void template, build and verification jobs, explicit XBPS/index artifact collection, manifest entries, and signed checksum coverage. Make assembly depend on successful Void verification. Update `scripts/verify-release-candidates.sh` to understand XBPS if it remains part of the release process. [Workflow](../../.github/workflows/release.yml), [verification script](../../scripts/verify-release-candidates.sh).

The current workflow contains gaps relevant to adding a trustworthy candidate:

- The physical gate warns and skips hash binding if `releases/<version>/` is absent, instead of downloading and comparing the actual draft assets. It only requires one matching hash somewhere in evidence.
- Unparseable evidence timestamps are skipped; the filename regular expression contains doubled backslashes. Require valid timestamps and every applicable required result, rejecting missing or stale records.
- Manifest desktop and physical evidence entries are hardcoded claims. Replace them with references to validated results, including the exact XBPS digest and the tested Void and desktop versions.
- Promotion downloads only `SHA256SUMS`, signs it, and publishes the draft. Despite the step name, it does not download/reverify the candidate files. Before signing, compare the complete draft inventory against the manifest and checksum file, validate source/tag identity and evidence, then publish unchanged bytes.
- The manifest generator writes into the directory it hashes. Avoid including a partial `release-manifest.json` in its own candidate enumeration. Build metadata outside the directory or enumerate explicit candidate names.

These findings come directly from [release.yml at the inspected source revision](https://github.com/Bongbetic/Threshold/blob/534892138d93b832aa53ea0415c060b49bff9563/.github/workflows/release.yml). Keep the protected `release-promotion` environment; the accepted publication request does not require bypassing its gate.

## Physical evidence boundary

Before declaring supported Void operation, record acceptance on actual `x86_64-glibc` Void using the exact candidate digest. Cover installation, live write/readback, persisted threshold, enabled runit service across reboot, absent/failed kernel builds and recovery, Secure Boot state, and removal. Extend desktop evidence to actual niri/DankMaterialShell Wayland behavior and clipping checks defined by the desktop work. Containers can establish package installation and payload behavior; they cannot establish hardware EC control, real reboot reconciliation, or desktop integration. [Void acceptance requirement](../../INSTALL.md#void-linux-x86_64-glibc), [physical protocol](../verification/msi-physical-gate.md).

The existing physical protocol is DEB/systemd oriented and needs Void equivalents. Its documentation demands evidence no older than seven days and bound to the same immutable artifact. Research cannot fabricate the missing Void hardware run. Candidate preparation can finish before that run; support claims and protected public promotion must wait for the applicable recorded evidence.

## Research method and remaining work

Used Context7 library resolution followed by two documentation queries against `/void-linux/void-docs`, then official Void manuals and upstream source where snippets lacked implementation detail. No Context7 quota error occurred. No packages were built or installed, no application code changed, and no release was mutated. Remaining implementation and evidence work belongs to the existing release delivery ticket; no new human choice emerged.
