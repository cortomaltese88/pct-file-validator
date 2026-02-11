# GD LEX – Verifica Deposito PCT/PDUA

Applicazione desktop + CLI per Linux, orientata a controllo conservativo dei file destinati al deposito telematico PCT/PDUA.

## Caratteristiche MVP

- Analisi file/cartelle con regole da YAML.
- Segnalazione incompatibilità note (estensioni, ZIP non flat, nomi, PDF invalidi/cifrati).
- Normalizzazione conservativa dei nomi file.
- Creazione copia sanitizzata **senza alterare originali**.
- Backup automatico, `manifest.json`, `report.txt`.
- GUI PySide6 sobria (drag&drop, tabella stato, log tecnico).
- CLI `gdlex-check` con modalità analyze/sanitize/json/dry-run.

## Installazione

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Uso CLI

Comando base:

```bash
gdlex-check input_folder --output out_folder --profile pdua_safe
```

Esempi utili:

```bash
gdlex-check fascicolo/ --analyze --report
gdlex-check fascicolo/ --sanitize --profile pdua_safe
gdlex-check fascicolo/ --sanitize --json --dry-run
```

Opzioni supportate:

- `--analyze`
- `--sanitize`
- `--report`
- `--strict`
- `--profile`
- `--json`
- `--dry-run`

## Uso GUI

```bash
gdlex-gui
```

Flusso:
1. Trascinare file/cartella nell’area Drag & Drop.
2. Cliccare **Analizza** per controllo.
3. Cliccare **Crea Copia Conforme** per output sanitizzato.
4. Consultare tabella, dettagli e log tecnico.

## Struttura progetto

- `core/`: regole, validatori, sanitizzazione, report
- `gui/`: interfaccia PySide6
- `cli/`: parser e comando shell
- `configs/`: profili YAML
- `tests/`: pytest

## Limiti noti MVP

- Rilevazione firma PAdES euristica (pattern interno PDF).
- Verifica PDF basata su controlli strutturali leggeri (header/trailer/encryption marker).
- In GUI il profilo è fisso su `pdua_safe` (CLI supporta tutti i profili YAML).
- `--output` in CLI riservato per estensione futura.

## Avvertenze legali

Il software fornisce un supporto tecnico-informatico conservativo e non sostituisce il controllo professionale del difensore sulla conformità del deposito telematico.
