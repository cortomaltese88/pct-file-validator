# Troubleshooting

Questa pagina raccoglie problemi ricorrenti coerenti con il flusso
attuale del progetto.

## Pacchetto in stato `iF`

Sintomo:

- `dpkg -l` mostra il pacchetto in stato `iF`.

Contesto tipico:

- `postinst` interrotto o fallito dopo l'installazione del `.deb`.

Azioni utili:

```bash
sudo apt -f install
sudo dpkg --configure -a
```

Se il problema persiste, leggere il log del `postinst` e verificare che
la macchina possa creare la `venv` e installare il progetto locale.

## `postinst` fallito

Cause comuni:

- ambiente Python di sistema incompleto;
- errore durante `python3 -m venv`;
- errore nel `pip install -e /usr/lib/gdlex-pct-validator/app`.

Verifiche:

```bash
python3 --version
python3 -m venv --help
```

Nei sistemi colpiti conviene anche rieseguire configurazione e
controllare l'output:

```bash
sudo dpkg --configure -a
```

## `setuptools-scm` / metadata di versione

Il progetto deriva la versione dai tag Git, ma il pacchetto Debian
installato non ha i metadata `.git`. Per questo il `postinst` esporta
`SETUPTOOLS_SCM_PRETEND_VERSION_FOR_GDLEX_PCT_VALIDATOR`.

Se compaiono errori di versioning:

- verificare che il placeholder nel `postinst` sia stato sostituito con
  la versione reale durante la build;
- verificare che il `.deb` sia stato costruito passando `APP_VERSION` o
  un argomento esplicito allo script.

## Warning APT su `Origin` / `Label` / `Suite` / `Codename`

Il workflow `publish-apt-repo` esegue controlli espliciti su questi
campi del file `Release`.

Se il client APT segnala mismatch:

- verificare i contenuti di `dists/stable/Release` nel repository APT;
- rieseguire la pubblicazione correttiva con nuova versione solo se il
  repository e' effettivamente incoerente;
- considerare il caching lato client e riprovare con `sudo apt update`.

## `Bad credentials` nel workflow APT

Causa tipica:

- secret `GDLEX_APT_REPO_TOKEN` assente, scaduto o non autorizzato sul
  repository target.

Azioni:

- controllare il secret nel repository GitHub sorgente;
- verificare che il token consenta checkout e push verso
  `cortomaltese88/gdlex-apt-repo`;
- non ripubblicare lo stesso tag per tentare un workaround.

## `Candidate` APT non aggiornato

Dopo una release riuscita:

```bash
sudo apt update
apt policy gdlex-pct-validator
```

Se la `Candidate` non cambia:

- attendere la propagazione GitHub Pages;
- verificare che `Packages` e `Packages.gz` includano la nuova versione;
- controllare il file `Release` e il percorso del `.deb` nel repository
  APT.

## Asset Windows mancante

Se la GitHub Release non contiene l'installer Windows o il checksum:

- controllare il workflow `release-windows`;
- verificare che esistano
  `dist-installer/gdlex-pct-validator-<version>-windows.exe`
  e relativo `.sha256`;
- verificare che il job abbia girato su un tag `v*`.

## PySide6 / notices mancanti nel bundle Windows

Il workflow si aspetta:

- `dist/gdlex-pct-validator/licenses/`
- almeno un artefatto collegato a PySide6 o Qt;
- un artefatto collegato a `shiboken6` oppure `README-licenses.txt`.

Se questi controlli falliscono:

- verificare l'ambiente della `venv` Windows di build;
- controllare che `build.ps1` riesca a trovare `site-packages`;
- confermare che la raccolta dei file licenza non sia stata rimossa o
  alterata.

## Warning manpage o `lintian`

Warning minori su manpage o metadati Debian possono emergere anche con
build riuscita.

Azioni:

- rieseguire `lintian dist/gdlex-pct-validator_<version>_amd64.deb`;
- verificare compressione e installazione di `gdlex-gui.1`;
- controllare desktop entry, icone e metadati del pacchetto.

## Icona o voce menu desktop mancanti

Il pacchetto installa:

- desktop file in `/usr/share/applications/`;
- icone `hicolor` in piu' dimensioni;
- refresh opzionale di `update-desktop-database` e
  `gtk-update-icon-cache`.

Se menu o icona non compaiono subito:

- rieseguire login grafico o refresh della cache desktop;
- verificare che il pacchetto sia configurato correttamente;
- controllare la presenza del file
  `gdlex-pct-validator.desktop` e delle icone installate.
