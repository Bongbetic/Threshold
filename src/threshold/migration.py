"""Migrate user preferences from the old batteryguard schema to threshold.

On first launch after upgrading from an earlier version, this module reads
every user-set key from the ``com.bongbetic.batteryguard`` schema and writes
it into the corresponding ``com.bongbetic.threshold`` key.  A boolean key
``migration-done`` in the *new* schema gates the one-time migration so it
never runs twice.

The old schema ships alongside the new one for a few releases to give every
user the chance to upgrade, and can then be dropped.
"""

from __future__ import annotations

import gi

gi.require_version('Gio', '2.0')

from gi.repository import Gio  # noqa: E402

_OLD_SCHEMA_ID = 'com.bongbetic.batteryguard'
_NEW_SCHEMA_ID = 'com.bongbetic.threshold'

_KEYS = [
    # (gsettings key, gtype getter, gtype setter)
    ('dark-mode', 'get_boolean', 'set_boolean'),
    ('autostart', 'get_boolean', 'set_boolean'),
    ('window-width', 'get_int', 'set_int'),
    ('window-height', 'get_int', 'set_int'),
    ('maximized', 'get_boolean', 'set_boolean'),
    ('charge-threshold', 'get_int', 'set_int'),
]

MIGRATION_DONE_KEY = 'migration-done'


def _schema_is_installed(schema_id: str) -> bool:
    """Return True if *schema_id* can be found in the compiled schemas."""
    source = Gio.SettingsSchemaSource.get_default()
    if source is None:
        return False
    return source.lookup(schema_id, recursive=True) is not None


def migrate(old_settings: Gio.Settings, new_settings: Gio.Settings) -> bool:
    """Copy user-set values from *old_settings* to *new_settings*.

    Returns True if any key was actually migrated.
    """
    migrated = False
    for key, getter, setter in _KEYS:
        old_val = old_settings.get_user_value(key)
        if old_val is not None:
            getattr(new_settings, setter)(key, old_val.get_value())
            migrated = True
    return migrated


def migrate_if_needed() -> bool:
    """Run schema migration if it has not already been performed.

    Returns True if migration happened (or had already happened).
    Returns False when the old schema is absent — i.e. fresh install.
    """
    if not _schema_is_installed(_OLD_SCHEMA_ID):
        # No old schema → fresh install, nothing to migrate.
        return True

    new_settings = Gio.Settings.new(_NEW_SCHEMA_ID)

    # Already migrated?
    if new_settings.get_boolean(MIGRATION_DONE_KEY):
        return True

    old_settings = Gio.Settings.new(_OLD_SCHEMA_ID)
    migrated = migrate(old_settings, new_settings)

    # Mark done regardless — even if nothing was user-set, we still want
    # to skip the lookup on every future launch.
    new_settings.set_boolean(MIGRATION_DONE_KEY, True)

    return migrated
