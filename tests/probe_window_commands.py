#!/usr/bin/env python3
"""Real-shell probe: exercises a web-to-native window command.

This script simulates the bridge handler receiving a window command
and dispatching it to the window. It verifies that the command flows
through the dispatcher correctly.
"""

import sys
from unittest.mock import MagicMock

# Add src to path for imports
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parents[1] / 'src'))

from threshold.commands import CommandDispatcher, ErrorCode
from threshold.config import Config


def test_window_command_dispatch():
    """Verify that window commands flow through the dispatcher."""
    # Create a mock config and window
    config = MagicMock()
    window = MagicMock()
    window.is_maximized.return_value = False

    # Create dispatcher and set window
    dispatcher = CommandDispatcher(config)
    dispatcher.set_window(window)

    # Test minimize command
    result = dispatcher.dispatch("minimize", {}, None)
    assert result.success is True, f"minimize failed: {result.message}"
    assert result.data.get("minimized") is True
    window.minimize.assert_called_once()
    print("✓ minimize command dispatched successfully")

    # Reset mock
    window.reset_mock()

    # Test toggle_maximize command
    result = dispatcher.dispatch("toggle_maximize", {}, None)
    assert result.success is True, f"toggle_maximize failed: {result.message}"
    assert result.data.get("maximized") is True
    window.maximize.assert_called_once()
    print("✓ toggle_maximize command dispatched successfully")

    # Reset mock
    window.reset_mock()

    # Test close command
    result = dispatcher.dispatch("close", {}, None)
    assert result.success is True, f"close failed: {result.message}"
    assert result.data.get("closed") is True
    window.close.assert_called_once()
    print("✓ close command dispatched successfully")

    # Reset mock
    window.reset_mock()

    # Test begin_drag command
    result = dispatcher.dispatch("begin_drag", {}, None)
    assert result.success is True, f"begin_drag failed: {result.message}"
    assert result.data.get("dragging") is True
    window.begin_move_drag.assert_called_once_with(1, -1, -1, -1)
    print("✓ begin_drag command dispatched successfully")

    print("\nAll window command dispatches passed!")


if __name__ == "__main__":
    try:
        test_window_command_dispatch()
    except Exception as e:
        print(f"✗ Probe failed: {e}", file=sys.stderr)
        sys.exit(1)
