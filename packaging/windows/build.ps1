$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "../..")
Set-Location $root

$venv = Join-Path $root ".venv-winbuild"
if (Test-Path $venv) {
  Remove-Item -Recurse -Force $venv
}

python -m venv $venv
$py = Join-Path $venv "Scripts/python.exe"
$pip = Join-Path $venv "Scripts/pip.exe"

& $py -m pip install --upgrade pip
& $pip install -e .
& $pip install pyinstaller pillow cairosvg

& $py packaging/generate_icons.py

$stableIcon = Join-Path $root "packaging/windows/assets/app.ico"
if (-not (Test-Path $stableIcon)) {
  throw "Installer icon not found after generation: $stableIcon"
}

$manifest = Join-Path $root "packaging/windows/app.manifest"
if (-not (Test-Path $manifest)) {
  throw "Manifest file not found: $manifest"
}

& $py -m PyInstaller `
  --noconfirm `
  --clean `
  --windowed `
  --name "GDLEX-PCT-Validator" `
  --icon "$stableIcon" `
  --manifest "$manifest" `
  --collect-all PySide6 `
  --add-data "configs\default.yaml;configs" `
  --add-data "configs;configs" `
  gui/app.py

Write-Host "PyInstaller build completed: dist/GDLEX-PCT-Validator/"
Write-Host "Installer icon path: $stableIcon"
