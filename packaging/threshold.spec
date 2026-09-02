# Unified RPM spec for Threshold (issue #86).
#
# One distribution-neutral RPM carries the application, the vendored
# msi-ec source, and the shared EC lifecycle integration. It replaces
# the officially released paired main+msi-ec-dkms RPMs: its first NEVR
# (2.0.0) is higher than every paired release, and versioned
# Provides/Obsoletes replace the old pair without a conflict.
# Shared native integration inputs define lifecycle behavior once;
# scriptlets invoke /usr/sbin/threshold-ec-lifecycle without
# reimplementing it, and no lifecycle failure ever fails the transaction.

%global msi_ec_ver 0.13.112

Name:           threshold
Version:        2.0.0
Release:        1
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
BuildRequires:  gtk4-devel >= 4.14
BuildRequires:  libadwaita-devel >= 1.5
BuildRequires:  python3-devel
BuildRequires:  python3-gobject
BuildRequires:  desktop-file-utils
BuildRequires:  libappstream-glib
BuildRequires:  systemd-rpm-macros

# Portable runtime capabilities (same contract as the DEB hard requires).
Requires:       python3-gobject
Requires:       gtk4 >= 4.14
Requires:       libadwaita >= 1.5
Requires:       libnotify
Requires:       hicolor-icon-theme
Requires:       dkms
Requires:       kmod
Requires:       systemd
# Explicit x86-64 GI typelib capabilities for the Carbon shell + tray.
Requires:       gtk4(x86-64)
Requires:       libadwaita(x86-64)
Requires:       libnotify(x86-64)
Requires:       dbusmenu-gtk3(x86-64)
Requires:       webkit2gtk-6.0(x86-64)
Recommends:     polkit
Recommends:     mokutil

# Replace the officially released paired RPM layout without a conflict.
Provides:       threshold-msi-ec-dkms = %{version}-%{release}
Obsoletes:      threshold-msi-ec-dkms < 2.0.0

%description
Threshold provides a GTK4 graphical interface for setting the battery
charge threshold on Linux laptops. When the msi-ec kernel module is
available the charge limit is written directly to the EC microcontroller
and persists across reboots. When no EC/sysfs charge control is available
the application falls back to a notification alarm that alerts the user
once the charge threshold is reached. This unified RPM additionally
carries the vendored msi-ec %{msi_ec_ver} source and the shared EC
lifecycle integration; EC setup is attempted only on MSI hardware and an
EC failure never fails installation.

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

# Shared EC lifecycle authority + boot reconciler unit
install -Dpm 0755 packaging/threshold-ec-lifecycle %{buildroot}%{_sbindir}/threshold-ec-lifecycle
install -Dpm 0644 data/threshold-boot-reconcile.service %{buildroot}%{_unitdir}/threshold-boot-reconcile.service

# DKMS source bundle → /usr/src, owned privately; only the lifecycle
# command materializes the DKMS registration.
mkdir -p %{buildroot}%{_usrsrc}/msi-ec-%{msi_ec_ver}
cp -a msi-ec-src/. %{buildroot}%{_usrsrc}/msi-ec-%{msi_ec_ver}/
install -Dpm 0644 %{buildroot}%{_usrsrc}/msi-ec-%{msi_ec_ver}/dkms.conf %{buildroot}%{_usrsrc}/msi-ec-%{msi_ec_ver}/dkms.conf

# Autoload hint (registered in the ownership ledger by the lifecycle script)
mkdir -p %{buildroot}%{_modulesloaddir}
echo msi-ec > %{buildroot}%{_modulesloaddir}/msi-ec.conf

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/com.bongbetic.threshold.desktop
appstream-util validate-relax %{buildroot}%{_metainfodir}/com.bongbetic.threshold.metainfo.xml

# Distribution-owned triggers handle GSettings, desktop, AppStream, and icon
# caches (RPM file triggers owned by glib2/desktop-file-utils/hicolor).
#
# %post: sysusers + udev integration, and official legacy handoff evidence
# capture while an officially released paired RPM may still own assets.
%post
%sysusers_create threshold.conf
udevadm control --reload 2>/dev/null || :
udevadm trigger --subsystem-match=power_supply 2>/dev/null || :
mkdir -p /var/lib/threshold/ec
if rpm -q threshold-msi-ec-dkms >/dev/null 2>&1; then
    rpm -q --qf 'legacy %{NAME} %{VERSION}-%{RELEASE}\n' threshold-msi-ec-dkms \
        > /var/lib/threshold/ec/legacy-handoff 2>/dev/null || :
fi
systemctl preset threshold-boot-reconcile.service >/dev/null 2>&1 || :

# %posttrans: after obsolete-package erasure, run the shared
# install-or-upgrade reconciliation. Migration snapshots official legacy
# ownership while the old package is still installed; reconstruction of
# managed DKMS state happens here. Never fails the transaction.
%posttrans
if [ -x %{_sbindir}/threshold-ec-lifecycle ]; then
    %{_sbindir}/threshold-ec-lifecycle install-or-upgrade || :
fi

# %preun: invoke removal only when the package is actually being removed;
# upgrades perform no cleanup.
%preun
if [ "$1" = "0" ] && [ -x %{_sbindir}/threshold-ec-lifecycle ]; then
    %{_sbindir}/threshold-ec-lifecycle remove || :
fi
if [ "$1" = "0" ]; then
    systemctl disable threshold-boot-reconcile.service >/dev/null 2>&1 || :
fi

%files
%license LICENSE
%doc README.md
%{_bindir}/threshold
%{_sbindir}/threshold-ec-lifecycle
%{_unitdir}/threshold-boot-reconcile.service
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
%{_usrsrc}/msi-ec-%{msi_ec_ver}/
%{_modulesloaddir}/msi-ec.conf

%changelog
* Tue Sep 02 2026 Soubarna <Soubarna@live.in> - 2.0.0-1
- Unified RPM: one distribution-neutral artifact replaces the paired
  main + msi-ec-dkms release; shared EC lifecycle authority, boot
  reconciliation unit, and ledger-owned removal (issue #86)

* Sat Aug 29 2026 Soubarna <Soubarna@live.in> - 1.4.2-1
- Release 1.4.2: Fedora .rpm joins the .deb in CI-built GitHub Releases

* Fri Aug 28 2026 Soubarna <Soubarna@live.in> - 1.4.1-1
- Initial Fedora RPM: sysusers.d group threshold replaces plugdev, manual
  %%py_byte_compile for the /usr/share python tree, DKMS subpackage for the
  bundled msi-ec %{msi_ec_ver} source, no cache scriptlets (RPM file triggers)
