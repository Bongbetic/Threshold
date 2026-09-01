
"""Adapter: builds ThresholdState from sysfs readings and Config."""

import os
from pathlib import Path
from typing import Optional

from threshold.battery import (
    ControlMode,
    battery_health_percent,
    detect_control_mode,
    find_battery_path,
    health_grade,
    read_capacity_wh,
    read_charge_percent,
    read_cycle_count,
    read_power_source,
    read_sysfs,
)
from threshold.config import Config
from threshold.state import ThresholdState


def detect_system_theme_scheme() -> str:
    """Detect the system color scheme from GNOME/Adwaita settings.

    Returns 'dark' or 'light'. Falls back to 'light' on unknown DEs.
    """
    try:
        import gi
        gi.require_version('Gio', '2.0')
        from gi.repository import Gio

        settings = Gio.Settings.new('org.gnome.desktop.interface')
        scheme = settings.get_string('color-scheme')
        if scheme in ('prefer-dark', 'default'):
            # 'default' on GNOME means dark variant is available;
            # Adwaita uses 'default' to mean follow-dark when the
            # GTK theme is Adwaita-dark.  Read the GTK theme name to
            # disambiguate.
            if scheme == 'prefer-dark':
                return 'dark'
            # 'default' — check the GTK theme for dark variant
            theme = settings.get_string('gtk-theme')
            if theme and 'dark' in theme.lower():
                return 'dark'
        return 'light'
    except Exception:
        # Non-GNOME or missing GSettings — fall back
        return 'light'


def build_state(
    config: Config,
    battery_path: Optional[Path] = None,
    pending_threshold: Optional[int] = None,
    alarm_armed: bool = False,
    alarm_fired: bool = False,
) -> ThresholdState:
    """Build a ThresholdState snapshot from sysfs and config.
    
    Args:
        config: GSettings wrapper for preferences.
        battery_path: Override for sysfs path (None = discover).
        pending_threshold: User's pending threshold value.
        alarm_armed: Whether alarm is armed (notification-only).
        alarm_fired: Whether alarm has fired (notification-only).
    
    Returns:
        Complete ThresholdState snapshot with domain values.
    """
    if battery_path is None:
        battery_path = find_battery_path()
    
    control_mode = detect_control_mode(battery_path)
    
    # Battery telemetry
    charge_percent = read_charge_percent(battery_path) if battery_path else None
    charge_status = read_sysfs(battery_path / "status") if battery_path else None
    power_source = read_power_source() if battery_path else None
    
    # Threshold
    active_threshold = None
    if battery_path:
        raw = read_sysfs(battery_path / "charge_control_end_threshold")
        if raw is not None:
            try:
                active_threshold = int(raw)
            except ValueError:
                pass
    
    # Diagnostics
    health_pct = battery_health_percent(battery_path) if battery_path else None
    cycles = read_cycle_count(battery_path) if battery_path else None
    capacity = read_capacity_wh(battery_path) if battery_path else None
    
    full_wh = capacity[0] if capacity else None
    design_wh = capacity[1] if capacity else None
    
    system_theme = detect_system_theme_scheme()

    return ThresholdState(
        battery_available=battery_path is not None,
        battery_path=battery_path,
        control_mode=control_mode,
        charge_percent=charge_percent,
        charge_status=charge_status,
        power_source=power_source,
        active_threshold=active_threshold,
        pending_threshold=pending_threshold,
        health_percent=health_pct,
        health_grade=health_grade(health_pct),
        cycle_count=cycles,
        capacity_full_wh=full_wh,
        capacity_design_wh=design_wh,
        dark_mode=config.get_dark_mode(),
        accent_color=config.get_accent_color(),
        system_theme_scheme=system_theme,
        compact_mode=config.get_compact_mode(),
        title_percentage=config.get_title_percentage(),
        show_notifications=config.get_show_notifications(),
        minimize_to_tray=config.get_minimize_to_tray(),
        window_width=config.get_window_width(),
        window_height=config.get_window_height(),
        window_maximized=config.get_maximized(),
        alarm_armed=alarm_armed,
        alarm_fired=alarm_fired,
    )
