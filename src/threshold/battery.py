"""Battery sysfs interaction — core domain logic."""

from enum import Enum
import subprocess
from pathlib import Path


THRESHOLD_MIN = 20
THRESHOLD_MAX = 100
THRESHOLD_PRESETS = (60, 70, 80, 90, 100)

MSI_EC_PLATFORM = Path("/sys/devices/platform/msi-ec")


class ControlMode(Enum):
    """How the application communicates charge thresholds to the battery."""

    EC_MSI = "msi-ec"
    SYSFS_VENDOR = "sysfs"
    NOTIFY_ONLY = "notify"


def _enumerate_power_supplies():
    """Yield each subdirectory under /sys/class/power_supply/."""
    psy_dir = Path("/sys/class/power_supply")
    if not psy_dir.is_dir():
        return
    for entry in sorted(psy_dir.iterdir()):
        if entry.is_dir():
            yield entry


def find_battery_path() -> Path | None:
    """Return the first battery sysfs path with ``type == Battery``.

    Enumerates ``/sys/class/power_supply/`` dynamically.  First qualifying
    entry wins.  Does not require ``charge_control_end_threshold`` so the
    battery can still be used for capacity/status reads in notification-only
    mode.
    """
    for psy_path in _enumerate_power_supplies():
        type_val = read_sysfs(psy_path / "type")
        if type_val == "Battery":
            return psy_path
    return None


def msi_ec_loaded() -> bool:
    """Return True if the msi-ec platform device is present."""
    return MSI_EC_PLATFORM.is_dir()


def detect_control_mode(bat_path: Path | None) -> ControlMode | None:
    """Detect which control mode applies for the given battery.

    Returns None when no battery path is provided.
    """
    if bat_path is None:
        return None

    has_threshold = (bat_path / "charge_control_end_threshold").exists()

    if has_threshold and msi_ec_loaded():
        return ControlMode.EC_MSI
    if has_threshold:
        return ControlMode.SYSFS_VENDOR
    return ControlMode.NOTIFY_ONLY


def evaluate_alarm(pct: int | None, status: str | None,
                   threshold: int, fired: bool) -> bool:
    """Decide whether the threshold-reached alarm should fire.

    Fires once when charging/full and the charge percentage meets or
    exceeds the threshold.  Returns False if the alarm has already
    fired, the threshold is 100 (disarmed), or no percentage/status
    is available.
    """
    if threshold >= THRESHOLD_MAX or pct is None or status is None:
        return False
    if fired:
        return False
    if status not in ("Charging", "Full"):
        return False
    return pct >= threshold


def read_sysfs(path: Path) -> str | None:
    """Read a sysfs file, return stripped content or None on any error."""
    try:
        return path.read_text().strip()
    except Exception:
        return None


def read_charge_percent(bat_path: Path) -> int | None:
    """Return state of charge as an integer percent (0–100), or None.

    Prefers kernel ``capacity``, then ``charge_now / charge_full``,
    then ``charge_now / charge_full_design``.
    """
    capacity = read_sysfs(bat_path / "capacity")
    if capacity is not None:
        try:
            return max(0, min(100, int(float(capacity))))
        except ValueError:
            pass

    charge_now = read_sysfs(bat_path / "charge_now")
    if charge_now is None:
        return None

    for full_name in ("charge_full", "charge_full_design"):
        charge_full = read_sysfs(bat_path / full_name)
        if charge_full is None:
            continue
        try:
            full = float(charge_full)
            if full <= 0:
                continue
            return max(0, min(100, int(float(charge_now) / full * 100)))
        except ValueError:
            continue
    return None


def write_threshold(bat_path: Path, value: int) -> tuple[bool, str]:
    """
    Write threshold value to sysfs.

    Tries direct write first (works if udev rule is in place),
    then falls back to pkexec (PolicyKit).
    Returns ``(success, method_or_error)``.
    """
    if not THRESHOLD_MIN <= value <= THRESHOLD_MAX:
        return False, f"Threshold must be {THRESHOLD_MIN}–{THRESHOLD_MAX}"

    threshold_file = str(bat_path / "charge_control_end_threshold")

    # Try direct write first (udev rule grants permission)
    try:
        (bat_path / "charge_control_end_threshold").write_text(str(value))
        return True, "direct"
    except PermissionError:
        pass
    except OSError as e:
        return False, str(e)

    # Fallback: pkexec (PolicyKit – shows a native auth dialog, no terminal)
    try:
        result = subprocess.run(
            ["pkexec", "tee", threshold_file],
            input=str(value),
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return True, "pkexec"
        return False, result.stderr.strip() or "pkexec failed"
    except FileNotFoundError:
        return (
            False,
            "pkexec not found – install policykit-1, or join the "
            "plugdev group (see INSTALL.md)",
        )
    except subprocess.TimeoutExpired:
        return False, "Auth dialog timed out"
    except Exception as e:
        return False, str(e)
