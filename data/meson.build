app_id = 'com.bongbetic.threshold'

# GResource bundle
app_resources = gnome.compile_resources(
    'threshold',
    'resources/resources.gresource.xml',
    source_dir: [meson.current_build_dir(), meson.current_source_dir()],
    gresource_bundle: true,
    install: true,
    install_dir: pkgdatadir,
)

# Desktop file
desktop_conf = configuration_data()
desktop_conf.set('bindir', get_option('prefix') / get_option('bindir'))

desktop_file = configure_file(
    input: '@0@.desktop'.format(app_id),
    output: '@0@.desktop'.format(app_id),
    configuration: desktop_conf,
    install: true,
    install_dir: get_option('datadir') / 'applications',
)

# Metainfo
configure_file(
    input: '@0@.metainfo.xml'.format(app_id),
    output: '@0@.metainfo.xml'.format(app_id),
    copy: true,
    install: true,
    install_dir: get_option('datadir') / 'metainfo',
)

# GSettings schema (new)
configure_file(
    input: '@0@.gschema.xml'.format(app_id),
    output: '@0@.gschema.xml'.format(app_id),
    copy: true,
    install: true,
    install_dir: get_option('datadir') / 'glib-2.0' / 'schemas',
)

# GSettings compatibility schema (old batteryguard → threshold migration)
configure_file(
    input: 'com.bongbetic.batteryguard.gschema.xml',
    output: 'com.bongbetic.batteryguard.gschema.xml',
    copy: true,
    install: true,
    install_dir: get_option('datadir') / 'glib-2.0' / 'schemas',
)

# GSettings migration map for upgrades from the former application ID.
install_data(
    'com.bongbetic.batteryguard.convert',
    install_dir: get_option('datadir') / 'GConf' / 'gsettings',
)

# Schema validation
compile_schemas = find_program('glib-compile-schemas', required: false)
if compile_schemas.found()
    test(
        'Validate GSettings schema',
        compile_schemas,
        args: ['--strict', '--dry-run', meson.current_source_dir()],
    )
endif

# Icons
install_subdir(
    'icons/hicolor',
    install_dir: get_option('datadir') / 'icons',
)

# udev rule for passwordless charge-threshold writes (plugdev group).
# Packaged into /usr/lib/udev/rules.d (not /etc — lintian udev-rule-in-etc).
install_data(
    '99-msi-battery.rules',
    install_dir: get_option('prefix') / 'lib' / 'udev' / 'rules.d',
)

# CSS (also in GResource — separate install for development convenience)
install_data(
    'style.css',
    install_dir: pkgdatadir,
)
