import sys
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gio, Gtk, Adw, Gdk, GObject


@Gtk.Template(resource_path='/com/bongbetic/batteryguard/window.ui')
class BatteryGuardWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'BatteryGuardWindow'

    current_charge_label: Gtk.Label = Gtk.Template.Child()
    current_status_label: Gtk.Label = Gtk.Template.Child()
    active_threshold_label: Gtk.Label = Gtk.Template.Child()
    charge_scale: Gtk.Scale = Gtk.Template.Child()
    charge_value_label: Gtk.Label = Gtk.Template.Child()
    apply_button: Gtk.Button = Gtk.Template.Child()
    restore_button: Gtk.Button = Gtk.Template.Child()
    dark_mode_switch: Adw.SwitchRow = Gtk.Template.Child()
    launch_switch: Adw.SwitchRow = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Connect scale slider to the percentage label
        self.charge_scale.connect('value-changed', self._on_scale_changed)

        # Wire apply/restore buttons (placeholder handlers)
        self.apply_button.connect('clicked', self._on_apply)
        self.restore_button.connect('clicked', self._on_restore)

        # Dark mode toggling via adw style manager
        self.dark_mode_switch.connect('notify::active', self._on_dark_mode_toggled)

        # Set placeholder static data
        self._set_placeholder_data()

    def _set_placeholder_data(self):
        self.current_charge_label.set_label('72%')
        self.current_status_label.set_label('\u26a1 Charging')
        self.active_threshold_label.set_label('80%')
        self.charge_scale.set_value(80)
        self.charge_value_label.set_label('80%')

    def _on_scale_changed(self, scale):
        value = int(scale.get_value())
        self.charge_value_label.set_label(f'{value}%')

    def _on_apply(self, button):
        pass  # Placeholder — wiring in ticket #4

    def _on_restore(self, button):
        pass  # Placeholder — wiring in ticket #4

    def _on_dark_mode_toggled(self, switch, param):
        style_manager = Adw.StyleManager.get_default()
        style_manager.set_color_scheme(
            Adw.ColorScheme.FORCE_DARK if switch.get_active()
            else Adw.ColorScheme.FORCE_LIGHT
        )


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
