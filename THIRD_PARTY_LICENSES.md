# THIRD_PARTY_LICENSES

Documento preparatorio di ricognizione licenze per dipendenze, bundle e
asset collegati a `pct-file-validator`.

La licenza principale del progetto resta quella descritta in `LICENSE`.
Le componenti di terze parti mantengono le rispettive licenze.

| Componente | Uso nel progetto | Incluso nel pacchetto? | Licenza verificata localmente | Note |
|---|---|---|---|---|
| Python runtime | Runtime dell'applicazione | `.deb`: no; bundle Windows: da verificare | da verificare | Il pacchetto Debian dipende da `python3`; il bundle Windows potrebbe includere il runtime Python tramite PyInstaller. |
| PySide6 | GUI runtime Qt for Python | `.deb`: installato lato utente; bundle Windows: sì | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only | Dipendenza runtime dichiarata in `pyproject.toml`; il workflow Windows usa `--collect-all PySide6`. |
| shiboken6 | Supporto runtime per binding Qt/PySide6 | `.deb`: installato lato utente; bundle Windows: sì | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only | Materialmente rilevante soprattutto per il bundle Windows insieme a PySide6. |
| Pillow | Generazione icone e asset raster | `.deb`: no; bundle Windows: no | HPND | Usato nei workflow/build script per generare icone. |
| PyYAML | Parsing configurazioni YAML | da verificare | MIT | Non risulta dichiarato in `pyproject.toml`; presenza da confermare se usato indirettamente o in fasi successive. |
| pytest | Test suite | no | da verificare | Tool di test/dev usato in CI e nella documentazione di sviluppo locale. |
| ruff | Linting | no | da verificare | Tool di qualità/dev usato in CI e nella documentazione di sviluppo locale. |
| PyInstaller | Creazione bundle Windows | bundle Windows: usato in build; incluso nel pacchetto finale: no | da verificare | Tool di build che assembla il contenuto di `dist/gdlex-pct-validator/`. |
| Inno Setup | Creazione installer Windows | installer Windows: sì | da verificare | Usato nel workflow Windows per produrre il setup `.exe`. |
| setuptools | Build backend Python | no | da verificare | Dichiarato in `[build-system]` di `pyproject.toml`. |
| wheel | Supporto build pacchetti Python | no | da verificare | Dichiarato in `[build-system]` di `pyproject.toml`. |
| setuptools-scm | Derivazione versione da Git tag | no | da verificare | Dichiarato in `[build-system]` di `pyproject.toml`. |
| Logo e icone GD LEX | Branding applicazione e pacchetti | sì | Proprietà/licenza separata del titolare del progetto | Asset di identità visiva dello Studio; non concessi come marchio dalla licenza software. |

## Note

- Le dipendenze di terze parti mantengono le rispettive licenze.
- Su Windows il bundle PyInstaller può includere materialmente
  `PySide6` e `shiboken6` e richiede notices/licenze adeguate.
- La licenza del software non concede diritti d'uso su nome, logo,
  marchio o identità visiva **STUDIO GD LEX** / **GD LEX**.
- Prima di pubblicare nuove release binarie occorre verificare che
  `LICENSE` e `THIRD_PARTY_LICENSES.md` siano inclusi nei pacchetti.
