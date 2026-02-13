# GD LEX – PCT File Validator

![Latest Release](https://img.shields.io/github/v/release/studio-gdlex/pct-file-validator?display_name=release)

Strumento interno **Studio GD LEX** per analizzare e correggere in modo conservativo file/cartelle destinati al deposito telematico PCT/PDUA.

## Versione

La versione visualizzata in GUI (titolo finestra + About), CLI (`gdlex-check --version`) e packaging deriva dallo stesso valore in `pyproject.toml` tramite `core/version.py`.

## Download release

Scarica sempre gli artefatti più aggiornati dalla pagina **GitHub Releases** del repository.

- **Windows**: `GDLEX-PCT-Validator-Setup.exe`
- **Debian/Ubuntu**: `gdlex-pct-validator_<version>_amd64.deb`
- **Checksum**: file `.sha256` allegati alla release

## Installazione

### Windows

1. Scarica `GDLEX-PCT-Validator-Setup.exe` dalla release.
2. Esegui il setup (installazione per-user, non richiede admin di default).
3. Avvia dal menu Start: **GD LEX - PCT Validator**.

> Nota SmartScreen/AV: su eseguibili non firmati può apparire un warning. È comportamento previsto.

### Debian / Ubuntu

```bash
sudo dpkg -i gdlex-pct-validator_<version>_amd64.deb
sudo apt -f install
```

Il pacchetto installa launcher desktop e icone hicolor (PNG multi-size + SVG scalable).

## Uso rapido

### CLI

```bash
gdlex-check <input> --sanitize --profile pdua_safe
gdlex-check --version
```

### GUI

```bash
gdlex-gui
```

Nel menu **Aiuto → Informazioni…** trovi:
- nome applicazione
- versione
- build info (commit breve + data)
- credits Studio GD LEX

## Packaging icone (no binari in git)

L’icona sorgente è solo testo SVG:
- `assets/icons/gdlex-pct-validator.svg`

I binari (`.png`, `.ico`) vengono generati **solo in build/CI** con:

```bash
python packaging/generate_icons.py --output-dir dist-installer/assets --check
```

## Sviluppo locale

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .
pytest -q
```
