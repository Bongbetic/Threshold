project(
    'threshold',
    version: '1.4.2',
    meson_version: '>= 1.0.0',
    license: 'GPL-3.0-or-later',
    default_options: [
        'warning_level=2',
    ],
)

gnome = import('gnome')
i18n = import('i18n')

app_id = 'com.bongbetic.threshold'

prefix = get_option('prefix')
bindir = prefix / get_option('bindir')
datadir = prefix / get_option('datadir')
pkgdatadir = datadir / app_id

dependency('gtk4', version: '>= 4.14')
dependency('libadwaita-1', version: '>= 1.5')

# Optional WebKitGTK 6.0 for Carbon shell
webkit_dep = dependency('webkitgtk-6.0', version: '>= 2.40', required: false)
if webkit_dep.found()
  message('WebKitGTK 6.0 found: Carbon shell enabled')
else
  message('WebKitGTK 6.0 not found: Carbon shell disabled')
endif

subdir('data')
subdir('src')
subdir('po')
subdir('tests')

# Install committed web/dist if present
web_dist = meson.current_source_dir() / 'web' / 'dist'
if web_dist.is_dir()
  install_subdir(
    web_dist,
    install_dir: pkgdatadir / 'web',
  )
  message('Installing web/dist to: ' + pkgdatadir / 'web')
endif

gnome.post_install(
    glib_compile_schemas: true,
    gtk_update_icon_cache: true,
    update_desktop_database: true,
)
