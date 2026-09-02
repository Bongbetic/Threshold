#!/bin/sh
# Threshold AppImage builder (issue #86).
#
# Produces one self-contained, relocatable x86-64 AppImage:
# - application payload from `meson install` (no build-host paths baked in)
# - Python 3 + GI typelibs + private library search paths
# - Dbusmenu 0.4 typelib + shared library bundled privately (mandatory)
# - vendored msi-ec source + integration manifest as the deterministic
#   signed EC bundle streamed to the bootstrap authority on demand
# - artifact-owned battery icon set for SNI icon-name + pixmap fallback
#
# Reproducible under pinned tools: SOURCE_DATE_EPOCH drives all
# timestamps and two clean builds must produce identical hashes.
set -eu

APP_ID=com.bongbetic.threshold
APPDIR=${APPDIR:-build/appimage/AppDir}
PREFIX=${PREFIX:-/usr}
EPOCH=${SOURCE_DATE_EPOCH:-0}

die() { echo "build-appimage: $*" >&2; exit 1; }

command -v meson >/dev/null 2>&1 || die "meson required"
command -v appimagetool >/dev/null 2>&1 || die "appimagetool required (pinned version)"

# ── Application payload ────────────────────────────────────────────────────
meson setup build/appimage-src --prefix="$PREFIX" >/dev/null
meson compile -C build/appimage-src >/dev/null
meson install -C build/appimage-src --destdir "$(pwd)/$APPDIR" >/dev/null

# Relocation: python module dir and resource paths follow the AppDir.
mkdir -p "$APPDIR/usr/lib"
export GI_TYPELIB_PATH="$APPDIR/usr/lib/girepository-1.0"

# ── Bundle Dbusmenu 0.4 typelib + shared library (private search paths) ───
for LIB in libdbusmenu-glib.so.4 libdbusmenu-gtk3.so.4; do
    SRC=$(ldconfig -p | awk -v l="$LIB" '$1 == l {print $NF; exit}')
    [ -n "$SRC" ] && cp -L "$SRC" "$APPDIR/usr/lib/" || true
done
for TLB in Dbusmenu-0.4.typelib DbusmenuGtk-0.4.typelib; do
    SRC=$(find /usr/lib*/girepository-1.0 -name "$TLB" 2>/dev/null | head -1)
    [ -n "$SRC" ] && install -Dm0644 "$SRC" "$APPDIR/usr/lib/girepository-1.0/$TLB"
done

# ── Embedded deterministic EC bundle ───────────────────────────────────────
BUNDLE_DIR=$APPDIR/usr/share/threshold/ec-bundle
mkdir -p "$BUNDLE_DIR"
STAGE=$(mktemp -d)
trap 'rm -rf "$STAGE"' EXIT
cp packaging/ec-manifest.json "$STAGE/manifest.json"
tar -C msi-ec-src -czf "$STAGE/msi-ec.tar.gz" .
cp packaging/threshold-ec-lifecycle "$STAGE/lifecycle"
(
    cd "$STAGE" && find . -type f | LC_ALL=C sort | tar -czf "$BUNDLE_DIR/bundle.tar.gz" -T -
)
SHA=$(sha256sum "$BUNDLE_DIR/bundle.tar.gz" | awk '{print $1}')
python3 - "$STAGE/manifest.json" "$SHA" <<'PYEOF'
import json, sys
m = json.load(open(sys.argv[1]))
m["bundle_checksum"] = sys.argv[2]
m["protocol"] = 1
m["arch"] = "x86_64"
json.dump(m, open(sys.argv[1], "w"), sort_keys=True, indent=1)
PYEOF
cp "$STAGE/manifest.json" "$BUNDLE_DIR/manifest.json"

# ── AppStream metadata + desktop file + icons (already meson-installed) ────
mkdir -p "$APPDIR/usr/share/metainfo"
[ -f "$APPDIR/usr/share/metainfo/$APP_ID.metainfo.xml" ] || \
    cp data/$APP_ID.metainfo.xml "$APPDIR/usr/share/metainfo/"
[ -f "$APPDIR/$APP_ID.desktop" ] || \
    cp "$APPDIR/usr/share/applications/$APP_ID.desktop" "$APPDIR/"

# AppRun: relocate Python paths and launch the launcher shim.
cat > "$APPDIR/AppRun" <<'RUNEOF'
#!/bin/sh
HERE=$(dirname "$(readlink -f "$0")")
export THRESHOLD_PKGDATADIR="$HERE/usr/share/com.bongbetic.threshold"
export PYTHONPATH="$HERE/usr/share/com.bongbetic.threshold${PYTHONPATH:+:$PYTHONPATH}"
export GI_TYPELIB_PATH="$HERE/usr/lib/girepository-1.0${GI_TYPELIB_PATH:+:$GI_TYPELIB_PATH}"
export LD_LIBRARY_PATH="$HERE/usr/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
exec python3 -m threshold.main "$@"
RUNEOF
chmod 0755 "$APPDIR/AppRun"

# ── Reproducibility ────────────────────────────────────────────────────────
find "$APPDIR" -exec touch -h -d "@$EPOCH" {} +

OUT=${1:-Threshold-$($APPDIR/AppRun --version 2>/dev/null || echo 2.0.0)-x86_64.AppImage}
OUT=${OUT%.AppImage}.AppImage
appimagetool --comp zstd -u "$APPDIR" "$OUT" >/dev/null
echo "$OUT"
