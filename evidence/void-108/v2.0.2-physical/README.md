# v2.0.2 physical candidate rejection

Candidate: `threshold-2.0.2_1.x86_64.xbps`  
SHA-256: `9ea803b6e2a8ea65cb994526829aa52804c107af7c68351b1608120ef8d9dcad`  
Source: `19ffc812d14278d26edeb245a7a9cdb6f784d778`  
Observed: 2026-09-29, Void Linux glibc, MSI Thin A15 B7UCX, kernel `7.2.8_1`.

The immutable draft is **not accepted for promotion**. Installation built and
loaded the vendored EC module successfully on the real laptop. The installed
battery write function, invoked administratively, wrote 70% and read 70%, then
restored the original 60% and read 60%. Secure Boot is disabled; this proves no
enrollment or enabled-Secure-Boot behavior.

The normal desktop user's `_persist_machine_threshold(60)` returned without
creating `/var/lib/threshold/ec/charge-threshold`: the lifecycle directory is
root-owned and write errors were swallowed. Machine-policy acceptance fails.
The user's GSettings preference remains 80%; the active hardware limit is 60%.
No policy was manually seeded to disguise this failure. The disabled runit
service remains disabled, and no reboot acceptance has been claimed.

The installed native application was probed in the actual niri/DMS session:
Wayland display/toplevel, System appearance consuming the DMS dark palette,
640/480-pixel tiled widths without horizontal document overflow, and ready
notification-area close/hide followed by D-Bus Activate reopening all passed.
These observations do not prove pointer/menu interaction, activation tokens,
watcher/portal restarts, other scales, KDE Plasma or XFCE. No live desktop
configuration or DMS palette was changed by the probe.

Files contain sanitized observations. The boot identity is SHA-256 only.
These are partial/rejection evidence, not `release-acceptance.json`.
