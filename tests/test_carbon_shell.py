"""Tests for the Carbon shell bridge handler and message protocol."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure src is importable
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from threshold.commands import CommandDispatcher, CommandResult
from threshold.state import ThresholdState
from threshold.battery import ControlMode


# ── Golden fixtures (mirrored from web/test/fixtures/messages.json) ────────


@pytest.fixture
def fixtures():
    """Load shared contract fixtures."""
    fixture_path = (
        Path(__file__).resolve().parent.parent
        / "web" / "test" / "fixtures" / "messages.json"
    )
    if fixture_path.exists():
        return json.loads(fixture_path.read_text())
    return {
        "ready_request": {"id": "req-ready-0", "cmd": "ready"},
        "ready_response": {"id": "req-ready-0", "ok": True, "data": {"acknowledged": True}},
        "get_state_request": {"id": "req-state-1", "cmd": "get_state"},
        "unknown_command_request": {"id": "req-unk-7", "cmd": "nonexistent_command"},
        "unknown_command_response": {"id": "req-unk-7", "ok": False, "error": "Unknown command: nonexistent_command"},
    }


@pytest.fixture
def mock_config():
    config = MagicMock()
    config.get_dark_mode.return_value = False
    config.get_accent_color.return_value = "orange"
    config.get_compact_mode.return_value = False
    config.get_title_percentage.return_value = True
    config.get_show_notifications.return_value = True
    config.get_minimize_to_tray.return_value = True
    config.get_charge_threshold.return_value = 80
    config.get_last_applied_time.return_value = 0
    return config


@pytest.fixture
def ec_msi_state():
    return ThresholdState(
        battery_available=True,
        battery_path=Path("/sys/class/power_supply/BAT0"),
        control_mode=ControlMode.EC_MSI,
        charge_percent=75,
        charge_status="Charging",
        active_threshold=80,
        pending_threshold=80,
        cycle_count=142,
        capacity_full_wh=52.5,
        capacity_design_wh=56.0,
        health_percent=92,
        health_grade="Good",
        power_source="AC Adapter",
        dark_mode=False,
        accent_color="orange",
    )


# ── Bridge handler tests ────────────────────────────────────────────────────


class TestBridgeHandlerSerialization:
    """Test that state serialization produces valid bridge payloads."""

    def test_serialize_state_battery_fields(self, ec_msi_state):
        from threshold.carbon_shell import BridgeHandler
        config = MagicMock()
        web_view = MagicMock()
        handler = BridgeHandler.__new__(BridgeHandler)
        handler._config = config
        handler._web_view = web_view
        handler._dispatcher = CommandDispatcher(config)
        handler._state = ec_msi_state
        handler._battery_path = ec_msi_state.battery_path

        serialized = handler._serialize_state(ec_msi_state)
        assert serialized["battery_available"] is True
        assert serialized["charge_percent"] == 75
        assert serialized["charge_status"] == "Charging"
        assert serialized["active_threshold"] == 80
        assert serialized["pending_threshold"] == 80
        assert serialized["control_mode"] == "msi-ec"
        assert serialized["battery_identifier"] == "BAT0"
        assert serialized["health_percent"] == 92
        assert serialized["health_grade"] == "Good"
        assert serialized["power_source"] == "AC Adapter"
        assert serialized["cycle_count"] == 142
        assert serialized["capacity_full_wh"] == 52.5
        assert serialized["capacity_design_wh"] == 56.0
        assert serialized["alarm_armed"] is False
        assert serialized["alarm_fired"] is False
        assert serialized["dark_mode"] is False
        assert serialized["accent_color"] == "orange"

    def test_serialize_appearance(self, ec_msi_state):
        from threshold.carbon_shell import BridgeHandler
        handler = BridgeHandler.__new__(BridgeHandler)
        appearance = handler._serialize_appearance(ec_msi_state)
        assert appearance["scheme"] == "light"
        assert appearance["accent_color"] == "orange"

    def test_serialize_appearance_dark(self):
        from threshold.carbon_shell import BridgeHandler
        state = ThresholdState(battery_available=False, dark_mode=True, accent_color="blue")
        handler = BridgeHandler.__new__(BridgeHandler)
        appearance = handler._serialize_appearance(state)
        assert appearance["scheme"] == "dark"
        assert appearance["accent_color"] == "blue"

    def test_serialize_state_no_battery(self):
        from threshold.carbon_shell import BridgeHandler
        state = ThresholdState(battery_available=False)
        handler = BridgeHandler.__new__(BridgeHandler)
        serialized = handler._serialize_state(state)
        assert serialized["battery_available"] is False
        assert serialized["charge_percent"] is None
        assert serialized["charge_status"] is None
        assert serialized["active_threshold"] is None
        assert serialized["pending_threshold"] is None
        assert serialized["control_mode"] is None
        assert serialized["battery_identifier"] is None
        assert serialized["cycle_count"] is None
        assert serialized["capacity_full_wh"] is None
        assert serialized["capacity_design_wh"] is None
        assert serialized["alarm_armed"] is False
        assert serialized["alarm_fired"] is False


class TestBridgeHandlerReadyCommand:

    def test_ready_returns_full_state(self, mock_config, ec_msi_state, fixtures):
        from threshold.carbon_shell import BridgeHandler
        web_view = MagicMock()
        with patch.object(BridgeHandler, '_build_state', return_value=ec_msi_state):
            handler = BridgeHandler(mock_config, web_view)
            handler._state = ec_msi_state

            msg = MagicMock()
            msg.to_string.return_value = json.dumps(
                fixtures["ready_request"]
            )
            handler.on_message(None, msg)

            web_view.evaluate_javascript.assert_called_once()
            call_args = web_view.evaluate_javascript.call_args
            js = call_args[0][0]

            assert 'window.threshold._handleMessage(' in js
            start = js.index('window.threshold._handleMessage(') + len('window.threshold._handleMessage(')
            end = js.rindex(')')
            inner_json = json.loads(json.loads(js[start:end]))

            assert inner_json["id"] == fixtures["ready_request"]["id"]
            assert inner_json["ok"] is True
            assert inner_json["data"]["acknowledged"] is True
            assert "state" in inner_json["data"]
            assert "appearance" in inner_json["data"]


class TestBridgeHandlerGetState:

    def test_get_state_returns_snapshot(self, mock_config, ec_msi_state, fixtures):
        from threshold.carbon_shell import BridgeHandler
        web_view = MagicMock()
        with patch.object(BridgeHandler, '_build_state', return_value=ec_msi_state):
            handler = BridgeHandler(mock_config, web_view)
            msg = MagicMock()
            msg.to_string.return_value = json.dumps(
                fixtures["get_state_request"]
            )
            handler.on_message(None, msg)

            web_view.evaluate_javascript.assert_called_once()
            call_args = web_view.evaluate_javascript.call_args
            js = call_args[0][0]

            start = js.index('window.threshold._handleMessage(') + len('window.threshold._handleMessage(')
            end = js.rindex(')')
            inner_json = json.loads(json.loads(js[start:end]))

            assert inner_json["ok"] is True
            assert inner_json["data"]["state"]["charge_percent"] == 75


class TestBridgeHandlerUnknownCommand:

    def test_unknown_command_error(self, mock_config, ec_msi_state, fixtures):
        from threshold.carbon_shell import BridgeHandler
        web_view = MagicMock()
        with patch.object(BridgeHandler, '_build_state', return_value=ec_msi_state):
            handler = BridgeHandler(mock_config, web_view)
            msg = MagicMock()
            msg.to_string.return_value = json.dumps(
                fixtures["unknown_command_request"]
            )
            handler.on_message(None, msg)

            web_view.evaluate_javascript.assert_called_once()
            call_args = web_view.evaluate_javascript.call_args
            js = call_args[0][0]

            start = js.index('window.threshold._handleMessage(') + len('window.threshold._handleMessage(')
            end = js.rindex(')')
            inner_json = json.loads(json.loads(js[start:end]))

            assert inner_json["ok"] is False
            assert "Unknown command" in inner_json["error"]
            assert inner_json["id"] == fixtures["unknown_command_request"]["id"]


class TestBridgeHandlerMalformedPayload:

    def test_malformed_json_returns_error(self, mock_config, ec_msi_state):
        from threshold.carbon_shell import BridgeHandler
        web_view = MagicMock()
        with patch.object(BridgeHandler, '_build_state', return_value=ec_msi_state):
            handler = BridgeHandler(mock_config, web_view)
            msg = MagicMock()
            msg.to_string.return_value = "not-json"
            handler.on_message(None, msg)

            web_view.evaluate_javascript.assert_called_once()
            call_args = web_view.evaluate_javascript.call_args
            js = call_args[0][0]

            start = js.index('window.threshold._handleMessage(') + len('window.threshold._handleMessage(')
            end = js.rindex(')')
            inner_json = json.loads(json.loads(js[start:end]))

            assert inner_json["ok"] is False
            assert "Malformed" in inner_json["error"]


class TestBridgeHandlerThresholdCommand:

    def test_apply_threshold_success(self, mock_config, ec_msi_state, fixtures):
        from threshold.carbon_shell import BridgeHandler
        web_view = MagicMock()
        with patch.object(BridgeHandler, '_build_state', return_value=ec_msi_state), \
             patch("threshold.commands.write_threshold", return_value=(True, "direct")), \
             patch("threshold.commands.read_sysfs", return_value="80"):
            handler = BridgeHandler(mock_config, web_view)
            msg = MagicMock()
            msg.to_string.return_value = json.dumps({
                "id": "req-thresh-2",
                "cmd": "apply_threshold",
                "args": {"threshold": 80}
            })
            handler.on_message(None, msg)

            web_view.evaluate_javascript.assert_called_once()
            call_args = web_view.evaluate_javascript.call_args
            js = call_args[0][0]

            start = js.index('window.threshold._handleMessage(') + len('window.threshold._handleMessage(')
            end = js.rindex(')')
            inner_json = json.loads(json.loads(js[start:end]))

            assert inner_json["ok"] is True
            assert inner_json["id"] == "req-thresh-2"
            assert inner_json["data"]["threshold"] == 80


class TestCarbonShellModule:

    def test_carbon_enabled_default(self):
        from threshold.carbon_shell import carbon_enabled
        import os
        with patch.dict(os.environ, {}, clear=True):
            assert carbon_enabled() is False

    def test_carbon_enabled_via_env(self):
        from threshold.carbon_shell import carbon_enabled
        import os
        with patch.dict(os.environ, {"THRESHOLD_CARBON": "1"}):
            assert carbon_enabled() is True

    def test_carbon_enabled_via_flag(self):
        from threshold.carbon_shell import _carbon_requested
        # Temporarily add --carbon to argv
        saved = sys.argv[:]
        sys.argv.append("--carbon")
        try:
            assert _carbon_requested() is True
        finally:
            sys.argv[:] = saved

    def test_find_bundle_missing(self):
        from threshold.carbon_shell import _find_bundle
        result = _find_bundle()
        assert result is None or isinstance(result, Path)


# ── Projected event tests ────────────────────────────────────────────────────
# Covers: complete, partial, changed-hardware, notification-only, no-battery


def _make_handler(state, config=None):
    """Create a BridgeHandler with mocked web_view for event testing."""
    from threshold.carbon_shell import BridgeHandler
    from threshold.commands import CommandDispatcher
    cfg = config or MagicMock()
    handler = BridgeHandler.__new__(BridgeHandler)
    handler._config = cfg
    handler._web_view = MagicMock()
    handler._dispatcher = CommandDispatcher(cfg)
    handler._state = state
    handler._battery_path = state.battery_path
    handler._writing = False
    handler._polling_source_id = None
    handler._tray = None
    handler._alarm_armed = False
    handler._alarm_fired = False
    handler._gsettings_handler_ids = []
    return handler


def _extract_pushed_event(handler):
    """Extract the last event pushed to JS via _push_to_js."""
    handler._web_view.evaluate_javascript.assert_called()
    call_args = handler._web_view.evaluate_javascript.call_args_list
    last_js = call_args[-1][0][0]
    start = last_js.index('window.threshold._handleMessage(') + len('window.threshold._handleMessage(')
    end = last_js.rindex(')')
    return json.loads(json.loads(last_js[start:end]))


class TestProjectedEventsCompleteBattery:
    """Full battery state push event."""

    def test_complete_state_serialized(self):
        state = ThresholdState(
            battery_available=True,
            battery_path=Path("/sys/class/power_supply/BAT0"),
            control_mode=ControlMode.EC_MSI,
            charge_percent=75,
            charge_status="Charging",
            active_threshold=80,
            pending_threshold=80,
            health_percent=92,
            health_grade="Good",
            cycle_count=142,
            capacity_full_wh=52.5,
            capacity_design_wh=56.0,
            power_source="AC Adapter",
            alarm_armed=False,
            alarm_fired=False,
            dark_mode=False,
            accent_color="orange",
        )
        handler = _make_handler(state)
        handler._push_to_js({
            "event": "battery",
            "data": handler._serialize_state(state),
        })
        event = _extract_pushed_event(handler)
        assert event["event"] == "battery"
        data = event["data"]
        assert data["battery_available"] is True
        assert data["charge_percent"] == 75
        assert data["control_mode"] == "msi-ec"
        assert data["battery_identifier"] == "BAT0"
        assert data["cycle_count"] == 142
        assert data["capacity_full_wh"] == 52.5
        assert data["capacity_design_wh"] == 56.0


class TestProjectedEventsPartialData:
    """Partial sysfs data — some values null, others valid."""

    def test_partial_sysfs_values(self):
        state = ThresholdState(
            battery_available=True,
            battery_path=Path("/sys/class/power_supply/BAT0"),
            control_mode=ControlMode.NOTIFY_ONLY,
            charge_percent=55,
            charge_status="Discharging",
            active_threshold=None,
            pending_threshold=None,
            health_percent=None,
            health_grade=None,
            cycle_count=None,
            capacity_full_wh=None,
            capacity_design_wh=None,
            power_source="Battery",
            alarm_armed=False,
            alarm_fired=False,
        )
        handler = _make_handler(state)
        handler._push_to_js({
            "event": "battery",
            "data": handler._serialize_state(state),
        })
        event = _extract_pushed_event(handler)
        data = event["data"]
        # Available fields present
        assert data["charge_percent"] == 55
        assert data["charge_status"] == "Discharging"
        assert data["power_source"] == "Battery"
        # Null fields render as None (UI shows "—")
        assert data["health_percent"] is None
        assert data["health_grade"] is None
        assert data["cycle_count"] is None
        assert data["capacity_full_wh"] is None
        assert data["capacity_design_wh"] is None
        assert data["active_threshold"] is None


class TestProjectedEventsChangedHardware:
    """EC threshold changed externally — active threshold updates."""

    def test_ec_threshold_changed(self):
        state = ThresholdState(
            battery_available=True,
            battery_path=Path("/sys/class/power_supply/BAT0"),
            control_mode=ControlMode.EC_MSI,
            charge_percent=90,
            charge_status="Full",
            active_threshold=65,
            pending_threshold=65,
            health_percent=92,
            health_grade="Good",
            cycle_count=142,
            capacity_full_wh=52.5,
            capacity_design_wh=56.0,
            power_source="AC Adapter",
            alarm_armed=False,
            alarm_fired=False,
        )
        handler = _make_handler(state)
        handler._push_to_js({
            "event": "battery",
            "data": handler._serialize_state(state),
        })
        event = _extract_pushed_event(handler)
        data = event["data"]
        assert data["active_threshold"] == 65
        assert data["pending_threshold"] == 65


class TestProjectedEventsNotificationOnly:
    """Notification-only mode distinguishes alarm threshold."""

    def test_alarm_threshold_distinguished(self):
        state = ThresholdState(
            battery_available=True,
            battery_path=Path("/sys/class/power_supply/BAT0"),
            control_mode=ControlMode.NOTIFY_ONLY,
            charge_percent=85,
            charge_status="Charging",
            active_threshold=None,
            pending_threshold=80,
            health_percent=78,
            health_grade="Fair",
            cycle_count=310,
            capacity_full_wh=42.0,
            capacity_design_wh=56.0,
            power_source="AC Adapter",
            alarm_armed=True,
            alarm_fired=False,
        )
        handler = _make_handler(state)
        handler._push_to_js({
            "event": "battery",
            "data": handler._serialize_state(state),
        })
        event = _extract_pushed_event(handler)
        data = event["data"]
        # Notification-only: no hardware threshold
        assert data["active_threshold"] is None
        assert data["pending_threshold"] == 80
        assert data["control_mode"] == "notify"
        # Alarm state present for UI to distinguish
        assert data["alarm_armed"] is True
        assert data["alarm_fired"] is False


class TestProjectedEventsNoBattery:
    """No battery produces error-state event with all nulls."""

    def test_no_battery_all_nulls(self):
        state = ThresholdState(battery_available=False)
        handler = _make_handler(state)
        handler._push_to_js({
            "event": "battery",
            "data": handler._serialize_state(state),
        })
        event = _extract_pushed_event(handler)
        data = event["data"]
        assert data["battery_available"] is False
        assert data["charge_percent"] is None
        assert data["control_mode"] is None
        assert data["battery_identifier"] is None
        assert data["active_threshold"] is None
        assert data["cycle_count"] is None
        assert data["capacity_full_wh"] is None


class TestPollingPush:
    """Python-owned poll pushes state to JS."""

    def test_poll_tick_pushes_battery_event(self):
        state = ThresholdState(
            battery_available=True,
            battery_path=Path("/sys/class/power_supply/BAT0"),
            control_mode=ControlMode.EC_MSI,
            charge_percent=75,
            charge_status="Charging",
            active_threshold=80,
            pending_threshold=80,
        )
        handler = _make_handler(state)
        with patch.object(handler, '_build_state', return_value=state),              patch.object(handler, '_sync_from_hardware'):
            handler._poll_tick()
        event = _extract_pushed_event(handler)
        assert event["event"] == "battery"
        assert event["data"]["charge_percent"] == 75

    def test_sync_from_hardware_skipped_during_write(self):
        state = ThresholdState(
            battery_available=True,
            battery_path=Path("/sys/class/power_supply/BAT0"),
            control_mode=ControlMode.EC_MSI,
            charge_percent=75,
            active_threshold=80,
        )
        handler = _make_handler(state)
        handler._writing = True
        # Should return without error or state change
        handler._sync_from_hardware()
        assert handler._state.active_threshold == 80

    def test_sync_from_hardware_follows_ec_change(self):
        state = ThresholdState(
            battery_available=True,
            battery_path=Path("/sys/class/power_supply/BAT0"),
            control_mode=ControlMode.EC_MSI,
            charge_percent=75,
            active_threshold=80,
        )
        handler = _make_handler(state)
        with patch("threshold.battery.read_sysfs") as mock_sysfs:
            mock_sysfs.return_value = "65"
            handler._sync_from_hardware()
        assert handler._state.active_threshold == 65
        assert handler._state.pending_threshold == 65
        handler._config.set_charge_threshold.assert_called_with(65)


# ── Appearance serialization tests ─────────────────────────────────────────


class TestAppearanceSerialization:
    """Test appearance state serialization includes new fields."""

    def test_serialize_state_includes_compact_mode(self):
        state = ThresholdState(
            battery_available=True,
            battery_path=Path("/sys/class/power_supply/BAT0"),
            control_mode=ControlMode.EC_MSI,
            charge_percent=75,
            dark_mode=False,
            accent_color="orange",
            compact_mode=True,
            title_percentage=False,
        )
        handler = _make_handler(state)
        serialized = handler._serialize_state(state)
        assert serialized["compact_mode"] is True
        assert serialized["title_percentage"] is False

    def test_serialize_state_defaults(self):
        state = ThresholdState(battery_available=False)
        handler = _make_handler(state)
        serialized = handler._serialize_state(state)
        assert serialized["compact_mode"] is False
        assert serialized["title_percentage"] is True  # default in ThresholdState

    def test_serialize_appearance_with_system_theme(self):
        """Appearance uses effective_theme_scheme, not raw dark_mode."""
        state = ThresholdState(
            battery_available=False,
            dark_mode=False,
            system_theme_scheme="dark",
            accent_color="purple",
        )
        handler = _make_handler(state)
        appearance = handler._serialize_appearance(state)
        # dark_mode=False but system is dark → effective scheme is dark
        assert appearance["scheme"] == "dark"
        assert appearance["accent_color"] == "purple"

    def test_serialize_appearance_dark_mode_forces_dark(self):
        state = ThresholdState(
            battery_available=False,
            dark_mode=True,
            system_theme_scheme="light",
            accent_color="red",
        )
        handler = _make_handler(state)
        appearance = handler._serialize_appearance(state)
        assert appearance["scheme"] == "dark"
        assert appearance["accent_color"] == "red"


# ── GSettings listener tests ───────────────────────────────────────────────


class TestGSettingsListeners:
    """Test GSettings change listeners push events to JS."""

    def test_start_gsettings_listeners_connects_handlers(self):
        from threshold.carbon_shell import BridgeHandler
        config = MagicMock()
        web_view = MagicMock()
        handler = BridgeHandler.__new__(BridgeHandler)
        handler._config = config
        handler._web_view = web_view
        handler._dispatcher = CommandDispatcher(config)
        handler._state = ThresholdState(battery_available=False)
        handler._battery_path = None
        handler._writing = False
        handler._polling_source_id = None
        handler._gsettings_handler_ids = []

        handler.start_gsettings_listeners()

        # Should have connected to 7 keys (4 appearance + 3 preference)
        assert len(handler._gsettings_handler_ids) == 7
        assert config.connect.call_count == 7

    def test_stop_gsettings_listeners_clears_handlers(self):
        from threshold.carbon_shell import BridgeHandler
        handler = BridgeHandler.__new__(BridgeHandler)
        handler._gsettings_handler_ids = [1, 2, 3, 4]

        handler.stop_gsettings_listeners()

        assert handler._gsettings_handler_ids == []

    def test_on_appearance_changed_pushes_events(self):
        from threshold.carbon_shell import BridgeHandler
        config = MagicMock()
        web_view = MagicMock()
        handler = BridgeHandler.__new__(BridgeHandler)
        handler._config = config
        handler._web_view = web_view
        handler._dispatcher = CommandDispatcher(config)
        handler._state = ThresholdState(battery_available=False)
        handler._battery_path = None
        handler._writing = False
        handler._polling_source_id = None
        handler._gsettings_handler_ids = []

        with patch.object(handler, '_build_state') as mock_build:
            new_state = ThresholdState(
                battery_available=False,
                dark_mode=True,
                accent_color="blue",
                compact_mode=True,
                title_percentage=False,
            )
            mock_build.return_value = new_state
            handler._on_appearance_changed(config, "dark-mode")

        # Should have pushed appearance and battery events
        assert web_view.evaluate_javascript.call_count >= 2

    def test_on_appearance_changed_pushes_title_update(self):
        from threshold.carbon_shell import BridgeHandler
        config = MagicMock()
        web_view = MagicMock()
        handler = BridgeHandler.__new__(BridgeHandler)
        handler._config = config
        handler._web_view = web_view
        handler._dispatcher = CommandDispatcher(config)
        handler._state = ThresholdState(battery_available=False)
        handler._battery_path = None
        handler._writing = False
        handler._polling_source_id = None
        handler._gsettings_handler_ids = []

        with patch.object(handler, '_build_state') as mock_build:
            new_state = ThresholdState(
                battery_available=True,
                charge_percent=75,
                title_percentage=True,
            )
            mock_build.return_value = new_state
            handler._on_appearance_changed(config, "title-percentage")

        # Should have pushed 3 events: appearance, battery, title_update
        assert web_view.evaluate_javascript.call_count == 3
        # Verify the title_update event
        calls = web_view.evaluate_javascript.call_args_list
        last_js = calls[-1][0][0]
        start = last_js.index('window.threshold._handleMessage(') + len('window.threshold._handleMessage(')
        end = last_js.rindex(')')
        event = json.loads(json.loads(last_js[start:end]))
        assert event["event"] == "title_update"
        assert event["data"]["title_percentage"] is True
        assert event["data"]["charge_percent"] == 75


# ── Appearance event serialization tests ──────────────────────────────────


class TestAppearanceEvents:
    """Test appearance event payloads match JS fixture contracts."""

    def test_appearance_push_event_dark(self):
        state = ThresholdState(
            battery_available=False,
            dark_mode=True,
            accent_color="blue",
        )
        handler = _make_handler(state)
        handler._push_to_js({
            "event": "appearance",
            "data": handler._serialize_appearance(state),
        })
        event = _extract_pushed_event(handler)
        assert event["event"] == "appearance"
        assert event["data"]["scheme"] == "dark"
        assert event["data"]["accent_color"] == "blue"

    def test_battery_push_event_includes_appearance_fields(self):
        state = ThresholdState(
            battery_available=True,
            battery_path=Path("/sys/class/power_supply/BAT0"),
            control_mode=ControlMode.EC_MSI,
            charge_percent=75,
            dark_mode=True,
            accent_color="green",
            compact_mode=True,
            title_percentage=False,
        )
        handler = _make_handler(state)
        handler._push_to_js({
            "event": "battery",
            "data": handler._serialize_state(state),
        })
        event = _extract_pushed_event(handler)
        data = event["data"]
        assert data["dark_mode"] is True
        assert data["accent_color"] == "green"
        assert data["compact_mode"] is True
        assert data["title_percentage"] is False

    def test_title_update_event_payload(self):
        state = ThresholdState(
            battery_available=True,
            charge_percent=82,
            title_percentage=True,
        )
        handler = _make_handler(state)
        handler._push_to_js({
            "event": "title_update",
            "data": {
                "title_percentage": state.title_percentage,
                "charge_percent": state.charge_percent,
            },
        })
        event = _extract_pushed_event(handler)
        assert event["event"] == "title_update"
        assert event["data"]["title_percentage"] is True
        assert event["data"]["charge_percent"] == 82


# ── Tray integration tests ──────────────────────────────────────────────────


class TestTraySetup:
    """Test tray icon creation and lifecycle in Carbon shell."""

    def test_setup_tray_creates_icon_when_dbusmenu_available(self):
        state = ThresholdState(
            battery_available=True,
            battery_path=Path("/sys/class/power_supply/BAT0"),
            control_mode=ControlMode.EC_MSI,
            charge_percent=75,
            charge_status="Charging",
            active_threshold=80,
            pending_threshold=80,
        )
        handler = _make_handler(state)
        mock_tray = MagicMock()
        mock_tray_mod = MagicMock()
        mock_tray_mod.TrayIcon = MagicMock(return_value=mock_tray)
        mock_tray_mod.HAS_DBUSMENU = True
        with patch.dict("sys.modules", {"threshold.tray": mock_tray_mod}):
            handler._setup_tray()
        assert handler._tray is mock_tray
        mock_tray.set_state.assert_called_once()

    def test_setup_tray_noop_when_dbusmenu_unavailable(self):
        handler = _make_handler(ThresholdState(battery_available=False))
        mock_tray_mod = MagicMock()
        mock_tray_mod.HAS_DBUSMENU = False
        with patch.dict("sys.modules", {"threshold.tray": mock_tray_mod}):
            handler._setup_tray()
        assert handler._tray is None

    def test_update_tray_syncs_icon_with_state(self):
        state = ThresholdState(
            battery_available=True,
            battery_path=Path("/sys/class/power_supply/BAT0"),
            control_mode=ControlMode.EC_MSI,
            charge_percent=75,
            charge_status="Charging",
            active_threshold=80,
            pending_threshold=80,
        )
        handler = _make_handler(state)
        handler._tray = MagicMock()
        with patch("threshold.carbon_shell._battery_icon_name", return_value="battery-good-charging"):
            handler._update_tray()
        handler._tray.set_state.assert_called_once_with(
            75, "Charging", "battery-good-charging", 80
        )

    def test_update_tray_noop_without_tray(self):
        handler = _make_handler(ThresholdState(battery_available=False))
        handler._tray = None
        handler._update_tray()  # Should not raise

    def test_cleanup_tray_unregisters(self):
        handler = _make_handler(ThresholdState(battery_available=False))
        mock_tray = MagicMock()
        handler._tray = mock_tray
        handler._cleanup_tray()
        mock_tray.unregister.assert_called_once()
        assert handler._tray is None

    def test_on_tray_show_presents_window(self):
        handler = _make_handler(ThresholdState(battery_available=False))
        mock_window = MagicMock()
        handler._window = mock_window
        handler._on_tray_show()
        mock_window.present.assert_called_once()

    def test_on_tray_quit_stops_polling_and_quits(self):
        handler = _make_handler(ThresholdState(battery_available=False))
        mock_tray = MagicMock()
        handler._tray = mock_tray
        mock_window = MagicMock()
        mock_app = MagicMock()
        mock_window.get_application.return_value = mock_app
        handler._window = mock_window
        handler._polling_source_id = None  # no active polling to remove
        handler._on_tray_quit()
        mock_tray.unregister.assert_called_once()
        mock_app.quit.assert_called_once()

    def test_on_tray_threshold_applies_preset(self):
        state = ThresholdState(
            battery_available=True,
            battery_path=Path("/sys/class/power_supply/BAT0"),
            control_mode=ControlMode.EC_MSI,
            charge_percent=75,
            active_threshold=80,
        )
        handler = _make_handler(state)
        with patch.object(handler, "_build_state", return_value=state), \
             patch.object(handler._dispatcher, "dispatch", return_value=CommandResult(success=True)) as mock_dispatch, \
             patch.object(handler, "_push_to_js"):
            handler._on_tray_threshold(70)
        mock_dispatch.assert_called_once_with(
            "apply_threshold", args={"threshold": 70}, state=state
        )


# ── Close-to-tray tests ────────────────────────────────────────────────────


class TestCloseToTray:
    """Test close-to-tray behavior in Carbon shell."""

    def test_close_hides_window_when_tray_enabled(self):
        handler = _make_handler(ThresholdState(battery_available=False))
        handler._config.get_minimize_to_tray.return_value = True
        mock_tray = MagicMock()
        handler._tray = mock_tray
        mock_window = MagicMock()
        handler._window = mock_window
        result = handler.handle_close_request()
        assert result is True
        mock_window.set_visible.assert_called_once_with(False)

    def test_close_allows_destroy_when_tray_disabled(self):
        handler = _make_handler(ThresholdState(battery_available=False))
        handler._config.get_minimize_to_tray.return_value = False
        handler._tray = MagicMock()
        handler._window = MagicMock()
        result = handler.handle_close_request()
        assert result is False

    def test_close_allows_destroy_when_no_tray(self):
        handler = _make_handler(ThresholdState(battery_available=False))
        handler._config.get_minimize_to_tray.return_value = True
        handler._tray = None
        handler._window = MagicMock()
        result = handler.handle_close_request()
        assert result is False


# ── Preference sync tests ──────────────────────────────────────────────────


class TestPreferenceSync:
    """Test preference change events pushed to JS."""

    def test_preference_changed_pushes_event(self):
        state = ThresholdState(battery_available=False, show_notifications=True, minimize_to_tray=True)
        handler = _make_handler(state)
        with patch.object(handler, "_build_state", return_value=state):
            handler._on_preference_changed(None, "show-notifications")
        # Should have pushed preference + battery events
        assert handler._web_view.evaluate_javascript.call_count >= 2

    def test_preference_event_contains_key_and_values(self):
        state = ThresholdState(
            battery_available=False,
            show_notifications=False,
            minimize_to_tray=True,
        )
        handler = _make_handler(state)
        with patch.object(handler, "_build_state", return_value=state):
            handler._on_preference_changed(None, "minimize-to-tray")
        calls = handler._web_view.evaluate_javascript.call_args_list
        # First call is the preference event
        first_js = calls[0][0][0]
        start = first_js.index('window.threshold._handleMessage(') + len('window.threshold._handleMessage(')
        end = first_js.rindex(')')
        event = json.loads(json.loads(first_js[start:end]))
        assert event["event"] == "preference"
        assert event["data"]["key"] == "minimize-to-tray"
        assert event["data"]["show_notifications"] is False
        assert event["data"]["minimize_to_tray"] is True

    def test_start_gsettings_listeners_connects_preference_keys(self):
        handler = _make_handler(ThresholdState(battery_available=False))
        handler._gsettings_handler_ids = []
        handler.start_gsettings_listeners()
        # 4 appearance + 3 preference = 7
        assert len(handler._gsettings_handler_ids) == 7


# ── State serialization preference fields ──────────────────────────────────


class TestSerializedPreferences:
    """Test that _serialize_state includes preference fields."""

    def test_serialized_state_includes_preferences(self):
        state = ThresholdState(
            battery_available=True,
            battery_path=Path("/sys/class/power_supply/BAT0"),
            control_mode=ControlMode.EC_MSI,
            charge_percent=75,
            show_notifications=False,
            minimize_to_tray=True,
        )
        handler = _make_handler(state)
        serialized = handler._serialize_state(state)
        assert serialized["show_notifications"] is False
        assert serialized["minimize_to_tray"] is True

    def test_serialized_state_defaults(self):
        state = ThresholdState(battery_available=False)
        handler = _make_handler(state)
        serialized = handler._serialize_state(state)
        assert serialized["show_notifications"] is True
        assert serialized["minimize_to_tray"] is True


# ── Notification tests ─────────────────────────────────────────────────────


class TestThresholdNotifications:
    """Test that threshold commands trigger libnotify notifications."""

    def test_apply_threshold_triggers_notification(self):
        state = ThresholdState(
            battery_available=True,
            battery_path=Path("/sys/class/power_supply/BAT0"),
            control_mode=ControlMode.EC_MSI,
            charge_percent=75,
            active_threshold=80,
        )
        handler = _make_handler(state)
        with patch.object(handler, "_show_notification") as mock_notif:
            msg = MagicMock()
            msg.to_string.return_value = json.dumps({
                "id": "req-notif-1",
                "cmd": "apply_threshold",
                "args": {"threshold": 80},
            })
            with patch.object(handler._dispatcher, "_cmd_apply_threshold",
                              return_value=CommandResult(
                                  success=True,
                                  data={"threshold": 80, "method": "direct", "ec_mismatch": False}
                              )):
                handler.on_message(None, msg)
        mock_notif.assert_called_once()
        # First arg is title, second is body
        title_arg = mock_notif.call_args[0][0]
        assert "80%" in title_arg

    def test_restore_threshold_triggers_notification(self):
        state = ThresholdState(
            battery_available=True,
            battery_path=Path("/sys/class/power_supply/BAT0"),
            control_mode=ControlMode.EC_MSI,
            charge_percent=75,
            active_threshold=80,
        )
        handler = _make_handler(state)
        with patch.object(handler, "_show_notification") as mock_notif:
            msg = MagicMock()
            msg.to_string.return_value = json.dumps({
                "id": "req-notif-2",
                "cmd": "restore_threshold",
                "args": {},
            })
            with patch.object(handler._dispatcher, "_cmd_restore_threshold",
                              return_value=CommandResult(
                                  success=True,
                                  data={"threshold": 100, "method": "direct", "ec_mismatch": False}
                              )):
                handler.on_message(None, msg)
        mock_notif.assert_called_once()
        # First arg is title, second is body
        title_arg = mock_notif.call_args[0][0]
        assert "100%" in title_arg

    def test_alarm_threshold_triggers_notification(self):
        state = ThresholdState(
            battery_available=True,
            battery_path=Path("/sys/class/power_supply/BAT0"),
            control_mode=ControlMode.NOTIFY_ONLY,
            charge_percent=85,
            active_threshold=None,
        )
        handler = _make_handler(state)
        with patch.object(handler, "_show_notification") as mock_notif:
            msg = MagicMock()
            msg.to_string.return_value = json.dumps({
                "id": "req-notif-3",
                "cmd": "apply_threshold",
                "args": {"threshold": 80},
            })
            with patch.object(handler._dispatcher, "_cmd_apply_threshold",
                              return_value=CommandResult(
                                  success=True,
                                  data={"threshold": 80, "method": "alarm"}
                              )):
                handler.on_message(None, msg)
        mock_notif.assert_called_once()
        assert handler._alarm_armed is True
        assert handler._alarm_fired is False

    def test_notification_suppressed_when_disabled(self):
        state = ThresholdState(
            battery_available=True,
            battery_path=Path("/sys/class/power_supply/BAT0"),
            control_mode=ControlMode.EC_MSI,
            charge_percent=75,
            active_threshold=80,
            show_notifications=False,
        )
        handler = _make_handler(state)
        handler._config.get_show_notifications.return_value = False
        msg = MagicMock()
        msg.to_string.return_value = json.dumps({
            "id": "req-notif-4",
            "cmd": "apply_threshold",
            "args": {"threshold": 80},
        })
        with patch.object(handler._dispatcher, "_cmd_apply_threshold",
                          return_value=CommandResult(
                              success=True,
                              data={"threshold": 80, "method": "direct", "ec_mismatch": False}
                          )):
            handler.on_message(None, msg)
        # _show_notification was called but returned early (config check)
        handler._config.get_show_notifications.assert_called()


# ── Alarm evaluation tests ─────────────────────────────────────────────────


class TestAlarmEvaluation:
    """Test notification-only alarm logic in Carbon shell."""

    def test_alarm_fires_when_threshold_reached(self):
        state = ThresholdState(
            battery_available=True,
            battery_path=Path("/sys/class/power_supply/BAT0"),
            control_mode=ControlMode.NOTIFY_ONLY,
            charge_percent=80,
            pending_threshold=80,
            active_threshold=None,
        )
        handler = _make_handler(state)
        handler._alarm_armed = True
        handler._alarm_fired = False
        with patch("threshold.battery.evaluate_alarm", return_value=True),              patch("threshold.battery.read_sysfs", return_value="Charging"),              patch.object(handler, "_show_notification") as mock_notif:
            handler._evaluate_alarm()
        assert handler._alarm_fired is True
        mock_notif.assert_called_once()
        assert "80%" in mock_notif.call_args[0][1]

    def test_alarm_rearms_on_discharge(self):
        state = ThresholdState(
            battery_available=True,
            battery_path=Path("/sys/class/power_supply/BAT0"),
            control_mode=ControlMode.NOTIFY_ONLY,
            charge_percent=60,
            pending_threshold=80,
        )
        handler = _make_handler(state)
        handler._alarm_armed = True
        handler._alarm_fired = True
        with patch("threshold.battery.read_sysfs", return_value="Discharging"):
            handler._evaluate_alarm()
        assert handler._alarm_fired is False

    def test_alarm_skipped_when_not_notify_only(self):
        state = ThresholdState(
            battery_available=True,
            battery_path=Path("/sys/class/power_supply/BAT0"),
            control_mode=ControlMode.EC_MSI,
            charge_percent=75,
            active_threshold=80,
        )
        handler = _make_handler(state)
        handler._alarm_armed = True
        handler._evaluate_alarm()  # Should return early, no error

    def test_alarm_skipped_when_not_armed(self):
        state = ThresholdState(
            battery_available=True,
            battery_path=Path("/sys/class/power_supply/BAT0"),
            control_mode=ControlMode.NOTIFY_ONLY,
            charge_percent=80,
            pending_threshold=80,
        )
        handler = _make_handler(state)
        handler._alarm_armed = False
        handler._evaluate_alarm()  # Should return early

    def test_alarm_skipped_when_no_battery_path(self):
        state = ThresholdState(battery_available=False)
        handler = _make_handler(state)
        handler._alarm_armed = True
        handler._evaluate_alarm()  # Should return early

