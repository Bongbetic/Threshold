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
        self._writing = False
        self._polling_source_id = None
        self._gsettings_handler_ids: list[int] = []
        self._window = None

    def set_window(self, window) -> None:
        """Set the window reference for window commands."""
        self._window = window
        self._dispatcher.set_window(window)

    def _build_state(self):
        """Build a fresh state snapshot."""
        from threshold.adapter import build_state
        return build_state(self._config, battery_path=self._battery_path)

    def start_gsettings_listeners(self) -> None:
        """Listen for GSettings appearance changes and push events to JS."""
        appearance_keys = [
            'dark-mode',
            'accent-color',
            'compact-mode',
            'title-percentage',
        ]
        for key in appearance_keys:
            handler_id = self._config.connect(
                f'changed::{key}',
                self._on_appearance_changed,
            )
            self._gsettings_handler_ids.append(handler_id)

    def stop_gsettings_listeners(self) -> None:
        """Disconnect GSettings listeners."""
        self._gsettings_handler_ids.clear()

    def _on_appearance_changed(self, settings, key) -> None:
        """Handle a GSettings appearance change — push updated state to JS."""
        # Rebuild state from fresh config
        self._state = self._build_state()

        # Push appearance event
        self._push_to_js({
            'event': 'appearance',
            'data': self._serialize_appearance(self._state),
        })

        # Push full battery event (includes dark_mode, accent_color, compact_mode)
        self._push_to_js({
            'event': 'battery',
            'data': self._serialize_state(self._state),
        })

        # If title-percentage changed, push title update
        if key == 'title-percentage':
            self._push_to_js({
                'event': 'title_update',
                'data': {
                    'title_percentage': self._state.title_percentage,
                    'charge_percent': self._state.charge_percent,
                },
            })

    def _is_write_command(self, cmd: str) -> bool:
        """Return True if the command initiates a threshold write."""
        return cmd in ("apply_threshold", "restore_threshold")

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

        # Track write-in-flight for external EC change detection
        self._writing = self._is_write_command(cmd)

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

        # Clear write-in-flight flag after response sent
        if self._writing:
            self._writing = False

    def start_polling(self, interval_seconds: int = 5) -> None:
        """Start periodic state push to JS.

        Mirrors the GTK window's 5-second poll — no JS timer needed.
        """
        from gi.repository import GLib
        if self._polling_source_id is not None:
            return
        self._polling_source_id = GLib.timeout_add_seconds(
            interval_seconds, self._poll_tick
        )

    def stop_polling(self) -> None:
        """Stop periodic state push."""
        from gi.repository import GLib
        if self._polling_source_id is not None:
            GLib.source_remove(self._polling_source_id)
            self._polling_source_id = None

    def _poll_tick(self) -> bool:
        """Called every interval_seconds — refresh state and push to JS."""
        from threshold.battery import detect_control_mode, read_sysfs
        from gi.repository import GLib

        # Re-detect mode and follow external EC threshold changes
        self._sync_from_hardware()

        # Build fresh state and push
        self._state = self._build_state()
        self._push_to_js({
            "event": "battery",
            "data": self._serialize_state(self._state),
        })

        return GLib.SOURCE_CONTINUE

    def _sync_from_hardware(self) -> None:
        """Re-detect mode and follow external EC threshold changes.

        Skipped while a write is in flight.
        """
        if self._writing or self._battery_path is None:
            return

        from threshold.battery import detect_control_mode, read_sysfs

        mode = detect_control_mode(self._battery_path)
        if mode != self._state.control_mode:
            self._state = self._state.with_updates(control_mode=mode)

        # Follow external EC threshold changes
        raw = read_sysfs(self._battery_path / "charge_control_end_threshold")
        if raw is not None:
            try:
                ec_value = int(raw)
            except ValueError:
                return
            current = self._state.active_threshold
            if ec_value != current:
                self._state = self._state.with_updates(
                    active_threshold=ec_value,
                    pending_threshold=ec_value,
                )
                self._config.set_charge_threshold(ec_value)

    def _serialize_state(self, state) -> dict[str, Any]:
        """Serialize ThresholdState for the bridge."""
        return {
            "battery_available": state.battery_available,
            "charge_percent": state.charge_percent,
            "charge_status": state.charge_status,
            "active_threshold": state.active_threshold,
            "pending_threshold": state.pending_threshold,
            "control_mode": state.control_mode.value if state.control_mode else None,
            "battery_identifier": state.battery_path.name if state.battery_path else None,
            "health_percent": state.health_percent,
            "health_grade": state.health_grade,
            "power_source": state.power_source,
            "cycle_count": state.cycle_count,
            "capacity_full_wh": state.capacity_full_wh,
            "capacity_design_wh": state.capacity_design_wh,
            "alarm_armed": state.alarm_armed,
            "alarm_fired": state.alarm_fired,
            "dark_mode": state.dark_mode,
            "accent_color": state.accent_color,
            "compact_mode": state.compact_mode,
            "title_percentage": state.title_percentage,
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
    saved_width = config.get_window_width() or WINDOW_WIDTH
    saved_height = config.get_window_height() or WINDOW_HEIGHT
    saved_maximized = config.get_maximized()

    win = Gtk.ApplicationWindow(
        application=application,
        title="Threshold",
        default_width=saved_width,
        default_height=saved_height,
    )
    win.set_resizable(True)
    win.set_size_request(MIN_WIDTH, MIN_HEIGHT)
    win.set_child(web_view)

    # Wire window reference to handler and dispatcher
    handler.set_window(win)

    # Restore maximized state if saved
    if saved_maximized:
        win.maximize()

    # Connect close request
    def on_close_request(*_args):
        handler.stop_polling()
        handler.stop_gsettings_listeners()
        if not win.is_maximized():
            config.set_window_width(win.get_width())
            config.set_window_height(win.get_height())
        config.set_maximized(win.is_maximized())
        return False

    win.connect("close-request", on_close_request)

    # Start Python-owned 5-second poll
    handler.start_polling(5)

    # Listen for GSettings appearance changes
    handler.start_gsettings_listeners()

    return win
