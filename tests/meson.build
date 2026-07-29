test(
    'scaffold',
    find_program('python3'),
    args: ['-m', 'pytest', '-v', meson.current_source_dir()],
    env: {
        'PYTHONPATH': meson.project_source_root() / 'src',
        'GI_TYPELIB_PATH': '',
        'MESON_BUILD_ROOT': meson.project_build_root(),
    },
    workdir: meson.project_source_root(),
)
