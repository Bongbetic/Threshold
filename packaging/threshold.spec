# Spec for the GitHub-Release RPM of Threshold (charter: map #35 — not COPR,
# not official Fedora). Layout mirrors debian/ packaging; research notes with
# primary-source citations: docs/research/fedora-packaging.md (ticket #43).

%global msi_ec_ver 0.13.112

Name:           threshold
Version:        1.4.2
Release:        1%{?dist}
Summary:        Battery charge threshold controller for Linux laptops
License:        GPL-3.0-or-later
URL:            https://github.com/Bongbetic/Threshold
Source0:        %{url}/archive/v%{version}/Threshold-%{version}.tar.gz
Source1:        threshold.sysusers
BuildArch:      noarch

BuildRequires:  meson
BuildRequires:  ninja-build
BuildRequires:  pkgconf-pkg-config
BuildRequires:  gettext
BuildRequires:  blueprint-compiler
BuildRequires:  gtk4-devel >= 4.14
BuildRequires:  libadwaita-devel >= 1.5
BuildRequires:  python3-devel
BuildRequires:  python3-gobject
BuildRequires:  desktop-file-utils
BuildRequires:  libappstream-glib
BuildRequires:  systemd-rpm-macros

Requires:       python3-gobject
Requires:       gtk4 >= 4.14
Requires:       libadwaita >= 1.5
Requires:       libnotify
Requires:       hicolor-icon-theme
Recommends:     %{name}-msi-ec-dkms
Recommends:     polkit

%description
Threshold provides a GTK4 graphical interface for setting the battery
charge threshold on Linux laptops. When the msi-ec kernel module is
available the charge limit is written directly to the EC microcontroller
and persists across reboots. When no EC/sysfs charge control is available
the application falls back to a notification alarm that alerts the user
once the charge threshold is reached.

%package msi-ec-dkms
Summary:        DKMS source for the bundled msi-ec kernel module
BuildArch:      noarch
Requires:       dkms
Requires(post): dkms
Requires(preun): dkms

%description msi-ec-dkms
Bundled msi-ec %{msi_ec_ver} kernel module source, built against the running
kernel at install time via DKMS (mirrors the Debian package's /usr/src
bundle). On Secure Boot systems the module must be signed (MOK) to load.

%prep
%autosetup -p1 -n Threshold-%{version}
# Fedora has no plugdev group: rewrite the Debian-ism to our sysusers.d group
# (see research notes §5). sed touches the RUN+= chgrp lines and the comments.
sed -i 's/\bplugdev\b/threshold/g' data/99-msi-battery.rules

%build
%meson
%meson_build

%install
%meson_install
# Python lives in %%{_datadir}, not sitelib — brp does not cover it (§1)
%py_byte_compile %{python3} %{buildroot}%{_datadir}/com.bongbetic.threshold/threshold/

# Dedicated system group instead of plugdev (§5.3)
install -Dpm 0644 %{SOURCE1} %{buildroot}%{_sysusersdir}/threshold.conf

# DKMS source bundle → /usr/src, same as the .deb
mkdir -p %{buildroot}%{_usrsrc}/msi-ec-%{msi_ec_ver}
cp -a msi-ec-src/. %{buildroot}%{_usrsrc}/msi-ec-%{msi_ec_ver}/

# Autoload hint
mkdir -p %{buildroot}%{_modulesloaddir}
echo msi-ec > %{buildroot}%{_modulesloaddir}/msi-ec.conf

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/com.bongbetic.threshold.desktop
appstream-util validate-relax %{buildroot}%{_metainfodir}/com.bongbetic.threshold.metainfo.xml

# No icon-cache/desktop-database/gschema-compile scriptlets: RPM file triggers
# owned by hicolor-icon-theme/desktop-file-utils/glib2 refresh those caches (§4).
%post
udevadm control --reload || :
udevadm trigger --subsystem-match=power_supply || :

%post msi-ec-dkms
if command -v dkms >/dev/null 2>&1; then
    dkms add    -m msi-ec -v %{msi_ec_ver} || :
    dkms build  -m msi-ec -v %{msi_ec_ver} || :
    dkms install -m msi-ec -v %{msi_ec_ver} || :
fi
modprobe msi-ec || :
# Secure Boot: unsigned module will not load; enroll a MOK key:
#   sudo mokutil --import /var/lib/shim-signed/mok/mok.pub && reboot

%preun msi-ec-dkms
if [ "$1" = "0" ]; then
    dkms remove -m msi-ec -v %{msi_ec_ver} --all || :
fi

%files
%license LICENSE
%doc README.md
%{_bindir}/threshold
%{_datadir}/com.bongbetic.threshold/
%{_datadir}/applications/com.bongbetic.threshold.desktop
%{_metainfodir}/com.bongbetic.threshold.metainfo.xml
%{_datadir}/glib-2.0/schemas/com.bongbetic.threshold.gschema.xml
%{_datadir}/glib-2.0/schemas/com.bongbetic.batteryguard.gschema.xml
%{_datadir}/GConf/gsettings/com.bongbetic.batteryguard.convert
%{_datadir}/icons/hicolor/scalable/apps/com.bongbetic.threshold.svg
%{_datadir}/icons/hicolor/symbolic/apps/com.bongbetic.threshold-symbolic.svg
# po/LINGUAS is empty — no .mo installed yet; re-add
# %%{_datadir}/locale/*/LC_MESSAGES/*.mo when translations land
%{_udevrulesdir}/99-msi-battery.rules
%{_sysusersdir}/threshold.conf

%files msi-ec-dkms
%{_usrsrc}/msi-ec-%{msi_ec_ver}/
%{_modulesloaddir}/msi-ec.conf

%changelog
* Sat Aug 29 2026 Soubarna <Soubarna@live.in> - 1.4.2-1
- Release 1.4.2: Fedora .rpm joins the .deb in CI-built GitHub Releases

* Fri Aug 28 2026 Soubarna <Soubarna@live.in> - 1.4.1-1
- Initial Fedora RPM: sysusers.d group threshold replaces plugdev, manual
  %%py_byte_compile for the /usr/share python tree, DKMS subpackage for the
  bundled msi-ec %{msi_ec_ver} source, no cache scriptlets (RPM file triggers)
