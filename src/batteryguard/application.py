import sys
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gio, Adw


class BatteryGuardApplication(Adw.Application):

    def __init__(self):
        super().__init__(
            application_id='com.bongbetic.batteryguard',
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = Adw.ApplicationWindow(application=self)
            win.set_title('MSI BatteryGuard')
            win.set_default_size(480, 540)
        win.present()

    def do_startup(self):
        Adw.Application.do_startup(self)
