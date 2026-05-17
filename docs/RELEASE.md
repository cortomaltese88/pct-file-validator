# Release

Questa nota riassume il flusso release attuale osservabile nel
repository alla release `v1.2.1`.

## Principio generale

La versione del progetto e' tag-driven:

- `pyproject.toml` usa `setuptools-scm`;
- i workflow di release leggono la versione dal tag Git;
- il packaging Debian e Windows riceve la versione tramite
  `APP_VERSION`.

Non rifare tag gia' pubblicati.

## Controlli pre-tag

Prima di creare il tag:

1. Verificare che il working tree sia pulito.
2. Eseguire `pytest`.
3. Verificare che `README.md`, documentazione e note licenze siano
   coerenti con la release.
4. Controllare che packaging Debian e workflow coinvolti riflettano lo
   stato desiderato.
5. Confermare il numero di versione da pubblicare.

Se la release cambia il comportamento utente o il packaging, aggiornare
anche `CHANGELOG.md` e i documenti sotto `docs/`.

## Bump versione

Il repository non usa una versione hard-coded in `pyproject.toml`: il
bump avviene pubblicando un nuovo tag annotato.

Esempio:

```bash
git tag -a v1.2.2 -m "Release v1.2.2"
git push origin v1.2.2
```

Usare tag annotati, non tag leggeri.

## Workflow coinvolti

I workflow di rilascio attuali sono:

- `release-deb`
- `release-windows`
- `publish-apt-repo`

### `release-deb`

Parte su push di tag `v*` e:

- installa dipendenze e test;
- esegue `pytest -q`;
- lancia `./packaging/build_deb.sh`;
- verifica l'asset versionato;
- pubblica il `.deb` nella GitHub Release.

### `release-windows`

Parte su push di tag `v*` e anche via `workflow_dispatch` su ref di tipo
tag. Il workflow:

- ricava la versione da `GITHUB_REF_NAME`;
- esegue `packaging/windows/build.ps1`;
- controlla bundle, icona, documenti e cartella `licenses`;
- costruisce l'installer Inno Setup;
- genera il checksum SHA256;
- pubblica `.exe` e `.sha256` nella GitHub Release.

### `publish-apt-repo`

Parte su push di tag `v*` e puo' essere richiamato anche manualmente con
input `version`. Il workflow:

- risolve la versione dal tag o dall'input;
- ricostruisce il pacchetto Debian;
- verifica l'artefatto `.deb`;
- richiede il secret `GDLEX_APT_REPO_TOKEN`;
- aggiorna il repository `gdlex-apt-repo`;
- rigenera `Packages`, `Packages.gz` e `Release`;
- esegue hard check su metadati e filename;
- effettua push sul repository APT;
- prova la visibilita' remota con retry non bloccante.

## Controllo asset release

Dopo il completamento dei workflow verificare che la GitHub Release
contenga almeno:

- `gdlex-pct-validator_<version>_amd64.deb`
- `gdlex-pct-validator-<version>-windows.exe`
- `gdlex-pct-validator-<version>-windows.exe.sha256`

Se la release Debian o Windows fallisce, correggere la causa e creare una
nuova release con nuova versione; evitare di riscrivere una release gia'
pubblicata con lo stesso tag.

## Controllo APT

Dopo la pubblicazione del repository APT:

```bash
sudo apt update
apt policy gdlex-pct-validator
```

Verificare che la `Candidate` corrisponda alla versione attesa e che il
repository esponga `Origin`, `Label`, `Suite` e `Codename` coerenti.

## Se la publish APT fallisce

Controlli consigliati:

1. Verificare la presenza e validita' del secret
   `GDLEX_APT_REPO_TOKEN`.
2. Controllare che il `.deb` atteso esista davvero in `dist/`.
3. Verificare che il repository APT venga aggiornato con:
   `pool/main/g/gdlex-pct-validator/`
   e `dists/stable/main/binary-amd64/`.
4. Controllare i log dei passaggi `Hard checks on generated indexes` e
   `Remote visibility check`.
5. Considerare un ritardo di propagazione GitHub Pages prima di
   classificare il problema come definitivo.

Se il tag e' gia' pubblico, evitare di cancellarlo o riutilizzarlo:
preparare una nuova release correttiva con nuova versione.

## Attenzione ai secret

- Non stampare o committare token nei log, negli script o nella
  documentazione.
- `GDLEX_APT_REPO_TOKEN` deve restare confinato ai secret GitHub.
- Non usare credenziali personali in sostituzione se non strettamente
  necessario e solo in canali riservati.
