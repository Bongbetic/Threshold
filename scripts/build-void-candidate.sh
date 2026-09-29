#!/bin/bash
# Run ONLY inside a disposable Void container: ethereal uses its root filesystem.
set -euo pipefail
source_root=$(realpath "$1")
archive=$(realpath "$2")
out=$(realpath -m "$3")
test -f /run/.containerenv || test -f /.dockerenv
source "$source_root/packaging/void/build-pins.env"
test ! -e "$out"
xbps-install -Suy xbps
xbps-install -Sy bash git python3
xbps-install -Sy -R https://repo-default.voidlinux.org/current/bootstrap base-chroot
build_root=$(mktemp -d)
git init -q "$build_root/void-packages"
git -C "$build_root/void-packages" fetch -q --depth 1 https://github.com/void-linux/void-packages.git "$VOID_PACKAGES_COMMIT"
git -C "$build_root/void-packages" checkout -q --detach FETCH_HEAD
python3 "$source_root/scripts/prepare-void-source.py" "$source_root" "$archive" "$build_root/void-packages"
cd "$build_root/void-packages"
ln -s / masterdir
xbps-uhelper arch > /.xbps_chroot_init
export XBPS_CHROOT_CMD=ethereal XBPS_ALLOW_CHROOT_BREAKOUT=yes
./xbps-src binary-bootstrap
# Preserve build dependencies until their exact versions are recorded.
./xbps-src -C pkg threshold 2>&1 | tee "$build_root/build.log"
if grep -q '=> ERROR:' "$build_root/build.log"; then
    echo "xbps-src reported a failed hook; refusing candidate output" >&2
    exit 1
fi
version=$(sed -n 's/^version=//p' srcpkgs/threshold/template)
revision=$(sed -n 's/^revision=//p' srcpkgs/threshold/template)
mkdir "$out"
cp "hostdir/binpkgs/threshold-${version}_${revision}.x86_64.xbps" "$out/"
xbps-rindex -a "$out/threshold-${version}_${revision}.x86_64.xbps"
xbps-query -l > "$out/void-dependencies.txt"
python3 - "$out" "$archive" "$VOID_PACKAGES_COMMIT" "$VOID_IMAGE" "$PWD/srcpkgs/threshold/template" <<'PY'
import hashlib, json, sys
from pathlib import Path
out, archive = map(Path, sys.argv[1:3])
(out / 'void-build.json').write_text(json.dumps({
    'source_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
    'void_packages_commit': sys.argv[3], 'image': sys.argv[4],
    'dependencies': 'void-dependencies.txt',
    'build_template_sha256': hashlib.sha256(Path(sys.argv[5]).read_bytes()).hexdigest(),
}, indent=2) + '\n')
PY
(cd "$out" && sha256sum *.xbps x86_64-repodata void-build.json void-dependencies.txt > candidate.sha256)
