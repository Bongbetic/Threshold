"""Tests for window command dispatch in the Carbon shell.

Verifies that the CommandDispatcher correctly handles window commands
(minimize, maximize, restore, toggle_maximize, close, begin_drag)
and returns appropriate results.
"""

from unittest.mock import MagicMock, patch

import pytest

from threshold.commands import CommandDispatcher, ErrorCode
from threshold.state import ThresholdState


@pytest.fixture
def mock_config():
    """Create a mock Config object."""
    config = MagicMock()
    config.get_dark_mode.return_value = False
    config.get_accent_color.return_value = "orange"
    config.get_compact_mode.return_value = False
    config.get_title_percentage.return_value = True
    config.get_show_notifications.return_value = True
    config.get_minimize_to_tray.return_value = True
    config.get_window_width.return_value = 1180
    config.get_window_height.return_value = 860
    config.get_maximized.return_value = False
    return config


@pytest.fixture
def dispatcher(mock_config):
    """Create a CommandDispatcher with mock config."""
    return CommandDispatcher(mock_config)


@pytest.fixture
def mock_window():
    """Create a mock GTK window."""
    window = MagicMock()
    window.is_maximized.return_value = False
    return window


@pytest.fixture
def state_with_battery():
    """Create a ThresholdState with battery available."""
    return ThresholdState(
        battery_available=True,
        charge_percent=75,
        charge_status="Charging",
        active_threshold=80,
        control_mode=None,
    )


class TestWindowCommands:
    """Test window commands in CommandDispatcher."""

    def test_minimize_without_window_returns_error(self, dispatcher):
        """Minimize command without window reference returns error."""
        result = dispatcher.dispatch("minimize", {}, None)
        assert result.success is False
        assert result.error_code == ErrorCode.WINDOW_NOT_AVAILABLE
        assert "Window reference not set" in result.message

    def test_minimize_with_window_succeeds(self, dispatcher, mock_window):
        """Minimize command with window reference succeeds."""
        dispatcher.set_window(mock_window)
        result = dispatcher.dispatch("minimize", {}, None)
        assert result.success is True
        assert result.data.get("minimized") is True
        mock_window.minimize.assert_called_once()

    def test_maximize_without_window_returns_error(self, dispatcher):
        """Maximize command without window reference returns error."""
        result = dispatcher.dispatch("maximize", {}, None)
        assert result.success is False
        assert result.error_code == ErrorCode.WINDOW_NOT_AVAILABLE

    def test_maximize_with_window_succeeds(self, dispatcher, mock_window):
        """Maximize command with window reference succeeds."""
        dispatcher.set_window(mock_window)
        result = dispatcher.dispatch("maximize", {}, None)
        assert result.success is True
        assert result.data.get("maximized") is True
        mock_window.maximize.assert_called_once()

    def test_restore_without_window_returns_error(self, dispatcher):
        """Restore command without window reference returns error."""
        result = dispatcher.dispatch("restore", {}, None)
        assert result.success is False
        assert result.error_code == ErrorCode.WINDOW_NOT_AVAILABLE

    def test_restore_with_window_succeeds(self, dispatcher, mock_window):
        """Restore command with window reference succeeds."""
        dispatcher.set_window(mock_window)
        result = dispatcher.dispatch("restore", {}, None)
        assert result.success is True
        assert result.data.get("maximized") is False
        mock_window.unmaximize.assert_called_once()

    def test_toggle_maximize_without_window_returns_error(self, dispatcher):
        """Toggle maximize command without window reference returns error."""
        result = dispatcher.dispatch("toggle_maximize", {}, None)
        assert result.success is False
        assert result.error_code == ErrorCode.WINDOW_NOT_AVAILABLE

    def test_toggle_maximize_when_not_maximized_succeeds(self, dispatcher, mock_window):
        """Toggle maximize when not maximized should maximize."""
        mock_window.is_maximized.return_value = False
        dispatcher.set_window(mock_window)
        result = dispatcher.dispatch("toggle_maximize", {}, None)
        assert result.success is True
        assert result.data.get("maximized") is True
        mock_window.maximize.assert_called_once()
        mock_window.unmaximize.assert_not_called()

    def test_toggle_maximize_when_maximized_succeeds(self, dispatcher, mock_window):
        """Toggle maximize when maximized should restore."""
        mock_window.is_maximized.return_value = True
        dispatcher.set_window(mock_window)
        result = dispatcher.dispatch("toggle_maximize", {}, None)
        assert result.success is True
        assert result.data.get("maximized") is False
        mock_window.unmaximize.assert_called_once()
        mock_window.maximize.assert_not_called()

    def test_close_without_window_returns_error(self, dispatcher):
        """Close command without window reference returns error."""
        result = dispatcher.dispatch("close", {}, None)
        assert result.success is False
        assert result.error_code == ErrorCode.WINDOW_NOT_AVAILABLE

    def test_close_with_window_succeeds(self, dispatcher, mock_window):
        """Close command with window reference succeeds."""
        dispatcher.set_window(mock_window)
        result = dispatcher.dispatch("close", {}, None)
        assert result.success is True
        assert result.data.get("closed") is True
        mock_window.close.assert_called_once()

    def test_begin_drag_without_window_returns_error(self, dispatcher):
        """Begin drag command without window reference returns error."""
        result = dispatcher.dispatch("begin_drag", {}, None)
        assert result.success is False
        assert result.error_code == ErrorCode.WINDOW_NOT_AVAILABLE

    def test_begin_drag_with_window_succeeds(self, dispatcher, mock_window):
        """Begin drag command with window reference succeeds."""
        dispatcher.set_window(mock_window)
        result = dispatcher.dispatch("begin_drag", {}, None)
        assert result.success is True
        assert result.data.get("dragging") is True
        mock_window.begin_move_drag.assert_called_once_with(1, -1, -1, -1)

    def test_set_window_sets_reference(self, dispatcher, mock_window):
        """set_window sets the window reference."""
        dispatcher.set_window(mock_window)
        assert dispatcher._window is mock_window

    def test_window_commands_after_set_window(self, mock_config, mock_window):
        """Window commands work after setting window reference."""
        dispatcher = CommandDispatcher(mock_config)
        dispatcher.set_window(mock_window)

        # Test minimize
        result = dispatcher.dispatch("minimize", {}, None)
        assert result.success is True

        # Test maximize
        result = dispatcher.dispatch("maximize", {}, None)
        assert result.success is True

        # Test restore
        result = dispatcher.dispatch("restore", {}, None)
        assert result.success is True

        # Test toggle_maximize
        result = dispatcher.dispatch("toggle_maximize", {}, None)
        assert result.success is True

        # Test close
        result = dispatcher.dispatch("close", {}, None)
        assert result.success is True

        # Test begin_drag
        result = dispatcher.dispatch("begin_drag", {}, None)
        assert result.success is True


class TestWindowCommandErrorCodes:
    """Test error codes for window commands."""

    def test_window_not_available_error_code(self):
        """Verify WINDOW_NOT_AVAILABLE error code exists."""
        assert hasattr(ErrorCode, "WINDOW_NOT_AVAILABLE")
        assert ErrorCode.WINDOW_NOT_AVAILABLE == "window_not_available"

    def test_window_commands_return_correct_error_code(self, dispatcher):
        """All window commands return WINDOW_NOT_AVAILABLE when window is not set."""
        commands = ["minimize", "maximize", "restore", "toggle_maximize", "close", "begin_drag"]
        for cmd in commands:
            result = dispatcher.dispatch(cmd, {}, None)
            assert result.success is False
            assert result.error_code == ErrorCode.WINDOW_NOT_AVAILABLE
