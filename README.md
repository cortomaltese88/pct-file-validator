# GD LEX – PCT File Validator (v1.0.0)

Strumento interno Studio GD LEX per analizzare e correggere in modo conservativo file/cartelle destinati al deposito telematico.
Include interfaccia GUI (PySide6) e CLI per uso operativo quotidiano su pratiche batch.

### Caratteristiche principali

- Analisi di file singoli e cartelle con profilo configurabile.
- Correzione automatica batch su tutte le righe analizzate.
- Output separato in cartella `*_conforme`, senza modificare gli originali.
- Report tecnici in `.gdlex`: `REPORT.txt`, `REPORT.json`, `MANIFEST.csv`.
- Tooltips estesi in GUI (hover) con spiegazione operativa di stato/problemi/esito.
- Stampa report e **Export PDF** 📄 direttamente dalla GUI.
- Smart Rename configurabile (attivo di default) con gestione path lunghi/collisioni.
- Riparazione ZIP (flatten struttura + normalizzazione nomi interni + rebuild).
- Warning informativi evidenziati (es. `zip_mixed_pades`).

### Installazione

#### Da sorgente (sviluppo)

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .
```

#### Da pacchetto `.deb` (Slimbook OS / Ubuntu-based)

```bash
sudo dpkg -i dist/gdlex-pct-validator_1.0.0_amd64.deb
sudo apt -f install
```

Dopo l’installazione:
- applicazione in `/opt/gdlex-pct-validator/`
- launcher CLI/GUI: `gdlex-gui`
- voce menu desktop: **GD LEX – Verifica Deposito PCT/PDUA**

### Uso rapido

#### CLI

Comando tipico:

```bash
gdlex-check <input> --sanitize --profile pdua_safe
```

Esempio con output custom:

```bash
gdlex-check fascicolo --sanitize --profile pdua_safe --output /percorso/output
```

Output default:
- input cartella → `<parent>/<nome_input>_conforme`
- input file → `<parent>/<stem_file>_conforme`

#### GUI

```bash
gdlex-gui
```

Flusso operativo consigliato:
1. Drag&drop di file/cartella (oppure caricamento da pulsanti).
2. `Analizza`.
3. `Correggi automaticamente`.

La tabella resta popolata e mostra per ogni riga: stato finale, esito correzione, nuovo nome, output, azioni.

### Output e Report

L’applicazione non modifica i file originali: crea sempre un output separato `*_conforme`.

Dentro la cartella output viene creata una directory tecnica `.gdlex` con:
- `REPORT.txt` (report tecnico leggibile)
- `REPORT.json` (strutturato)
- `MANIFEST.csv` (tracciamento sintetico)

Significato esiti correzione:
- `NON ESEGUITA`: analisi effettuata, correzione non lanciata.
- `OK`: file già adeguato, copiato senza correzioni sostanziali.
- `CORRETTA`: correzione applicata con esito positivo.
- `PARZIALE`: output prodotto ma con warning/error residui.
- `IMPOSSIBILE`: correzione automatica non eseguibile per quel file.
- `ERRORE`: errore tecnico durante la correzione.

### Smart Rename

Smart Rename è attivo di default e configurabile da GUI (Impostazioni).

Trigger principali:
- superamento `max_filename_len`
- pattern UUID/random nel basename
- superamento `max_output_path_len`

Comportamento:
- normalizzazione conservativa del nome
- proposta di nomi più leggibili (es. ricevute PagoPA)
- prevenzione duplicazioni (evita `_signed_signed`)
- gestione collisioni con suffissi incrementali (`_02`, `_03`, ...)

Nota operativa: la mitigazione dei path lunghi riduce problemi tipici in OneDrive e cartelle annidate profonde.

### Limiti noti

- `zip_mixed_pades` è warning informativo: non viene eseguito split automatico dei contenuti ZIP.
- I controlli PDF sono strutturali/operativi (non validazione forense completa).

### Struttura progetto

- `core/` — validazione, sanitizzazione, reportistica.
- `gui/` — interfaccia desktop PySide6.
- `cli/` — comandi terminale.
- `configs/` — profili YAML.
- `packaging/` — script/build assets `.deb` (launcher, desktop file).
- `assets/icons/` — icone applicazione.
- `tests/` — suite `pytest`.

### Avvertenze

Tool tecnico interno Studio GD LEX.
Non fornisce garanzie di accettazione del deposito e non sostituisce la verifica professionale finale sul fascicolo.

### Troubleshooting (KDE / Wayland)

- Se il launcher non parte, verificare runtime locale del pacchetto:
  - `/opt/gdlex-pct-validator/venv/bin/python`
- Avvio diretto diagnostico:

```bash
/opt/gdlex-pct-validator/venv/bin/python -m gui.app
```

- In ambienti con policy grafiche restrittive, provare sessione X11 o avvio da terminale per leggere eventuali errori Qt.

### Release GitHub (v1.0.0)

Workflow consigliato:

```bash
git tag v1.0.0
git push origin v1.0.0
```

Con il workflow CI (`.github/workflows/release-deb.yml`):
- esegue `compileall` + `pytest -q`
- genera il `.deb`
- crea release **GD LEX PCT Validator 1.0.0**
- allega l’asset `.deb`

### Changelog

#### v1.0.0 — Prima release stabile

- Analisi file/cartelle con profili configurabili.
- Correzione batch con output separato `*_conforme`.
- Report tecnici (`REPORT.txt`, `REPORT.json`, `MANIFEST.csv`) in `.gdlex`.
- GUI dark con tabella risultati persistente e tooltips estesi.
- Stampa report e Export PDF 📄.
- Smart Rename configurabile con mitigazione path lunghi/collisioni.
- Riparazione ZIP (flatten + normalizzazione + rebuild).
