#!/usr/bin/env bash
# CP-2: package the Linux PyInstaller onedir build into the beta tar.gz.
#
# Usage (repo root, after `pyinstaller RhythmAlign.spec --clean --noconfirm`):
#   bash packaging/linux/package_artifact.sh [dist-dir]
#
# Produces dist/RhythmAlign-v<VERSION>-linux-x86_64-beta.tar.gz (+ .sha256).
# The archive contains a single top-level RhythmAlign/ directory with the
# onedir build plus launch/desktop-integration helpers. Entry permissions
# (notably the executable bit) come from PyInstaller's output and are
# preserved by tar; timestamps are normalized and gzip -n is used so the
# archive of identical content is byte-stable.
set -euo pipefail

cd "$(dirname "$0")/../.."

DIST_DIR="${1:-dist}"
APP_DIR="$DIST_DIR/RhythmAlign"
STAGE="$DIST_DIR/_stage"

[ -x "$APP_DIR/RhythmAlign" ] || {
  echo "error: $APP_DIR/RhythmAlign not found — build with: pyinstaller RhythmAlign.spec --clean --noconfirm" >&2
  exit 1
}

VERSION="$(python3 -c 'import app_info; print(app_info.APP_VERSION)')"
ARTIFACT="$DIST_DIR/RhythmAlign-v${VERSION}-linux-x86_64-beta"

rm -rf "$STAGE"
mkdir -p "$STAGE/RhythmAlign"
cp -a "$APP_DIR/." "$STAGE/RhythmAlign/"

# Launch/docs helpers shipped alongside the application.
cp packaging/linux/README-linux.txt "$STAGE/RhythmAlign/"
cp packaging/linux/RhythmAlign.desktop "$STAGE/RhythmAlign/"
cp packaging/linux/install-desktop-integration.sh "$STAGE/RhythmAlign/"
cp LICENSE "$STAGE/RhythmAlign/"
chmod +x "$STAGE/RhythmAlign/RhythmAlign" "$STAGE/RhythmAlign/install-desktop-integration.sh"

# Normalize timestamps so identical content produces a stable archive.
find "$STAGE" -depth -exec touch -h -d "@1704067200" {} +

( cd "$STAGE" && tar --sort=name --owner=0 --group=0 --numeric-owner -cf - RhythmAlign ) \
  | gzip -n -9 > "$ARTIFACT.tar.gz"
sha256sum "$ARTIFACT.tar.gz" > "$ARTIFACT.tar.gz.sha256"
rm -rf "$STAGE"

echo "packaged: $ARTIFACT.tar.gz"
cat "$ARTIFACT.tar.gz.sha256"
