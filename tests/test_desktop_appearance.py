"""Appearance precedence, migration and untrusted palette regression tests."""
from pathlib import Path
import subprocess

import pytest

from threshold.appearance import DesktopAppearance, parse_palette

DARK = '''
@define-color window_bg_color #141218;
@define-color window_fg_color #e6e0e9;
@define-color card_bg_color #211f24;
@define-color card_fg_color @window_fg_color;
@define-color accent_bg_color #d0bcff;
@define-color accent_fg_color #381e72;
'''
LIGHT = (DARK.replace('#141218', '#ffffff').replace('#211f24', '#eeeeee')
         .replace('#e6e0e9', '#111111').replace('#d0bcff', '#6743a4')
         .replace('#381e72', '#ffffff'))


def test_palette_requires_valid_readable_pairs():
    assert parse_palette(DARK)['--text-secondary'] == '#e6e0e9'
    assert parse_palette(LIGHT)['--bg-page'] == '#ffffff'
    for bad in (DARK.replace('#141218', 'url(file:///secret)'),
                DARK.replace('#e6e0e9', '#141218'),
                DARK.replace('#e6e0e9', '@card_fg_color'),
                DARK.replace('#e6e0e9', '@unknown'), 'x' * 65537):
        assert parse_palette(bad) == {}


def test_partial_replace_remove_and_late_directory(tmp_path):
    path = tmp_path / 'late/colors.css'
    desktop = DesktopAppearance(path)
    assert desktop.palette == {}
    path.parent.mkdir()
    path.write_text(DARK)
    desktop.refresh()
    previous = desktop.palette
    path.write_text('@define-color')
    desktop.refresh()
    assert desktop.palette == previous
    replacement = path.with_suffix('.tmp')
    replacement.write_text(LIGHT)
    replacement.replace(path)
    desktop.refresh()
    assert desktop.palette['--bg-page'] == '#ffffff'
    path.unlink()
    desktop.refresh()
    desktop.refresh()
    assert desktop.palette == {}


def test_precedence_and_scheme_agreement(tmp_path):
    path = tmp_path / 'colors.css'
    path.write_text(DARK)
    desktop = DesktopAppearance(path)
    assert desktop.snapshot('system', 'light', 'red')['scheme'] == 'dark'
    assert desktop.snapshot('light', 'dark', 'red')['palette'] == {}
    assert desktop.snapshot('light', 'dark', 'red')['scheme'] == 'light'
    desktop.scheme = 'light'
    assert desktop.snapshot('system', 'dark', 'red')['palette'] == {}
    desktop.scheme = 'dark'
    assert desktop.snapshot('system', 'light', 'red')['palette']
    assert desktop.snapshot('dark', 'light', 'red')['accent_color'] == 'red'


@pytest.mark.parametrize('saved, expected', [(None, 'system'), (True, 'dark'), (False, 'light')])
def test_real_gsettings_preference_migration(tmp_path, saved, expected):
    from gi.repository import Gio
    from threshold.config import Config
    schema = Path(__file__).resolve().parents[1] / 'data/com.bongbetic.threshold.gschema.xml'
    (tmp_path / schema.name).write_text(schema.read_text())
    subprocess.run(['glib-compile-schemas', str(tmp_path)], check=True)
    source = Gio.SettingsSchemaSource.new_from_directory(str(tmp_path), None, False)
    settings = Gio.Settings.new_full(
        source.lookup('com.bongbetic.threshold', False), Gio.memory_settings_backend_new(), None,
    )
    if saved is not None:
        settings.set_boolean('dark-mode', saved)
    config = Config(settings)
    assert config.get_appearance_mode() == expected
    config.set_appearance_mode('system')
    assert config.get_appearance_mode() == 'system'
    config.set_dark_mode(False)
    assert config.get_appearance_mode() == 'light'


def test_argb_network_byte_order():
    from threshold.tray import TrayIcon
    _, _, pixels = TrayIcon._render_pixmap(80)
    assert pixels[:4] == b'\0\0\0\0'
    assert pixels[(3 * 16 + 2) * 4:(3 * 16 + 3) * 4] == bytes((255, 32, 129, 192))


def test_host_loss_restores_hidden_window_once():
    from unittest.mock import MagicMock
    from threshold.tray import TrayIcon
    from threshold.notification_area_readiness import NotificationAreaReadiness, ReadinessState
    from threshold.carbon_shell import BridgeHandler

    handler = BridgeHandler.__new__(BridgeHandler)
    handler._window = MagicMock()
    handler._window.get_visible.return_value = False
    tray = TrayIcon.__new__(TrayIcon)
    tray._readiness = NotificationAreaReadiness()
    tray._readiness.watcher_appeared()
    tray._readiness.registration_confirmed()
    tray._host_registered = True
    tray._on_readiness_lost = handler._on_notification_area_lost
    assert tray.readiness is ReadinessState.READY
    tray._set_host(False)
    tray._set_host(False)
    assert tray.readiness is ReadinessState.UNAVAILABLE
    handler._window.present.assert_called_once()
    tray._set_host(True)
    assert tray.readiness is ReadinessState.READY
