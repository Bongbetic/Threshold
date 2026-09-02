"""Command dispatcher — presentation-neutral boundary for UI actions.

Validates command names, argument types, ranges, and capabilities.
Returns structured results instead of raising through the presentation boundary.
"""

from dataclasses import dataclass, field
from typing import Any, Optional

from threshold.battery import (
    THRESHOLD_MIN,
    THRESHOLD_MAX,
    ControlMode,
    read_sysfs,
    write_threshold,
)
from threshold.config import Config
from threshold.state import ThresholdState

# Machine-wide threshold policy mirror read by the EC lifecycle authority's
# boot reconciliation (written best-effort; unprivileged runs simply skip it).
EC_THRESHOLD_FILE = "/var/lib/threshold/ec/charge-threshold"


def _persist_machine_threshold(value: int) -> None:
    """Best-effort machine-wide copy of the confirmed charge threshold."""
    import pathlib

    try:
        path = pathlib.Path(EC_THRESHOLD_FILE)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"{value}\n")
    except OSError:
        pass


# ── Result types ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class CommandResult:
    """Structured result from a command dispatch."""
    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    error_code: Optional[str] = None
    message: Optional[str] = None


# ── Error codes ──────────────────────────────────────────────────────────────


class ErrorCode:
    UNKNOWN_COMMAND = "unknown_command"
    INVALID_ARGS = "invalid_args"
    THRESHOLD_OUT_OF_RANGE = "threshold_out_of_range"
    NO_BATTERY = "no_battery"
    WRITE_FAILED = "write_failed"
    PERMISSION_DENIED = "permission_denied"
    EC_MISMATCH = "ec_mismatch"
    WINDOW_NOT_AVAILABLE = "window_not_available"


# ── Valid values ──────────────────────────────────────────────────────────────

VALID_ACCENT_COLORS = frozenset({"orange", "blue", "green", "purple", "red"})


# ── Dispatcher ───────────────────────────────────────────────────────────────


class CommandDispatcher:
    """Validates and dispatches UI commands to backend behavior."""

    def __init__(self, config: Config):
        self._config = config

    def dispatch(
        self,
        command: str,
        args: dict[str, Any] | None = None,
        state: ThresholdState | None = None,
    ) -> CommandResult:
        """Dispatch a command and return structured result."""
        args = args or {}

        handler = getattr(self, f"_cmd_{command}", None)
        if handler is None:
            return CommandResult(
                success=False,
                error_code=ErrorCode.UNKNOWN_COMMAND,
                message=f"Unknown command: {command}",
            )

        return handler(args, state)

    # ── State ──────────────────────────────────────────────────────────────────

    def _cmd_get_state(
        self, args: dict, state: ThresholdState | None
    ) -> CommandResult:
        if state is None:
            return CommandResult(
                success=False,
                error_code=ErrorCode.NO_BATTERY,
                message="No state available",
            )
        return CommandResult(success=True, data={"state": state})

    # ── Threshold ──────────────────────────────────────────────────────────────

    def _cmd_apply_threshold(
        self, args: dict, state: ThresholdState | None
    ) -> CommandResult:
        # Validate args
        if "threshold" not in args:
            return CommandResult(
                success=False,
                error_code=ErrorCode.INVALID_ARGS,
                message="Missing required argument: threshold",
            )

        threshold = args["threshold"]
        if not isinstance(threshold, int):
            return CommandResult(
                success=False,
                error_code=ErrorCode.INVALID_ARGS,
                message="threshold must be an integer",
            )

        if not THRESHOLD_MIN <= threshold <= THRESHOLD_MAX:
            return CommandResult(
                success=False,
                error_code=ErrorCode.THRESHOLD_OUT_OF_RANGE,
                message=f"Threshold must be {THRESHOLD_MIN}–{THRESHOLD_MAX}",
            )

        # Validate capabilities
        if state is None or not state.battery_available:
            return CommandResult(
                success=False,
                error_code=ErrorCode.NO_BATTERY,
                message="No battery available",
            )

        # Notification-only mode — alarm only, no sysfs write
        if state.control_mode == ControlMode.NOTIFY_ONLY:
            self._config.set_charge_threshold(threshold)
            _persist_machine_threshold(threshold)
            return CommandResult(
                success=True,
                data={
                    "threshold": threshold,
                    "method": "alarm",
                    "ec_mismatch": False,
                },
            )

        # Direct write
        if state.battery_path is None:
            return CommandResult(
                success=False,
                error_code=ErrorCode.NO_BATTERY,
                message="No battery path available",
            )

        success, message = write_threshold(state.battery_path, threshold)

        if not success:
            error_code = ErrorCode.WRITE_FAILED
            if "Permission denied" in message:
                error_code = ErrorCode.PERMISSION_DENIED
            return CommandResult(
                success=False,
                error_code=error_code,
                message=message,
            )

        # EC value mismatch check
        actual = read_sysfs(state.battery_path / "charge_control_end_threshold")
        ec_mismatch = False
        if actual is not None:
            try:
                if int(actual) != threshold:
                    ec_mismatch = True
                    message = f"{message} (EC stored {actual}%)"
            except ValueError:
                pass

        self._config.set_charge_threshold(threshold)
        _persist_machine_threshold(threshold)

        return CommandResult(
            success=True,
            data={
                "threshold": threshold,
                "method": message,
                "ec_mismatch": ec_mismatch,
            },
        )

    def _cmd_restore_threshold(
        self, args: dict, state: ThresholdState | None
    ) -> CommandResult:
        return self._cmd_apply_threshold({"threshold": THRESHOLD_MAX}, state)

    # ── Preferences ────────────────────────────────────────────────────────────

    def _cmd_set_dark_mode(
        self, args: dict, state: ThresholdState | None
    ) -> CommandResult:
        return self._set_bool_pref(args, "dark_mode", self._config.set_dark_mode)

    def _cmd_set_compact_mode(
        self, args: dict, state: ThresholdState | None
    ) -> CommandResult:
        return self._set_bool_pref(
            args, "compact_mode", self._config.set_compact_mode
        )

    def _cmd_set_title_percentage(
        self, args: dict, state: ThresholdState | None
    ) -> CommandResult:
        return self._set_bool_pref(
            args, "title_percentage", self._config.set_title_percentage
        )

    def _cmd_set_show_notifications(
        self, args: dict, state: ThresholdState | None
    ) -> CommandResult:
        return self._set_bool_pref(
            args, "show_notifications", self._config.set_show_notifications
        )

    def _cmd_set_minimize_to_tray(
        self, args: dict, state: ThresholdState | None
    ) -> CommandResult:
        return self._set_bool_pref(
            args, "minimize_to_tray", self._config.set_minimize_to_tray
        )

    def _cmd_set_accent_color(
        self, args: dict, state: ThresholdState | None
    ) -> CommandResult:
        if "value" not in args:
            return CommandResult(
                success=False,
                error_code=ErrorCode.INVALID_ARGS,
                message="Missing required argument: value",
            )

        value = args["value"]
        if not isinstance(value, str) or value not in VALID_ACCENT_COLORS:
            return CommandResult(
                success=False,
                error_code=ErrorCode.INVALID_ARGS,
                message=(
                    "Invalid accent color. Must be one of: "
                    + ", ".join(sorted(VALID_ACCENT_COLORS))
                ),
            )

        self._config.set_accent_color(value)
        return CommandResult(success=True, data={"accent_color": value})

    def _set_bool_pref(
        self, args: dict, key: str, setter
    ) -> CommandResult:
        if "value" not in args:
            return CommandResult(
                success=False,
                error_code=ErrorCode.INVALID_ARGS,
                message="Missing required argument: value",
            )

        value = args["value"]
        if not isinstance(value, bool):
            return CommandResult(
                success=False,
                error_code=ErrorCode.INVALID_ARGS,
                message="value must be a boolean",
            )

        setter(value)
        return CommandResult(success=True, data={key: value})

    # ── Window commands ─────────────────────────────────────────────────────

    def _cmd_minimize(
        self, args: dict, state: ThresholdState | None
    ) -> CommandResult:
        """Minimize the window. Requires window reference set externally."""
        if not hasattr(self, '_window') or self._window is None:
            return CommandResult(
                success=False,
                error_code=ErrorCode.WINDOW_NOT_AVAILABLE,
                message="Window reference not set",
            )
        self._window.minimize()
        return CommandResult(success=True, data={"minimized": True})

    def _cmd_maximize(
        self, args: dict, state: ThresholdState | None
    ) -> CommandResult:
        """Maximize the window."""
        if not hasattr(self, '_window') or self._window is None:
            return CommandResult(
                success=False,
                error_code=ErrorCode.WINDOW_NOT_AVAILABLE,
                message="Window reference not set",
            )
        self._window.maximize()
        return CommandResult(success=True, data={"maximized": True})

    def _cmd_restore(
        self, args: dict, state: ThresholdState | None
    ) -> CommandResult:
        """Restore (unmaximize) the window."""
        if not hasattr(self, '_window') or self._window is None:
            return CommandResult(
                success=False,
                error_code=ErrorCode.WINDOW_NOT_AVAILABLE,
                message="Window reference not set",
            )
        self._window.unmaximize()
        return CommandResult(success=True, data={"maximized": False})

    def _cmd_toggle_maximize(
        self, args: dict, state: ThresholdState | None
    ) -> CommandResult:
        """Toggle maximize/restore the window."""
        if not hasattr(self, '_window') or self._window is None:
            return CommandResult(
                success=False,
                error_code=ErrorCode.WINDOW_NOT_AVAILABLE,
                message="Window reference not set",
            )
        if self._window.is_maximized():
            self._window.unmaximize()
            return CommandResult(success=True, data={"maximized": False})
        else:
            self._window.maximize()
            return CommandResult(success=True, data={"maximized": True})

    def _cmd_close(
        self, args: dict, state: ThresholdState | None
    ) -> CommandResult:
        """Close the window."""
        if not hasattr(self, '_window') or self._window is None:
            return CommandResult(
                success=False,
                error_code=ErrorCode.WINDOW_NOT_AVAILABLE,
                message="Window reference not set",
            )
        self._window.close()
        return CommandResult(success=True, data={"closed": True})

    def _cmd_begin_drag(
        self, args: dict, state: ThresholdState | None
    ) -> CommandResult:
        """Begin window drag operation."""
        if not hasattr(self, '_window') or self._window is None:
            return CommandResult(
                success=False,
                error_code=ErrorCode.WINDOW_NOT_AVAILABLE,
                message="Window reference not set",
            )
        # begin_move_drag takes (button, window_x, window_y, timestamp)
        # Use -1 for timestamp to let GTK use current time
        self._window.begin_move_drag(1, -1, -1, -1)
        return CommandResult(success=True, data={"dragging": True})

    def set_window(self, window) -> None:
        """Set the window reference for window commands."""
        self._window = window
