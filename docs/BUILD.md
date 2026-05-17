# Build

Questa nota descrive il flusso di build attuale del repository senza
introdurre varianti non presenti nei workflow.

## Ambiente Python locale

Setup minimo:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e .
```

Se si vogliono eseguire anche i test locali:

```bash
pip install pytest
pytest -q
```

La CI usa anche `ruff check .`; in locale e' utile eseguirlo quando si
tocca codice o test.

## Installazione editable

L'installazione editable (`pip install -e .`) e' il percorso previsto
dal progetto:

- per sviluppo locale;
- per i workflow GitHub Actions;
- per il `postinst` del pacchetto Debian, che crea una `venv` sotto
  `/usr/lib/gdlex-pct-validator/venv` e installa l'applicazione in modo
  editable dal contenuto copiato nel pacchetto.

## Test

Eseguire:

```bash
pytest
```

oppure, se si vuole un output piu' compatto:

```bash
pytest -q
```

## Build Debian locale

Lo script di riferimento e':

```bash
APP_VERSION=1.2.1 ./packaging/build_deb.sh
```

In alternativa la versione puo' essere passata come argomento:

```bash
./packaging/build_deb.sh 1.2.1
```

Lo script:

- richiede una versione esplicita;
- genera `core/_build_info.py` in modo temporaneo;
- rigenera le icone in `dist/icons`;
- costruisce uno stage Debian sotto `dist/stage`;
- produce il pacchetto `.deb` in `dist/`.

Artefatto atteso:

```text
dist/gdlex-pct-validator_<version>_amd64.deb
```

## Verifica con lintian

Se `lintian` e' disponibile nel sistema:

```bash
lintian dist/gdlex-pct-validator_<version>_amd64.deb
```

Il controllo e' utile soprattutto dopo modifiche a packaging, manpage,
desktop entry o metadati del pacchetto.

## Build Windows

La build Windows e' documentata dal workflow `release-windows` e dallo
script:

```text
packaging/windows/build.ps1
```

Il repository non mostra un flusso locale Windows supportato da Linux;
il percorso ordinario e' GitHub Actions su `windows-latest`.

Lo script Windows:

- crea una `venv` dedicata `.venv-winbuild`;
- installa il progetto in editable;
- installa `pyinstaller` e `pillow`;
- genera le icone;
- produce il bundle `dist/gdlex-pct-validator/`;
- include `LICENSE`, `README.md` e `THIRD_PARTY_LICENSES.md`;
- raccoglie notices/licenze per PySide6 e componenti collegati.

Il workflow costruisce poi l'installer Inno Setup e allega anche il file
`.sha256`.

## Pacchetti generati

Output principali attesi:

- Debian: `dist/gdlex-pct-validator_<version>_amd64.deb`
- Windows bundle: `dist/gdlex-pct-validator/`
- Windows installer: `dist-installer/gdlex-pct-validator-<version>-windows.exe`
- Checksum Windows: `dist-installer/gdlex-pct-validator-<version>-windows.exe.sha256`

## Cosa non committare

- ambienti virtuali locali (`.venv`, `.venv-winbuild`);
- output temporanei di build non richiesti dal repository;
- file reali di clienti o report contenenti dati sensibili;
- token, credenziali o altri segreti;
- artefatti locali creati solo per prove manuali.
