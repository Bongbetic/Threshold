# Native desktop controls and recovery observations for issue #120 (user-attested)

Recorded `2026-10-06` (UTC date of attestation). Time of the underlying
observations: not recorded.

Candidate: `threshold-2.0.4_1.x86_64.xbps`, SHA-256
`62d55b0b7814472fdf2effb3efbe2c85eb1f90278b23777941e187af01af74f6`
(identical to the baseline in the parent README and `appearance-119/`).
Signed source: `3682e414b40918ff7c1a8071ae26830e1dd858c4`.

Environment as stated by the maintainer: physical MSI Thin A15 B7UCX, Void
Linux glibc, niri 26.04, kernel `7.2.9_1`, dms-1.6.2_2, quickshell-0.3.1_1.
Portal service version and session details: not recorded.

## Nature of this evidence

**Every result below is user-attested.** The maintainer stated, in chat on
2026-10-06, that all of the physical tests for issue #120 were performed on the
physical laptop with the installed candidate and that everything was verified.
The maintainer gave no per-item observations. The agent recording this did not
observe any of it, captured no screenshots or other assets, and has no hashes,
timings, menu positions, or outcomes beyond what is stated here. Automated
tests, staged probes, and the earlier D-Bus Activate probe are not counted.

Because there are no supporting assets, this record does not satisfy the
release validator's requirement of a sanitized supporting asset with a SHA-256
per passing check, nor the acceptance item asking for privacy-reviewed
screenshots. It does not change `release-acceptance.json`. Whether to accept
user attestation for release promotion is a maintainer decision outside this
record.

## Results

| Check | Result | Basis | Details |
| --- | --- | --- | --- |
| `pointer_controls` | PASS | user-attested, 2026-10-06 | Window movement, minimize/maximize/restore/close behaviour and continued usability under niri: not recorded |
| `notification_area_menu` | PASS | user-attested, 2026-10-06 | Icon and tooltip rendering, menu placement, preset success/error outcomes, reopen, Quit, and restoration of the confirmed threshold: not recorded |
| close-to-notification-area safety | PASS | user-attested, 2026-10-06 | Behaviour with live host and after host disappearance: not recorded |
| `watcher_restart` | PASS | user-attested, 2026-10-06 | Re-registration and recovery after restarting the watcher/host: not recorded; which service was restarted: not recorded |
| `portal_restart` | PASS | user-attested, 2026-10-06 | Preference/appearance updates and usability after portal restart: not recorded; which portal service: not recorded |
| `activation_token` | PASS | user-attested, 2026-10-06 | Visibility and focus outcomes (to be judged separately, respecting compositor policy): not recorded |

Candidate identity verification at execution time (acceptance item 1) was not
independently re-observed by the agent; the identity above is carried from the
existing evidence and the maintainer's statement that the installed candidate
was used.
