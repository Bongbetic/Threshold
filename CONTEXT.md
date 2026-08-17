# Threshold

A battery charge-threshold controller: reads and writes the kernel's battery charge limit via sysfs so the EC stops charging at a user-set percentage.

## Language

**Threshold-capable battery**:
A battery whose sysfs directory has `type == Battery` and exposes `charge_control_end_threshold`. The set of batteries the app can control; discovery is the sysfs interface itself, not a brand/module table.
_Avoid_: supported battery, EC-compatible device, MSI battery

**Charge threshold**:
The user-set charge limit (20–100%) written to `charge_control_end_threshold`, persisted by the EC firmware across reboots.
_Avoid_: charge cap, battery limit

**EC module**:
The kernel module (msi-ec, thinkpad-acpi, asus-wmi, …) that exposes the battery's charge-threshold sysfs interface. The app never detects or names the module — the sysfs file's presence is the only signal.
_Avoid_: driver, firmware
