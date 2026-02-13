#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="$ROOT_DIR/dist"
STAGE_DIR="$DIST_DIR/stage"
PKG_NAME="gdlex-pct-validator"
MAINTAINER="Studio GD LEX"

version_from_pyproject() {
  python3 - <<'PY'
from pathlib import Path
import re
text = Path('pyproject.toml').read_text(encoding='utf-8')
m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
print(m.group(1) if m else "")
PY
}

VERSION="${1:-$(cd "$ROOT_DIR" && version_from_pyproject)}"
if [[ -z "$VERSION" ]]; then
  echo "Errore: versione non trovata in pyproject.toml e non passata come argomento." >&2
  exit 1
fi

ARCH="$(dpkg --print-architecture 2>/dev/null || echo amd64)"
APP_PREFIX="$STAGE_DIR/opt/gdlex-pct-validator"
APP_SRC="$APP_PREFIX/app"
VENV_DIR="$APP_PREFIX/venv"

rm -rf "$STAGE_DIR"
mkdir -p "$STAGE_DIR" "$DIST_DIR"

ICON_BUILD_DIR="$DIST_DIR/iconset"
python3 "$ROOT_DIR/packaging/generate_icons.py" --output-dir "$ICON_BUILD_DIR" --check

install -d -m 755 "$APP_SRC"
rsync -a --exclude '.git' --exclude '.venv' --exclude '__pycache__' --exclude 'dist' "$ROOT_DIR/" "$APP_SRC/"

install -Dm755 "$ROOT_DIR/packaging/usr-bin/gdlex-gui" "$STAGE_DIR/usr/bin/gdlex-gui"
install -Dm644 "$ROOT_DIR/packaging/gdlex-pct-validator.desktop" "$STAGE_DIR/usr/share/applications/gdlex-pct-validator.desktop"
install -Dm644 "$ICON_BUILD_DIR/linux/gdlex-pct-validator.svg" "$STAGE_DIR/usr/share/icons/hicolor/scalable/apps/gdlex-pct-validator.svg"
for size in 16 24 32 48 64 128 256; do
  install -Dm644 "$ICON_BUILD_DIR/linux/gdlex-pct-validator-${size}.png" "$STAGE_DIR/usr/share/icons/hicolor/${size}x${size}/apps/gdlex-pct-validator.png"
done

# Permessi coerenti per il payload
find "$STAGE_DIR/opt/gdlex-pct-validator" -type d -exec chmod 755 {} +
find "$STAGE_DIR/opt/gdlex-pct-validator" -type f -exec chmod 644 {} +
chmod 755 "$STAGE_DIR/usr/bin/gdlex-gui"
chmod 644 "$STAGE_DIR/usr/share/applications/gdlex-pct-validator.desktop"

SHORT_DESC="Tool interno GD LEX per analisi/correzione conservativa file PCT/PDUA"
LONG_DESC="GD LEX PCT Validator include GUI e CLI per analisi batch, correzioni conservative e report tecnici (.gdlex)."

POSTINST="$DIST_DIR/postinst"
cat > "$POSTINST" <<'POST'
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

exit 0
POST
chmod 755 "$POSTINST"

DEB_PATH="$DIST_DIR/${PKG_NAME}_${VERSION}_${ARCH}.deb"

if command -v fpm >/dev/null 2>&1; then
  fpm -s dir -t deb \
    -n "$PKG_NAME" \
    -v "$VERSION" \
    --architecture "$ARCH" \
    --maintainer "$MAINTAINER" \
    --description "$SHORT_DESC" \
    --depends "python3" \
    --depends "python3-venv" \
    --depends "python3-pip" \
    --after-install "$POSTINST" \
    -C "$STAGE_DIR" \
    --package "$DEB_PATH" \
    .
else
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
  install -Dm755 "$POSTINST" "$CONTROL_DIR/postinst"
  dpkg-deb --build "$STAGE_DIR" "$DEB_PATH"
fi

echo "Pacchetto creato: $DEB_PATH"
