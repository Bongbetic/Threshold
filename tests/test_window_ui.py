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
    "mode_label",
    "power_source_label",
    "health_label",
    "last_changed_label",
    "charge_scale",
    "charge_value_label",
    "apply_button",
    "restore_button",
    "dark_mode_switch",
    "launch_switch",
    "tray_switch",
    "notifications_switch",
    "compact_switch",
    "title_percentage_switch",
    "cycle_count_label",
    "design_capacity_label",
    "full_capacity_label",
    "health_pct_label",
    "preset_60",
    "preset_70",
    "preset_80",
    "preset_90",
    "preset_100",
    "swatch_orange",
    "swatch_blue",
    "swatch_green",
    "swatch_purple",
    "swatch_red",
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


def test_window_ui_uses_tight_non_resizable_canvas():
    text = WINDOW_UI.read_text(encoding="utf-8")
    assert '<property name="default-width">760</property>' in text
    assert '<property name="default-height">365</property>' in text
    assert '<property name="width-request">760</property>' in text
    assert '<property name="height-request">365</property>' in text
    assert '<property name="resizable">false</property>' in text
    assert "ScrolledWindow" not in text
