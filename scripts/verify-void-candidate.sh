#!/bin/bash
# Disposable-container package verification; this does not produce physical acceptance.
set -euo pipefail
test -f /run/.containerenv || test -f /.dockerenv
candidate_dir=$(realpath "$1")
report=$(realpath -m "$2")
cd "$candidate_dir"
sha256sum --check candidate.sha256
packages=(threshold-*.x86_64.xbps)
test "${#packages[@]}" -eq 1
package=${packages[0]}
expression=${package%.x86_64.xbps}
xbps-install -Suy xbps
xbps-install -Sy --repository="$candidate_dir" "$expression"
xbps-query -f threshold > /tmp/threshold-installed-files
for file in \
    /usr/bin/threshold /usr/bin/threshold-ec-lifecycle \
    /etc/sv/threshold-boot-reconcile/run \
    /usr/share/com.bongbetic.threshold/web/dist/index.html \
    /usr/share/com.bongbetic.threshold/web/dist/shim.js \
    /usr/share/glib-2.0/schemas/com.bongbetic.threshold.gschema.xml \
    /usr/share/applications/com.bongbetic.threshold.desktop \
    /usr/share/icons/hicolor/scalable/apps/com.bongbetic.threshold.svg \
    /usr/src/msi-ec-0.13.112/dkms.conf; do
    test -f "$file"
    grep -Fx "$file" /tmp/threshold-installed-files
done
test ! -e /usr/lib/systemd/system/threshold-boot-reconcile.service
test ! -e /var/service/threshold-boot-reconcile
test -f /var/lib/threshold/ec/package-owned
grep -q threshold /usr/lib/udev/rules.d/99-msi-battery.rules
python3 - <<'PY'
import gi
for namespace, version in [('Gtk', '4.0'), ('Adw', '1'), ('WebKit', '6.0'), ('Notify', '0.7'), ('Dbusmenu', '0.4')]:
    gi.require_version(namespace, version)
    __import__('gi.repository.' + namespace)
from gi.repository import Gio
assert Gio.SettingsSchemaSource.get_default().lookup('com.bongbetic.threshold', True)
PY
# Reinstallation exercises package upgrade hooks; prior-version upgrade is recorded separately.
echo 80 > /var/lib/threshold/ec/charge-threshold
mkdir -p /usr/src/threshold-foreign-probe
printf 'foreign\n' > /usr/src/threshold-foreign-probe/marker
xbps-install -yf --repository="$candidate_dir" "$expression"
test "$(cat /var/lib/threshold/ec/charge-threshold)" = 80
xbps-remove -y threshold
test "$(cat /var/lib/threshold/ec/charge-threshold)" = 80
test "$(cat /usr/src/threshold-foreign-probe/marker)" = foreign
test ! -e /usr/bin/threshold
sha256sum --check candidate.sha256
python3 - "$package" "$report" <<'PY'
from datetime import datetime, timezone
import hashlib, json, sys
from pathlib import Path
package, report = map(Path, sys.argv[1:])
report.parent.mkdir(parents=True, exist_ok=True)
report.write_text(json.dumps({
    'candidate': package.name,
    'sha256': hashlib.sha256(package.read_bytes()).hexdigest(),
    'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
    'physical': False,
    'checks': ['installation', 'owned_payload', 'runtime_typelibs', 'schema',
               'disabled_service', 'reinstall_policy', 'removal_policy', 'foreign_probe_preserved'],
    'unverified': ['previous_version_upgrade', 'hardware', 'reboot', 'desktop'],
    'result': 'pass',
}, indent=2) + '\n')
PY
