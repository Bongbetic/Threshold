"""Threshold main window — wires battery logic, GSettings, and UI together."""

from datetime import datetime
from gettext import gettext as _
from pathlib import Path
import threading

import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Notify', '0.7')

from gi.repository import GLib, Gtk, Adw, Gdk, Notify  # noqa: E402

from threshold.battery import (  # noqa: E402
    ControlMode,
    battery_health_percent,
    detect_control_mode,
    evaluate_alarm,
    find_battery_path,
    health_grade,
    read_capacity_wh,
    read_charge_percent,
    read_cycle_count,
    read_power_source,
    read_sysfs,
    write_threshold,
)
from threshold.config import Config  # noqa: E402


try:
    from threshold.tray import TrayIcon, HAS_DBUSMENU
    HAS_TRAY = HAS_DBUSMENU
except (ImportError, RuntimeError):
    TrayIcon = None  # type: ignore
    HAS_DBUSMENU = False
    HAS_TRAY = False


AUTOSTART_DIR = Path(GLib.get_user_config_dir()) / 'autostart'
AUTOSTART_FILE = AUTOSTART_DIR / 'com.bongbetic.threshold.desktop'

DESKTOP_ENTRY_TEMPLATE = """\
[Desktop Entry]
Type=Application
Name=Threshold
Comment=Battery charge threshold controller for Linux laptops
Icon=com.bongbetic.threshold
StartupNotify=true
Exec=threshold
Categories=GTK;GNOME;System;Utility;
"""

_MODE_LABELS = {
    ControlMode.EC_MSI: _('EC control — msi-ec'),
    ControlMode.SYSFS_VENDOR: _('Vendor sysfs control'),
    ControlMode.NOTIFY_ONLY: _('Notification only'),
}

_CHARGING_SUFFIX = {
    'Charging': '-charging',
    'Full': '',
    'Discharging': '',
    'Not charging': '',
}

_PRESET_WIDGETS = {
    60: 'preset_60',
    70: 'preset_70',
    80: 'preset_80',
    90: 'preset_90',
    100: 'preset_100',
}

_ACCENT_WIDGETS = {
    'orange': 'swatch_orange',
    'blue': 'swatch_blue',
    'green': 'swatch_green',
    'purple': 'swatch_purple',
    'red': 'swatch_red',
}


def _battery_icon_name(pct: int, status: str | None) -> str:
    """Return a freedesktop battery icon name for the given charge level."""
    if pct <= 10:
        level = 'empty'
    elif pct <= 30:
        level = 'low'
    elif pct <= 50:
        level = 'medium'
    elif pct <= 80:
        level = 'good'
    else:
        level = 'full'
    suffix = _CHARGING_SUFFIX.get(status, '')
    return f'battery-{level}{suffix}'


def _format_last_changed(timestamp: int) -> str:
    """Format a unix timestamp as 'Today, HH:MM' or a date."""
    if timestamp <= 0:
        return _('—')
    dt = datetime.fromtimestamp(timestamp)
    today = datetime.now().date()
    if dt.date() == today:
        return _('Today, {time}').format(time=dt.strftime('%H:%M'))
    return dt.strftime('%Y-%m-%d %H:%M')


@Gtk.Template(resource_path='/com/bongbetic/threshold/window.ui')
class ThresholdWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'ThresholdWindow'

    current_charge_label: Gtk.Label = Gtk.Template.Child()
    current_status_label: Gtk.Label = Gtk.Template.Child()
    active_threshold_label: Gtk.Label = Gtk.Template.Child()
    battery_name_label: Gtk.Label = Gtk.Template.Child()
    mode_label: Gtk.Label = Gtk.Template.Child()
    power_source_label: Gtk.Label = Gtk.Template.Child()
    health_label: Gtk.Label = Gtk.Template.Child()
    last_changed_label: Gtk.Label = Gtk.Template.Child()
    charge_scale: Gtk.Scale = Gtk.Template.Child()
    charge_value_label: Gtk.Label = Gtk.Template.Child()
    apply_button: Gtk.Button = Gtk.Template.Child()
    restore_button: Gtk.Button = Gtk.Template.Child()
    dark_mode_switch: Gtk.Switch = Gtk.Template.Child()
    launch_switch: Gtk.Switch = Gtk.Template.Child()
    tray_switch: Gtk.Switch = Gtk.Template.Child()
    notifications_switch: Gtk.Switch = Gtk.Template.Child()
    compact_switch: Gtk.Switch = Gtk.Template.Child()
    title_percentage_switch: Gtk.Switch = Gtk.Template.Child()
    cycle_count_label: Gtk.Label = Gtk.Template.Child()
    design_capacity_label: Gtk.Label = Gtk.Template.Child()
    full_capacity_label: Gtk.Label = Gtk.Template.Child()
    health_pct_label: Gtk.Label = Gtk.Template.Child()
    preset_60: Gtk.ToggleButton = Gtk.Template.Child()
    preset_70: Gtk.ToggleButton = Gtk.Template.Child()
    preset_80: Gtk.ToggleButton = Gtk.Template.Child()
    preset_90: Gtk.ToggleButton = Gtk.Template.Child()
    preset_100: Gtk.ToggleButton = Gtk.Template.Child()
    swatch_orange: Gtk.ToggleButton = Gtk.Template.Child()
    swatch_blue: Gtk.ToggleButton = Gtk.Template.Child()
    swatch_green: Gtk.ToggleButton = Gtk.Template.Child()
    swatch_purple: Gtk.ToggleButton = Gtk.Template.Child()
    swatch_red: Gtk.ToggleButton = Gtk.Template.Child()
    live_dot: Gtk.Label = Gtk.Template.Child()
    status_bar: Gtk.Label = Gtk.Template.Child()

    def __init__(self, config: Config | None = None, **kwargs):
        super().__init__(**kwargs)

        self._config = config or Config()
        self._battery_path = find_battery_path()
        self._control_mode = detect_control_mode(self._battery_path)
        self._polling_id = None
        self._reset_dot_id = None
        self._pending_idle_id = None
        self._writing = False
        self._closed = False
        self._tray = None
        self._charge_pct = 0
        self._geometry_debounce_id = None
        self._suppress_launch_toggle = False
        self._preset_widgets = {
            value: getattr(self, _PRESET_WIDGETS[value])
            for value in _PRESET_WIDGETS
        }
        self._swatch_widgets = {
            name: getattr(self, _ACCENT_WIDGETS[name])
            for name in _ACCENT_WIDGETS
        }

        # Build exclusive radio groups in code (avoids GTK4 set_group assertion)
        for widget in list(self._preset_widgets.values())[1:]:
            widget.set_group(self.preset_60)
        for widget in list(self._swatch_widgets.values())[1:]:
            widget.set_group(self.swatch_orange)

        # Alarm state for notification-only fallback
        self._alarm_armed = False
        self._alarm_fired = False

        self.charge_scale.connect('value-changed', self._on_scale_changed)
        self.apply_button.connect('clicked', self._on_apply)
        self.restore_button.connect('clicked', self._on_restore)
        self.dark_mode_switch.connect('notify::active', self._on_dark_mode_toggled)
        self.launch_switch.connect('notify::active', self._on_launch_toggled)
        self.tray_switch.connect('notify::active', self._on_tray_toggled)
        self.notifications_switch.connect('notify::active', self._on_notifications_toggled)
        self.compact_switch.connect('notify::active', self._on_compact_toggled)
        self.title_percentage_switch.connect(
            'notify::active', self._on_title_percentage_toggled
        )
        for value, widget in self._preset_widgets.items():
            widget.connect('toggled', self._on_preset_toggled, value)
        for name, widget in self._swatch_widgets.items():
            widget.connect('toggled', self._on_swatch_toggled, name)
        self.connect('notify::default-width', self._on_default_size_changed)
        self.connect('notify::default-height', self._on_default_size_changed)
        self.connect('notify::maximized', self._on_maximized_changed)
        self.connect('close-request', self._on_close_request)
        self.connect('destroy', self._on_destroy)

        self._load_settings()
        self._sync_dark_class()
        self._refresh_battery_data()
        self._update_mode_label()
        self._setup_tray()
        self._start_polling()

        # Keep the .app-dark class in sync when the system theme changes
        Adw.StyleManager.get_default().connect(
            'notify::dark', lambda *_a: self._sync_dark_class()
        )

    def _load_settings(self):
        """Restore preferences from GSettings into the UI."""
        dark = self._config.get_dark_mode()
        self.dark_mode_switch.set_active(dark)
        self._apply_color_scheme(dark)

        autostart = AUTOSTART_FILE.is_file()
        if autostart != self._config.get_autostart():
            self._config.set_autostart(autostart)
        self._suppress_launch_toggle = True
        self.launch_switch.set_active(autostart)
        self._suppress_launch_toggle = False

        self.tray_switch.set_active(self._config.get_minimize_to_tray())
        self.notifications_switch.set_active(self._config.get_show_notifications())

        accent = self._config.get_accent_color()
        self._set_accent(accent)

        compact = self._config.get_compact_mode()
        self.compact_switch.set_active(compact)
        self._apply_compact(compact)

        title_pct = self._config.get_title_percentage()
        self.title_percentage_switch.set_active(title_pct)

        threshold = self._config.get_charge_threshold()
        if self._battery_path is not None and self._has_threshold_control():
            ec = read_sysfs(self._battery_path / 'charge_control_end_threshold')
            if ec is not None:
                try:
                    threshold = int(ec)
                except ValueError:
                    pass
        self.charge_scale.set_value(threshold)
        self.charge_value_label.set_label(f'{threshold}%')
        self._sync_presets(threshold)

        self.last_changed_label.set_label(
            _format_last_changed(self._config.get_last_applied_time())
        )

        if self._control_mode is ControlMode.NOTIFY_ONLY:
            self._alarm_armed = threshold < 100
            self._alarm_fired = False

    def _has_threshold_control(self) -> bool:
        return self._control_mode in (ControlMode.EC_MSI, ControlMode.SYSFS_VENDOR)

    @staticmethod
    def _apply_color_scheme(force_dark: bool) -> None:
        style_manager = Adw.StyleManager.get_default()
        style_manager.set_color_scheme(
            Adw.ColorScheme.FORCE_DARK if force_dark
            else Adw.ColorScheme.DEFAULT
        )

    def _sync_dark_class(self):
        """Sync the .app-dark window class with the effective scheme."""
        dark = Adw.StyleManager.get_default().props.dark
        classes = self.get_css_classes()
        base = [c for c in classes if c != 'app-dark']
        if dark:
            base.append('app-dark')
        self.set_css_classes(base)

    def _set_accent(self, name: str):
        """Apply an accent scheme class to the window."""
        if name not in _ACCENT_WIDGETS:
            name = 'orange'
        classes = self.get_css_classes()
        base = [c for c in classes if not c.startswith('accent-')]
        base.append(f'accent-{name}')
        self.set_css_classes(base)
        for accent_name, widget in self._swatch_widgets.items():
            widget.set_active(accent_name == name)

    def _apply_compact(self, active: bool):
        """Toggle the .compact class on the window."""
        classes = self.get_css_classes()
        if active and 'compact' not in classes:
            classes.append('compact')
        elif not active and 'compact' in classes:
            classes.remove('compact')
        self.set_css_classes(classes)

    def _sync_presets(self, value: int):
        """Mark the preset tile matching ``value`` as selected."""
        for preset_value, widget in self._preset_widgets.items():
            widget.set_active(preset_value == value)

    def _refresh_battery_data(self):
        """Read current battery data from sysfs and update the UI."""
        if self._battery_path is None:
            self._show_error_state()
            return

        pct = read_charge_percent(self._battery_path)
        if pct is not None:
            self._charge_pct = pct
            self.current_charge_label.set_label(f'{pct}%')
        else:
            self._charge_pct = 0
            self.current_charge_label.set_label('--%')

        status = read_sysfs(self._battery_path / 'status')
        if status:
            self.current_status_label.set_label(status)
            self._update_battery_icon(status)

        threshold = read_sysfs(
            self._battery_path / 'charge_control_end_threshold'
        )
        if threshold is not None:
            self.active_threshold_label.set_label(f'{threshold}%')
        elif self._control_mode is ControlMode.NOTIFY_ONLY:
            val = int(self.charge_scale.get_value())
            self.active_threshold_label.set_label(f'{val}% (alarm)')
        else:
            self.active_threshold_label.set_label('--%')

        self.battery_name_label.set_label(self._battery_path.name)
        self.power_source_label.set_label(read_power_source())

        health_pct = battery_health_percent(self._battery_path)
        self.health_label.set_label(health_grade(health_pct))
        self.health_pct_label.set_label(
            f'{health_pct}%' if health_pct is not None else _('—')
        )

        cycles = read_cycle_count(self._battery_path)
        self.cycle_count_label.set_label(
            str(cycles) if cycles is not None else _('—')
        )

        capacity = read_capacity_wh(self._battery_path)
        if capacity is not None:
            full_wh, design_wh = capacity
            self.full_capacity_label.set_label(f'{full_wh:.1f} Wh')
            self.design_capacity_label.set_label(f'{design_wh:.1f} Wh')
        else:
            self.full_capacity_label.set_label(_('—'))
            self.design_capacity_label.set_label(_('—'))

        self._update_title()

    def _update_battery_icon(self, status: str):
        """Refresh the battery status card icon to match charge + status."""
        icon = _battery_icon_name(self._charge_pct, status)
        image = self.current_status_label.get_prev_sibling()
        if image is not None and isinstance(image, Gtk.Image):
            image.set_from_icon_name(icon)

    def _update_title(self):
        """Show battery % in the window title when enabled."""
        if self._config.get_title_percentage():
            self.set_title(_('Threshold — {pct}%').format(pct=self._charge_pct))
        else:
            self.set_title(_('Threshold'))

    def _show_error_state(self):
        """Display error state when no threshold-capable battery is found."""
        self.current_charge_label.set_label('--%')
        self.current_status_label.set_label(_('—'))
        self.active_threshold_label.set_label('--%')
        self.power_source_label.set_label(_('—'))
        self.health_label.set_label(_('—'))
        self.cycle_count_label.set_label(_('—'))
        self.design_capacity_label.set_label(_('—'))
        self.full_capacity_label.set_label(_('—'))
        self.health_pct_label.set_label(_('—'))
        self.charge_scale.set_sensitive(False)
        self.apply_button.set_sensitive(False)
        self.restore_button.set_sensitive(False)
        self._set_status(
            _('No charge-threshold-capable battery detected'),
            is_error=True,
        )

    def _update_mode_label(self):
        if self._control_mode is None:
            self.mode_label.set_label('')
            return
        self.mode_label.set_label(_MODE_LABELS.get(self._control_mode, ''))

    def _start_polling(self):
        """Start 5-second polling for battery charge refresh."""
        self._polling_id = GLib.timeout_add_seconds(5, self._poll_tick)

    def _stop_polling(self):
        """Remove polling, live-dot, geometry and pending-write sources."""
        for attr in (
            self._polling_id,
            self._reset_dot_id,
            self._pending_idle_id,
            self._geometry_debounce_id,
        ):
            if attr is not None:
                GLib.source_remove(attr)

        self._polling_id = None
        self._reset_dot_id = None
        self._pending_idle_id = None
        self._geometry_debounce_id = None

    def _poll_tick(self):
        """Called every 5 seconds — refresh battery data and animate dot."""
        if self._battery_path is None:
            # msi-ec may have loaded after launch — retry discovery.
            self._battery_path = find_battery_path()
            if self._battery_path is not None:
                self._control_mode = detect_control_mode(self._battery_path)
                self._update_mode_label()
                if self._has_threshold_control():
                    self.charge_scale.set_sensitive(True)
                    self.apply_button.set_sensitive(True)
                    self.restore_button.set_sensitive(True)
        elif self._control_mode is None:
            self._control_mode = detect_control_mode(self._battery_path)
            self._update_mode_label()

        self._refresh_battery_data()
        self._update_tray_label()
        self._evaluate_alarm()

        self.live_dot.set_label('●')
        if self._reset_dot_id is not None:
            GLib.source_remove(self._reset_dot_id)
        self._reset_dot_id = GLib.timeout_add(500, self._reset_dot)
        return GLib.SOURCE_CONTINUE

    def _evaluate_alarm(self):
        """Fire or re-arm the threshold-reached alarm in notify-only mode."""
        if self._control_mode is not ControlMode.NOTIFY_ONLY:
            return
        if not self._alarm_armed:
            return

        threshold = int(self.charge_scale.get_value())
        status = read_sysfs(self._battery_path / 'status')

        # Re-arm when the battery discharges below threshold
        if status == 'Discharging' or (
            self._charge_pct is not None
            and self._charge_pct < threshold - 2
        ):
            self._alarm_fired = False
            return

        if evaluate_alarm(self._charge_pct, status, threshold,
                          self._alarm_fired):
            self._alarm_fired = True
            self._show_notification(
                _('Battery reached {threshold}%').format(threshold=threshold),
                _(
                    'Charge has reached the {threshold}% limit you set. '
                    'Unplug the charger to preserve battery lifespan.'
                ).format(threshold=threshold),
                is_error=True,
            )
            self._set_status(
                _('Threshold reached — unplug the charger'),
                is_error=True,
            )

    def _reset_dot(self):
        self._reset_dot_id = None
        self.live_dot.set_label('○')
        return GLib.SOURCE_REMOVE

    def _on_destroy(self, *_args):
        self._closed = True
        self._stop_polling()
        self._cleanup_tray()

    def _on_scale_changed(self, scale):
        value = int(scale.get_value())
        self.charge_value_label.set_label(f'{value}%')
        self._sync_presets(value)

    def _on_preset_toggled(self, button, value):
        if not button.get_active():
            return
        self.charge_scale.set_value(value)
        self.charge_value_label.set_label(f'{value}%')
        self._sync_presets(value)

    def _on_swatch_toggled(self, button, name):
        if not button.get_active():
            return
        self._set_accent(name)
        self._config.set_accent_color(name)

    def _on_tray_toggled(self, switch, _param):
        self._config.set_minimize_to_tray(switch.get_active())

    def _on_notifications_toggled(self, switch, _param):
        self._config.set_show_notifications(switch.get_active())

    def _on_compact_toggled(self, switch, _param):
        active = switch.get_active()
        self._apply_compact(active)
        self._config.set_compact_mode(active)

    def _on_title_percentage_toggled(self, switch, _param):
        self._config.set_title_percentage(switch.get_active())
        self._update_title()

    def _on_apply(self, button):
        if self._battery_path is None or self._writing:
            return

        self._writing = True
        button.set_sensitive(False)
        self.restore_button.set_sensitive(False)
        button.set_label(_('Applying…'))

        value = int(self.charge_scale.get_value())
        bat_path = self._battery_path
        notify_only = self._control_mode is ControlMode.NOTIFY_ONLY

        def worker():
            if notify_only:
                result = (True, 'alarm')
            else:
                result = write_threshold(bat_path, value)
            if not self._closed:
                self._pending_idle_id = GLib.idle_add(
                    self._finish_apply, button, value, result
                )

        threading.Thread(target=worker, daemon=True).start()

    def _finish_apply(self, button, value, result):
        self._pending_idle_id = None
        if self._closed:
            return GLib.SOURCE_REMOVE
        success, message = result
        if success:
            self._config.set_charge_threshold(value)
            self._config.set_last_applied_time(int(datetime.now().timestamp()))
            self.last_changed_label.set_label(
                _format_last_changed(self._config.get_last_applied_time())
            )
            if self._has_threshold_control():
                self.active_threshold_label.set_label(f'{value}%')
            else:
                self.active_threshold_label.set_label(f'{value}% (alarm)')
            self._sync_presets(value)
            self._alarm_armed = value < 100
            self._alarm_fired = False
            self._set_status(
                _('Threshold set to {value}% via {message}').format(
                    value=value, message=message
                ),
                is_success=True,
            )
            if self._has_threshold_control():
                self._show_notification(
                    _('Threshold set to {value}%').format(value=value),
                    _(
                        'Written to EC firmware (via {message}). '
                        'Persists across reboots.'
                    ).format(message=message),
                )
            else:
                self._show_notification(
                    _('Threshold set to {value}%').format(value=value),
                    _(
                        'Alarm armed — you will be notified when the '
                        'battery reaches {value}%.'
                    ).format(value=value),
                )
        else:
            self._set_status(_('Error: {message}').format(message=message), is_error=True)
            self._show_notification(
                _('Failed to set threshold'),
                message,
                is_error=True,
            )

        button.set_sensitive(True)
        self.restore_button.set_sensitive(True)
        button.set_label(_('Apply Threshold'))
        self._writing = False
        return GLib.SOURCE_REMOVE

    def _on_restore(self, button):
        if self._battery_path is None or self._writing:
            return

        self._writing = True
        button.set_sensitive(False)
        self.apply_button.set_sensitive(False)
        button.set_label(_('Restoring…'))

        bat_path = self._battery_path
        notify_only = self._control_mode is ControlMode.NOTIFY_ONLY

        def worker():
            if notify_only:
                result = (True, 'alarm')
            else:
                result = write_threshold(bat_path, 100)
            if not self._closed:
                self._pending_idle_id = GLib.idle_add(
                    self._finish_restore, button, result
                )

        threading.Thread(target=worker, daemon=True).start()

    def _finish_restore(self, button, result):
        self._pending_idle_id = None
        if self._closed:
            return GLib.SOURCE_REMOVE
        success, message = result
        if success:
            self.charge_scale.set_value(100)
            self.charge_value_label.set_label('100%')
            self._sync_presets(100)
            self._config.set_charge_threshold(100)
            self._config.set_last_applied_time(int(datetime.now().timestamp()))
            self.last_changed_label.set_label(
                _format_last_changed(self._config.get_last_applied_time())
            )
            if self._has_threshold_control():
                self.active_threshold_label.set_label('100%')
            else:
                self.active_threshold_label.set_label('--')
            self._alarm_armed = False
            self._alarm_fired = False
            self._set_status(_('Threshold restored to 100%'), is_success=True)
            if self._has_threshold_control():
                self._show_notification(
                    _('Threshold restored to 100%'),
                    _('Written to EC firmware. Persists across reboots.'),
                )
            else:
                self._show_notification(
                    _('Threshold restored to 100%'),
                    _('Alarm disarmed.'),
                )
        else:
            self._set_status(_('Error: {message}').format(message=message), is_error=True)
            self._show_notification(
                _('Failed to restore threshold'),
                message,
                is_error=True,
            )

        button.set_sensitive(True)
        self.apply_button.set_sensitive(True)
        button.set_label(_('Restore to 100%'))
        self._writing = False
        return GLib.SOURCE_REMOVE

    def _on_dark_mode_toggled(self, switch, _param):
        active = switch.get_active()
        self._apply_color_scheme(active)
        self._config.set_dark_mode(active)
        self._sync_dark_class()

    def _on_launch_toggled(self, switch, _param):
        if self._suppress_launch_toggle:
            return
        active = switch.get_active()
        try:
            if active:
                self._enable_autostart()
            else:
                self._disable_autostart()
        except OSError as e:
            self._suppress_launch_toggle = True
            switch.set_active(not active)
            self._suppress_launch_toggle = False
            self._set_status(
                _('Autostart error: {message}').format(message=e),
                is_error=True,
            )
            return
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
        """Create the system tray indicator with battery icon and threshold menu."""
        if not HAS_TRAY or TrayIcon is None:
            return

        self._tray = TrayIcon(
            on_activate=self._on_tray_show,
            on_threshold=self._on_tray_threshold,
            on_quit=self._on_tray_quit,
        )
        self._tray.set_state(
            self._charge_pct,
            None,
            'battery-good',
            int(self.charge_scale.get_value()),
        )

    def _update_tray_label(self):
        """Update the tray icon, tooltip, and menu marks."""
        if not hasattr(self, '_tray') or self._tray is None:
            return
        status = read_sysfs(self._battery_path / 'status') if self._battery_path else None
        self._tray.set_state(
            self._charge_pct,
            status,
            _battery_icon_name(self._charge_pct, status),
            int(self.charge_scale.get_value()),
        )

    def _on_tray_show(self, *_args):
        """Restore the window from tray."""
        self.present()

    def _on_tray_threshold(self, value):
        """Apply a threshold preset from the tray menu."""
        self.charge_scale.set_value(value)
        self.charge_value_label.set_label(f'{value}%')
        self._on_apply(self.apply_button)

    def _on_tray_quit(self, *_args):
        """Quit the application from tray."""
        self._stop_polling()
        self._cleanup_tray()
        app = self.get_application()
        if app is not None:
            app.quit()

    def _cleanup_tray(self):
        """Clean up the tray indicator."""
        if hasattr(self, '_tray') and self._tray is not None:
            self._tray.unregister()
            self._tray = None

    def _on_close_request(self, *_args):
        """Close-to-tray: hide window instead of destroying."""
        self._save_geometry()
        if (
            self._config.get_minimize_to_tray()
            and HAS_TRAY
            and getattr(self, '_tray', None) is not None
        ):
            self.set_visible(False)
            return True
        return False

    def _show_notification(self, title: str, body: str, is_error: bool = False):
        """Show a desktop notification via libnotify (if enabled)."""
        if not self._config.get_show_notifications():
            return
        try:
            notification = Notify.Notification.new(
                f'Threshold \u2014 {title}',
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
    provider.load_from_resource('/com/bongbetic/threshold/style.css')
    Gtk.StyleContext.add_provider_for_display(
        display,
        provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
    )
