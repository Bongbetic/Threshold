"""dbus-run-session integration probe for the notification-area service.

Runs the real TrayIcon service on a private session bus against a fake
StatusNotifierWatcher (issue #86): registration evidence, required SNI
properties, artifact-owned icon resolution, watcher loss revoking
readiness, and clean unregister.

Skipped where the Dbusmenu 0.4 typelib is unavailable; CI installs
gir1.2-dbusmenu-glib-0.4 and runs this probe for real.
"""

import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

_child = textwrap.dedent("""\
    import json, sys
    import gi
    gi.require_version('Dbusmenu', '0.4')
    from gi.repository import GLib, Gio

    loop = GLib.MainLoop()
    results = {"registered_items": [], "watcher_up": False}

    def watcher_register(conn, sender, path, iface, method, params, inv):
        results["registered_items"].append(params[0])
        inv.return_value(None)

    watcher_xml = \"\"\"
    <node>
      <interface name='org.kde.StatusNotifierWatcher'>
        <method name='RegisterStatusNotifierItem'>
          <arg type='s' direction='in'/>
        </method>
        <property name='IsStatusNotifierHostRegistered' type='b' access='read'/>
      </interface>
    </node>
    \"\"\"

    def on_bus(conn, _):
        results["watcher_up"] = True
        node = Gio.DBusNodeInfo.new_for_xml(watcher_xml)
        conn.register_object(
            '/StatusNotifierWatcher',
            node.lookup_interface('org.kde.StatusNotifierWatcher'),
            watcher_register, lambda *a: None, None,
        )

    def on_name_lost(_conn):
        results["watcher_up"] = False

    watcher_id = Gio.bus_own_name(
        Gio.BusType.SESSION, 'org.kde.StatusNotifierWatcher',
        Gio.BusNameOwnerFlags.NONE, on_bus, None, on_name_lost,
    )

    sys.path.insert(0, %(srcdir)r)
    os.environ.setdefault('GI_TYPELIB_PATH', '')
    from threshold.tray import TrayIcon
    from threshold.notification_area_readiness import ReadinessState

    tray = TrayIcon(
        on_activate=lambda: None,
        on_threshold=lambda v: None,
        on_quit=lambda: None,
    )
    tray.set_state(75, 'Charging', 'com.bongbetic.threshold-battery-good-charging', 80)

    conn = Gio.bus_get_sync(Gio.BusType.SESSION, None)

    def check(name):
        v = conn.call_sync(
            'com.bongbetic.threshold', '/StatusNotifierItem',
            'org.freedesktop.DBus.Properties', 'Get',
            GLib.Variant('(ss)', ('org.kde.StatusNotifierItem', name)),
            GLib.VariantType('(v)'), Gio.DBusCallFlags.NONE, -1, None,
        )
        return v[0]

    results["props"] = {
        "Id": check("Id").unpack(),
        "Category": check("Category").unpack(),
        "IconName": check("IconName").unpack(),
        "Menu": check("Menu").unpack(),
        "ItemIsMenu": check("ItemIsMenu").unpack(),
    }
    pix = check("IconPixmap")
    results["pixmap_ok"] = pix is not None

    # Menu path must point to the dbusmenu server.
    results["menu_path_ok"] = results["props"]["Menu"] == "/com/bongbetic/threshold/menu"

    # ── Phase 1: Watcher loss revokes readiness immediately ───────────────
    Gio.bus_unown_name(watcher_id)

    def assert_lost():
        results["readiness_after_loss"] = tray.readiness.value

        # ── Phase 2: Watcher recovery re-registers automatically ──────────
        # Re-own the watcher name — the tray's bus-watch should detect it
        # and start a fresh registration attempt (event-driven, no polling).
        def on_recovery_bus(conn2, _):
            node = Gio.DBusNodeInfo.new_for_xml(watcher_xml)
            conn2.register_object(
                '/StatusNotifierWatcher',
                node.lookup_interface('org.kde.StatusNotifierWatcher'),
                watcher_register, lambda *a: None, None,
            )

        def on_recovery_name_lost(_conn):
            pass

        recovery_id = Gio.bus_own_name(
            Gio.BusType.SESSION, 'org.kde.StatusNotifierWatcher',
            Gio.BusNameOwnerFlags.NONE, on_recovery_bus, None,
            on_recovery_name_lost,
        )

        def check_recovery():
            results["readiness_after_recovery"] = tray.readiness.value
            results["recovery_registered_items"] = len(results["registered_items"])

            # ── Phase 3: Clean unregister ─────────────────────────────────
            tray.unregister()
            results["unregister_clean"] = True
            Gio.bus_unown_name(recovery_id)
            loop.quit()
            return False

        GLib.timeout_add(500, check_recovery)
        return False

    GLib.timeout_add(200, assert_lost)
    GLib.timeout_add(8000, loop.quit)  # safety bound
    loop.run()
    print("PROBE:" + json.dumps(results))
""")


def _has_dbusmenu() -> bool:
    try:
        import gi
        gi.require_version('Dbusmenu', '0.4')
        from gi.repository import Dbusmenu  # noqa: F401
        return True
    except (ValueError, ImportError):
        return False


pytestmark = pytest.mark.skipif(
    not (_has_dbusmenu() and shutil.which("dbus-run-session")),
    reason="Dbusmenu 0.4 typelib or dbus-run-session unavailable",
)


def test_notification_area_service_probe(tmp_path):
    srcdir = ROOT / "src"
    script = tmp_path / "probe_child.py"
    script.write_text(_child % {"srcdir": str(srcdir)})
    env = dict(os.environ, GI_TYPELIB_PATH=os.environ.get("GI_TYPELIB_PATH", ""))
    r = subprocess.run(
        ["dbus-run-session", "--", sys.executable, str(script)],
        env=env, capture_output=True, text=True, timeout=60,
    )
    assert r.returncode == 0, r.stderr
    line = next(l for l in r.stdout.splitlines() if l.startswith("PROBE:"))
    results = json.loads(line[len("PROBE:"):])

    # ── Registration evidence ─────────────────────────────────────────────
    assert "/StatusNotifierItem" in results["registered_items"]

    # ── Required SNI properties ───────────────────────────────────────────
    assert results["props"]["Id"] == "com.bongbetic.threshold"
    assert results["props"]["Category"] == "ApplicationStatus"

    # ── Artifact-owned icon ───────────────────────────────────────────────
    assert results["props"]["IconName"].startswith("com.bongbetic.threshold-battery-")

    # ── Menu path resolves to dbusmenu server ─────────────────────────────
    assert results["props"]["Menu"] == "/com/bongbetic/threshold/menu"
    assert results["menu_path_ok"] is True
    assert results["props"]["ItemIsMenu"] is False

    # ── Pixmap fallback alongside icon name ───────────────────────────────
    assert results["pixmap_ok"]

    # ── Watcher loss revokes readiness immediately ────────────────────────
    assert results["readiness_after_loss"] == "lost"

    # ── Watcher recovery re-registers automatically ───────────────────────
    assert results["readiness_after_recovery"] == "ready"
    assert results["recovery_registered_items"] >= 2

    # ── Clean unregister succeeds without error ───────────────────────────
    assert results["unregister_clean"] is True
