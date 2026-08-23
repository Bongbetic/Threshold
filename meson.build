project(
    'threshold',
    version: '1.3.0',
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

subdir('data')
subdir('src')
subdir('po')
subdir('tests')

gnome.post_install(
    glib_compile_schemas: true,
    gtk_update_icon_cache: true,
    update_desktop_database: true,
)
