project(
    'batteryguard',
    version: '2.0.0',
    meson_version: '>= 1.0.0',
    license: 'GPL-3.0-or-later',
    default_options: [
        'warning_level=2',
    ],
)

gnome = import('gnome')
i18n = import('i18n')

app_id = 'com.bongbetic.batteryguard'

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

# udev rule for passwordless charge-threshold writes (plugdev group)
install_data(
    '99-msi-battery.rules',
    install_dir: get_option('prefix') / 'lib' / 'udev' / 'rules.d',
)

gnome.post_install(
    glib_compile_schemas: true,
    gtk_update_icon_cache: true,
    update_desktop_database: true,
)
