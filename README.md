# GD LEX – Verifica Deposito PCT/PDUA

Applicazione desktop + CLI per Linux, orientata al controllo conservativo dei file destinati al deposito telematico PCT/PDUA.

## Caratteristiche principali

- Analisi file/cartelle con regole da configurazione.
- Segnalazione incompatibilità note (estensioni, ZIP non flat, nomi, PDF invalidi/cifrati).
- Normalizzazione conservativa dei nomi file.
- Correzione automatica batch su **tutte le righe analizzate**.
- Output separato dall'input, senza modificare gli originali.
- Report dettagliati: `REPORT.txt`, `REPORT.json`, `MANIFEST.csv`.
- GUI PySide6 dark professionale + CLI `gdlex-check`.

## Installazione

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Uso CLI

Comando base:

```bash
gdlex-check input_folder --sanitize --profile pdua_safe
```

Output default:
- input cartella -> `<parent>/<nome_input>_conforme`
- input file -> `<parent>/<stem_file>_conforme`

Output custom:

```bash
gdlex-check fascicolo --sanitize --output /percorso/output
```

In questo caso l'output è creato in:
`/percorso/output/<basename_input>_conforme`

## Uso GUI

```bash
gdlex-gui
```

Flusso:
1. Trascinare file/cartella oppure usare i pulsanti di caricamento.
2. Cliccare **Analizza**.
3. Cliccare **Correggi automaticamente** per processare tutte le righe.
4. Verificare colonna **Esito correzione** e log tecnico.

## Come funziona “Correggi automaticamente”

La pipeline lavora su tutti i risultati di analisi:

1. Crea cartella output separata (`*_conforme`).
2. Per ogni file prova una correzione conservativa:
   - normalizzazione nome file,
   - riparazione ZIP (flatten, normalizzazione nomi interni, ricreazione archivio).
3. Rianalizza l'output del singolo file.
4. Assegna esito:
   - `NON ESEGUITA`
   - `OK`
   - `CORRETTA`
   - `PARZIALE`
   - `IMPOSSIBILE`
   - `ERRORE`
5. Continua anche se un file fallisce (error handling per-file).

## Limiti noti

- `zip_mixed_pades` resta warning informativo (non split automatico in questa versione).
- Alcuni file non ammessi per profilo sono marcati `IMPOSSIBILE` e non vengono corretti.
- Verifica PDF basata su controlli strutturali leggeri (header/trailer/encryption marker).

## Struttura progetto

- `core/`: regole, validatori, sanitizzazione, report
- `gui/`: interfaccia PySide6
- `cli/`: parser e comando shell
- `configs/`: profili YAML
- `tests/`: pytest

## Avvertenze legali

Il software fornisce supporto tecnico-informatico conservativo e non sostituisce il controllo professionale del difensore sulla conformità del deposito telematico.
