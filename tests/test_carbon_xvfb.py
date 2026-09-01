"""Xvfb smoke probe: WebKitGTK loads bundle, completes one round trip.

Requires:
  - WebKitGTK >= 2.40 (typelib-1_0-WebKit-6_0)
  - xvfb-run (xorg-x11-server-Xvfb)

Skips automatically if requirements are missing.
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def _webkit_available() -> bool:
    try:
        import gi
        gi.require_version("WebKit", "6.0")
        from gi.repository import WebKit  # noqa: F401
        return True
    except (ValueError, ImportError):
        return False


def _xvfb_available() -> bool:
    return subprocess.run(
        ["which", "xvfb-run"],
        capture_output=True,
    ).returncode == 0


SKIP_REASON = []
if not _webkit_available():
    SKIP_REASON.append("WebKitGTK 6.0 typelib not available")
if not _xvfb_available():
    SKIP_REASON.append("xvfb-run not found")


SMOKE_SCRIPT = """\
import json, sys, gi
gi.require_version("Gtk", "4.0")
gi.require_version("WebKit", "6.0")
from gi.repository import GLib, Gtk, WebKit, Gio

BUNDLE = sys.argv[1]
SHIM = sys.argv[2]
result_data = {}

def on_message(ucm, message):
    # WebKit 6.0: message is a JSC.Value
    raw = message.to_string()
    try:
        req = json.loads(raw)
    except json.JSONDecodeError as e:
        result_data["error"] = "parse error: " + str(e)
        app.quit()
        return

    cmd = req.get("cmd", "")
    msg_id = req.get("id", "")

    if cmd == "ready":
        resp = {"id": msg_id, "ok": True, "data": {"acknowledged": True}}
    elif cmd == "get_state":
        resp = {"id": msg_id, "ok": True, "data": {
            "state": {"battery_available": False, "charge_percent": None,
                       "charge_status": None, "active_threshold": None,
                       "control_mode": None, "health_percent": None,
                       "health_grade": None, "power_source": None,
                       "dark_mode": False, "accent_color": "orange"},
            "appearance": {"scheme": "light", "accent_color": "orange"},
        }}
    else:
        resp = {"id": msg_id, "ok": False, "error": "Unknown command: " + cmd}

    js_str = json.dumps(json.dumps(resp))
    web_view.evaluate_javascript(
        "window.threshold._handleMessage(" + js_str + ");",
        -1, None, None, None, None,
    )
    result_data["cmd"] = cmd
    result_data["result"] = resp
    app.quit()

def on_load_changed(wv, event):
    if event == WebKit.LoadEvent.FINISHED:
        def trigger():
            wv.evaluate_javascript(
                "window.threshold.request('ready').then("
                "  function(d){ window._ok = true; },"                "  function(e){ window._err = e.message; }"                ");",
                -1, None, None, None, None,
            )
            return False
        GLib.timeout_add(500, trigger)

web_view = None

def on_activate(a):
    global web_view
    settings = WebKit.Settings.new()
    settings.set_enable_javascript(True)
    settings.set_allow_file_access_from_file_urls(True)
    settings.set_allow_universal_access_from_file_urls(True)
    web_view = WebKit.WebView.new()
    web_view.set_settings(settings)

    ucm = web_view.get_user_content_manager()
    ucm.register_script_message_handler("threshold")
    ucm.connect("script-message-received::threshold", on_message)

    shim_us = WebKit.UserScript.new(
        SHIM,
        WebKit.UserContentInjectedFrames.TOP_FRAME,
        WebKit.UserScriptInjectionTime.START,
        [], [],
    )
    ucm.add_script(shim_us)
    web_view.connect("load-changed", on_load_changed)

    win = Gtk.ApplicationWindow(application=a)
    win.set_child(web_view)
    win.set_default_size(800, 600)
    win.present()
    web_view.load_uri("file://" + BUNDLE)

def on_command_line(a, cl):
    a.activate()
    return 0

app = Gtk.Application.new("com.bongbetic.threshold.smoke", Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
app.connect("activate", on_activate)
app.connect("command-line", on_command_line)
GLib.timeout_add(10000, lambda: app.quit())
app.run(sys.argv)
print(json.dumps(result_data))
"""


@pytest.mark.skipif(bool(SKIP_REASON), reason="; ".join(SKIP_REASON))
class TestCarbonXvfbSmoke:
    """End-to-end: WebKitGTK loads bundle, JS request round-trips to Python."""

    def test_ready_handshake_via_xvfb(self):
        bundle_path = Path(__file__).resolve().parent.parent / "web" / "dist" / "index.html"
        if not bundle_path.exists():
            pytest.skip("web/dist not built")

        shim_path = Path(__file__).resolve().parent.parent / "web" / "src" / "shim.js"
        if not shim_path.exists():
            pytest.skip("web/src/shim.js not found")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(SMOKE_SCRIPT)
            script_path = f.name

        try:
            proc = subprocess.run(
                [
                    "xvfb-run", "-a",
                    sys.executable, script_path,
                    str(bundle_path.resolve()),
                    str(shim_path.resolve()),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            lines = proc.stdout.strip().splitlines()
            result_line = lines[-1] if lines else ""

            try:
                result = json.loads(result_line)
            except json.JSONDecodeError:
                msg = "No valid JSON output. stdout=" + proc.stdout + " stderr=" + proc.stderr + " exit=" + str(proc.returncode)
                pytest.fail(msg)

            resp = result.get("result", {})
            if resp.get("ok") is not True:
                msg = "Ready handshake failed: " + json.dumps(resp) + " stderr=" + proc.stderr
                pytest.fail(msg)

            ack = resp.get("data", {}).get("acknowledged")
            assert ack is True

        finally:
            os.unlink(script_path)
