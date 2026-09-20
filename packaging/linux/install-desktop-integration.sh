#!/usr/bin/env bash
# RhythmAlign optional user-local desktop integration (CP-2).
#
#   ./install-desktop-integration.sh            install the menu entry
#   ./install-desktop-integration.sh --remove   remove it again
#
# Writes only into the current user's home directory
# (~/.local/share/applications); nothing is installed system-wide and the
# application itself never touches these paths during normal launches.
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
DESKTOP_FILE="$DATA_HOME/applications/rhythmalign.desktop"

# Escape sed replacement metacharacters so install paths containing "&"
# or "|" are inserted literally (a bare & would expand to the match).
APP_DIR_ESC="${APP_DIR//&/\\&}"
APP_DIR_ESC="${APP_DIR_ESC//|/\\|}"

case "${1:---install}" in
  --install)
    [ -f "$APP_DIR/RhythmAlign.desktop" ] || {
      echo "error: $APP_DIR/RhythmAlign.desktop not found (run from the extracted archive)" >&2
      exit 1
    }
    mkdir -p "$(dirname "$DESKTOP_FILE")"
    sed "s|__APP_DIR__|$APP_DIR_ESC|g" "$APP_DIR/RhythmAlign.desktop" > "$DESKTOP_FILE"
    if command -v update-desktop-database >/dev/null 2>&1; then
      update-desktop-database "$DATA_HOME/applications" || true
    fi
    echo "Installed user-local menu entry: $DESKTOP_FILE"
    echo "Application directory: $APP_DIR (do not move or delete it while the entry exists)"
    ;;
  --remove)
    rm -f "$DESKTOP_FILE"
    echo "Removed: $DESKTOP_FILE"
    ;;
  *)
    echo "usage: $0 [--install|--remove]" >&2
    exit 2
    ;;
esac
