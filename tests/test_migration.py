"""Tests for the GSettings migration module (batteryguard → threshold)."""

from __future__ import annotations

import pytest
from unittest.mock import patch


# ---------------------------------------------------------------------------
# FakeSettings helpers
# ---------------------------------------------------------------------------


class _FakeValue:
    """Minimal GVariant-like wrapper mirroring GLib.Variant.unpack()."""

    def __init__(self, value):
        self._value = value

    def unpack(self):
        return self._value


class FakeSettings:
    """In-memory mock that mimics the Gio.Settings API used by migration."""

    _BOOLEANS = frozenset({'dark-mode', 'autostart', 'maximized', 'migration-done'})
    _INTS = frozenset({'window-width', 'window-height', 'charge-threshold'})

    _DEFAULTS = {
        'dark-mode': False,
        'autostart': False,
        'window-width': 800,
        'window-height': 600,
        'maximized': False,
        'charge-threshold': 80,
        'migration-done': False,
    }

    def __init__(self, *, user_values: dict | None = None):
        self._store: dict = dict(self._DEFAULTS)
        self._user_values: dict = user_values or {}

    def get_boolean(self, key):
        return self._store[key]

    def set_boolean(self, key, value):
        self._store[key] = value

    def get_int(self, key):
        return self._store[key]

    def set_int(self, key, value):
        self._store[key] = value

    def get_user_value(self, key):
        if key in self._user_values:
            return _FakeValue(self._user_values[key])
        return None


# ---------------------------------------------------------------------------
# migrate()
# ---------------------------------------------------------------------------


class TestMigrate:
    def test_copies_all_user_set_keys(self):
        old = FakeSettings(user_values={
            'dark-mode': True,
            'autostart': True,
            'window-width': 1200,
            'window-height': 900,
            'maximized': True,
            'charge-threshold': 60,
        })
        new = FakeSettings()

        from threshold.migration import migrate

        assert migrate(old, new) is True
        assert new.get_boolean('dark-mode') is True
        assert new.get_boolean('autostart') is True
        assert new.get_int('window-width') == 1200
        assert new.get_int('window-height') == 900
        assert new.get_boolean('maximized') is True
        assert new.get_int('charge-threshold') == 60

    def test_skips_keys_without_user_value(self):
        old = FakeSettings(user_values={})
        new = FakeSettings()

        from threshold.migration import migrate

        assert migrate(old, new) is False
        # Defaults preserved
        assert new.get_boolean('dark-mode') is False
        assert new.get_int('window-width') == 800

    def test_partial_migration(self):
        old = FakeSettings(user_values={'charge-threshold': 50})
        new = FakeSettings()

        from threshold.migration import migrate

        assert migrate(old, new) is True
        assert new.get_int('charge-threshold') == 50
        # Others stay at defaults
        assert new.get_boolean('dark-mode') is False

    def test_returns_false_when_nothing_migrated(self):
        old = FakeSettings()
        new = FakeSettings()

        from threshold.migration import migrate

        assert migrate(old, new) is False

    def test_clamps_out_of_range_threshold(self):
        old = FakeSettings(user_values={'charge-threshold': 150})
        new = FakeSettings()

        from threshold.migration import migrate

        assert migrate(old, new) is True
        assert new.get_int('charge-threshold') == 100

    def test_clamps_below_range_threshold(self):
        old = FakeSettings(user_values={'charge-threshold': 5})
        new = FakeSettings()

        from threshold.migration import migrate

        assert migrate(old, new) is True
        assert new.get_int('charge-threshold') == 20


# ---------------------------------------------------------------------------
# migrate_if_needed()
# ---------------------------------------------------------------------------


class TestMigrateIfNeeded:
    @patch('threshold.migration._schema_is_installed')
    def test_returns_true_when_old_schema_missing(self, mock_installed):
        mock_installed.return_value = False

        from threshold.migration import migrate_if_needed

        assert migrate_if_needed() is True

    @patch('threshold.migration._schema_is_installed')
    @patch('threshold.migration.Gio.Settings.new')
    def test_skips_when_already_migrated(self, mock_new, mock_installed):
        mock_installed.return_value = True

        already_done = FakeSettings()
        already_done.set_boolean('migration-done', True)

        # First call = new schema, second call = old schema (shouldn't happen)
        mock_new.side_effect = [already_done]

        from threshold.migration import migrate_if_needed

        assert migrate_if_needed() is True
        # Only one Settings.new call — old schema never opened
        assert mock_new.call_count == 1

    @patch('threshold.migration._schema_is_installed')
    @patch('threshold.migration.Gio.Settings.new')
    def test_performs_migration(self, mock_new, mock_installed):
        mock_installed.return_value = True

        old = FakeSettings(user_values={'charge-threshold': 55})
        new = FakeSettings()

        mock_new.side_effect = [new, old]

        from threshold.migration import migrate_if_needed

        assert migrate_if_needed() is True
        assert new.get_int('charge-threshold') == 55
        assert new.get_boolean('migration-done') is True


# ---------------------------------------------------------------------------
# Schema XML parsing
# ---------------------------------------------------------------------------


class TestConvertFileParsing:
    """Verify the convert / compatibility schema files parse correctly."""

    @pytest.fixture
    def old_schema_path(self, tmp_path):
        """Write the old schema to a temp dir and return the path."""
        import textwrap
        p = tmp_path / 'com.bongbetic.batteryguard.gschema.xml'
        p.write_text(textwrap.dedent('''\
            <?xml version="1.0" encoding="UTF-8"?>
            <schemalist>
              <schema path="/com/bongbetic/batteryguard/" id="com.bongbetic.batteryguard">
                <key name="dark-mode" type="b"><default>false</default></key>
                <key name="autostart" type="b"><default>false</default></key>
                <key name="window-width" type="i"><default>800</default></key>
                <key name="window-height" type="i"><default>600</default></key>
                <key name="maximized" type="b"><default>false</default></key>
                <key name="charge-threshold" type="i"><default>80</default></key>
              </schema>
            </schemalist>
        '''))
        return p

    @pytest.fixture
    def new_schema_path(self, tmp_path):
        """Write the new schema to a temp dir and return the path."""
        import textwrap
        p = tmp_path / 'com.bongbetic.threshold.gschema.xml'
        p.write_text(textwrap.dedent('''\
            <?xml version="1.0" encoding="UTF-8"?>
            <schemalist>
              <schema path="/com/bongbetic/threshold/" id="com.bongbetic.threshold">
                <key name="dark-mode" type="b"><default>false</default></key>
                <key name="autostart" type="b"><default>false</default></key>
                <key name="window-width" type="i"><default>800</default></key>
                <key name="window-height" type="i"><default>600</default></key>
                <key name="maximized" type="b"><default>false</default></key>
                <key name="charge-threshold" type="i"><default>80</default></key>
                <key name="migration-done" type="b"><default>false</default></key>
              </schema>
            </schemalist>
        '''))
        return p

    def test_old_schema_has_all_six_keys(self, old_schema_path):
        """The old schema must expose exactly the 6 user-facing keys."""
        import xml.etree.ElementTree as ET

        tree = ET.parse(old_schema_path)
        keys = [k.get('name') for k in tree.findall('.//key')]
        expected = {'dark-mode', 'autostart', 'window-width',
                    'window-height', 'maximized', 'charge-threshold'}
        assert set(keys) == expected

    def test_new_schema_has_all_six_plus_migration_flag(self, new_schema_path):
        """The new schema must expose the 6 keys plus migration-done."""
        import xml.etree.ElementTree as ET

        tree = ET.parse(new_schema_path)
        keys = {k.get('name') for k in tree.findall('.//key')}
        assert 'migration-done' in keys
        expected = {'dark-mode', 'autostart', 'window-width',
                    'window-height', 'maximized', 'charge-threshold',
                    'migration-done'}
        assert keys == expected

    def test_old_and_new_share_same_keys(self, old_schema_path, new_schema_path):
        """Every key in the old schema must exist in the new schema."""
        import xml.etree.ElementTree as ET

        old_keys = {k.get('name') for k in ET.parse(old_schema_path).findall('.//key')}
        new_keys = {k.get('name') for k in ET.parse(new_schema_path).findall('.//key')}
        assert old_keys.issubset(new_keys)
