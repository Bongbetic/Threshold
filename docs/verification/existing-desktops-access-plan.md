# Existing-desktops physical access plan (issue #121)

Status: **BLOCKED on human decisions.** No qualifying environment is confirmed.
This document is preparation only. It is not evidence and does not satisfy any
acceptance check. Nothing here authorizes buying hardware, repartitioning,
installing an operating system, or changing boot configuration.

Parent: [#116](https://github.com/Bongbetic/Threshold/issues/116); umbrella
[#108](https://github.com/Bongbetic/Threshold/issues/108); map
[#103](https://github.com/Bongbetic/Threshold/issues/103).

## What the validator requires

From `scripts/release_inventory.py` (`validate_acceptance`):

- Exactly two physical records: `void-x86_64-glibc` (XBPS) and `existing-desktops`.
- Every record: `system == "MSI Thin A15 B7UCX"`, `physical == true`, non-empty
  `kernel` and `os`, candidate name and SHA-256 matching the release manifest.
- `existing-desktops` candidate must be an installable `.deb`, `.rpm` or
  `.AppImage` (not `.src.rpm`). AppImage is absent from v2.0.4. One of DEB or
  RPM suffices; both are not required.
- Checks (each: `result: pass`, non-empty `details`, UTC `timestamp` within the
  last 7 days and not in the future, sanitized `asset`, matching `asset_sha256`):
  `installation`, `live_ec`, `reboot_reconciliation`, `machine_policy`,
  `secure_boot`, `failed_kernel_build`, `known_good_boot`, `named_kernel_repair`,
  `subsequent_verification`, `safe_removal`, plus `kde_plasma_wayland` and `xfce`.

Procedure per check: [msi-physical-gate.md](msi-physical-gate.md) sections 1-12.
Its illustrative commands must be checked against the installed lifecycle
behavior before use.

## Candidate selection (verify identity at execution time)

Draft release tag `v2.0.4`, signed source `3682e414b40918ff7c1a8071ae26830e1dd858c4`.
Both assets are in the release manifest; choose one.

| Option | Asset | SHA-256 (from draft release metadata) | Suits |
| --- | --- | --- | --- |
| DEB | `threshold_2.0.4-1_amd64.deb` | `66e9526083db49a3d0d816464a145ef52ce770b5c8c83a5537144175e318f574` | Debian/Ubuntu/Kubuntu/Xubuntu |
| RPM | `threshold-2.0.4-1.noarch.rpm` | `5b7a726c9528d99d248ed226461c67759a06ea8357ed1d20b2a9efc3f480ff48` | Fedora KDE / openSUSE |

Selected candidate: **NOT YET CHOSEN** (depends on the OS the user agrees to).
Any source/package fix means a new version and new hashes; this table is then stale.

## Access options (user must choose; agent will not execute any)

The record needs the MSI Thin A15 B7UCX itself. The only known available unit
runs Void. Options:

1. **External/removable SSD with a DEB or RPM distro** that offers both KDE
   Plasma Wayland and XFCE, booted on the same laptop. No internal disk change;
   needs a drive, and boot-menu use. Likely least invasive.
2. **Second internal partition / dual boot.** Requires repartitioning; explicit
   user agreement and backup first.
3. **A second, separate MSI Thin A15 B7UCX** (borrowed/owned) with a suitable OS
   already installed. No effect on the Void machine.
4. **Replace Void temporarily.** Not recommended; invalidates Void evidence work.

Not acceptable: VM, container, other hardware model, remote staged probes, or
waiving the gate.

## Intake checklist (human to complete; agent fills in only what is supplied)

- [ ] Option chosen (1-4): ______
- [ ] Responsible operator with permission for package, EC, kernel, reboot, desktop work: ______
- [ ] Distro and release (DEB or RPM family), kernel with headers/DKMS available: ______
- [ ] KDE Plasma Wayland and XFCE sessions installable/available: ______
- [ ] Selected candidate (DEB or RPM) and SHA-256 verified against the draft manifest: ______
- [ ] Administrative (root/sudo) authorization confirmed: ______
- [ ] Battery sysfs `charge_control_end_threshold` reachable after msi-ec loads: ______
- [ ] Secure Boot state on that OS (enabled/disabled; disabled proves no MOK result): ______
- [ ] Recovery route (second kernel kept installed, boot menu access, live USB): ______
- [ ] Log collection method and privacy-reviewed screenshot method (no usernames,
      home paths, serials, UUIDs, credentials): ______
- [ ] Written agreement for any disk/boot change: ______

## Scheduling and sharing the machine

- Do not run kernel transitions (failed-build, known-good boot, named-kernel
  repair, reboots) on a given OS while another acceptance session is mid-run on
  the same machine. Each OS session holds the machine exclusively.
- Order: finish Void remaining items first (issues #122+ as scheduled) or keep
  them separate by boot target; never interleave reboots between them.
- Freshness: all checks must be within 7 days at promotion, so run the
  existing-desktops pass as one contiguous window shortly before promotion.
  Repeat observations against the unchanged candidate; do not just refresh timestamps.
- Restore the user's confirmed charge threshold after each controlled write test.
- Record UTC timestamps at observation time.

## Closing this issue

Close #121 only when an environment above is genuinely available, the checklist
is complete, and the candidate is recorded. Otherwise keep #121 and dependent
acceptance open and record the external blocker.
