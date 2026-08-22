# Threshold — repo review & bug-fix plan (approved 2026-08-22)

Full-repo review findings and the approved fix plan. Status column tracks
implementation.

## Findings

### P0 — installed app fails to launch

- **`src/meson.build` omits `threshold/migration.py` from `python_sources`.**
  `application.py` does `from threshold.migration import migrate_if_needed`,
  so the packaged app (`threshold_*.deb`) crashes on every launch with
  `ModuleNotFoundError: threshold.migration`. Development runs from `src/`
  mask the bug because the source tree is on `PYTHONPATH`.
  - Fix: list `threshold/migration.py` in `src/meson.build`.
  - Guard: regression test that parses `src/meson.build` and asserts every
    `src/threshold/*.py` module is listed in `python_sources`.

### P1 — crash risk on window close during a write

- **Pending `GLib.idle_add` callbacks fire on destroyed widgets.**
  `_on_apply`/`_on_restore` spawn a worker thread that schedules
  `_finish_apply`/`_finish_restore` via `GLib.idle_add`. If the window is
  destroyed before the idle runs (e.g. quit from tray mid-write), the
  callback touches disposed widgets → PyGObject "destroyed" errors or
  worse. `_stop_polling()` never cancels these idle sources.
  - Fix: track the pending idle source ids, remove them in
    `_stop_polling()`, and make the finish callbacks no-op safely if the
    window is gone (also guard the worker's `idle_add` when the window
    already died).

### P2 — functional bugs

- **`migration.migrate()` crashes on real GVariant values.** It calls
  `old_val.get_value()`. Real `Gio.Settings.get_user_value()` returns a
  `GLib.Variant`; its unpack method is `unpack()` (the test fakes expose a
  `get_value()` that does not exist on the real class). Migration would
  raise `AttributeError` on a real upgrade. Fix: use `old_val.unpack()`.
  - Related: migrated `charge-threshold` values are not clamped to the new
    schema's 20–100 range; an out-of-range legacy value is silently dropped
    by `set_int` (range check fails). Clamp before writing.
  - `migrate_if_needed()` docstring says it returns `False` on fresh
    install; the code returns `True` in that path. Align docstring with
    code (return value is "migration gate is settled", not "data copied").
  - `_KEYS` carries an unused `getter` column — remove it.
- **Autostart path ignores `XDG_CONFIG_HOME`.** `window.py` builds
  `Path.home() / '.config' / 'autostart'` directly. Use
  `GLib.get_user_config_dir()` (respects the env var).
- **No battery rediscovery.** `find_battery_path()` runs once in
  `__init__`; if `msi-ec` loads after launch the window stays in error
  state until restart. Re-run discovery on poll ticks while in error
  state and recover the UI.

### P3 — docs / packaging drift

- **README.md and INSTALL.md reference `msi-ec-dkms_0.13-1_amd64.deb`.**
  The deb version follows the source package (1.2.0-1), so the artifact is
  `msi-ec-dkms_1.2.0-1_amd64.deb` (see `output/`). 0.13 is only the DKMS
  module version. Fix the example commands to use `msi-ec-dkms_1.2.0-1`
  (or globs) in both docs.
- **`resources.py` re-registers without a guard** and hard-exits at import
  time. Add a duplicate-registration guard (idempotent) while keeping the
  existing error path.

## Verified non-bugs (checked, no change)

- `AyatanaAppIndicatorGlib` tray usage (`set_actions`,
  `set_secondary_activate_target`) — both exist in the Glib binding
  (verified against pgi-docs for 2.0.3).
- udev rule, pkexec fallback chain, migration one-shot gating,
  GSettings schemas, CI workflow contracts, metainfo content.

## Implementation order

1. P0 meson fix + regression test.
2. P1 idle-callback teardown safety.
3. P2 migration fixes (`unpack`, clamp, docstring, dead column) + tests.
4. P2 autostart XDG path + battery rediscovery.
5. P3 docs drift + resources guard.
6. Validate: `flake8 src/threshold tests` and full `meson test`.
