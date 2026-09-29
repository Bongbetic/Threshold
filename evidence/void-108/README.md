# Void release qualification

This record belongs to [Build, verify, and publish the Void-capable Threshold
release](https://github.com/Bongbetic/Threshold/issues/108). It is not physical
acceptance and must not authorize publication.

A qualification XBPS was constructed from the canonical Git archive of source
commit `20bc0d7`. Its SHA-256 is
`dd23116b5cc562ace672560a68d1be693960cac4f3a0add2dcb347cb60f321c2`.
The complete build was rejected during review because the disposable container
lacked `file`, causing upstream lint/strip hooks to emit errors despite producing
an archive. The builder now installs `base-chroot`, rejects reported hook errors,
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
