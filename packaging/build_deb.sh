#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="$ROOT_DIR/dist"
STAGE_DIR="$DIST_DIR/stage"
PKG_NAME="gdlex-pct-validator"
MAINTAINER="Studio GD LEX"

VERSION="${APP_VERSION:-${1:-}}"
if [[ -z "$VERSION" ]]; then
  echo "Errore: versione assente. Passa APP_VERSION o argomento (derivato da tag git)." >&2
  exit 1
fi
VERSION="${VERSION#v}"

ARCH="$(dpkg --print-architecture 2>/dev/null || echo amd64)"
APP_PREFIX="$STAGE_DIR/opt/gdlex-pct-validator"
APP_SRC="$APP_PREFIX/app"


BUILD_DATE="${BUILD_DATE:-$(date -u +%Y-%m-%d)}"
BUILD_CHANNEL="deb"
BUILD_INFO_FILE="$ROOT_DIR/core/_build_info.py"

RESTORE_BUILD_INFO=0
BACKUP_BUILD_INFO=""
if [[ -f "$BUILD_INFO_FILE" ]]; then
  RESTORE_BUILD_INFO=1
  BACKUP_BUILD_INFO="$(mktemp)"
  cp "$BUILD_INFO_FILE" "$BACKUP_BUILD_INFO"
fi

cat > "$BUILD_INFO_FILE" <<EOF
"""Generated at packaging time. Do not edit manually."""
__version__ = "$VERSION"
__build__ = "$BUILD_DATE"
__channel__ = "$BUILD_CHANNEL"
EOF

cleanup_build_info() {
  if [[ "$RESTORE_BUILD_INFO" -eq 1 ]]; then
    cp "$BACKUP_BUILD_INFO" "$BUILD_INFO_FILE"
    rm -f "$BACKUP_BUILD_INFO"
  else
    rm -f "$BUILD_INFO_FILE"
  fi
}
trap cleanup_build_info EXIT

rm -rf "$STAGE_DIR"
mkdir -p "$STAGE_DIR" "$DIST_DIR"

ICON_BUILD_DIR="$DIST_DIR/icons"
python3 "$ROOT_DIR/tools/generate_icons.py" --output-dir "$ICON_BUILD_DIR" --check

install -d -m 755 "$APP_SRC"
rsync -a --exclude '.git' --exclude '.venv' --exclude '__pycache__' --exclude 'dist' "$ROOT_DIR/" "$APP_SRC/"

install -Dm755 "$ROOT_DIR/packaging/usr-bin/gdlex-gui" "$STAGE_DIR/usr/bin/gdlex-gui"
install -Dm644 "$ROOT_DIR/packaging/gdlex-pct-validator.desktop" "$STAGE_DIR/usr/share/applications/gdlex-pct-validator.desktop"
for size in 16 24 32 48 64 128 256; do
  install -Dm644 "$ICON_BUILD_DIR/hicolor/${size}x${size}/apps/gdlex-pct-validator.png" "$STAGE_DIR/usr/share/icons/hicolor/${size}x${size}/apps/gdlex-pct-validator.png"
done

SHORT_DESC="Tool interno GD LEX per analisi/correzione conservativa file PCT/PDUA"
LONG_DESC="GD LEX PCT Validator include GUI e CLI per analisi batch, correzioni conservative e report tecnici (.gdlex)."

CONTROL_DIR="$STAGE_DIR/DEBIAN"
mkdir -p "$CONTROL_DIR"
cat > "$CONTROL_DIR/control" <<EOF
Package: $PKG_NAME
Version: $VERSION
Section: utils
Priority: optional
Architecture: $ARCH
Maintainer: $MAINTAINER
Depends: python3, python3-venv, python3-pip
Description: $SHORT_DESC
 $LONG_DESC
EOF

cat > "$CONTROL_DIR/postinst" <<'POST'
#!/usr/bin/env bash
set -e
APP_ROOT="/opt/gdlex-pct-validator"
VENV_DIR="$APP_ROOT/venv"
APP_DIR="$APP_ROOT/app"
VENV_PY="$VENV_DIR/bin/python"

if [[ ! -x "$VENV_PY" ]]; then
  python3 -m venv "$VENV_DIR"
  "$VENV_PY" -m pip install --upgrade pip
  "$VENV_DIR/bin/pip" install -e "$APP_DIR"
fi

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database /usr/share/applications || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  gtk-update-icon-cache -q /usr/share/icons/hicolor || true
fi
POST
chmod 755 "$CONTROL_DIR/postinst"

DEB_PATH="$DIST_DIR/${PKG_NAME}_${VERSION}_${ARCH}.deb"
dpkg-deb --build "$STAGE_DIR" "$DEB_PATH"

echo "Pacchetto creato: $DEB_PATH"
