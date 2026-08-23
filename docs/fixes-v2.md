# Threshold — fixes-v2: review report & fix plan (2026-08-23)

Full-repo review triggered by a user-reported flaw: *the app does not probe
the EC to find out what the present charge threshold has been set at.*

Method: static review of every module, a live SNI + dbusmenu protocol
harness running against the real app, live system probing on the target
laptop (MSI Thin A15, Xfce 4.20), and widget-level probes driving real
`ThresholdWindow` instances against a fake sysfs battery tree.

Application-logic and packaging fixes are **documented here only** — no code
changes were applied for them in this round. The three tray fixes marked
*applied* were made in the working tree during the earlier live tray
verification session (uncommitted). The UI tightening (F-13) was implemented
on explicit request.

## Status summary

| ID  | Sev | Area        | Status                | One-line summary |
|-----|-----|-------------|-----------------------|------------------|
| F-01 | P0 | tray        | applied (uncommitted) | Left-click broken on every host: introspection XML used `<parameter>` so `Activate` parses with zero args |
| F-02 | P0 | tray        | applied (uncommitted) | SNI method calls never replied → strict hosts time out |
| F-03 | P1 | tray/window | applied (uncommitted) | Tray menu radio marks lag up to 5 s after apply/restore |
| F-04 | P0 | window      | proposed              | EC threshold never probed after startup; mode never re-detected; no read-back (the reported flaw) |
| F-05 | P0 | packaging   | proposed              | msi-ec module never loads: `--no-depmod`, no modules-load entry, no modalias |
| F-06 | P2 | battery     | proposed              | Only the first battery is controlled on dual-battery machines |
| F-07 | P2 | window      | proposed              | Tray preset click during an in-flight write is silently dropped |
| F-08 | P3 | tray        | proposed              | Ghost tray icon on some hosts after quit (no `NewStatus` Passive) |
| F-09 | P3 | tray        | proposed              | Tooltip shows `0%` when capacity read fails |
| F-10 | P3 | window      | info                  | Status icon update couples to sibling widget order |
| F-11 | P3 | window      | info                  | Duplicate sysfs read per tick; dead None-check |
| F-12 | P2 | build       | info                  | Committed `window.ui` can drift from `window.blp` |
| F-13 | P1 | UI          | **implemented**       | Oversized fonts + padding forced scrolling at open |

---

## The reported flaw, dissected (F-04 + F-05)

Observed on the target machine: the EC is holding a charge threshold of
**60 %** (read directly from `charge_control_end_threshold` while the module
was loaded), yet the app opened showing **80 %** — its GSettings default —
and ran in *Notification only* mode.

The chain of causes, each verified live:

1. **The msi-ec kernel module is not loaded** (F-05, packaging).
   `charge_control_end_threshold` only exists when msi-ec is loaded, so the
   app cannot see any EC state and falls back to notify-only, where the
   threshold shown is the GSettings value — never the EC's.
2. **Even when msi-ec loads *after* the app starts, the app never notices**
   (F-04a). `_poll_tick` (`src/threshold/window.py:436-438`) only re-detects
   the control mode when it is `None`; once a battery is found the mode is
   frozen. A window constructed in notify-only mode stays there forever —
   empirically confirmed: after creating the platform dir and threshold file
   mid-session, two ticks later `control_mode` was still `NOTIFY_ONLY` and
   the mode label still "Notification only".
3. **External EC changes are never synced into the UI** (F-04b).
   `_refresh_battery_data` updates only `active_threshold_label` from
   sysfs; the slider, preset tiles, and tray radio marks keep whatever
   GSettings had. Empirically confirmed: EC set to 90 externally, slider at
   70 — after a tick the slider stayed 70 and the label showed a stale
   "70% (alarm)".
4. **Writes are never verified against the EC** (F-04c). `write_threshold`
   reports success without reading the value back. msi-ec validates per
   model and can clamp/round, so the app can claim "Threshold set to 75%"
   while the EC actually accepted a different value.

Startup itself is correct *when EC control is already available*:
`_load_settings` (`src/threshold/window.py:245-252`) prefers the sysfs value
over GSettings. The flaw is everything after/around that one read.

### Proposed fix (F-04)

Add a hardware-sync step to the poll path in `window.py`:

```python
def _sync_from_hardware(self):
    """Re-detect mode and follow the EC threshold when it changes
    externally. Skipped while a write is in flight or the user is
    dragging the slider."""
    if self._writing or self._battery_path is None:
        return
    mode = detect_control_mode(self._battery_path)
    if mode != self._control_mode:
        self._control_mode = mode
        self._update_mode_label()
        # re-enable controls if we gained EC/sysfs control
        ...
    if self._has_threshold_control():
        raw = read_sysfs(self._battery_path / 'charge_control_end_threshold')
        if raw is not None:
            try:
                ec_value = int(raw)
            except ValueError:
                return
            if ec_value != int(self.charge_scale.get_value()):
                self.charge_scale.set_value(ec_value)   # re-syncs presets
                self._config.set_charge_threshold(ec_value)
                self._update_tray_label()
```

Call it from `_poll_tick` (replacing the one-shot `elif self._control_mode
is None` branch). Guard against fighting the user: skip while `_writing`,
and only pull the slider when the EC value genuinely differs.

For F-04c, verify after writing in `_finish_apply`:

```python
def worker():
    result = write_threshold(bat_path, value)
    if result[0] and not notify_only:
        actual = read_sysfs(bat_path / 'charge_control_end_threshold')
        if actual is not None and int(actual) != value:
            result = (True, f'{message} (EC stored {actual}%)')
    ...
```

and surface the stored value in the status line/notification.

---

## F-05 — msi-ec never loads (packaging, P0)

Evidence gathered on the target machine:

- `dkms status` shows msi-ec only **built** (not installed) for the running
  kernel; `modprobe msi-ec` fails; no `charge_control_end_threshold`.
- `debian/threshold.postinst` runs `dkms add/build/install … --no-depmod`,
  so `modules.dep`/`modules.alias` are never regenerated — even a copied
  module file is unresolvable by modprobe.
- `msi-ec-src/msi-ec.c` contains **zero** `MODULE_DEVICE_TABLE` declarations
  (verified by grep). The module registers its platform device manually in
  `module_init`, so the kernel has **no modalias** to autoload it — ever.
- Nothing ships `/etc/modules-load.d/msi-ec.conf` (the upstream Makefile's
  `install` target writes one, but DKMS never runs those targets).
- The udev rule granting plugdev write access is installed but never
  re-triggered in postinst, so the freshly appeared threshold file keeps
  root-only permissions until the next boot/replug.

Net effect for every user: EC mode is unreachable, which is the root cause
of the reported "does not probe the EC" symptom.

### Proposed fix

`debian/threshold.postinst`:

```sh
configure)
    if command -v dkms >/dev/null 2>&1; then
        dkms add -m msi-ec -v 0.13 || true
        dkms build -m msi-ec -v 0.13 || true
        dkms install -m msi-ec -v 0.13 || true   # no --no-depmod
    fi
    # msi-ec has no modalias — it must be explicitly requested at boot
    echo msi-ec > /usr/lib/modules-load.d/msi-ec.conf
    modprobe msi-ec || true
    # apply the plugdev udev rule to the just-appeared threshold files
    udevadm control --reload-rules || true
    udevadm trigger --subsystem-match=power_supply || true
    ;;
```

Ship the modules-load file via `debian/threshold.install`
(`usr/lib/modules-load.d/msi-ec.conf`) instead of the echo if preferred —
then it is removed with the package. `debian/threshold.prerm` should remove
the DKMS module only on `remove` (not `upgrade`), and `postrm purge` should
delete the modules-load file.

---

## Tray findings (F-01 … F-03, applied in working tree)

- **F-01** `src/threshold/tray.py:23-52`: the introspection XML used
  `<parameter>` elements, which GLib's parser ignores. Every method parsed
  with zero in-args, so any host calling `Activate(ii)` on left-click got
  `org.freedesktop.DBus.Error.InvalidArgs` — left-click was broken on all
  desktops. Verified with the protocol harness before/after. Fix: use
  `<arg name="…" type="…" direction="in"/>`.
- **F-02** `_on_sni_method_call` never called `invocation.return_value()`;
  strict hosts performing a synchronous call (e.g. some GNOME shell
  extensions) block until timeout. Fix: always return the (empty) reply.
- **F-03** `_finish_apply`/`_finish_restore` did not call
  `_update_tray_label()`, so the dbusmenu radio marks and tooltip lagged one
  poll tick (up to 5 s) behind an apply. Fix: call it in both finishers.

Post-fix harness result: **21/21 checks pass** — registration handshake, all
SNI properties, left-click presents window, close-to-tray, right-click menu
(5 presets as radio items + separator + Open + Quit), preset click applies
threshold and moves the radio mark, middle-click tolerated, Quit exits
cleanly. Also verified against the *real* Xfce panel tray host.

Remaining tray nits (proposed, not applied):

- **F-08** `unregister()` should emit `NewStatus('Passive')` before
  releasing the name; a few hosts keep a ghost icon otherwise.
- **F-09** tooltip body should render `—` instead of `0%` when
  `read_charge_percent` fails.
- **F-07** `_on_tray_threshold` → `_on_apply` returns early while
  `_writing`; the click vanishes without feedback. Proposal: remember the
  last requested value and apply it when the in-flight write finishes.

---

## Other findings

- **F-06** `find_battery_path` returns the first `type == Battery` entry.
  On dual-battery MSI machines only BAT0/BAT1 (whichever sorts first) gets
  a threshold written. Proposal: write to every threshold-capable battery
  and read back the minimum for display, or add per-battery selection.
- **F-10** `_update_battery_icon` locates the icon via
  `current_status_label.get_prev_sibling()` — silent no-op if the template
  is reordered. Proposal: give the `Gtk.Image` a template child id.
- **F-11** `_evaluate_alarm` re-reads `status` from sysfs every tick
  although `_refresh_battery_data` just read it; and `self._charge_pct` is
  never `None` (initialized to 0), making its `is not None` guard dead.
- **F-12** `data/ui/window.ui` (compiled fallback + test fixture) is
  regenerated by hand; nothing stops it drifting from `window.blp`.
  (Regenerated in this round after the UI edits.) Proposal: add a CI step
  `blueprint-compiler compile data/ui/window.blp | diff - data/ui/window.ui`.

---

## F-13 — UI tightening (implemented this round)

User request: smaller fonts, no scrolling required when the app opens.

`data/style.css` — key size reductions:

| Selector                    | Before | After |
|-----------------------------|--------|-------|
| `instrument-value-accent`   | 40 px  | 28 px |
| `instrument-value-sm`       | 26 px  | 19 px |
| `panel-title`               | 17 px  | 14 px |
| `preset-value`              | 17 px  | 14 px |
| `preset-subtitle`           | 13 px  | 11 px |
| `settings-row-title`        | 15 px  | 13 px |
| `settings-row-desc`         | 13 px  | 11 px |
| `metadata-value`            | 15 px  | 13 px |
| `metadata-caption(-value)`  | 14/13 px | 13/12 px |
| action buttons              | 15 px / 42 px tall | 13 px / 32 px |
| preset tile                 | 56 px tall | 42 px |
| panel padding               | 14×16  | 10×12 |
| slider + handle             | 24/20 px | 18/15 px |
| compact-mode variants       | 34/22/16 px | 24/17/13 px |

`data/ui/window.blp`: outer margins 14/18 → 10/12, box/grid spacing 12 → 10,
panel-internal margins trimmed, swatches 24 → 20 px, default window
1100×820 → **980×680** (minimum 820×560). GSettings `window-width/height`
defaults updated to match.

Verification (widget-level probe against a real `ThresholdWindow`, checking
the `ScrolledWindow` adjustments after allocation):

```
1364x914: voverflow=0.0px hoverflow=0.0px -> fits   (user's saved size)
1100x820: voverflow=0.0px hoverflow=0.0px -> fits
 980x680: voverflow=0.0px hoverflow=0.0px -> fits   (new default)
 924x664: voverflow=0.0px hoverflow=0.0px -> fits
 820x560: voverflow=0.0px hoverflow=0.0px -> fits   (minimum size)
```

The `Gtk.ScrolledWindow` is intentionally retained as a safety net below the
minimum window size. Full test suite (132 tests) and flake8 pass after the
changes; `window.ui` regenerated from the edited blueprint.

---

## Proposed regression tests

1. **`tests/test_tray_sni.py`** — parse `SNI_INTROSPECT` with
   `Gio.DBusNodeInfo` and assert `Activate`/`SecondaryActivate`/`Scroll`
   declare `(ii)`/`(ii)`/`(is)` in-args. Would have caught F-01.
2. **`tests/test_window_hw_sync.py`** — fake sysfs battery tree; construct
   the window; create the threshold file + platform dir mid-session; tick;
   assert mode transitions to EC and the slider follows an external change
   (F-04a/b).
3. **Packaging assertion** — extend the install-layout test to require a
   modules-load entry and a postinst without `--no-depmod` (F-05).

## Release checklist (next version)

- Version bump `1.3.0` → `1.4.0` (`meson.build`, `debian/changelog`).
- Metainfo `<release version="1.4.0">` entry (screenshots optionally
  re-captured with the tightened UI).
- Commit the three tray fixes + UI tightening; apply F-04/F-05 or defer
  with explicit note in release notes.
- Tag `v1.4.0`; CI matrix: ubuntu-24.04, ubuntu-26.04, debian trixie
  container (build-and-test, deb-package, lintian).
