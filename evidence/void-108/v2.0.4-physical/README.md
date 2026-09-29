# v2.0.4 pre-reboot physical observations

Candidate: `threshold-2.0.4_1.x86_64.xbps`  
SHA-256: `62d55b0b7814472fdf2effb3efbe2c85eb1f90278b23777941e187af01af74f6`  
Signed source: `3682e414b40918ff7c1a8071ae26830e1dd858c4`  
Host: MSI Thin A15 B7UCX, Void Linux glibc, kernel `7.2.8_1`.

[Exact-source CI](https://github.com/Bongbetic/Threshold/actions/runs/36605558005)
and [immutable release construction](https://github.com/Bongbetic/Threshold/actions/runs/36606194015)
passed. All downloaded draft assets passed the release inventory verifier.
AppImage is absent: its optional build failed. Public promotion has not run.

## Actual observations

- Upgraded the real laptop from repaired v2.0.3 to this exact v2.0.4 XBPS.
  The installed application and EC lifecycle reported available/healthy.
- Removed v2.0.4: its managed DKMS registration was removed and the stock
  on-disk module restored. The working loaded module, active 60% threshold,
  machine policy, and unrelated NVIDIA registrations were preserved.
- Reinstalled the unchanged XBPS in the same boot: DKMS rebuilt and installed
  `msi-ec.ko.zst` successfully using the newly supplied zstd dependency.
- Invoked the installed command dispatcher as the normal desktop user.
  Real Polkit authorization permitted 70%, then 60%; hardware readback,
  GSettings preference, and machine policy all matched each requested value.
  No administrative cleanup was needed. Final limit and policy are 60%.
- The installed app used a native Wayland display/toplevel in niri, consumed
  the DMS dark palette, and showed no horizontal document overflow at tiled
  widths of 640 and 480 pixels. A ready notification-area item allowed hiding,
  and its exported D-Bus Activate method restored visibility.
- Enabled the installed runit service explicitly. It is running and completed
  a no-write reconciliation because active and desired values both equal 60%.
  Void's stage-1 module loader reads the installed `/usr/lib/modules-load.d`
  configuration. Secure Boot is disabled; MOK enrollment was not tested.

## Reboot handoff and limits

**No actual reboot has happened yet.** The current-boot known-good marker and
service run are not counted as real reboot acceptance. `before-boot.json`
records the hashed boot identity, installed package, policy, service state,
Secure Boot state, and lifecycle observations for comparison after reboot.

Reboot normally into the current `7.2.8_1` kernel, then resume this task.
The persistent local acceptance directory contains `capture-boot.py`; running
it administratively with argument `after` records the new boot without changing
hardware or package state. Require a changed boot identity, package 2.0.4,
working EC control, policy/readback 60%, a running reconciliation service,
and lifecycle state belonging to that actual new boot.

Remaining: actual reboot reconciliation/known-good boot, physical failed-kernel
build and named-kernel recovery sequence, post-reboot verification, live watcher
and portal restarts, scaling, pointer/menu interaction, activation-token checks,
and full visual clipping assessment. Only this Void laptop is available;
physical DEB/RPM KDE Plasma Wayland and XFCE acceptance remains unavailable.
The existing source-level recovery tests are not physical proof.

This is partial evidence, not a passing `release-acceptance.json`. Keep the
release task open and every draft unpublished until required gates pass.
Logs are sanitized; boot identities are hashed and no screenshots are included.
