import sys
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gio, Adw, GObject

from batteryguard.window import BatteryGuardWindow, load_css_from_resource


class BatteryGuardApplication(Adw.Application):

    def __init__(self):
        super().__init__(
            application_id='com.bongbetic.batteryguard',
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = BatteryGuardWindow(application=self)
        win.present()

    def do_startup(self):
        Adw.Application.do_startup(self)
        load_css_from_resource()
