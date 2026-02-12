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
PYTHON_BIN="${PYTHON_BIN:-}"
if [[ -z "$PYTHON_BIN" ]]; then
  if command -v python3.11 >/dev/null 2>&1 && python3.11 -V >/dev/null 2>&1; then
    PYTHON_BIN="python3.11"
  else
    PYTHON_BIN="python3"
  fi
fi

APP_PREFIX="$STAGE_DIR/opt/gdlex-pct-validator"
APP_SRC="$APP_PREFIX/app"
VENV_DIR="$APP_PREFIX/venv"

rm -rf "$STAGE_DIR"
mkdir -p "$STAGE_DIR" "$DIST_DIR"

mkdir -p "$APP_SRC"
rsync -a --exclude '.git' --exclude '.venv' --exclude '__pycache__' --exclude 'dist' "$ROOT_DIR/" "$APP_SRC/"

"$PYTHON_BIN" -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --no-index --upgrade pip setuptools wheel || true
if ! "$VENV_DIR/bin/pip" install --no-deps --no-build-isolation "$APP_SRC"; then
  echo "Errore: installazione nel venv fallita. Verificare versione Python (richiesta >=3.11)." >&2
  exit 1
fi

install -Dm755 "$ROOT_DIR/packaging/usr-bin/gdlex-gui" "$STAGE_DIR/usr/bin/gdlex-gui"
install -Dm644 "$ROOT_DIR/packaging/gdlex-pct-validator.desktop" "$STAGE_DIR/usr/share/applications/gdlex-pct-validator.desktop"
install -Dm644 "$ROOT_DIR/assets/icons/gdlex-pct-validator.svg" "$STAGE_DIR/usr/share/icons/hicolor/scalable/apps/gdlex-pct-validator.svg"

if [[ -f "$ROOT_DIR/assets/icons/gdlex-pct-validator-256.png" ]]; then
  install -Dm644 "$ROOT_DIR/assets/icons/gdlex-pct-validator-256.png" "$STAGE_DIR/usr/share/icons/hicolor/256x256/apps/gdlex-pct-validator.png"
fi

SHORT_DESC="Tool interno GD LEX per analisi/correzione conservativa file PCT/PDUA"
LONG_DESC="GD LEX PCT Validator include GUI e CLI per analisi batch, correzioni conservative e report tecnici (.gdlex)."

POSTINST="$DIST_DIR/postinst"
cat > "$POSTINST" <<'POST'
#!/usr/bin/env bash
set -e
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
Depends: python3, python3-venv
Description: $SHORT_DESC
 $LONG_DESC
EOF
  install -Dm755 "$POSTINST" "$CONTROL_DIR/postinst"
  dpkg-deb --build "$STAGE_DIR" "$DEB_PATH"
fi

echo "Pacchetto creato: $DEB_PATH"
