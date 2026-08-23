"""Self-contained StatusNotifierItem + dbusmenu tray icon.

Implements the SNI spec directly over Gio.DBusConnection and exports menus
via Dbusmenu (gir Dbusmenu 0.4), which is the protocol XFCE, MATE, KDE, Budgie
and GNOME (w/ extension) all support for tray menus.
"""

import logging

from gi.repository import GLib, Gio

log = logging.getLogger(__name__)

try:
    gi_require = __import__('gi').require_version
    gi_require('Dbusmenu', '0.4')
    from gi.repository import Dbusmenu
    HAS_DBUSMENU = True
except (ValueError, ImportError):
    Dbusmenu = None  # type: ignore
    HAS_DBUSMENU = False

SNI_INTROSPECT = """\
<node>
  <interface name="org.kde.StatusNotifierItem">
    <method name="Activate">
      <parameter name="x" type="i" direction="in"/>
      <parameter name="y" type="i" direction="in"/>
    </method>
    <method name="SecondaryActivate">
      <parameter name="x" type="i" direction="in"/>
      <parameter name="y" type="i" direction="in"/>
    </method>
    <method name="Scroll">
      <parameter name="delta" type="i" direction="in"/>
      <parameter name="orientation" type="s" direction="in"/>
    </method>
    <property name="Category" type="s" access="read"/>
    <property name="Id" type="s" access="read"/>
    <property name="Title" type="s" access="read"/>
    <property name="Status" type="s" access="read"/>
    <property name="IconName" type="s" access="read"/>
    <property name="IconThemePath" type="s" access="read"/>
    <property name="Menu" type="o" access="read"/>
    <property name="ItemIsMenu" type="b" access="read"/>
    <property name="ToolTip" type="(sa(iiay)sbs)" access="read"/>
    <signal name="NewTitle"/>
    <signal name="NewIcon"/>
    <signal name="NewToolTip"/>
    <signal name="NewStatus"/>
  </interface>
</node>"""

SNI_OBJECT_PATH = '/StatusNotifierItem'
WATCHER_NAME = 'org.kde.StatusNotifierWatcher'
WATCHER_PATH = '/StatusNotifierWatcher'
DBUS_MENU_PATH = '/com/bongbetic/threshold/menu'
ITEM_ID = 'com.bongbetic.threshold'


class TrayIcon:
    """System tray icon with dbusmenu threshold presets."""

    def __init__(self, on_activate=None, on_threshold=None, on_quit=None):
        if not HAS_DBUSMENU:
            raise RuntimeError('Dbusmenu 0.4 typelib not available')

        self._on_activate = on_activate
        self._on_threshold = on_threshold
        self._on_quit = on_quit
        self._conn = None
        self._sni_id = 0
        self._watcher_id = 0
        self._icon_name = 'battery-good'
        self._tooltip = ('battery-good', '', 'Threshold', '')
        self._status = 'Active'

        # Build menu tree
        self._menu_items = {}  # value -> Dbusmenu.Menuitem
        self._root = self._build_menu()
        self._menu_server = Dbusmenu.Server.new(DBUS_MENU_PATH)
        self._menu_server.set_root(self._root)

        # Register on session bus
        self._conn = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        iface = Gio.DBusNodeInfo.new_for_xml(
            SNI_INTROSPECT
        ).lookup_interface('org.kde.StatusNotifierItem')
        self._sni_id = self._conn.register_object(
            SNI_OBJECT_PATH,
            iface,
            self._on_sni_method_call,
            self._on_sni_get_property,
            None,
        )

        # Watch for watcher and register
        self._watcher_id = Gio.bus_watch_name(
            Gio.BusType.SESSION,
            WATCHER_NAME,
            Gio.BusNameWatcherFlags.NONE,
            self._on_watcher_appeared,
            None,
        )

    def _build_menu(self):
        """Build dbusmenu tree: presets + separator + Open + Quit."""
        from threshold.battery import THRESHOLD_PRESETS

        root = Dbusmenu.Menuitem.new()

        for value in THRESHOLD_PRESETS:
            item = Dbusmenu.Menuitem.new()
            item.property_set(Dbusmenu.MENUITEM_PROP_LABEL, f'{value}%')
            item.property_set(
                Dbusmenu.MENUITEM_PROP_TOGGLE_TYPE,
                Dbusmenu.MENUITEM_TOGGLE_RADIO,
            )
            item.property_set_int(
                Dbusmenu.MENUITEM_PROP_TOGGLE_STATE,
                Dbusmenu.MENUITEM_TOGGLE_STATE_UNCHECKED,
            )
            item.connect(
                Dbusmenu.MENUITEM_SIGNAL_ITEM_ACTIVATED,
                self._on_preset_activated,
                value,
            )
            self._menu_items[value] = item
            root.child_append(item)

        sep = Dbusmenu.Menuitem.new()
        sep.property_set(Dbusmenu.MENUITEM_PROP_TYPE, 'separator')
        root.child_append(sep)

        open_item = Dbusmenu.Menuitem.new()
        open_item.property_set(Dbusmenu.MENUITEM_PROP_LABEL, 'Open Threshold')
        open_item.connect(
            Dbusmenu.MENUITEM_SIGNAL_ITEM_ACTIVATED,
            self._on_open_activated,
        )
        root.child_append(open_item)

        quit_item = Dbusmenu.Menuitem.new()
        quit_item.property_set(Dbusmenu.MENUITEM_PROP_LABEL, 'Quit')
        quit_item.connect(
            Dbusmenu.MENUITEM_SIGNAL_ITEM_ACTIVATED,
            self._on_quit_activated,
        )
        root.child_append(quit_item)

        return root

    def _on_preset_activated(self, _item, _timestamp, value):
        if self._on_threshold:
            self._on_threshold(value)

    def _on_open_activated(self, _item, _timestamp):
        if self._on_activate:
            self._on_activate()

    def _on_quit_activated(self, _item, _timestamp):
        if self._on_quit:
            self._on_quit()

    # ── SNI D-Bus interface ──────────────────────────────────────────────

    def _on_sni_method_call(self, _conn, _sender, _path, _iface, method, params, _invocation):
        if method == 'Activate' or method == 'SecondaryActivate':
            if self._on_activate:
                self._on_activate()

    def _on_sni_get_property(self, _conn, _sender, _path, _iface, name):
        if name == 'Category':
            return GLib.Variant('s', 'ApplicationStatus')
        if name == 'Id':
            return GLib.Variant('s', ITEM_ID)
        if name == 'Title':
            return GLib.Variant('s', 'Threshold')
        if name == 'Status':
            return GLib.Variant('s', self._status)
        if name == 'IconName':
            return GLib.Variant('s', self._icon_name)
        if name == 'IconThemePath':
            return GLib.Variant('s', '')
        if name == 'Menu':
            return GLib.Variant('o', DBUS_MENU_PATH)
        if name == 'ItemIsMenu':
            return GLib.Variant('b', False)
        if name == 'ToolTip':
            icon, _path2, title, body = self._tooltip
            return GLib.Variant('(sa(iiay)sbs)', (
                icon,
                [],
                title,
                body,
                '',
            ))
        return None

    # ── Watcher registration ─────────────────────────────────────────────

    def _on_watcher_appeared(self, _conn, _name, _name_owner):
        try:
            self._conn.call_sync(
                WATCHER_NAME,
                WATCHER_PATH,
                WATCHER_NAME,
                'RegisterStatusNotifierItem',
                GLib.Variant('(s)', (SNI_OBJECT_PATH,)),
                None,
                Gio.DBusCallFlags.NONE,
                -1,
                None,
            )
        except GLib.Error as e:
            log.warning('Failed to register with StatusNotifierWatcher: %s', e)

    def _emit_signal(self, signal_name):
        if self._conn:
            self._conn.emit_signal(
                None,
                SNI_OBJECT_PATH,
                'org.kde.StatusNotifierItem',
                signal_name,
                None,
            )

    # ── Public API ───────────────────────────────────────────────────────

    def set_state(self, pct, status, icon_name, threshold):
        """Update tray icon, tooltip, and menu radio marks."""
        self._icon_name = icon_name
        self._status = 'Active'
        body = f'{pct}%'
        if status:
            body += f' \u2022 {status}'
        self._tooltip = (icon_name, '', 'Threshold', body)

        # Update radio marks
        for value, item in self._menu_items.items():
            state = (
                Dbusmenu.MENUITEM_TOGGLE_STATE_CHECKED
                if value == threshold
                else Dbusmenu.MENUITEM_TOGGLE_STATE_UNCHECKED
            )
            item.property_set_int(Dbusmenu.MENUITEM_PROP_TOGGLE_STATE, state)

        self._emit_signal('NewIcon')
        self._emit_signal('NewToolTip')

    def unregister(self):
        """Clean up all D-Bus registrations."""
        if self._watcher_id:
            Gio.bus_unwatch_name(self._watcher_id)
            self._watcher_id = 0
        if self._sni_id and self._conn:
            self._conn.unregister_object(self._sni_id)
            self._sni_id = 0
        self._menu_server = None
