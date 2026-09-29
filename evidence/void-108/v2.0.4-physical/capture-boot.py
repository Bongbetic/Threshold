#!/usr/bin/env python3
"""Capture a read-only, candidate-bound reboot comparison on the Void laptop."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import re
import subprocess
import sys
import time


CANDIDATE = {
    "version": "2.0.4",
    "package": "threshold-2.0.4_1",
    "asset": "threshold-2.0.4_1.x86_64.xbps",
    "sha256": "62d55b0b7814472fdf2effb3efbe2c85eb1f90278b23777941e187af01af74f6",
    "source_revision": "3682e414b40918ff7c1a8071ae26830e1dd858c4",
}
STATE_DIR = Path("/var/lib/threshold/ec")
SERVICE = "/var/service/threshold-boot-reconcile"
DEFAULT_DIR = Path(__file__).resolve().parent


def read(path):
    try:
        return Path(path).read_text().strip()
    except OSError:
        return None


def run(*args):
    try:
        return subprocess.run(args, check=False, capture_output=True, text=True)
    except OSError:
        return None


def key_values(text):
    result = {}
    for line in (text or "").splitlines():
        key, separator, value = line.partition("=")
        if separator:
            result[key] = value
    return result


def service_running():
    result = run("sv", "status", SERVICE)
    if result is None or result.returncode != 0:
        result = run("sudo", "-n", "sv", "status", SERVICE)
    return bool(
        result
        and result.returncode == 0
        and result.stdout.startswith("run:")
    )


def secure_boot_enabled():
    paths = sorted(Path("/sys/firmware/efi/efivars").glob("SecureBoot-*"))
    for path in paths:
        try:
            data = path.read_bytes()
        except OSError:
            continue
        if len(data) >= 5 and data[4] in (0, 1):
            return bool(data[4])
    return None


def wait_for_reconciliation(before, timeout_seconds=40):
    log_path = STATE_DIR / "kernels" / f"{before.get('kernel', '')}.log"
    prior_events = before.get("reconciliation_events", [])
    start = time.monotonic()
    while True:
        try:
            events = [
                line
                for line in log_path.read_text().splitlines()
                if "reconciliation=" in line
            ]
        except OSError:
            events = []
        if events[: len(prior_events)] == prior_events and len(events) > len(prior_events):
            return round(time.monotonic() - start, 1)
        elapsed = time.monotonic() - start
        if elapsed >= timeout_seconds:
            return round(elapsed, 1)
        time.sleep(min(0.5, timeout_seconds - elapsed))


def capture(phase):
    boot_id = read("/proc/sys/kernel/random/boot_id") or ""
    kernel = platform.release()
    os_release = platform.freedesktop_os_release()
    dmi_vendor = read("/sys/class/dmi/id/sys_vendor")
    dmi_product = read("/sys/class/dmi/id/product_name")
    manufacturer = "MSI" if dmi_vendor and "Micro-Star" in dmi_vendor else dmi_vendor
    state = key_values(read(STATE_DIR / "state"))
    package = run("xbps-query", "-p", "pkgver", "threshold")
    module_names = {
        line.split(maxsplit=1)[0]
        for line in (read("/proc/modules") or "").splitlines()
        if line.split()
    }
    module_path = run("modinfo", "-n", "msi_ec")
    active_thresholds = []
    for path in sorted(Path("/sys/class/power_supply").glob("BAT*/charge_control_end_threshold")):
        value = read(path)
        if value is not None:
            active_thresholds.append({"battery": path.parent.name, "value": value})

    policy = read(STATE_DIR / "charge-threshold")
    session_preference = run("gsettings", "get", "com.bongbetic.threshold", "charge-threshold")
    session_preference_value = (
        session_preference.stdout.strip()
        if session_preference and session_preference.returncode == 0
        else None
    )
    if session_preference_value and not re.fullmatch(r"\d+", session_preference_value):
        session_preference_value = None
    lifecycle = Path("/usr/bin/threshold-ec-lifecycle")
    lifecycle_text = read(lifecycle) or ""
    timeout_match = re.search(r"^RECONCILE_TIMEOUT=(\d+)$", lifecycle_text, re.MULTILINE)
    timeout_seconds = int(timeout_match.group(1)) if timeout_match else None
    log_path = STATE_DIR / "kernels" / f"{kernel}.log"
    try:
        kernel_log = log_path.read_text().splitlines()
    except OSError:
        kernel_log = []
    reconciliation_events = [line for line in kernel_log if "reconciliation=" in line]
    package_version = package.stdout.strip() if package and package.returncode == 0 else None
    boot_hash = hashlib.sha256(boot_id.encode()).hexdigest() if boot_id else None
    lifecycle_boot = state.get("boot_id")
    service_enabled = Path(SERVICE).is_symlink()
    boot_time = None
    for line in (read("/proc/stat") or "").splitlines():
        if line.startswith("btime "):
            try:
                boot_time = int(line.split()[1])
            except (IndexError, ValueError):
                pass
            break
    marker = STATE_DIR / "kernels" / f"{kernel}.known-good"
    try:
        marker_mtime = marker.stat().st_mtime
    except OSError:
        marker_mtime = None

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z"),
        "phase": phase,
        "candidate": CANDIDATE,
        "physical_machine": " ".join(value for value in (manufacturer, dmi_product) if value),
        "os": os_release.get("PRETTY_NAME", "unknown"),
        "kernel": kernel,
        "boot_identity_sha256": boot_hash,
        "installed_package": package_version,
        "installed_package_matches_candidate_version": package_version == CANDIDATE["package"],
        "machine_policy": policy,
        "session_preference_threshold": session_preference_value,
        "session_preference_matches_policy": bool(policy)
        and session_preference_value == policy,
        "active_thresholds": active_thresholds,
        "active_thresholds_match_policy": bool(policy) and bool(active_thresholds) and all(
            battery["value"] == policy for battery in active_thresholds
        ),
        "module_loaded": "msi_ec" in module_names,
        "module_path": module_path.stdout.strip() if module_path and module_path.returncode == 0 else None,
        "reconciliation_service": {
            "name": "threshold-boot-reconcile",
            "enabled": service_enabled,
            "running": service_running(),
            "bounded_timeout_seconds": timeout_seconds,
            "bounded": timeout_seconds is not None and 'timeout "$RECONCILE_TIMEOUT"' in lifecycle_text,
        },
        "lifecycle_state": {
            "setup_state": state.get("setup_state"),
            "kernel": state.get("kernel"),
            "belongs_to_current_boot": bool(boot_id) and lifecycle_boot == boot_id,
        },
        "known_good_marker": marker_mtime is not None,
        "known_good_marker_updated_this_boot": marker_mtime is not None
        and boot_time is not None
        and marker_mtime >= boot_time,
        "known_good_marker_timestamp": datetime.fromtimestamp(marker_mtime, timezone.utc).isoformat(
            timespec="seconds"
        ).replace("+00:00", "Z")
        if marker_mtime is not None
        else None,
        "secure_boot_enabled": secure_boot_enabled(),
        "reconciliation_events": reconciliation_events,
    }


def compare(before, after):
    prior_events = before.get("reconciliation_events", [])
    current_events = after.get("reconciliation_events", [])
    log_is_append_only = current_events[: len(prior_events)] == prior_events
    new_events = current_events[len(prior_events) :] if log_is_append_only else []
    new_reconciliation = next(
        (event for event in reversed(new_events) if "reconciliation=" in event), None
    )
    match = re.search(r"reconciliation=([^\s]+)", new_reconciliation or "")
    outcome = match.group(1) if match else None
    prior_threshold = before.get("machine_policy")
    after_thresholds = after.get("active_thresholds", [])
    return {
        "boot_changed": bool(before.get("boot_identity_sha256"))
        and before.get("boot_identity_sha256") != after.get("boot_identity_sha256"),
        "candidate_unchanged": before.get("candidate") == after.get("candidate"),
        "installed_package_unchanged": before.get("installed_package") == after.get("installed_package"),
        "preboot_policy_preserved": bool(prior_threshold)
        and after.get("machine_policy") == prior_threshold,
        "session_preference_preserved": before.get("session_preference_threshold") is not None
        and after.get("session_preference_threshold") == before.get("session_preference_threshold"),
        "postboot_session_preference_matches_policy": after.get(
            "session_preference_matches_policy", False
        ),
        "postboot_active_matches_preboot_policy": bool(prior_threshold)
        and bool(after_thresholds)
        and all(battery["value"] == prior_threshold for battery in after_thresholds),
        "postboot_active_matches_postboot_policy": after.get("active_thresholds_match_policy", False),
        "module_loaded": after.get("module_loaded", False),
        "reconciliation_service_enabled": after.get("reconciliation_service", {}).get("enabled", False),
        "reconciliation_service_running": after.get("reconciliation_service", {}).get("running", False),
        "reconciliation_service_bounded": after.get("reconciliation_service", {}).get("bounded", False),
        "lifecycle_state_belongs_to_current_boot": after.get("lifecycle_state", {}).get(
            "belongs_to_current_boot", False
        ),
        "known_good_marker": after.get("known_good_marker", False),
        "known_good_marker_updated_this_boot": after.get("known_good_marker_updated_this_boot", False),
        "new_boot_reconciliation_event": new_reconciliation,
        "new_boot_reconciliation_outcome": outcome,
        "no_op_reconciliation": outcome == "noop",
        "write_and_readback_reconciliation": outcome == "reconciled",
        "kernel_log_appended_since_preboot": log_is_append_only and bool(new_events),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("before", "after"))
    parser.add_argument("--before", type=Path, help="pre-reboot JSON required for an after capture")
    parser.add_argument("--output", type=Path, help="new output path; existing files are never replaced")
    args = parser.parse_args()
    if args.phase == "after" and not args.before:
        parser.error("after capture requires --before")
    if args.phase == "before" and args.before:
        parser.error("--before is only valid for an after capture")

    output = args.output or DEFAULT_DIR / f"controlled-{args.phase}-reboot.json"
    if output.exists():
        parser.error(f"refusing to replace existing capture: {output.name}")
    before = None
    reconciliation_wait = None
    if args.phase == "after":
        before = json.loads(args.before.read_text())
        if before.get("phase") != "before" or before.get("candidate") != CANDIDATE:
            parser.error("comparison input is not a matching v2.0.4 pre-reboot capture")
        reconciliation_wait = wait_for_reconciliation(before)
    observation = capture(args.phase)
    if args.phase == "after":
        observation["comparison"] = compare(before, observation)
        observation["reconciliation_wait_seconds"] = reconciliation_wait
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x") as stream:
        json.dump(observation, stream, indent=2)
        stream.write("\n")
    print(output)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, json.JSONDecodeError) as error:
        sys.exit(f"capture failed: {error}")
