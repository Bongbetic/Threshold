# Threshold

A battery charge-threshold controller: reads and writes the kernel's battery charge limit via sysfs so the EC stops charging at a user-set percentage.

## Language

**Threshold-capable battery**:
A battery whose sysfs directory has `type == Battery`. The app discovers
batteries by enumerating `/sys/class/power_supply/` dynamically.
_Avoid_: supported battery, EC-compatible device, MSI battery

**Charge threshold**:
The user-set charge limit (20–100%) written to `charge_control_end_threshold`,
persisted by the EC firmware across reboots. In notification-only mode the
threshold is saved to GSettings and used as an alarm trigger.
_Avoid_: charge cap, battery limit

**Control mode**:
How the application communicates charge thresholds to the battery.
Three modes detected automatically at runtime:
- **EC msi-ec**: the msi-ec kernel module is loaded and exposes
  `charge_control_end_threshold` on the battery sysfs device.
- **Vendor sysfs**: a native vendor driver (thinkpad-acpi, asus-wmi, …)
  exposes the threshold file without msi-ec.
- **Notification only**: no threshold control is available; the app monitors
  capacity and notifies the user once the charge reaches the threshold.
_Avoid_: driver, firmware

**EC module**:
The kernel module (msi-ec, thinkpad-acpi, asus-wmi, …) that exposes the
battery's charge-threshold sysfs interface.  The app detects mode based on
whether the msi-ec platform device is present alongside the threshold file.
_Avoid_: driver, firmware

### Appearance

**Dark mode**:
The appearance setting that forces the dark theme when on; when off, the UI
follows the system's light/dark preference instead.
_Avoid_: night mode, force dark

**Theme scheme**:
Which of the light or dark themes the UI renders right now: dark when Dark
mode is on, otherwise whatever the system currently prefers.
_Avoid_: color scheme, theme

**Accent color**:
The highlight hue applied across the UI, chosen from five presets
(orange, blue, green, purple, red); orange is the default.
_Avoid_: theme color, highlight color
