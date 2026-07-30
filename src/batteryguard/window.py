"""BatteryGuard main window — wires battery logic, GSettings, and UI together."""

from gettext import gettext as _
from pathlib import Path

import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Notify', '0.7')

from gi.repository import GLib, Gtk, Adw, Gdk, Notify  # noqa: E402

from batteryguard.battery import find_battery_path, read_sysfs, write_threshold  # noqa: E402
from batteryguard.config import Config  # noqa: E402


try:
    gi.require_version('AyatanaAppIndicatorGlib', '2.0')
    from gi.repository import AyatanaAppIndicatorGlib as AppIndicator
    HAS_TRAY = True
except (ValueError, ImportError):
    AppIndicator = None  # type: ignore
    HAS_TRAY = False


AUTOSTART_DIR = Path.home() / '.config' / 'autostart'
AUTOSTART_FILE = AUTOSTART_DIR / 'com.bongbetic.batteryguard.desktop'

DESKTOP_ENTRY_TEMPLATE = """\
[Desktop Entry]
Type=Application
Name=MSI BatteryGuard
Comment=Battery charge threshold controller for MSI laptops
Icon=com.bongbetic.batteryguard
StartupNotify=true
Exec=msi-batteryguard
Categories=GTK;GNOME;System;Utility;
"""


@Gtk.Template(resource_path='/com/bongbetic/batteryguard/window.ui')
class BatteryGuardWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'BatteryGuardWindow'

    current_charge_label: Gtk.Label = Gtk.Template.Child()
    current_status_label: Gtk.Label = Gtk.Template.Child()
    active_threshold_label: Gtk.Label = Gtk.Template.Child()
    battery_name_label: Gtk.Label = Gtk.Template.Child()
    charge_scale: Gtk.Scale = Gtk.Template.Child()
    charge_value_label: Gtk.Label = Gtk.Template.Child()
    apply_button: Gtk.Button = Gtk.Template.Child()
    restore_button: Gtk.Button = Gtk.Template.Child()
    dark_mode_switch: Adw.SwitchRow = Gtk.Template.Child()
    launch_switch: Adw.SwitchRow = Gtk.Template.Child()
    live_dot: Gtk.Label = Gtk.Template.Child()
    status_bar: Gtk.Label = Gtk.Template.Child()

    def __init__(self, config: Config | None = None, **kwargs):
        super().__init__(**kwargs)

        self._config = config or Config()
        self._battery_path = find_battery_path()
        self._polling_id = None
        self._writing = False
        self._indicator = None
        self._charge_pct = 0
        self._geometry_debounce_id = None

        self.charge_scale.connect('value-changed', self._on_scale_changed)
        self.apply_button.connect('clicked', self._on_apply)
        self.restore_button.connect('clicked', self._on_restore)
        self.dark_mode_switch.connect('notify::active', self._on_dark_mode_toggled)
        self.launch_switch.connect('notify::active', self._on_launch_toggled)
        self.connect('notify::default-width', self._on_default_size_changed)
        self.connect('notify::default-height', self._on_default_size_changed)
        self.connect('notify::maximized', self._on_maximized_changed)
        self.connect('close-request', self._on_close_request)

        self._load_settings()
        self._refresh_battery_data()
        self._setup_tray()
        self._start_polling()

    def _load_settings(self):
        """Restore preferences from GSettings into the UI."""
        dark = self._config.get_dark_mode()
        self.dark_mode_switch.set_active(dark)
        self._apply_color_scheme(dark)

        self.launch_switch.set_active(self._config.get_autostart())

        # Prefer live EC threshold; fall back to last applied GSettings value.
        threshold = self._config.get_charge_threshold()
        if self._battery_path is not None:
            ec = read_sysfs(self._battery_path / 'charge_control_end_threshold')
            if ec is not None:
                try:
                    threshold = int(ec)
                except ValueError:
                    pass
        self.charge_scale.set_value(threshold)
        self.charge_value_label.set_label(f'{threshold}%')

    @staticmethod
    def _apply_color_scheme(force_dark: bool) -> None:
        style_manager = Adw.StyleManager.get_default()
        style_manager.set_color_scheme(
            Adw.ColorScheme.FORCE_DARK if force_dark
            else Adw.ColorScheme.DEFAULT
        )

    def _refresh_battery_data(self):
        """Read current battery data from sysfs and update the UI."""
        if self._battery_path is None:
            self._show_error_state()
            return

        charge_now = read_sysfs(self._battery_path / 'charge_now')
        charge_full = read_sysfs(self._battery_path / 'charge_full_design')
        if charge_now is not None and charge_full is not None:
            try:
                pct = int(float(charge_now) / float(charge_full) * 100)
                self._charge_pct = pct
                self.current_charge_label.set_label(f'{pct}%')
            except (ValueError, ZeroDivisionError):
                self._charge_pct = 0
                self.current_charge_label.set_label('--%')

        status = read_sysfs(self._battery_path / 'status')
        if status:
            icon = '⚡' if status == 'Charging' else '🔋'
            self.current_status_label.set_label(f'{icon} {status}')

        threshold = read_sysfs(
            self._battery_path / 'charge_control_end_threshold'
        )
        if threshold is not None:
            self.active_threshold_label.set_label(f'{threshold}%')
        else:
            self.active_threshold_label.set_label('--%')

        self.battery_name_label.set_label(self._battery_path.name)

    def _show_error_state(self):
        """Display error state when no battery path is found."""
        self.current_charge_label.set_label('--')
        self.current_status_label.set_label(_('msi-ec not loaded'))
        self.active_threshold_label.set_label('--')
        self.charge_scale.set_sensitive(False)
        self.apply_button.set_sensitive(False)
        self.restore_button.set_sensitive(False)
        self._set_status(_('msi-ec kernel module not detected'), is_error=True)

    def _start_polling(self):
        """Start 5-second polling for battery charge refresh."""
        self._polling_id = GLib.timeout_add_seconds(5, self._poll_tick)

    def _poll_tick(self):
        """Called every 5 seconds — refresh battery data and animate dot."""
        self._refresh_battery_data()
        self._update_tray_label()
        self.live_dot.set_label('●')
        GLib.timeout_add(500, self._reset_dot)
        return GLib.SOURCE_CONTINUE

    def _reset_dot(self):
        self.live_dot.set_label('○')
        return GLib.SOURCE_REMOVE

    def _on_scale_changed(self, scale):
        value = int(scale.get_value())
        self.charge_value_label.set_label(f'{value}%')

    def _on_apply(self, button):
        if self._battery_path is None or self._writing:
            return

        self._writing = True
        button.set_sensitive(False)
        button.set_label(_('Applying…'))

        value = int(self.charge_scale.get_value())
        success, message = write_threshold(self._battery_path, value)

        if success:
            self._config.set_charge_threshold(value)
            self.active_threshold_label.set_label(f'{value}%')
            self._set_status(
                _('Threshold set to {value}% via {message}').format(
                    value=value, message=message
                ),
                is_success=True,
            )
            self._show_notification(
                _('Threshold set to {value}%').format(value=value),
                _(
                    'Written to EC firmware (via {message}). '
                    'Persists across reboots.'
                ).format(message=message),
            )
        else:
            self._set_status(_('Error: {message}').format(message=message), is_error=True)
            self._show_notification(
                _('Failed to set threshold'),
                message,
                is_error=True,
            )

        button.set_sensitive(True)
        button.set_label(_('Apply Threshold'))
        self._writing = False

    def _on_restore(self, button):
        if self._battery_path is None or self._writing:
            return

        self._writing = True
        button.set_sensitive(False)
        button.set_label(_('Restoring…'))

        self.charge_scale.set_value(100)
        self.charge_value_label.set_label('100%')

        success, message = write_threshold(self._battery_path, 100)

        if success:
            self._config.set_charge_threshold(100)
            self.active_threshold_label.set_label('100%')
            self._set_status(_('Threshold restored to 100%'), is_success=True)
            self._show_notification(
                _('Threshold restored to 100%'),
                _('Written to EC firmware. Persists across reboots.'),
            )
        else:
            self._set_status(_('Error: {message}').format(message=message), is_error=True)
            self._show_notification(
                _('Failed to restore threshold'),
                message,
                is_error=True,
            )

        button.set_sensitive(True)
        button.set_label(_('Restore to 100%'))
        self._writing = False

    def _on_dark_mode_toggled(self, switch, _param):
        active = switch.get_active()
        self._apply_color_scheme(active)
        self._config.set_dark_mode(active)

    def _on_launch_toggled(self, switch, _param):
        active = switch.get_active()
        if active:
            self._enable_autostart()
        else:
            self._disable_autostart()
        self._config.set_autostart(active)

    def _enable_autostart(self):
        AUTOSTART_DIR.mkdir(parents=True, exist_ok=True)
        AUTOSTART_FILE.write_text(DESKTOP_ENTRY_TEMPLATE)
        self._set_status(_('Launch at login enabled'))

    def _disable_autostart(self):
        if AUTOSTART_FILE.exists():
            AUTOSTART_FILE.unlink()
        self._set_status(_('Launch at login disabled'))

    def _on_default_size_changed(self, *_args):
        if self.props.maximized:
            return
        if self._geometry_debounce_id:
            GLib.source_remove(self._geometry_debounce_id)
        self._geometry_debounce_id = GLib.timeout_add(500, self._save_geometry)

    def _save_geometry(self):
        self._geometry_debounce_id = None
        if not self.props.maximized:
            self._config.set_window_width(self.get_width())
            self._config.set_window_height(self.get_height())
        return GLib.SOURCE_REMOVE

    def _on_maximized_changed(self, *_args):
        self._config.set_maximized(self.props.maximized)

    def _setup_tray(self):
        """Create the system tray indicator (AyatanaAppIndicatorGlib + Gio.Menu)."""
        if not HAS_TRAY:
            return

        from gi.repository import Gio

        self._indicator = AppIndicator.Indicator.new(
            'com.bongbetic.batteryguard',
            'com.bongbetic.batteryguard',
            AppIndicator.IndicatorCategory.APPLICATION_STATUS,
        )
        self._indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE)
        self._indicator.set_title(_('MSI BatteryGuard'))

        actions = Gio.SimpleActionGroup.new()
        show_action = Gio.SimpleAction.new('show', None)
        show_action.connect('activate', self._on_tray_show)
        actions.add_action(show_action)

        quit_action = Gio.SimpleAction.new('quit', None)
        quit_action.connect('activate', self._on_tray_quit)
        actions.add_action(quit_action)

        menu = Gio.Menu.new()
        menu.append(_('Show BatteryGuard'), 'indicator.show')
        menu.append(_('Quit'), 'indicator.quit')

        self._indicator.set_menu(menu)
        self._indicator.set_actions(actions)
        self._indicator.set_secondary_activate_target('show')

        self._update_tray_label()

    def _update_tray_label(self):
        """Update the tray indicator label with current charge percentage."""
        if self._indicator is not None:
            self._indicator.set_label(f'{self._charge_pct}%', '100%')

    def _on_tray_show(self, *_args):
        """Restore the window from tray."""
        self.present()

    def _on_tray_quit(self, *_args):
        """Quit the application from tray."""
        self._cleanup_tray()
        app = self.get_application()
        if app is not None:
            app.quit()

    def _cleanup_tray(self):
        """Clean up the tray indicator."""
        if self._indicator is not None:
            self._indicator.set_status(AppIndicator.IndicatorStatus.PASSIVE)
            self._indicator = None

    def _on_close_request(self, *_args):
        """Close-to-tray: hide window instead of destroying."""
        self._save_geometry()
        if HAS_TRAY and self._indicator is not None:
            self.set_visible(False)
            return True
        return False

    def _show_notification(self, title: str, body: str, is_error: bool = False):
        """Show a desktop notification via libnotify."""
        try:
            notification = Notify.Notification.new(
                f'BatteryGuard \u2014 {title}',
                body,
            )
            if is_error:
                notification.set_urgency(Notify.Urgency.CRITICAL)
            notification.show()
        except Exception:
            pass

    def _set_status(self, message: str, is_success: bool = False, is_error: bool = False):
        self.status_bar.set_label(message)
        classes = self.status_bar.get_css_classes()
        base = [c for c in classes if c not in ('success', 'error')]
        if is_success:
            base.append('success')
        elif is_error:
            base.append('error')
        self.status_bar.set_css_classes(base)


def load_css_from_resource():
    """Load the bundled style.css into the default display."""
    display = Gdk.Display.get_default()
    if display is None:
        return
    provider = Gtk.CssProvider()
    provider.load_from_resource('/com/bongbetic/batteryguard/style.css')
    Gtk.StyleContext.add_provider_for_display(
        display,
        provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
    )
