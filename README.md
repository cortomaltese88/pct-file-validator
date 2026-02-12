# GD LEX – PCT File Validator (v1.0.0)

Strumento interno Studio GD LEX per analizzare e correggere in modo conservativo file/cartelle destinati al deposito telematico.
Include interfaccia GUI (PySide6) e CLI per uso operativo quotidiano su pratiche batch.

### Caratteristiche principali

- Analisi di file singoli e cartelle con profilo configurabile.
- Correzione automatica batch su tutte le righe analizzate.
- Output separato in cartella `*_conforme`, senza modificare gli originali.
- Report tecnici strutturati in `.gdlex`:
  - `REPORT.txt`
  - `REPORT.json`
  - `MANIFEST.csv`
- Tooltips estesi in GUI (hover) con spiegazione operativa di stato/problemi/esito.
- Stampa report e **Export PDF** 📄 direttamente dalla GUI.
- Smart Rename configurabile (attivo di default) con gestione path lunghi e collisioni.
- Riparazione ZIP: flatten struttura, normalizzazione nomi interni, ricreazione archivio.
- Evidenza warning informativi (es. `zip_mixed_pades`) senza bloccare automaticamente il flusso.

### Installazione

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Uso rapido

#### CLI

Comando tipico:

```bash
gdlex-check <input> --sanitize --profile pdua_safe
```

Esempio:

```bash
gdlex-check fascicolo --sanitize --profile pdua_safe
```

Output default (consigliato):
- input cartella → `<parent>/<nome_input>_conforme`
- input file → `<parent>/<stem_file>_conforme`

Output custom:

```bash
gdlex-check fascicolo --sanitize --profile pdua_safe --output /percorso/output
```

In questo caso l’output viene creato in:
`/percorso/output/<basename_input>_conforme`

#### GUI

```bash
gdlex-gui
```

Flusso operativo consigliato:
1. Drag&drop di file/cartella (oppure caricamento da pulsanti).
2. `Analizza`.
3. `Correggi automaticamente`.

Dopo la correzione, la tabella resta popolata e mostra per ogni riga: stato finale, esito correzione, nuovo nome, output, azioni.

### Output e Report

L’applicazione non modifica i file originali: crea sempre un output separato `*_conforme`.

Dentro la cartella output viene creata una directory tecnica `.gdlex` con:
- `REPORT.txt` (report tecnico leggibile)
- `REPORT.json` (strutturato, utile per integrazioni)
- `MANIFEST.csv` (tracciamento sintetico file/output/esiti)

Significato esiti correzione:
- `NON ESEGUITA`: analisi effettuata, correzione non ancora lanciata.
- `OK`: file già adeguato, copiato senza necessità di correzioni sostanziali.
- `CORRETTA`: correzione applicata con esito positivo.
- `PARZIALE`: output prodotto ma con warning/error residui.
- `IMPOSSIBILE`: correzione automatica non eseguibile per quel file.
- `ERRORE`: errore tecnico durante la correzione.

### Smart Rename

Smart Rename è attivo di default e configurabile da GUI (Impostazioni).

Trigger principali:
- superamento soglia `max_filename_len`
- pattern UUID/random nel basename
- superamento soglia `max_output_path_len`

Comportamento:
- normalizzazione conservativa del nome
- proposta di nomi più leggibili in casi noti (es. ricevute PagoPA)
- prevenzione duplicazioni (es. evita `_signed_signed`)
- gestione collisioni con suffissi incrementali (`_02`, `_03`, ...)

Nota operativa: il controllo sulla lunghezza del path aiuta a ridurre problemi tipici di ambienti sincronizzati (es. OneDrive) e cartelle annidate profonde.

### Limiti noti

- `zip_mixed_pades` è trattato come warning informativo: non viene effettuato split automatico dei contenuti ZIP.
- I controlli PDF sono strutturali/operativi (non costituiscono validazione forense completa del documento).

### Struttura progetto

- `core/` — logica di validazione, sanitizzazione, reportistica.
- `gui/` — interfaccia desktop PySide6.
- `cli/` — entrypoint e comandi terminale.
- `configs/` — profili YAML.
- `tests/` — suite `pytest`.

### Avvertenze

Questo software è un supporto tecnico-operativo interno.
Non fornisce garanzie di accettazione del deposito e non sostituisce la verifica professionale finale sul fascicolo da parte dell’operatore.

### Changelog

#### v1.0.0 — Prima release stabile

- Analisi file/cartelle con profili configurabili.
- Correzione batch con output separato `*_conforme`.
- Report tecnici (`REPORT.txt`, `REPORT.json`, `MANIFEST.csv`) in `.gdlex`.
- GUI dark con tabella risultati persistente e tooltips estesi.
- Stampa report e Export PDF 📄 da interfaccia.
- Smart Rename configurabile con mitigazione path lunghi/collisioni.
- Riparazione ZIP (flatten + normalizzazione + rebuild).
