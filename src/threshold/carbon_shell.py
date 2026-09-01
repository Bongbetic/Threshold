"""Opt-in WebKitGTK Carbon shell - offline, self-hosted bundle.

Launches the Carbon web UI when THRESHOLD_CARBON=1 or --carbon flag is set.
Otherwise, falls back to the existing GTK presentation.

Requires WebKitGTK >= 2.40 for evaluate_javascript + world param.
All GTK/WebKit imports are deferred so the module can be imported on
systems without the typelibs (for testing helpers like carbon_enabled).
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Optional


# ── Constants ────────────────────────────────────────────────────────────────

WINDOW_WIDTH = 1180
WINDOW_HEIGHT = 860
MIN_WIDTH = 960
MIN_HEIGHT = 700

SHIM_SCRIPT_PATH = Path(__file__).resolve().parent.parent.parent / "web" / "src" / "shim.js"

# Bundle search paths (committed dist in source tree)
_BUNDLE_CANDIDATES = [
    # Dev: relative to source root
    Path(__file__).resolve().parent.parent.parent / "web" / "dist" / "index.html",
    # Installed: under pkgdatadir/web/
    Path(os.environ.get("THRESHOLD_PKGDATADIR", "")) / "web" / "index.html"
    if os.environ.get("THRESHOLD_PKGDATADIR") else None,
]


def _find_bundle() -> Optional[Path]:
    """Locate the committed Vite production bundle."""
    for candidate in _BUNDLE_CANDIDATES:
        if candidate is None:
            continue
        if candidate.exists():
            return candidate
    return None


def carbon_enabled() -> bool:
    """Check if the Carbon shell is opt-in enabled."""
    return os.environ.get("THRESHOLD_CARBON", "0") == "1"


def _carbon_requested() -> bool:
    """Check if the Carbon shell was requested via --carbon flag or env var."""
    if "--carbon" in sys.argv:
        return True
    return os.environ.get("THRESHOLD_CARBON", "0") == "1"


# ── Bridge handler (deferred GTK imports) ───────────────────────────────────


class BridgeHandler:
    """Handles messages from JS via webkit message handlers.

    Dispatches through the CommandDispatcher and pushes responses/events
    back to JS via evaluate_javascript.
    """

    def __init__(self, config, web_view):
        from threshold.adapter import build_state
        from threshold.commands import CommandDispatcher
        from threshold.battery import find_battery_path

        self._config = config
        self._web_view = web_view
        self._dispatcher = CommandDispatcher(config)
        self._state = None
        self._battery_path = find_battery_path()

    def _build_state(self):
        """Build a fresh state snapshot."""
        from threshold.adapter import build_state
        return build_state(self._config, battery_path=self._battery_path)

    def _push_to_js(self, message: dict[str, Any]) -> None:
        """Send a message to JS via evaluate_javascript (WebKit 6.0 async API)."""
        js = "window.threshold._handleMessage(" + json.dumps(json.dumps(message)) + ");"
        self._web_view.evaluate_javascript(
            js,
            -1,  # length (-1 = null-terminated)
            None,  # world_name (default)
            None,  # source_uri
            None,  # cancellable
            None,  # callback
        )

    def on_message(self, _user_content_manager, message) -> None:
        """Handle an incoming message from JS.

        WebKit 6.0 passes a JSC.Value, not a UserMessage.
        """
        try:
            raw = message.to_string()
            msg = json.loads(raw)
        except (json.JSONDecodeError, Exception) as e:
            error_resp = {"id": "", "ok": False, "error": f"Malformed request: {e}"}
            self._push_to_js(error_resp)
            return

        cmd = msg.get("cmd", "")
        msg_id = msg.get("id", "")
        args = msg.get("args", {})

        # Build state for the command
        self._state = self._build_state()

        # Dispatch through the command boundary
        result = self._dispatcher.dispatch(
            command=cmd,
            args=args,
            state=self._state,
        )

        # Special handling for 'ready' command - return full state + appearance
        if cmd == "ready":
            response = {
                "id": msg_id,
                "ok": True,
                "data": {
                    "acknowledged": True,
                    "state": self._serialize_state(self._state),
                    "appearance": self._serialize_appearance(self._state),
                },
            }
        elif cmd == "get_state":
            response = {
                "id": msg_id,
                "ok": result.success,
                "data": {
                    "state": self._serialize_state(self._state),
                    "appearance": self._serialize_appearance(self._state),
                },
            }
        else:
            response = {
                "id": msg_id,
                "ok": result.success,
            }
            if result.success:
                response["data"] = result.data
            else:
                response["error"] = result.message or result.error_code or "Unknown error"

        self._push_to_js(response)

    def _serialize_state(self, state) -> dict[str, Any]:
        """Serialize ThresholdState for the bridge."""
        return {
            "battery_available": state.battery_available,
            "charge_percent": state.charge_percent,
            "charge_status": state.charge_status,
            "active_threshold": state.active_threshold,
            "control_mode": state.control_mode.value if state.control_mode else None,
            "health_percent": state.health_percent,
            "health_grade": state.health_grade,
            "power_source": state.power_source,
            "dark_mode": state.dark_mode,
            "accent_color": state.accent_color,
        }

    def _serialize_appearance(self, state) -> dict[str, Any]:
        """Serialize appearance state for the bridge."""
        return {
            "scheme": state.effective_theme_scheme,
            "accent_color": state.accent_color,
        }


# ── Carbon Window (deferred GTK imports) ────────────────────────────────────


def create_carbon_window(application, config):
    """Create a CarbonWindow. Raises ImportError if WebKitGTK is missing."""
    import gi
    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1")
    gi.require_version("WebKit", "6.0")
    from gi.repository import Gtk, WebKit

    bundle_path = _find_bundle()
    if bundle_path is None:
        raise FileNotFoundError(
            "Carbon bundle not found. Build with: cd web && npm run build"
        )

    # Configure WebKit settings for offline operation
    settings = WebKit.Settings.new()
    settings.set_enable_javascript(True)
    settings.set_allow_file_access_from_file_urls(True)
    settings.set_allow_universal_access_from_file_urls(True)

    # Create WebView
    web_view = WebKit.WebView.new_with_settings(settings)

    # Register the message handler for JS -> Python communication
    user_content = web_view.get_user_content_manager()
    handler = BridgeHandler(config, web_view)
    user_content.register_script_message_handler("threshold")
    user_content.connect("script-message-received::threshold", handler.on_message)

    # Inject the document-start shim
    shim_uri = "file://" + str(SHIM_SCRIPT_PATH.resolve())
    shim = WebKit.UserScript.new(
        shim_uri,
        WebKit.UserContentInjectedFrames.TOP_FRAME,
        WebKit.UserScriptInjectionTime.START,
        [],  # allow_list
        [],  # block_list
    )
    user_content.add_script(shim)

    # Load the bundle (offline via file://)
    bundle_uri = "file://" + str(bundle_path.resolve())
    web_view.load_uri(bundle_uri)

    # Create the window
    win = Gtk.ApplicationWindow(
        application=application,
        title="Threshold",
        default_width=WINDOW_WIDTH,
        default_height=WINDOW_HEIGHT,
    )
    win.set_resizable(True)
    win.set_size_request(MIN_WIDTH, MIN_HEIGHT)
    win.set_child(web_view)

    # Connect close request
    def on_close_request(*_args):
        if not win.is_maximized():
            config.set_window_width(win.get_width())
            config.set_window_height(win.get_height())
        config.set_maximized(win.is_maximized())
        return False

    win.connect("close-request", on_close_request)
    return win
