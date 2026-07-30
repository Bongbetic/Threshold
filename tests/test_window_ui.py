"""Regression: Blueprint template children must expose XML object IDs."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WINDOW_UI = ROOT / "data" / "ui" / "window.ui"

REQUIRED_IDS = (
    "current_charge_label",
    "current_status_label",
    "active_threshold_label",
    "battery_name_label",
    "charge_scale",
    "charge_value_label",
    "apply_button",
    "restore_button",
    "dark_mode_switch",
    "launch_switch",
    "live_dot",
    "status_bar",
)


def test_window_ui_exposes_template_child_ids():
    assert WINDOW_UI.is_file()
    text = WINDOW_UI.read_text(encoding="utf-8")
    for widget_id in REQUIRED_IDS:
        assert f'id="{widget_id}"' in text, f'missing id="{widget_id}" in {WINDOW_UI}'
        # Gtk.Widget "name" property is not a Template.Child binding handle.
        assert (
            f'<property name="name">{widget_id}</property>' not in text
        ), f'id "{widget_id}" incorrectly emitted as name property'
