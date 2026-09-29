# Void release qualification

This record belongs to [Build, verify, and publish the Void-capable Threshold
release](https://github.com/Bongbetic/Threshold/issues/108). It is not physical
acceptance and must not authorize publication.

A qualification XBPS was constructed from the canonical Git archive of source
commit `20bc0d7`. Its SHA-256 is
`dd23116b5cc562ace672560a68d1be693960cac4f3a0add2dcb347cb60f321c2`.
The complete build was rejected during review because the disposable container
lacked `file`, causing upstream lint/strip hooks to emit errors despite producing
an archive. The builder now installs the native `base-devel`, `file`, and `bsdtar` toolset, rejects reported hook errors,
and preserves build dependencies until their exact versions have been recorded.
The qualification package cannot become the final release candidate.

The produced package was nevertheless useful for diagnosing package lifecycle
behavior. [Fresh-container results](qualification.json) establish installation,
owned payload, runtime GI typelibs, schema availability, disabled runit service,
same-version reinstallation, and removal. Machine policy and a foreign DKMS
source registration survived reinstallation/removal. SHA-256 checks before and
after the operations matched. Extracted installed `index.html` and `appearance.py`
matched the committed application content. The generated install script did not
include the generic XBPS DKMS trigger.

These checks did not launch a physical desktop, reboot, write a live threshold,
exercise kernel recovery, or establish previous-version upgrade. The retained
older untracked XBPS was not used or replaced. Final CI construction and
qualification must pass from the selected release revision before immutable
draft assets are assembled. Physical evidence must then reference those final
assets; none of the observations here substitutes for it.

## Corrected CI qualification

[CI run 36598068587](https://github.com/Bongbetic/Threshold/actions/runs/36598068587)
passed every job on source commit `e1b2734`, including the corrected Void build,
installed-package verification, both Ubuntu test/package targets, Debian 13,
both Fedora RPM builds, dnf/zypper installation checks, web tests, and bundle
freshness. [The CI package report](ci-qualification.json) binds its container
checks to XBPS SHA-256
`494a7ac3d9e3c3e63d3e2e3650709fc95004280080832248eaebaff05338fdae`.
The downloaded artifact's package, repository metadata, build provenance and
dependency inventory all passed their recorded checksums locally.

This successful CI package supersedes the failed local construction for package
qualification. It remains a qualification package, not the final tagged release
candidate. Physical acceptance and signed-tag construction remain outstanding.
