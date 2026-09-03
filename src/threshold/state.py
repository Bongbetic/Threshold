
"""Presentation-neutral Threshold state boundary.

Domain values only — no GTK widgets, no localized strings.
"""

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Optional

from threshold.battery import ControlMode
from threshold.ec_state import ECSetupState, ECSetupReason, ECMaintenanceStatus


@dataclass(frozen=True)
class Capabilities:
    """What the current control mode can do."""
    can_write_threshold: bool = False
    can_restore: bool = False
    supports_alarm: bool = False
    write_method: Optional[str] = None


def detect_capabilities(mode: Optional[ControlMode]) -> Capabilities:
    """Derive capabilities from the detected control mode."""
    if mode is None:
        return Capabilities()
    
    if mode == ControlMode.EC_MSI:
        return Capabilities(
            can_write_threshold=True,
            can_restore=True,
            supports_alarm=False,
            write_method="direct",
        )
    if mode == ControlMode.SYSFS_VENDOR:
        return Capabilities(
            can_write_threshold=True,
            can_restore=True,
            supports_alarm=False,
            write_method="direct",
        )
    # NOTIFY_ONLY
    return Capabilities(
        can_write_threshold=False,
        can_restore=False,
        supports_alarm=True,
    )


@dataclass(frozen=True)
class ThresholdState:
    """Complete presentation-neutral snapshot of Threshold state.
    
    All domain values — no GTK widgets or localized strings.
    """
    # ── Battery availability ──────────────────────────────────────────────
    battery_available: bool = False
    battery_path: Optional[Path] = None
    control_mode: Optional[ControlMode] = None
    
    # ── Battery telemetry ─────────────────────────────────────────────────
    charge_percent: Optional[int] = None
    charge_status: Optional[str] = None
    power_source: Optional[str] = None
    
    # ── Threshold ─────────────────────────────────────────────────────────
    active_threshold: Optional[int] = None
    pending_threshold: Optional[int] = None
    # Machine-wide charge threshold (latest user-confirmed value wins;
    # persists across pending/unavailable EC setup states).
    charge_threshold: Optional[int] = None

    # ── EC setup / maintenance (independent of control mode) ──────────────
    ec_setup_state: Optional[ECSetupState] = None
    ec_setup_reason: Optional[ECSetupReason] = None
    ec_maintenance_status: ECMaintenanceStatus = ECMaintenanceStatus.OK
    # Actions the UI may offer for current EC state (never automatic).
    ec_recovery_actions: tuple = ()
    
    # ── Diagnostics ───────────────────────────────────────────────────────
    health_percent: Optional[int] = None
    health_grade: Optional[str] = None
    cycle_count: Optional[int] = None
    capacity_full_wh: Optional[float] = None
    capacity_design_wh: Optional[float] = None
    
    # ── Preferences ───────────────────────────────────────────────────────
    dark_mode: bool = False
    accent_color: str = "orange"
    compact_mode: bool = False
    title_percentage: bool = True
    show_notifications: bool = True
    minimize_to_tray: bool = True
    
    # ── Window state ──────────────────────────────────────────────────────
    window_width: int = 800
    window_height: int = 600
    window_maximized: bool = False
    
    # ── Alarm state (notification-only mode) ──────────────────────────────
    alarm_armed: bool = False
    alarm_fired: bool = False
    
    # ── System theme (read by adapter, not authoritative) ─────────────────
    system_theme_scheme: str = "light"

    # ── Derived values ────────────────────────────────────────────────────
    @property
    def effective_theme_scheme(self) -> str:
        """Effective theme scheme: dark_mode forces dark, otherwise follows system."""
        if self.dark_mode:
            return "dark"
        return self.system_theme_scheme
    
    @property
    def capabilities(self) -> Capabilities:
        """Capabilities derived from control mode."""
        return detect_capabilities(self.control_mode)
    
    def with_updates(self, **kwargs) -> "ThresholdState":
        """Return new state with specified fields updated (immutable)."""
        return replace(self, **kwargs)
