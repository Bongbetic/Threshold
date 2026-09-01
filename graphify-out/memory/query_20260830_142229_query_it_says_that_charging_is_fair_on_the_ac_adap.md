---
type: "query"
date: "2026-08-30T14:22:29.517114+00:00"
question: "query it says that charging is fair on the AC adapter why?"
contributor: "graphify"
outcome: "useful"
source_nodes: ["battery_health_percent()", "health_grade()", "read_power_source()", "ThresholdWindow"]
---

# Q: query it says that charging is fair on the AC adapter why?

## Answer

Expanded from original query via vocab: [battery, capacity, charge, charging, fair, grade, health, percent, power, status]. On the Battery Telemetry card, 'AC adapter' and 'Fair' are two separate metrics: (1) Power Source displays 'AC adapter' because read_power_source() detected that a Mains power supply is online. (2) Health displays 'Fair' because battery_health_percent() calculated that the battery's full charge capacity (energy_full or charge_full) is between 60% and 79% of its original design capacity (energy_full_design or charge_full_design), which health_grade() maps to HEALTH_FAIR.

## Outcome

- Signal: useful

## Source Nodes

- battery_health_percent()
- health_grade()
- read_power_source()
- ThresholdWindow