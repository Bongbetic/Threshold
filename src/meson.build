pkgdatadir = get_option('prefix') / get_option('datadir') / 'com.bongbetic.threshold'

python_sources = [
    'threshold/__init__.py',
    'threshold/battery.py',
    'threshold/config.py',
    'threshold/main.py',
    'threshold/application.py',
    'threshold/migration.py',
    'threshold/tray.py',
    'threshold/window.py',
    'threshold/resources.py',
]

install_data(
    python_sources,
    install_dir: pkgdatadir / 'threshold',
)

script_conf = configuration_data()
script_conf.set('app_id', 'com.bongbetic.threshold')
script_conf.set('pkgdatadir', pkgdatadir)
script_conf.set('localedir', get_option('prefix') / get_option('localedir'))
script_conf.set('python', find_program('python3').full_path())

configure_file(
    input: 'launcher.in',
    output: 'threshold',
    configuration: script_conf,
    install: true,
    install_dir: get_option('bindir'),
    install_mode: 'rwxr-xr-x',
)
