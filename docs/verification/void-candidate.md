# Void XBPS candidate protocol

The release target is Void Linux x86_64-glibc. Package CI is qualification,
not physical acceptance or a support declaration.

## Exact source construction

Rebuild `web/dist` and commit it with all application and package changes.
Preflight rebuilds the web bundle and rejects drift. The source job archives
only the selected Git revision, with one `Threshold-<version>/` root. It does
not include local untracked files. Preserve that archive and its hash.

Run `scripts/build-void-candidate.sh SOURCE ARCHIVE OUTPUT` only inside the
pinned disposable Void container from `packaging/void/build-pins.env`. Ethereal
mode operates on the container root; never run it on a real host. The script
pins void-packages, seeds its source cache with the canonical archive, and
replaces the build-local template URL, checksum, and source root. A cache miss
cannot fall back to an older release tag. The checked-in template deliberately
has a placeholder checksum; use source preparation, not an unchecked direct build.

The outputs are the unified XBPS, `x86_64-repodata`, `void-build.json`, and
`void-dependencies.txt`, with `candidate.sha256` for transport verification.
The provenance records the image digest, void-packages revision, actual
installed build dependency versions, and source archive hash. This establishes
traceable construction, not bit-for-bit reproducibility against future rolling
repositories. Final candidates are built once and never substituted after testing.

## Installed package qualification

In a fresh disposable Void container run:

```sh
bash scripts/verify-void-candidate.sh /candidates /reports/void-verification.json
```

This validates hashes before and after installation, payload ownership,
Python GI runtime dependencies, schemas, disabled runit service, same-version
reinstallation, and removal policy. It does not assert previous-version upgrade,
GUI operation, live module control, or reboot behavior. Keep a separate
previous-version upgrade record if testing an already installed older package.

Threshold's package hooks own initial EC setup and removal through the shared
lifecycle ledger. The generic XBPS DKMS trigger is not enabled because it can
remove registrations without provenance checks. The kernel package's DKMS
integration still processes registered modules. Verify physical kernel update,
failure, repair, and removal behavior before support is declared.

## Physical acceptance and publication

The release workflow assembles a draft only after package jobs pass. Its
manifest binds every asset to the source revision and hashes, without claiming
that package tests establish physical or desktop success. The existing AppImage
trust-key packaging remains unresolved; its job is optional and no AppImage is
advertised unless its canonical asset actually exists and passes verification.

Physical evidence is collected after the immutable draft exists. Commit
`evidence/release-acceptance.json` and its sanitized supporting logs/screenshots
on a separate evidence branch. Pass that full commit ID as `evidence_ref` when
running release promotion on the release tag. This avoids changing the tagged
source simply to add evidence about artifacts built from it.

The report has `source_revision` and two `records`: `void-x86_64-glibc` names
the exact XBPS; `existing-desktops` names the tested DEB, RPM, or AppImage.
Each record contains `candidate`, `sha256`, `physical: true`, `system:
"MSI Thin A15 B7UCX"`, `os`, `kernel`, and a `checks` mapping. Record actual
versions, observations and limitations. Never produce acceptance from simulation.

Every check contains `result: "pass"`, `timestamp` in UTC
`YYYY-MM-DDTHH:MM:SSZ`, nonempty `details`, an `asset` path relative to the
report, and that file's `asset_sha256`. Supporting assets must be sanitized.
Screenshots require human privacy review; text pattern checks cannot inspect pixels.

Both records require installation, live EC write/readback, reboot reconciliation,
machine policy, Secure Boot state/behavior, failed kernel build, known-good boot,
named-kernel repair, subsequent verification, and safe removal. The exact check
keys are `PHYSICAL_CHECKS` in `scripts/release_inventory.py`. Secure Boot disabled
is a passing state observation only when documented; do not invent an MOK test.
The existing-desktops record additionally requires `kde_plasma_wayland` and `xfce`.
The Void record additionally requires every `VOID_DESKTOP_CHECKS` entry, covering
native Wayland, DMS colors, tiling/clipping, watcher and portal restart, scaling,
pointer controls, menu behavior, and activation tokens. Reopen may restore
visibility without focus; record compositor behavior rather than claiming focus.

Validate locally against downloaded draft assets:

```sh
python3 scripts/release_inventory.py physical /draft \
  --version '<version>' --revision '<full-source-commit>' \
  --evidence evidence/release-acceptance.json
```

The validator rejects absent checks, unsuccessful results, malformed dates,
future/stale evidence (older than seven days), wrong candidate hashes, absent
assets, and known privacy patterns. It verifies the complete draft inventory,
including repository metadata and canonical source provenance. Protected
promotion repeats these checks after approval, signs the unchanged checksum
inventory, downloads and checks everything again, then publishes. Existing
assets are never overwritten. The repository administrator must configure
reviewers on the `release-promotion` environment; naming an environment alone
does not enable an approval rule.
