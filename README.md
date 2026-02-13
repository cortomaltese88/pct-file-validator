# GD LEX – Verifica Deposito PCT/PDUA

![Latest Release](https://img.shields.io/github/v/release/studio-gdlex/pct-file-validator?display_name=release)

Tool desktop (GUI + CLI) per analisi/correzione conservativa dei file per deposito telematico.

## Download

Dalla pagina Releases:
- **Windows**: `pct-file-validator-<version>-windows.exe`
- **Debian/Ubuntu**: `pct-file-validator_<version>_amd64.deb`
- **Checksum**: file `.sha256` allegati

## Installazione rapida

### Windows
1. Scarica `pct-file-validator-<version>-windows.exe`
2. Esegui il setup per-user
3. Avvia dal menu Start

> SmartScreen/AV può mostrare warning sugli eseguibili non firmati.

### Debian / Ubuntu

```bash
sudo dpkg -i pct-file-validator_<version>_amd64.deb
sudo apt -f install
```

## Uso

```bash
gdlex-gui
gdlex-check --version
```

## Icon & Release System

Il sistema di release è hardenizzato e deterministico:

- **Single source icona**: `assets/icons/master.base64` (payload testuale nel repository).
- **Generazione automatica**: `tools/generate_icons.py` ricostruisce `master.png` in `dist/icons/` e genera PNG Linux (`256,128,64,48,32,24,16`) + ICO Windows multi-size (`dist/icons/app.ico`).
- **Nessun `.ico` manuale**: i binari icona vengono prodotti solo in CI/build (`dist/icons/...`) e non sono versionati in git.
- **Single source versione**: la versione deriva **solo dal tag Git** (`GITHUB_REF_NAME`/`APP_VERSION`).
- **Artifact versionati obbligatori**:
  - `pct-file-validator_<version>_amd64.deb`
  - `pct-file-validator-<version>-windows.exe`
- **No passi manuali**: workflow GitHub Actions estrae versione, genera icone, builda pacchetti e pubblica asset.

## Sviluppo locale

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
pytest -q
```
