"""Battery sysfs interaction — core domain logic."""

import subprocess
from pathlib import Path


SYSFS_BASES = [
    "/sys/class/power_supply/BAT0",
    "/sys/class/power_supply/BAT1",
]


def find_battery_path() -> Path | None:
    """Return the first battery sysfs path that has a charge_control_end_threshold file."""
    for base in SYSFS_BASES:
        p = Path(base)
        if (p / "charge_control_end_threshold").exists():
            return p
    return None


def read_sysfs(path: Path) -> str | None:
    """Read a sysfs file, return stripped content or None on any error."""
    try:
        return path.read_text().strip()
    except Exception:
        return None


def write_threshold(bat_path: Path, value: int) -> tuple[bool, str]:
    """
    Write threshold value to sysfs.

    Tries direct write first (works if udev rule is in place),
    then falls back to pkexec (PolicyKit), then sudo tee.
    Returns ``(success, method_or_error)``.
    """
    threshold_file = str(bat_path / "charge_control_end_threshold")

    # Try direct write first (udev rule grants permission)
    try:
        (bat_path / "charge_control_end_threshold").write_text(str(value))
        return True, "direct"
    except PermissionError:
        pass

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
        try:
            result = subprocess.run(
                ["sudo", "tee", threshold_file],
                input=str(value),
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                return True, "sudo"
            return False, result.stderr.strip() or "Permission denied – see INSTALL.md Step 4"
        except Exception as e:
            return False, str(e)
    except subprocess.TimeoutExpired:
        return False, "Auth dialog timed out"
    except Exception as e:
        return False, str(e)
