# Vendored `msi-ec` kernel module

This directory contains a vendored snapshot of the upstream
[BeardOverflow/msi-ec](https://github.com/BeardOverflow/msi-ec) kernel module,
used to build the `msi-ec-dkms` Debian package.

- **Upstream version:** `0.13` (`Makefile.vars`)
- **Snapshot commit:** `050d4394a6747ebd106ae2f8ddb3a4eebe7c700f`
- **License:** GPL-2.0 (see `LICENSE`)
- **Support:** includes EC firmware `16RKIMS1.111` (MSI Thin A15 B7UCX) under
  `CONF_G2_6` in `msi-ec.c`.

The only change from upstream is `dkms.conf`, where the `@VERSION@` placeholder
used by the upstream `dkms-install` Makefile target is hardcoded to `0.13` so
the module can be registered directly with DKMS from a packaged source tree.

To sync to a newer upstream snapshot, replace the source files above with the
new upstream content and bump `PACKAGE_VERSION` in `dkms.conf` and `VERSION` in
`Makefile.vars`.
