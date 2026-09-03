"""Opt-in WebKitGTK Carbon shell - offline, self-hosted bundle.

Launches the Carbon web UI when THRESHOLD_CARBON=1 or --carbon flag is set.
Otherwise, falls back to the existing GTK presentation.

Requires WebKitGTK >= 2.40 for evaluate_javascript + world param.
All GTK/WebKit imports are deferred so the module can be imported on
systems without the typelibs (for testing).
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


def _load_shim_source() -> str:
    """Load document-start bridge JavaScript for WebKit injection."""
    return SHIM_SCRIPT_PATH.read_text(encoding="utf-8")





# ── Icon helpers ──────────────────────────────────────────────────────────────

_CHARGING_SUFFIX = {
    'Charging': '-charging',
    'Full': '',
    'Discharging': '',
    'Not charging': '',
}


def _battery_icon_name(pct: int, status: str | None) -> str:
    """Return the artifact-owned Threshold battery icon name.

    Namespaced empty/low/medium/good/full icons in charging and
    non-charging forms ship inside every artifact, so the SNI icon name
    always resolves without depending on the host icon theme.
    """
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
    return f'com.bongbetic.threshold-battery-{level}{suffix}'


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
        self._tray = None
        self._alarm_armed = False
        self._alarm_fired = False

    def set_window(self, window) -> None:
        """Set the window reference for window commands."""
        self._window = window
        self._dispatcher.set_window(window)

    def _build_state(self):
        """Build a fresh state snapshot."""
        from threshold.adapter import build_state
        return build_state(self._config, battery_path=self._battery_path)

    def start_gsettings_listeners(self) -> None:
        """Listen for GSettings appearance and preference changes."""
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

        preference_keys = [
            'show-notifications',
            'minimize-to-tray',
            'autostart',
        ]
        for key in preference_keys:
            handler_id = self._config.connect(
                f'changed::{key}',
                self._on_preference_changed,
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

    def _on_preference_changed(self, settings, key) -> None:
        """Handle a GSettings preference change — push updated state to JS."""
        self._state = self._build_state()

        # Push preference event so JS can update UI
        self._push_to_js({
            'event': 'preference',
            'data': {
                'key': key,
                'show_notifications': self._state.show_notifications,
                'minimize_to_tray': self._state.minimize_to_tray,
            },
        })

        # Push full state so JS has current values
        self._push_to_js({
            'event': 'battery',
            'data': self._serialize_state(self._state),
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

        # Show notification for threshold results
        if cmd in ("apply_threshold", "restore_threshold") and result.success:
            threshold = result.data.get("threshold", 100)
            method = result.data.get("method", "")
            if method == "alarm":
                self._show_notification(
                    f"Threshold set to {threshold}%",
                    "Alarm armed. You will be notified when capacity reaches the threshold.",
                )
                self._alarm_armed = True
                self._alarm_fired = False
            elif threshold == 100:
                self._show_notification(
                    "Threshold restored to 100%",
                    "Written to EC firmware. Persists across reboots.",
                )
                self._alarm_armed = False
                self._alarm_fired = False
            else:
                self._show_notification(
                    f"Threshold set to {threshold}%",
                    "Written to EC firmware. Persists across reboots.",
                )

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

        # Sync tray icon with live state
        self._update_tray()

        # Evaluate alarm for notification-only mode
        self._evaluate_alarm()

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

    # ── Tray integration ──────────────────────────────────────────────────

    def _setup_tray(self) -> None:
        """Create the system tray indicator."""
        try:
            from threshold.tray import TrayIcon, HAS_DBUSMENU
        except (ImportError, RuntimeError):
            return
        if not HAS_DBUSMENU:
            return

        self._tray = TrayIcon(
            on_activate=self._on_tray_show,
            on_threshold=self._on_tray_threshold,
            on_quit=self._on_tray_quit,
        )
        if self._state:
            self._update_tray()

    def _update_tray(self) -> None:
        """Update the tray icon, tooltip, and menu marks from current state."""
        if self._tray is None or self._state is None:
            return
        pct = self._state.charge_percent or 0
        status = self._state.charge_status
        threshold = self._state.pending_threshold or self._state.active_threshold or 100
        self._tray.set_state(
            pct,
            status,
            _battery_icon_name(pct, status),
            threshold,
        )

    def _on_tray_show(self, *_args) -> None:
        """Restore the window from tray."""
        if self._window is not None:
            self._window.present()

    def _on_tray_threshold(self, value) -> None:
        """Apply a threshold preset from the tray menu."""
        self._state = self._build_state()
        result = self._dispatcher.dispatch(
            'apply_threshold',
            args={'threshold': value},
            state=self._state,
        )
        if result.success:
            self._state = self._build_state()
            self._push_to_js({
                'event': 'battery',
                'data': self._serialize_state(self._state),
            })

    def _on_tray_quit(self, *_args) -> None:
        """Quit the application from tray."""
        self.stop_polling()
        self.stop_gsettings_listeners()
        self._cleanup_tray()
        if self._window is not None:
            app = self._window.get_application()
            if app is not None:
                app.quit()

    def _cleanup_tray(self) -> None:
        """Clean up the tray indicator."""
        if self._tray is not None:
            self._tray.unregister()
            self._tray = None

    def _evaluate_alarm(self) -> None:
        """Fire or re-arm the threshold-reached alarm in notify-only mode."""
        from threshold.battery import ControlMode, evaluate_alarm, read_sysfs

        if self._state is None or self._battery_path is None:
            return
        if self._state.control_mode is not ControlMode.NOTIFY_ONLY:
            return
        if not self._alarm_armed:
            return

        threshold = self._state.pending_threshold or self._state.active_threshold
        if threshold is None:
            return
        threshold = int(threshold)

        status = read_sysfs(self._battery_path / 'status')
        charge_pct = self._state.charge_percent

        # Re-arm when the battery discharges below threshold
        if status == 'Discharging' or (
            charge_pct is not None
            and charge_pct < threshold - 2
        ):
            self._alarm_fired = False
            return

        if evaluate_alarm(charge_pct, status, threshold, self._alarm_fired):
            self._alarm_fired = True
            self._show_notification(
                f'Battery reached {threshold}%',
                f'Charge has reached the {threshold}% limit you set. '
                f'Unplug the charger to preserve battery lifespan.',
                is_error=True,
            )

    def handle_close_request(self) -> bool:
        """Handle window close per notification-area readiness.

        Hides to the notification area only in `ready`. In every other
        readiness state the window stays visible and the reason is pushed
        to the UI. With the preference disabled, close exits normally.

        Returns True to prevent default close (window kept/hidden), False to allow.
        """
        if (
            self._config.get_minimize_to_tray()
            and self._tray is not None
            and self._window is not None
        ):
            from threshold.notification_area_readiness import ReadinessState

            if self._tray.readiness is ReadinessState.READY:
                self._window.set_visible(False)
                return True
            # Not ready: keep the window visible and explain why.
            self._push_to_js({
                'type': 'close_blocked',
                'reason': 'notification_area_not_ready',
                'readiness': self._tray.readiness.value,
            })
            return True
        return False

    # ── Notifications (libnotify) ─────────────────────────────────────────

    def _show_notification(self, title: str, body: str, is_error: bool = False) -> None:
        """Show a desktop notification via libnotify (if enabled)."""
        if not self._config.get_show_notifications():
            return
        try:
            import gi
            gi.require_version('Notify', '0.7')
            from gi.repository import Notify
            if not Notify.is_initted():
                return
            notification = Notify.Notification.new(
                f'Threshold \u2014 {title}',
                body,
            )
            if is_error:
                notification.set_urgency(Notify.Urgency.CRITICAL)
            notification.show()
        except Exception:
            pass

    def _serialize_state(self, state) -> dict[str, Any]:
        """Serialize ThresholdState for the bridge."""
        return {
            "battery_available": state.battery_available,
            "charge_percent": state.charge_percent,
            "charge_status": state.charge_status,
            "active_threshold": state.active_threshold,
            "pending_threshold": state.pending_threshold,
            "charge_threshold": state.charge_threshold,
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
            "show_notifications": state.show_notifications,
            "minimize_to_tray": state.minimize_to_tray,
            "dark_mode": state.dark_mode,
            "accent_color": state.accent_color,
            "compact_mode": state.compact_mode,
            "title_percentage": state.title_percentage,
            "ec_setup_state": state.ec_setup_state.value if state.ec_setup_state else None,
            "ec_setup_reason": state.ec_setup_reason.value if state.ec_setup_reason else None,
            "ec_maintenance_status": state.ec_maintenance_status.value,
            "ec_recovery_actions": list(state.ec_recovery_actions),
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
    web_view = WebKit.WebView()
    web_view.set_settings(settings)

    # Register the message handler for JS -> Python communication
    user_content = web_view.get_user_content_manager()
    handler = BridgeHandler(config, web_view)
    user_content.register_script_message_handler("threshold")
    user_content.connect("script-message-received::threshold", handler.on_message)

    # Inject bridge source at document start. UserScript.new expects
    # JavaScript source, not a file URI.
    shim = WebKit.UserScript.new(
        _load_shim_source(),
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
    win._handler = handler  # expose for application shutdown cleanup

    # Restore maximized state if saved
    if saved_maximized:
        win.maximize()

    # Set up native tray icon
    handler._setup_tray()

    # Connect close request — minimize-to-tray or normal close
    def on_close_request(*_args):
        if handler.handle_close_request():
            # Window hidden to tray — don't destroy
            return True
        # Normal close: save geometry, tear down
        handler.stop_polling()
        handler.stop_gsettings_listeners()
        handler._cleanup_tray()
        if not win.is_maximized():
            config.set_window_width(win.get_width())
            config.set_window_height(win.get_height())
        config.set_maximized(win.is_maximized())
        return False

    win.connect("close-request", on_close_request)

    # Start Python-owned 5-second poll
    handler.start_polling(5)

    # Listen for GSettings appearance + preference changes
    handler.start_gsettings_listeners()

    return win
