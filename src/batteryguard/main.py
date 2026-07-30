import gettext
import locale
import os
import sys

import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from batteryguard.application import BatteryGuardApplication  # noqa: E402


def _setup_i18n():
    """Bind gettext domain so _() and Blueprint strings resolve."""
    try:
        locale.setlocale(locale.LC_ALL, '')
    except locale.Error:
        pass
    localedir = os.environ.get('LOCALEDIR')
    if localedir:
        gettext.bindtextdomain('batteryguard', localedir)
        locale.bindtextdomain('batteryguard', localedir)
    gettext.textdomain('batteryguard')


def main():
    _setup_i18n()
    app = BatteryGuardApplication()
    return app.run(sys.argv)


if __name__ == '__main__':
    sys.exit(main())
