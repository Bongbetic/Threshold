# Graph Report - Threshold  (2026-09-01)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 653 nodes · 882 edges · 81 communities (32 shown, 49 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 53 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `280223df`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- msi-ec.c
- test_config.py
- Threshold Domain Context
- window.py
- FakeSettings
- test_battery.py
- ThresholdWindow
- Config
- test_install_layout.py
- test_metainfo.py
- TrayIcon
- _mock_power_supply_root
- GTK4 Modern UI Prototype Mockup Screenshot
- BatteryGuardApp
- ._load_settings
- TestConvertFileParsing
- ._update_tray_label
- Threshold Dark Mode Icon 512px
- Bongbetic Light Wordmark (wordmark-light.png)
- ThresholdApplication
- application.py
- ._cleanup_tray
- test_packaging_versions.py
- ._set_status
- .__init__
- test_install_modules.py
- test_workflows.py
- Threshold Scalable Application Icon
- GitHub Issue Tracker Conventions
- Vendored msi-ec Kernel Module Snapshot
- Debhelper 13 Meson Build Rules
- ThresholdPrototype
- test_import
- Graphify Knowledge Graph Rule
- devDependencies
- test_window_ui.py
- Hardware Sync Mechanism
- DFSG and NEW Queue Archive Review
- Debian 13 GNOME 48 / GTK 4.18 / libadwaita 1.7 Stack
- Fedora 44 Bare-Metal Verification Bar
- load_css_from_resource
- Bongbetic Brand B Glyph Vector Asset
- F-13 UI Tightening and Window Sizing
- P0 Migration Module Meson Packaging Bug
- Pure Python Architecture: all Decision
- GSettings Schema Dpkg Triggers Handling
- debian/watch Version 5 GitHub Monitoring
- Intent To Package (ITP) Bug Submission
- universalDKMSModuleUninstaller.sh
- Charge Limit Instrument Panel Design
- .connect
- .__init__
- __init__.py
- test_find_battery_path_no_matching_battery
- test_find_battery_path_mixed_devices
- test_read_sysfs_directory
- test_write_threshold_direct
- test_write_threshold_permission_error_pkexec_success
- test_write_threshold_permission_error_pkexec_fails
- test_write_threshold_pkexec_missing
- test_write_threshold_pkexec_timeout
- test_write_threshold_direct_write_other_error_returns_failure
- test_write_threshold_generic_exception_in_pkexec
- test_detect_control_mode_ec_msi
- test_detect_control_mode_sysfs_vendor
- test_detect_control_mode_notify_only_no_attr
- test_detect_control_mode_notify_only_msi_unsupported
- test_find_battery_path_dynamic_bat0_found
- test_find_battery_path_filters_non_battery_type
- test_find_battery_path_skips_no_type_file
- F-01 SNI Introspection XML Fix
- F-02 SNI Method Call Reply Fix
- F-03 Tray Menu Radio Lag Fix
- P1 Teardown Safety for GLib.idle_add Callbacks
- P2 GVariant Unpack Migration Bug
- Project CLA and DCO Policy Status
- Debian 13 Trixie Target Baseline
- Gettext and i18n Meson Integration
- Python 3.14 and GIRepository 2.0 Compatibility
- Ubuntu 26.04 LTS Resolute Package Stack
- Industrial Charcoal and Orange Palette

## God Nodes (most connected - your core abstractions)
1. `ThresholdWindow` - 55 edges
2. `Config` - 35 edges
3. `_mock_power_supply_root()` - 17 edges
4. `TrayIcon` - 16 edges
5. `FakeSettings` - 16 edges
6. `read_sysfs()` - 16 edges
7. `FakeSettings` - 13 edges
8. `BatteryGuardApp` - 13 edges
9. `_root()` - 13 edges
10. `ThresholdApplication` - 10 edges

## Surprising Connections (you probably didn't know these)
- `Charge Limit Slider with Quick Presets (60% Daily, 70% Balanced, 80% Recommended, 90% Extended, 100% Travel)` --semantically_similar_to--> `Threshold Adjustment Slider Control`  [INFERRED] [semantically similar]
  prototype-gtk4-ui/new-variant.png → data/screenshots/main-window.png
- `Debian and Ubuntu Package Installation` --semantically_similar_to--> `Release Deb Package Build Job`  [INFERRED] [semantically similar]
  INSTALL.md → .github/workflows/release.yml
- `Fedora RPM Package Installation` --semantically_similar_to--> `Release RPM Package Build Job`  [INFERRED] [semantically similar]
  INSTALL.md → .github/workflows/release.yml
- `Gemini Knowledge Graph Instructions` --semantically_similar_to--> `Graphify Knowledge Graph Rule`  [INFERRED] [semantically similar]
  GEMINI.md → .agents/rules/graphify.md
- `F-13 UI Tightening and Window Sizing` --semantically_similar_to--> `Industrial Grid UI Design Specification`  [INFERRED] [semantically similar]
  docs/fixes-v2.md → prototype-gtk4-ui/Threshold — Industrial Grid UI Design Specification.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Control Mode Triad** — context_ec_msi_ec_mode, context_vendor_sysfs_mode, context_notification_only_mode [EXTRACTED 1.00]
- **Distribution Packaging Pipeline** — _github_workflows_ci_deb_package_job, _github_workflows_ci_rpm_package_job, _github_workflows_release_rpm_smoke_job, _github_workflows_release_publish_release_job [EXTRACTED 1.00]
- **Fix v3 Regression & Remediation Cluster** — docs_fix_v3_v3_1_ec_rw_failure, docs_fix_v3_v3_2_dkms_packaging, docs_fix_v3_v3_3_ui_gridlines_and_size [EXTRACTED 1.00]
- **Debian Archive Readiness and Compliance Pipeline** — docs_research_debian_submission_process_itp_procedure, docs_research_debian_submission_process_dfsg_new_queue, docs_research_contribution_policies_dep5_compliance, docs_research_debian_submission_process_quilt_source_format [INFERRED 0.85]
- **GTK4 Libadwaita Desktop Architecture** — docs_research_gtk4_pygobject_structure_adw_application_pattern, docs_research_gtk4_pygobject_structure_gresource_bundle, docs_research_gtk4_pygobject_structure_blueprint_pipeline, prototype_gtk4_ui_threshold_industrial_grid_ui_design_specification_widget_mapping [INFERRED 0.85]
- **Hardware Threshold Control and Sync Lifecycle** — docs_fixes_v2_hardware_sync, docs_fixes_v2_f04_ec_threshold_probe, docs_fixes_v2_f05_msi_ec_packaging, msi_ec_src_readme_vendored_msi_ec [INFERRED 0.85]

## Communities (81 total, 49 thin omitted)

### Community 0 - "msi-ec.c"
Cohesion: 0.06
Nodes (38): charge_control_end_threshold_show(), charge_control_end_threshold_store(), charge_control_start_threshold_show(), charge_control_start_threshold_store(), cooler_boost_show(), cooler_boost_store(), direction_is_left(), ec_check_bit() (+30 more)

### Community 1 - "test_config.py"
Cohesion: 0.05
Nodes (5): config(), FakeSettings, fixture, Tests for the GSettings wrapper (config.py)., In-memory Gio.Settings mock for testing.

### Community 2 - "Threshold Domain Context"
Cohesion: 0.06
Nodes (39): CI Build and Test Job, GitHub Actions CI Workflow, CI Ubuntu Debian Package Job, CI Debian 13 Container Job, CI Fedora RPM Package Job, Release Deb Package Build Job, Publish GitHub Release Job, GitHub Actions Release Workflow (+31 more)

### Community 3 - "window.py"
Cohesion: 0.11
Nodes (35): Enum, battery_health_percent(), ControlMode, detect_control_mode(), _enumerate_power_supplies(), evaluate_alarm(), find_battery_path(), health_grade() (+27 more)

### Community 4 - "FakeSettings"
Cohesion: 0.09
Nodes (16): patch, migrate(), migrate_if_needed(), Settings, Migrate user preferences from the old batteryguard schema to threshold. On…, Return True if *schema_id* can be found in the compiled schemas., Copy user-set values from *old_settings* to *new_settings*. Returns True if any…, Ensure the batteryguard → threshold migration gate is settled. Returns True… (+8 more)

### Community 6 - "ThresholdWindow"
Cohesion: 0.09
Nodes (9): Sync the .app-dark window class with the effective scheme., Apply an accent scheme class to the window., Toggle the .compact class on the window., Show battery % in the window title when enabled., Restore the window from tray., Apply a threshold preset from the tray menu., Close-to-tray: hide window instead of destroying., ThresholdWindow (+1 more)

### Community 8 - "test_install_layout.py"
Cohesion: 0.15
Nodes (19): _assert_builddir_matches_repo(), _build_root(), destdir(), _install_to_destdir(), _meson(), fixture, Path, Meson install layout: icons, metainfo, udev, and ship-critical files. (+11 more)

### Community 9 - "test_metainfo.py"
Cohesion: 0.16
Nodes (19): Element, _description_text(), _normalized_text(), AppStream metainfo: content contract and schema validation., msi-ec-dkms is now bundled, not a recommends dependency., Element text with XML whitespace/newlines collapsed., _root(), test_metainfo_categories_include_system_and_hardware_settings() (+11 more)

### Community 10 - "TrayIcon"
Cohesion: 0.11
Nodes (7): Self-contained StatusNotifierItem + dbusmenu tray icon. Implements the SNI spec…, Build dbusmenu tree: presets + separator + Open + Quit., Update tray icon, tooltip, and menu radio marks., Clean up all D-Bus registrations., System tray icon with dbusmenu threshold presets., TrayIcon, Create the system tray indicator with battery icon and threshold menu.

### Community 11 - "_mock_power_supply_root"
Cohesion: 0.12
Nodes (18): _mock_power_supply_root(), Skips entries that have type Battery but lack threshold file., When multiple batteries qualify, returns the first one found., Returns the path when BAT0 has type Battery and charge_control_end_threshold., Returns the first Battery-type entry by sort order., Returns the battery even when it lacks the threshold file., Returns None when power_supply directory is empty., Monkeypatch Path.iterdir on /sys/class/power_supply to return items from… (+10 more)

### Community 12 - "GTK4 Modern UI Prototype Mockup Screenshot"
Cohesion: 0.16
Nodes (16): Apply Threshold Action Button, Charge Threshold Percentage Display, Header Bar - MSI BatteryGuard, Threshold Main Window UI Screenshot (MSI BatteryGuard), Restore to 100% Quick Action Button, Threshold Adjustment Slider Control, msi-ec Driver and Hardware Status Indicator, Active Threshold Status Card (80% on BAT1) (+8 more)

### Community 14 - "._load_settings"
Cohesion: 0.22
Nodes (5): _format_last_changed(), Format a unix timestamp as 'Today, HH:MM' or a date., Restore preferences from GSettings into the UI., Mark the preset tile matching ``value`` as selected., Show a desktop notification via libnotify (if enabled).

### Community 15 - "TestConvertFileParsing"
Cohesion: 0.17
Nodes (8): fixture, Verify the convert / compatibility schema files parse correctly., Write the old schema to a temp dir and return the path., Write the new schema to a temp dir and return the path., The old schema must expose exactly the 6 user-facing keys., The new schema must expose the 6 keys plus migration-done., Every key in the old schema must exist in the new schema., TestConvertFileParsing

### Community 16 - "._update_tray_label"
Cohesion: 0.20
Nodes (6): _battery_icon_name(), Refresh the battery status card icon to match charge + status., Called every 5 seconds — refresh battery data and animate dot., Fire or re-arm the threshold-reached alarm in notify-only mode., Update the tray icon, tooltip, and menu marks., Return a freedesktop battery icon name for the given charge level.

### Community 17 - "Threshold Dark Mode Icon 512px"
Cohesion: 0.25
Nodes (9): Threshold Dark Theme Brand Identity & Visual Assets, Dark Icon 192px Stylized B Glyph, Threshold Dark Mode Icon 192px, Dark Icon 512px Stylized B Glyph, Threshold Dark Mode Icon 512px, Threshold Dark Mode Wordmark (2x High Resolution), Threshold Dark Wordmark High-DPI Lettering, Threshold Dark Mode Wordmark (+1 more)

### Community 18 - "Bongbetic Light Wordmark (wordmark-light.png)"
Cohesion: 0.31
Nodes (9): Bongbetic Light Icon 192px (icon-light-192.png), Bongbetic 'B' Light Icon Monogram, Bongbetic 'B' High-Resolution Light Monogram, Bongbetic Light Icon 512px (icon-light-512.png), High-DPI Retina Light Wordmark, Bongbetic Light Wordmark @2x (wordmark-light@2x.png), Red Letter Accents (O and E), Bongbetic Light Typographic Branding (+1 more)

### Community 19 - "ThresholdApplication"
Cohesion: 0.28
Nodes (5): Save window geometry and tear down notifications on shutdown., ThresholdApplication, main(), Bind gettext domain so _() and Blueprint strings resolve., _setup_i18n()

### Community 20 - "application.py"
Cohesion: 0.29
Nodes (5): Application class — startup, activation, shutdown, and autostart management., GSettings wrapper — typed access to application preferences., Register the compiled GResource bundle for UI templates and CSS., Locate and register ``threshold.gresource``. Returns True if a resource bundle…, register_resources()

### Community 21 - "._cleanup_tray"
Cohesion: 0.33
Nodes (3): Remove polling, live-dot, geometry and pending-write sources., Quit the application from tray., Clean up the tray indicator.

### Community 22 - "test_packaging_versions.py"
Cohesion: 0.48
Nodes (6): _dkms_version(), _find_versions(), Packaging drift guard: msi-ec version must be consistent. Prevents the 0.13 vs…, test_dkms_version_is_0_13_112(), test_dkms_version_matches_packaging(), test_makefile_vars_matches_dkms()

### Community 25 - "test_install_modules.py"
Cohesion: 0.47
Nodes (5): _listed_modules(), Regression: every src/threshold/*.py module must ship in python_sources. A…, migration.py is imported by application.py; it must be installed., test_all_threshold_modules_listed_in_python_sources(), test_migration_module_is_shipped()

### Community 27 - "Threshold Scalable Application Icon"
Cohesion: 0.40
Nodes (5): Threshold Scalable Application Icon, Green Gradient Battery Charge Fill Visual, FreeDesktop Hicolor Scalable Icon Theme Specification, Threshold Symbolic Status Icon, Monochrome CurrentColor Dynamic Tray / Panel Recoloring

### Community 28 - "GitHub Issue Tracker Conventions"
Cohesion: 0.40
Nodes (5): Native Issue Dependencies & Blocking, GitHub Issue Tracker Conventions, Wayfinding Map and Child Operations, Canonical Triage Roles, Triage Labels Role Mapping

### Community 29 - "Vendored msi-ec Kernel Module Snapshot"
Cohesion: 0.40
Nodes (5): F-05 msi-ec Kernel Module Loading Defect, DFSG Compliance Evaluation for msi-ec, GPL-3.0 and GPL-2.0-or-later License Compatibility, MSI Thin A15 EC Firmware Support, Vendored msi-ec Kernel Module Snapshot

### Community 30 - "Debhelper 13 Meson Build Rules"
Cohesion: 0.40
Nodes (5): Debhelper 13 Meson Build Rules, Blueprint to GtkBuilder Compilation Pipeline, GResource Binary Bundling for Python, python-bytecompile Meson Option, GTK4 and libadwaita Component Mapping

### Community 32 - "test_import"
Cohesion: 0.40
Nodes (4): Placeholder test — verifies pytest is wired into meson., Verify the threshold package is importable., test_import(), test_placeholder()

### Community 33 - "Graphify Knowledge Graph Rule"
Cohesion: 0.50
Nodes (4): Graphify Query & Update Workflow, Graphify Knowledge Graph Rule, Graphify Pipeline Workflow, Gemini Knowledge Graph Instructions

### Community 34 - "devDependencies"
Cohesion: 0.50
Nodes (3): devDependencies, prettier, prettier

### Community 36 - "Hardware Sync Mechanism"
Cohesion: 0.67
Nodes (3): F-04 EC Threshold Live Sync Defect, Hardware Sync Mechanism, P2 Battery Rediscovery on Poll Ticks

### Community 37 - "DFSG and NEW Queue Archive Review"
Cohesion: 0.67
Nodes (3): DEP-5 Copyright Machine-Readable Compliance, AppStream Metainfo Validation, DFSG and NEW Queue Archive Review

### Community 38 - "Debian 13 GNOME 48 / GTK 4.18 / libadwaita 1.7 Stack"
Cohesion: 0.67
Nodes (3): Meson Dependency Constraints Evaluation for Trixie, Debian 13 GNOME 48 / GTK 4.18 / libadwaita 1.7 Stack, GNOME 50 / GTK 4.22 / libadwaita 1.9 Dependencies

### Community 39 - "Fedora 44 Bare-Metal Verification Bar"
Cohesion: 0.67
Nodes (3): Fedora 44 Bare-Metal Verification Bar, Threshold Sysusers and pkexec Fallback Verification, Fedora RPM Verification Checklist Procedure

## Knowledge Gaps
- **66 isolated node(s):** `prettier`, `universalDKMSModuleUninstaller.sh script`, `Header Bar - MSI BatteryGuard`, `msi-ec Driver and Hardware Status Indicator`, `Active Threshold Status Card (80% on BAT1)` (+61 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 346 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **49 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ThresholdWindow` connect `ThresholdWindow` to `window.py`, `Config`, `TrayIcon`, `._load_settings`, `._update_tray_label`, `ThresholdApplication`, `application.py`, `._cleanup_tray`, `._set_status`, `.__init__`?**
  _High betweenness centrality (0.076) - this node is a cross-community bridge._
- **Why does `Config` connect `Config` to `test_config.py`, `window.py`, `ThresholdWindow`, `.connect`, `.__init__`, `ThresholdApplication`, `application.py`, `.__init__`?**
  _High betweenness centrality (0.052) - this node is a cross-community bridge._
- **Why does `migrate_if_needed()` connect `FakeSettings` to `load_css_from_resource`, `application.py`?**
  _High betweenness centrality (0.043) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `ThresholdWindow` (e.g. with `ThresholdApplication` and `ControlMode`) actually correct?**
  _`ThresholdWindow` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `Config` (e.g. with `ThresholdApplication` and `ThresholdWindow`) actually correct?**
  _`Config` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `prettier`, `universalDKMSModuleUninstaller.sh script`, `Header Bar - MSI BatteryGuard` to the rest of the system?**
  _66 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `msi-ec.c` be split into smaller, more focused modules?**
  _Cohesion score 0.055191256830601096 - nodes in this community are weakly interconnected._