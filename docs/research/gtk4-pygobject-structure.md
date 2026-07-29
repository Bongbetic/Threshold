# GTK4 + PyGObject Python Application Structure (Current Best Practices)

**Research ticket**: [#3](https://github.com/Bongbetic/MSI-batteryguard-for-Thin-A15-B7UCX/issues/3)

**Sources**: [GNOME Developer Docs](https://developer.gnome.org/documentation/tutorials/application.html), [GTK4 Getting Started](https://docs.gtk.org/gtk4/getting_started.html), [PyGObject Docs](https://pygobject.readthedocs.io), [Meson GNOME module](https://mesonbuild.com/Gnome-module.html), [Meson i18n module](https://mesonbuild.com/i18n-module.html), [Blueprint Compiler](https://gitlab.gnome.org/jwestman/blueprint-compiler), [Workbench](https://github.com/workbenchdev/Workbench)

---

## a) Gtk.Application Subclass Pattern

In PyGObject, the canonical pattern is to subclass `Gtk.Application` and override the `do_*` virtual methods. The `main()` entry point is minimal.

```python
# main.py
import sys
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Gio, GLib, Adw

class MyApplication(Adw.Application):
    """Main application class."""

    def __init__(self):
        super().__init__(
            application_id="com.example.MyApp",
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        self.connect("activate", self.on_activate)

    def on_activate(self, app):
        win = self.props.active_window
        if not win:
            win = MyWindow(application=self)
        win.present()

def main():
    app = MyApplication()
    return app.run(sys.argv)

if __name__ == "__main__":
    sys.exit(main())
```

Key points:
- Use `Adw.Application` (from libadwaita-1) instead of `Gtk.Application` for modern apps.
- Set `gi.require_version("Adw", "1")`.
- Override `do_activate` as a virtual method or connect to `"activate"` signal.
- `Gtk.Application` provides single-instance semantics and manages the main loop.
- For command-line handling: use `Gio.ApplicationFlags.HANDLES_COMMAND_LINE` and override `do_command_line`, or add main option entries via `self.add_main_option_entries()` for `--version`, `--debug`, etc.
- For file opening: set `Gio.ApplicationFlags.HANDLES_OPEN` and override `do_open(application, files, n_files, hint)`.

### Startup and Shutdown Lifecycle

| Signal/Vfunc | When emitted |
|---|---|
| `startup` | Called once on first launch, before `activate`/`open`. Set up actions, menus, resources here. |
| `activate` | Launched with no command-line arguments. Open default window. |
| `open` | Launched with files as arguments. Open files. |
| `shutdown` | Application exiting. Cleanup, save state. |

In PyGObject: override `do_startup`, `do_activate`, `do_open`, `do_shutdown`.

---

## b) GResource Bundling

### GResource XML file

Define resources in a `.gresource.xml` file:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<gresources>
  <gresource prefix="/com/example/MyApp">
    <file preprocess="xml-stripblanks">window.ui</file>
    <file preprocess="xml-stripblanks">preferences.ui</file>
    <file>style.css</file>
  </gresource>
</gresources>
```

### Meson invocation

```meson
gnome = import("gnome")

app_resources = gnome.compile_resources(
    meson.project_name(),
    "data/resources.gresource.xml",
    source_dir: "data",
    gresource_bundle: true,
    install: true,
    install_dir: pkgdatadir,
)
```

Key flags:
- `gresource_bundle: true` — outputs a `.gresource` binary file instead of C source. **For Python apps, always use `gresource_bundle: true`** since there's no compilation step.
- `source_dir` — where the resource compiler looks for files referenced in the XML.
- `install: true` + `install_dir` — install the `.gresource` bundle.

### Loading in Python

```python
resource = Gio.resource_load(
    Gio.Resource.open(f"{pkgdatadir}/myapp.gresource", 0)
)
Gio.resources_register(resource)

# Now GtkBuilder templates and CSS load from GResource paths:
builder = Gtk.Builder.new_from_resource("/com/example/MyApp/window.ui")
```

### Widget Templates

For composite widget templates (the preferred pattern):

```xml
<!-- data/window.ui -->
<?xml version="1.0" encoding="UTF-8"?>
<interface>
  <template class="MyWindow" parent="AdwApplicationWindow">
    <property name="title" translatable="yes">My App</property>
    <property name="default-width">600</property>
    <property name="default-height">400</property>
    <child>
      <!-- ... -->
    </child>
  </template>
</interface>
```

In Python:
```python
@Gtk.Template(resource_path="/com/example/MyApp/window.ui")
class MyWindow(Adw.ApplicationWindow):
    __gtype_name__ = "MyWindow"

    # Bind children from template:
    header_bar = Gtk.Template.Child()
    label = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
```

Bind callbacks with `@Gtk.Template.Callback()` decorator.

---

## c) Blueprint Integration

Blueprint (.blp) is a modern, readable format that compiles to GtkBuilder UI (.ui) XML. It is the recommended format for GNOME apps.

### Typical directory layout

```
data/
  ui/
    window.blp
    preferences.blp
  resources/
    resources.gresource.xml
  style.css
```

### Meson build integration

```meson
# Find blueprint compiler
blueprint_compiler = find_program("blueprint-compiler", required: true)

# Compile .blp → .ui
window_ui = custom_target(
    "window-ui",
    input: "data/ui/window.blp",
    output: "window.ui",
    command: [blueprint_compiler, "compile", "@INPUT@", "--output", "@OUTPUT@"],
)

preferences_ui = custom_target(
    "preferences-ui",
    input: "data/ui/preferences.blp",
    output: "preferences.ui",
    command: [blueprint_compiler, "compile", "@INPUT@", "--output", "@OUTPUT@"],
)

# Bundle compiled .ui into GResource
app_resources = gnome.compile_resources(
    meson.project_name(),
    "data/resources/resources.gresource.xml",
    source_dir: [meson.current_build_dir(), "data"],
    dependencies: [window_ui, preferences_ui],
    gresource_bundle: true,
    install: true,
    install_dir: pkgdatadir,
)
```

Important details:
- `source_dir` must include **both** `meson.current_build_dir()` (where compiled .ui lands) and `data` (for CSS/icons).
- `dependencies` ensures .blp → .ui compilation happens before GResource bundling.
- Use `preprocess="xml-stripblanks"` in gresource.xml for .ui files.

### Blueprint in Workbench

Workbench uses .blp files directly in its `src/` directory:
- `src/window.blp` — main window UI
- `src/shortcutsWindow.blp` — keyboard shortcuts window

This is the recommended convention: co-locate .blp with the source module it belongs to.

---

## d) GSettings Schema

### Schema XML

```xml
<!-- data/com.example.MyApp.gschema.xml -->
<?xml version="1.0" encoding="UTF-8"?>
<schemalist>
  <schema path="/com/example/MyApp/" id="com.example.MyApp">
    <key name="window-width" type="i">
      <default>800</default>
      <summary>Window width</summary>
      <description>Default window width in pixels.</description>
    </key>
    <key name="window-height" type="i">
      <default>600</default>
      <summary>Window height</summary>
      <description>Default window height in pixels.</description>
    </key>
    <key name="maximized" type="b">
      <default>false</default>
      <summary>Window maximized</summary>
    </key>
    <key name="dark-mode" type="b">
      <default>false</default>
      <summary>Dark mode</summary>
      <description>Use dark color scheme.</description>
    </key>
  </schema>
</schemalist>
```

### Meson install

```meson
configure_file(
    input: "data/com.example.MyApp.gschema.xml",
    output: "com.example.MyApp.gschema.xml",
    copy: true,
    install_dir: get_option("datadir") / "glib-2.0/schemas",
)

# Validate at build time
compile_schemas = find_program("glib-compile-schemas", required: true)
test(
    "Validate schema",
    compile_schemas,
    args: ["--strict", "--dry-run", meson.current_source_dir()],
)
```

### Using in Python

```python
from gi.repository import Gio

settings = Gio.Settings.new("com.example.MyApp")

# Read
width = settings.get_int("window-width")
dark = settings.get_boolean("dark-mode")

# Write
settings.set_int("window-width", 1024)

# Bind to widget property (auto-updates both directions)
settings.bind("dark-mode", color_scheme_combo, "selected",
              Gio.SettingsBindFlags.DEFAULT)

# Connect to change
settings.connect("changed::dark-mode", self.on_dark_mode_changed)
```

### Post-install schema compilation

In root `meson.build`:
```meson
gnome.post_install(
    glib_compile_schemas: true,
)
```

---

## e) gettext/i18n Integration

### Setup in meson.build

```meson
i18n = import("i18n")

i18n.gettext(
    meson.project_name(),
    args: [
        "--keyword=_",
        "--keyword=N_",
        "--keyword=C_:1c,2",
        "--keyword=NC_:1c,2",
        "--keyword=n_:1,2",
        "--flag=n_:1:pass-c-format",
        "--flag=n_:2:pass-c-format",
        "--keyword=ngettext:1,2",
    ],
    preset: "glib",
)

subdir("po")
```

### Directory layout for translations

```
po/
  LINGUAS          # Lists available languages (one per line: fr, de, es...)
  POTFILES         # Lists source files to scan for translatable strings
  POTFILES.skip    # Files to skip
  fr.po
  de.po
  ...
```

### POTFILES example

```
# po/POTFILES
data/ui/window.blp
data/com.example.MyApp.gschema.xml
src/main.py
src/window.py
```

### Marking strings for translation in Python

```python
import gettext
import locale

from gi.repository import GLib

# Set up locale
locale.bindtextdomain("myapp", GLib.get_locale_variant("localedir"))
locale.textdomain("myapp")
_ = gettext.gettext  # or use GLib.dgettext

# Use _()
label.set_label(_("Hello World"))

# In .blp files, use translatable="yes":
# <property name="title" translatable="yes">My Application</property>
```

### GLib preset

The `preset: "glib"` adds standard GLib xgettext flags that handle `C_()`, `NC_()`, `ngettext()`, etc.

### Update translations workflow

```shell
meson compile myapp-pot        # Regenerate .pot from sources
meson compile myapp-update-po  # Merge .pot into .po files
meson compile myapp-gmo        # Build .mo files
```

---

## f) Recommended Directory Tree

Based on Workbench and GNOME conventions:

```
myapp/
  meson.build                  # Root build file
  meson_options.txt            # Build options (if needed)
  build-aux/
    flatpak/
      com.example.MyApp.json   # Flatpak manifest
  data/
    ui/
      window.blp               # Main window blueprint
      preferences.blp          # Preferences dialog blueprint
      shortcuts.blp            # Keyboard shortcuts window
    resources/
      resources.gresource.xml  # GResource manifest
    style.css                  # App-wide CSS
    icons/
      hicolor/
        scalable/
          apps/
            com.example.MyApp.svg
        symbolic/
          apps/
            com.example.MyApp-symbolic.svg
    com.example.MyApp.desktop   # Desktop entry (template)
    com.example.MyApp.metainfo.xml  # AppStream metadata (template)
    com.example.MyApp.gschema.xml    # GSettings schema
  po/
    LINGUAS
    POTFILES
    fr.po
    de.po
  src/
    meson.build                # Source-level build rules
    main.py                    # Entry point
    application.py             # Gtk.Application subclass
    window.py                  # Main window widget
    preferences.py             # Preferences dialog
    utils.py                   # Utility functions
  tests/
    meson.build
    test_window.py
  flatpak/
    com.example.MyApp.json     # (Alternative location)
```

### Key design decisions:
- **`data/ui/` for .blp files**: Source UI definitions are in Blueprint format.
- **`data/resources/` for GResource manifest**: Keeps resource bundling separate from UI source.
- **`data/` for desktop, metainfo, schema, icons**: Standard GNOME convention.
- **`src/` for Python source**: All application logic.
- **`po/` for translations**: Standard gettext location.
- **Co-locate .blp with related Python module**: Some projects (like Workbench) put .blp in `src/` alongside their Python class. Either convention works; pick one and be consistent.
- **Use `Adw.Application` and `Adw.ApplicationWindow`** from libadwaita for modern UI.

---

## g) Template meson.build

### Root meson.build

```meson
project(
    "myapp",
    version: "0.1.0",
    meson_version: ">= 1.0.0",
    license: "GPL-3.0-or-later",
    default_options: [
        "warning_level=2",
    ],
)

gnome = import("gnome")
i18n = import("i18n")

app_id = "com.example.MyApp"

# Paths
prefix = get_option("prefix")
bindir = prefix / get_option("bindir")
datadir = prefix / get_option("datadir")
pkgdatadir = datadir / app_id

# Dependencies
dependency("gtk4", version: ">= 4.10")
dependency("libadwaita-1", version: ">= 1.4")

# Subdirectories
subdir("data")
subdir("src")
subdir("po")

# Post-install hooks
gnome.post_install(
    glib_compile_schemas: true,
    gtk_update_icon_cache: true,
    update_desktop_database: true,
)
```

### data/meson.build

```meson
# Compile Blueprint .blp → .ui
blueprint_compiler = find_program("blueprint-compiler", required: true)

window_ui = custom_target(
    "window-ui",
    input: "ui/window.blp",
    output: "window.ui",
    command: [blueprint_compiler, "compile", "@INPUT@", "--output", "@OUTPUT@"],
)

preferences_ui = custom_target(
    "preferences-ui",
    input: "ui/preferences.blp",
    output: "preferences.ui",
    command: [blueprint_compiler, "compile", "@INPUT@", "--output", "@OUTPUT@"],
)

# Bundle into GResource
app_resources = gnome.compile_resources(
    meson.project_name(),
    "resources/resources.gresource.xml",
    source_dir: [meson.current_build_dir(), "."],
    dependencies: [window_ui, preferences_ui],
    gresource_bundle: true,
    install: true,
    install_dir: pkgdatadir,
)

# Desktop file
configure_file(
    input: "@0@.desktop".format(app_id),
    output: "@0@.desktop".format(app_id),
    configuration: {"bindir": bindir},
    install_dir: get_option("datadir") / "applications",
)

# Metainfo
configure_file(
    input: "@0@.metainfo.xml".format(app_id),
    output: "@0@.metainfo.xml".format(app_id),
    configuration: {"app_id": app_id},
    install_dir: get_option("datadir") / "metainfo",
)

# GSettings schema
configure_file(
    input: "@0@.gschema.xml".format(app_id),
    output: "@0@.gschema.xml".format(app_id),
    copy: true,
    install_dir: get_option("datadir") / "glib-2.0/schemas",
)

# Schema validation
test(
    "Validate schema",
    find_program("glib-compile-schemas", required: true),
    args: ["--strict", "--dry-run", meson.current_source_dir()],
)

# Icons
install_subdir(
    "icons/hicolor",
    install_dir: get_option("datadir") / "icons",
)

# CSS
install_data(
    "style.css",
    install_dir: pkgdatadir,
)
```

### src/meson.build

```meson
# Install Python sources
python_sources = [
    "main.py",
    "application.py",
    "window.py",
    "preferences.py",
    "utils.py",
]

install_data(
    python_sources,
    install_dir: pkgdatadir,
)

# Entry point launcher script
script_conf = configuration_data()
script_conf.set("app_id", app_id)
script_conf.set("pkgdatadir", pkgdatadir)
script_conf.set("python", find_program("python3").full_path())

configure_file(
    input: "launcher.in",
    output: app_id,
    configuration: script_conf,
    install: true,
    install_dir: get_option("bindir"),
)

# Tests
test(
    "application tests",
    find_program("python3"),
    args: ["-m", "pytest", "-v"],
    env: {
        "GSETTINGS_SCHEMA_DIR": meson.project_build_root() / "data",
        "PYTHONPATH": meson.current_source_dir(),
    },
    workdir: meson.project_source_root(),
)

# Optional: install GResource alongside Python sources
# if the launcher script does not do it via configure_file
```

### src/launcher.in

```bash
#!/bin/sh
export PYTHONPATH="@pkgdatadir@:$PYTHONPATH"
exec @python@ -m main "$@"
```

### po/meson.build

```meson
i18n.gettext(
    meson.project_name(),
    preset: "glib",
)
```

### GResource XML (data/resources/resources.gresource.xml)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<gresources>
  <gresource prefix="/com/example/MyApp">
    <file preprocess="xml-stripblanks">window.ui</file>
    <file preprocess="xml-stripblanks">preferences.ui</file>
    <file>style.css</file>
  </gresource>
</gresources>
```

### Desktop entry (data/com.example.MyApp.desktop)

```desktop
[Desktop Entry]
Type=Application
Name=My App
Icon=com.example.MyApp
StartupNotify=true
Exec=@bindir@/com.example.MyApp
Categories=GTK;GNOME;Utility;
```

---

## Summary of Key Patterns

1. **Subclass `Adw.Application`** — use `do_activate`, `do_startup`, `do_shutdown`.
2. **Use composite widget templates** via `@Gtk.Template(resource_path=...)` with `.blp` Blueprint files.
3. **GResource bundle** with `gresource_bundle: true` in meson — no C compilation for Python.
4. **Blueprint → .ui → GResource pipeline**: custom_target for .blp→.ui, then `gnome.compile_resources()` with dependency chain.
5. **GSettings** via `Gio.Settings` with schema XML installed to `glib-2.0/schemas`.
6. **gettext** via `i18n.gettext()` with `preset: "glib"`, `.po` files in `po/`.
7. **Launcher script** in `src/launcher.in` → `configure_file` to install bindir entry point.
8. **Icon theme** in `data/icons/hicolor/scalable/apps/`, installed with `install_subdir`.
9. **Post-install hooks** via `gnome.post_install()` for schema/icon cache compilation.

### References

- GTK4 Widget Templates: https://docs.gtk.org/gtk4/class.Widget.html (search "template")
- Libadwaita Migrating to Breakpoints: https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/migrating-to-breakpoints.html
- Workbench source: https://github.com/workbenchdev/Workbench
- PyGObject User Guide: https://pygobject.readthedocs.io/en/latest/guide/
