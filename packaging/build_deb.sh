#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="$ROOT_DIR/dist"
STAGE_DIR="$DIST_DIR/stage"
PKG_NAME="gdlex-pct-validator"
MAINTAINER="Studio GD LEX <info@studiogdlex.it>"

VERSION="${APP_VERSION:-${1:-}}"
if [[ -z "$VERSION" ]]; then
  echo "Errore: versione assente. Passa APP_VERSION o argomento (derivato da tag git)." >&2
  exit 1
fi
VERSION="${VERSION#v}"

ARCH="$(dpkg --print-architecture 2>/dev/null || echo amd64)"
APP_PREFIX="$STAGE_DIR/usr/lib/gdlex-pct-validator"
APP_SRC="$APP_PREFIX/app"
DOC_DIR="$STAGE_DIR/usr/share/doc/$PKG_NAME"
MAN_DIR="$STAGE_DIR/usr/share/man/man1"


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

require_path() {
  local rel_path="$1"
  if [[ ! -e "$ROOT_DIR/$rel_path" ]]; then
    echo "Errore: path essenziale mancante: $rel_path" >&2
    exit 1
  fi
}

copy_path() {
  local rel_path="$1"
  local src="$ROOT_DIR/$rel_path"

  if [[ ! -e "$src" ]]; then
    return 0
  fi

  if [[ -d "$src" ]]; then
    (
      cd "$ROOT_DIR"
      tar \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='.pytest_cache' \
        --exclude='.ruff_cache' \
        -cf - "$rel_path"
    ) | (
      cd "$APP_SRC"
      tar -xf -
    )
    return 0
  fi

  install -d -m 755 "$APP_SRC/$(dirname "$rel_path")"
  cp -a "$src" "$APP_SRC/$rel_path"
}

install_doc() {
  local rel_path="$1"
  local src="$ROOT_DIR/$rel_path"

  if [[ ! -f "$src" ]]; then
    echo "Errore: file documentazione mancante: $rel_path" >&2
    exit 1
  fi

  install -Dm644 "$src" "$DOC_DIR/$(basename "$rel_path")"
}

REQUIRED_APP_PATHS=(
  "pyproject.toml"
  "README.md"
  "LICENSE"
  "THIRD_PARTY_LICENSES.md"
  "core"
  "cli"
  "gui"
  "configs"
  "assets"
)

install -d -m 755 "$APP_SRC" "$DOC_DIR"

for rel_path in "${REQUIRED_APP_PATHS[@]}"; do
  require_path "$rel_path"
  copy_path "$rel_path"
done

install_doc "README.md"
install_doc "LICENSE"
install_doc "THIRD_PARTY_LICENSES.md"
gzip -9n -c "$ROOT_DIR/debian/changelog" > "$DOC_DIR/changelog.gz"
install -d -m 755 "$MAN_DIR"
gzip -9n -c "$ROOT_DIR/packaging/man/gdlex-gui.1" > "$MAN_DIR/gdlex-gui.1.gz"
cat > "$DOC_DIR/copyright" <<'EOF'
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: gdlex-pct-validator
Source: https://github.com/cortomaltese88/pct-file-validator

Files: *
Copyright: 2026 Studio GD LEX
License: GPL-3.0-or-later
 This package is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.
 .
 On Debian systems, the full text of the GNU General Public License
 version 3 can be found in /usr/share/common-licenses/GPL-3.
EOF

install -Dm755 "$ROOT_DIR/packaging/usr-bin/gdlex-gui" "$STAGE_DIR/usr/bin/gdlex-gui"
install -Dm644 "$ROOT_DIR/packaging/gdlex-pct-validator.desktop" "$STAGE_DIR/usr/share/applications/gdlex-pct-validator.desktop"
for size in 16 24 32 48 64 128 256; do
  install -Dm644 "$ICON_BUILD_DIR/hicolor/${size}x${size}/apps/gdlex-pct-validator.png" "$STAGE_DIR/usr/share/icons/hicolor/${size}x${size}/apps/gdlex-pct-validator.png"
done

SHORT_DESC="Tool desktop GD LEX per verifica deposito PCT/PDUA"
LONG_DESC_1="GD LEX PCT Validator include GUI e CLI per analisi batch,"
LONG_DESC_2="correzioni conservative e report tecnici (.gdlex)."

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
 $LONG_DESC_1
 $LONG_DESC_2
EOF

cat > "$CONTROL_DIR/postinst" <<'POST'
#!/bin/bash
set -e
APP_ROOT="/usr/lib/gdlex-pct-validator"
VENV_DIR="$APP_ROOT/venv"
APP_DIR="$APP_ROOT/app"
VENV_PY="$VENV_DIR/bin/python"
export SETUPTOOLS_SCM_PRETEND_VERSION_FOR_GDLEX_PCT_VALIDATOR="__APP_VERSION__"

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
sed -i "s/__APP_VERSION__/$VERSION/g" "$CONTROL_DIR/postinst"
chmod 755 "$CONTROL_DIR/postinst"

DEB_PATH="$DIST_DIR/${PKG_NAME}_${VERSION}_${ARCH}.deb"
find "$STAGE_DIR" -type d -exec chmod 755 {} +
find "$STAGE_DIR" -type f -exec chmod 644 {} +
chmod 755 "$STAGE_DIR/usr/bin/gdlex-gui"
chmod 755 "$CONTROL_DIR/postinst"
chown -R root:root "$STAGE_DIR" 2>/dev/null || true
dpkg-deb --root-owner-group --build "$STAGE_DIR" "$DEB_PATH"

echo "Pacchetto creato: $DEB_PATH"
