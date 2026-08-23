# Threshold — fix-v3: investigation report & fix plan (2026-08-23)

Plan only — no code changes applied. Trigger: user-reported regression —
*app sets the alarm when threshold reached but never writes the threshold to
the EC microcontroller; never reads the msi-ec threshold at startup; UI lost
its industrial gridlines and is too large; msi-ec must ship inside the .deb
and be signed.*

Method: live system probing on the target laptop (MSI Thin A15 B7UCX,
Xfce 4.20, Debian 13, kernel 6.12.101+deb13-amd64, Secure Boot ON),
`dkms`/`modinfo`/journal inspection, deb content inspection, source review
of `src/threshold/`, `debian/`, `msi-ec-src/`, and the prototype spec.

---

## Status summary

| ID  | Sev | Area      | Symptom                                            | Root cause found |
|-----|-----|-----------|----------------------------------------------------|------------------|
| V3-1 | P0 | kernel/packaging | No EC read/write; alarm-only fallback        | **YES** — deb ships msi-ec v0.13; laptop FW `16RKIMS1.112` not in v0.13 whitelist |
| V3-2 | P0 | packaging | "msi-ec signed + in deb" requirement appears broken | **YES** — same as V3-1 (stale version); signing machinery itself works |
| V3-3 | P1 | UI         | Gridlines gone; UI too large                       | **YES** — gridline pattern never existed in CSS; sizes never scaled down |
| V3-4 | —  | install    | Remove currently installed Threshold              | remediation step (no bug) |

---

## V3-1 — App never reads/writes the EC threshold (P0)

### Evidence (all verified live, 2026-08-23)

- `dpkg -l`: `threshold 1.4.0-1` installed.
- `dkms status`:
  - `msi-ec/0.13, 6.12.101+deb13-amd64: installed` ← from the deb
  - `msi-ec/0.13.112, 6.12.101+deb13-amd64: built` ← the FIXED source, **never installed**
- Kernel log, boot 19:02:16:
  - `msi_ec: loading out-of-tree module taints kernel.`
  - `msi_ec: Your firmware version is not supported!`
- `modinfo /lib/modules/.../updates/dkms/msi-ec.ko.xz` → `version: 0.13`,
  `signer: DKMS module signing key` (module loads fine — it *rejects the firmware*).
- `/sys/devices/platform/msi-ec` — **absent** (module init bails before
  `platform_create_bundle`).
- `/sys/class/power_supply/BAT1/charge_control_end_threshold` — **absent**.
- Firmware whitelist in vendored `msi-ec-src/msi-ec.c` (== `/usr/src/msi-ec-0.13/msi-ec.c`):
  contains `16RKIMS1.110`, `16RKIMS1.111`, `16RKIMS2.108`, `16RKIMS2.111` —
  **not** `16RKIMS1.112`.
- `/usr/src/msi-ec-0.13.112/msi-ec.c:1598`: `"16RKIMS1.112", // Thin A15 B7UCX;
  same CONF_G2_6 layout, staged validation` — upstream 0.13.112 (reviewed
  commit `d7fbbd8` of BeardOverflow/msi-ec per its README.staged) supports it.

### Root-cause chain

1. msi-ec v0.13 module init reads EC firmware version (`16RKIMS1.112`),
   finds no whitelist match, prints "Your firmware version is not
   supported!", returns `-EOPNOTSUPP` → no platform device, no
   `charge_control_end_threshold` sysfs file.
2. App `detect_control_mode()` (src/threshold/battery.py) sees no threshold
   file → `ControlMode.NOTIFY_ONLY`.
3. In notify-only, `_on_apply`/`_on_restore` short-circuit with
   `(True, 'alarm')` — **no EC write ever attempted**; `_load_settings`
   reads the threshold from GSettings, **not the EC**. Exactly the
   reported symptoms.
3. The application code itself (v1.4.0: startup EC read, poll-time
   `_sync_from_hardware`, write + read-back verification in
   `_finish_apply`/`_finish_restore`) is correct — verified by review; it
   simply never gets an EC to talk to.
5. A working 0.13.112 source tree was staged on this machine and built for
   the running kernel, but installing `threshold 1.4.0` ran
   `dkms add/build/install -m msi-ec -v 0.13` (postinst), which overwrote
   the `updates/dkms` module slot with the broken v0.13.

**Conclusion: not an app-logic bug. The deb vendors a stale msi-ec that
does not know this laptop's firmware. Fix = ship msi-ec 0.13.112.**

---

## V3-2 — msi-ec inclusion + signing in the .deb (P0)

What is already true and works:

- `threshold_1.4.0-1_amd64.deb` **does** contain the msi-ec source tree
  (`./usr/src/msi-ec-0.13/…`, 8 files, verified with `dpkg -c`).
- `debian/threshold.postinst` runs `dkms add/build/install`.
- DKMS auto-signing works on this machine: MOK keypair exists at
  `/var/lib/shim-signed/mok/`, kernel log shows the enrolled cert
  `DKMS module signing key`, and the installed `msi-ec.ko.xz` carries
  that signature. **Secure Boot is not the blocker.**

What is broken:

- Stale source version (V3-1).
- The version string `0.13` is hardcoded in **three** packaging files:
  `debian/threshold.install` (`usr/src/msi-ec-0.13/`), `debian/threshold.postinst`
  (`dkms … -v 0.13` ×3), `debian/threshold.prerm` (`dkms remove … -v 0.13`).
  Every future module bump requires editing all three — this is exactly how
  the tree drifted (`0.13.112` sits on disk while packaging says `0.13`).
- `dkms build/install … || true` swallows every failure. On Secure Boot
  machines without an enrolled MOK, or a headers mismatch, install
  "succeeds" and the app silently degrades to notify-only — the user is
  never told EC control is dead. This is the mechanism that hid V3-1.
- `debian/threshold.postinst` writes `/usr/lib/modules-load.d/msi-ec.conf`
  via `echo` at install time — never removed on purge (`postrm` absent).

---

## V3-3 — UI: gridlines gone, window too large (P1)

Findings:

- **No gridline pattern has ever existed in the shipped CSS.** `data/style.css`
  (537 lines) has zero `repeating-linear-gradient`/crosshatch rules — neither
  does any commit in history, nor any prototype `.blp`/`.ui`/`.py`. The
  "Industrial Grid UI" name and the spec's reference image describe grid
  lines, but only the panel *layout* was ever implemented. The lines were
  never removed — they were never built.
- Window defaults: `default-width 980 × default-height 680`
  (data/ui/window.ui). Instrument font 28px, secondary 24px, smallest 11px.
  v1.4.0 "UI tightening" (F-13) only reduced card spacing — no scaling.

Interpretation **confirmed by user**: reduce to ~½ current footprint, and
**no scrolling to view the UI** — the whole dashboard must fit the window.
A literal ½ on fonts would put body text at 6–7px (unreadable), so geometry
is halved while fonts scale by ~0.6 with a 9–10px readability floor,
preserving the visual hierarchy.

Scroll-free constraint (current state violates it): `window.ui:12-28` sets
`width-request 820 / height-request 560` and wraps the entire content in a
`GtkScrolledWindow` — below 820×680 the UI scrolls today. At the new smaller
target this must be restructured, not just resized (Phase 2.3).

---

## V3-4 — Remove the currently installed Threshold

Remediation only. Current install: `threshold 1.4.0-1` (amd64) from
`releases/threshold_1.4.0-1_amd64.deb`, plus dkms `msi-ec/0.13` installed
and `msi-ec/0.13.112` built-but-not-installed. Removal covered in Phase 0.

---

## Fix plan

### Phase 0 — clean the machine (V3-4)

```sh
sudo apt remove --purge threshold
sudo dkms remove msi-ec/0.13 --all        # broken module from the deb
sudo dkms remove msi-ec/0.13.112 --all    # staged build; re-added cleanly later
sudo rm -rf /usr/src/msi-ec-0.13 /usr/src/msi-ec-0.13.112
sudo rm -f  /usr/lib/modules-load.d/msi-ec.conf
```

Purge keeps `~/.config` GSettings (schema id `com.bongbetic.threshold` survives
via `dconf`; threshold value preserved — no user-visible loss).

### Phase 1 — vendor msi-ec 0.13.112 (V3-1, V3-2)

1. Replace `msi-ec-src/` contents with upstream msi-ec **0.13.112**
   (BeardOverflow/msi-ec, reviewed commit `d7fbbd8…`, the same tree already
   staged at `/usr/src/msi-ec-0.13.112` — keep its `README.staged` note).
   Keep `LICENSE`, `Makefile*`, `dkms.conf`, `msi-ec.c`,
   `ec_memory_configuration.h`.
2. Update the hardcoded version in **all three** files to `0.13.112`:
   - `debian/threshold.install`: `msi-ec-src/* usr/src/msi-ec-0.13.112/`
   - `debian/threshold.postinst`: `dkms add/build/install -m msi-ec -v 0.13.112`
   - `debian/threshold.prerm`: `dkms remove -m msi-ec -v 0.13.112 --all`
3. Optional (recommended, prevents the next drift): drop the manual postinst
   dkms calls and let `dh_dkms` manage add/build/install/remove from
   `msi-ec-src/dkms.conf` — single source of version truth. Keep this as a
   follow-up if the minimal string bump is chosen first.
4. Make postinst **fail loudly** instead of `|| true`:
   - capture dkms build/install output; if install or `modprobe msi-ec`
     fails, emit a `debconf` note ("EC control unavailable — app will run
     in notification-only mode; run `mokutil --import
     /var/lib/shim-signed/mok/mok.pub` and reboot to enroll the signing
     key") and leave a `/var/lib/threshold/install-warnings` marker.
5. Add `debian/threshold.postrm`: on `purge`, delete
   `/usr/lib/modules-load.d/msi-ec.conf` (or ship that file via
   `threshold.install` so dpkg removes it — preferred).
6. `debian/changelog`: new entry `threshold (1.4.1-1)` describing the
   module bump; bump `meson.build` version to 1.4.0.x/1.4.1 consistently
   with existing scheme.
7. Rebuild: `dpkg-buildpackage -us -uc` → sign artifact checksums
   (`SHA256SUMS`/`SHA256SUMS.asc`) as in previous releases; place
   `threshold_1.4.1-1_amd64.deb` in `releases/`.

Signing requirement note: DKMS signs the module at install time with the
machine's MOK key when `/var/lib/shim-signed/mok/mok.key` exists and the
pub is enrolled. This machine already satisfies both — no extra work.
`INSTALL.md` already documents enrollment for fresh machines; verify that
section mentions the deb does it automatically.

### Phase 2 — UI: restore gridlines + scale down (V3-3)

All changes in `data/style.css`, `data/ui/window.blp`, `data/ui/window.ui`
(keep both in sync — fixes-v2 F-12):

1. **Gridlines**: add a crosshatch background to the window root, per the
   prototype spec's reference look:
   ```css
   .threshold-window {
     background-color: #F3F3F3;
     background-image:
       repeating-linear-gradient(0deg,   rgba(0,0,0,.05) 0 1px, transparent 1px 24px),
       repeating-linear-gradient(90deg,  rgba(0,0,0,.05) 0 1px, transparent 1px 24px);
   }
   .threshold-window.app-dark {
     background-color: #171717;
     background-image:
       repeating-linear-gradient(0deg,   rgba(255,255,255,.04) 0 1px, transparent 1px 24px),
       repeating-linear-gradient(90deg,  rgba(255,255,255,.04) 0 1px, transparent 1px 24px);
   }
   ```
   Panels get slightly translucent backgrounds (`rgba(255,255,255,.92)` /
   `rgba(34,34,34,.92)`) so the grid reads through behind cards — the
   "industrial instrument" feel. `panel-title` may gain a small corner-tick
   or keep current borders; grid pitch 24px matches the spec's 4px base grid.
2. **Scale down to ~½ footprint, scroll-free** (user-confirmed):
   - Window defaults: `980×680` → **`700×520`**.
   - **Remove the content `GtkScrolledWindow`** (window.ui:28) entirely —
     replace with a plain vertical `GtkBox`, matching the scroll-free
     prototype philosophy. If it must stay for tiny displays, gate it:
     visible only below a `Gtk.ScrolledWindow` min-content threshold that
     the default size never hits.
   - Set `width-request 700 / height-request 520` == default size, so the
     window cannot be shrunk below the fitted layout (no scrollbars ever
     at default). Content below 700px width degrades via column
     reflow, not scrollbars.
   - **Vertical budget at 520px** (drives the card redesign):
     headerbar ~47 + top cards ~105 + charge panel ~165 + settings row
     ~115 + status bar ~22 + spacings ~66 ≈ 520. Every panel's min height
     must be re-measured after font/padding halving — use
     `Gtk.Window.set_default_size` + measured requisition during dev, not
     guesswork; assert in a widget test that the root box's requisition
     fits ≤700×520 (see tests below).
   - Paddings: `panel 10px 12px` → `6px 8px`; grid/box spacings halved
     (18→10, 12→6, 10→5, 8→4).
   - Fonts (readability floor ~9px): 28→17, 24→14, 19→12, 17→11, 14→10,
     13→10, 12/11→9–10 (captions may use 9px tabular).
   - Introduce CSS custom-property tokens (`--font-instrument`,
     `--grid-pitch`, `--panel-pad`) at the top of the stylesheet so the
     next scale adjustment is one edit.
   - Buttons/preset tiles/scale/slider heights reduced proportionally;
     preset tile height ~70 → ~40.
   - Keep `.compact` mode class working on top of the new base (compact
     remains a further ~10% squeeze, not the primary size fix).
3. Regenerate `window.ui` from `window.blp` (blueprint-compiler) in the
   same commit; run the app once to screenshot before/after for
   `data/screenshots/`.

### Phase 3 — app hardening (optional, small, no behavior change)

- `_finish_apply`: when `read-back` differs, message already says
  `(EC stored X%)` — also log to stderr for journald.
- Startup: if mode is `NOTIFY_ONLY` **but** `/sys/devices/platform/msi-ec`
  exists (module loaded but firmware rejected), show a one-time status
  hint: "msi-ec loaded but rejected this firmware — update the package".
  This would have made V3-1 self-diagnosing. Keep the check cheap (dir
  exists test already in battery.py).
- tests: add unit test asserting `debian/*` msi-ec version strings match
  `msi-ec-src/dkms.conf` `PACKAGE_VERSION` (kills the drift class).

### Phase 4 — reinstall & verify (on this machine)

```sh
sudo apt install ./releases/threshold_1.4.1-1_amd64.deb
```

Acceptance checklist — all must pass:

1. `dkms status` → `msi-ec/0.13.112 …: installed` for running kernel.
2. `sudo modprobe msi-ec` → no error; `journalctl -k | grep msi_ec`
   shows **no** "firmware version is not supported".
3. `/sys/devices/platform/msi-ec/` exists.
4. `/sys/class/power_supply/BAT1/charge_control_end_threshold` exists;
   `cat` shows EC-persisted value.
5. `modinfo -F signer <module>` → `DKMS module signing key` (signed).
6. Launch Threshold: mode label reads **"EC control — msi-ec"**; slider and
   Active Threshold show the **EC value read at startup** (not GSettings).
7. Set 80% → Apply → status "written via direct/pkexec"; re-read file
   shows 80; unplug/replug or reboot → value persists (EC-held).
8. Set 60% from another terminal
   (`pkexec tee …/charge_control_end_threshold <<< 60`) → within one poll
   tick (≤5s) slider/preset/tray follow to 60 (hardware sync).
9. UI: gridlines visible behind panels in light and dark; window opens at
   the new smaller default **with no scrollbars and no GtkScrolledWindow
   reachable** — every panel (top cards, charge panel incl. slider+
   presets+buttons, settings cards, status bar) visible without scrolling
   at 700×520; fonts legible; widget test asserts root requisition ≤
   700×520.
10. Reboot → module auto-loads (`modules-load.d`), app autostarts with EC
    mode and correct threshold.
11. `apt remove --purge threshold` (dry run of uninstall path) → dkms
    module removed, `/usr/src/msi-ec-0.13.112` gone, modules-load file gone.

### Rollback

- Keep `releases/threshold_1.4.0-1_amd64.deb`; revert = purge 1.4.1 +
  install 1.4.0 + `dkms remove msi-ec/0.13 --all` (accepting notify-only
  behavior), or boot the previous kernel.
- CSS/UI revert: single commit revert; tokens centralize the change.
- 0.13.112 whitelist entry is marked "staged validation" upstream: if the
  EC rejects/clamps a threshold write oddly on this exact firmware, the
  module also supports `modprobe msi-ec firmware=16RKIMS1.111` as a
  stopgap override — document in the release notes, do not ship it as
  default.

---

## Open questions for the user

1. ~~UI scale~~ **Confirmed**: ~½ footprint, fonts floored at 9–10px, and
   scroll-free — entire UI fits `700×520` (Phase 2.2).
2. Gridline density: 24px pitch OK (plan's default), or match the spec's
   finer graph-paper look (~12px)?
3. Keep the notify-only alarm fallback as-is (unchanged in this plan) —
   only its silent activation path gets a warning (Phase 1.4).
