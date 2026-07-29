pkgdatadir = get_option('prefix') / get_option('datadir') / 'com.bongbetic.batteryguard'

python_sources = [
    'batteryguard/__init__.py',
    'batteryguard/battery.py',
    'batteryguard/main.py',
    'batteryguard/application.py',
    'batteryguard/window.py',
]

install_data(
    python_sources,
    install_dir: pkgdatadir / 'batteryguard',
)

script_conf = configuration_data()
script_conf.set('app_id', 'com.bongbetic.batteryguard')
script_conf.set('pkgdatadir', pkgdatadir)
script_conf.set('python', find_program('python3').full_path())

configure_file(
    input: 'launcher.in',
    output: 'com.bongbetic.batteryguard',
    configuration: script_conf,
    install: true,
    install_dir: get_option('bindir'),
    install_mode: 'rwxr-xr-x',
)
