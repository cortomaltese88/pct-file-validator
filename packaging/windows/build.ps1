$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "../..")
Set-Location $root

$version = $env:APP_VERSION
if (-not $version) { $version = $env:GITHUB_REF_NAME }
if (-not $version) { throw "Missing APP_VERSION/GITHUB_REF_NAME (must come from git tag)." }
$version = $version.TrimStart('v')
$buildDate = if ($env:BUILD_DATE) { $env:BUILD_DATE } else { (Get-Date).ToUniversalTime().ToString("yyyy-MM-dd") }

$buildInfoPath = Join-Path $root "core/_build_info.py"
$backupBuildInfo = $null
if (Test-Path $buildInfoPath) {
  $backupBuildInfo = Join-Path $root "dist/_build_info.py.bak"
  New-Item -ItemType Directory -Force -Path (Split-Path $backupBuildInfo) | Out-Null
  Copy-Item $buildInfoPath $backupBuildInfo -Force
}

@"
"""Generated at packaging time. Do not edit manually."""
__version__ = "$version"
__build__ = "$buildDate"
__channel__ = "windows"
"@ | Out-File -FilePath $buildInfoPath -Encoding utf8

try {
  $venv = Join-Path $root ".venv-winbuild"
  if (Test-Path $venv) { Remove-Item -Recurse -Force $venv }

  python -m venv $venv
  $py = Join-Path $venv "Scripts/python.exe"
  $pip = Join-Path $venv "Scripts/pip.exe"

  & $py -m pip install --upgrade pip
  & $pip install -e .
  & $pip install pyinstaller pillow

  $iconOut = Join-Path $root "dist/icons"
  & $py tools/generate_icons.py --output-dir $iconOut --check

  $stableIcon = Join-Path $iconOut "app.ico"
  if (-not (Test-Path $stableIcon)) { throw "Icon missing: $stableIcon" }

  $versionFile = Join-Path $root "dist/windows-version.txt"
  @"
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=($($version.Replace('.',', ')), 0),
    prodvers=($($version.Replace('.',', ')), 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  )
)
"@ | Out-File -FilePath $versionFile -Encoding ascii

  & $py -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --name "gdlex-pct-validator" `
    --icon "$stableIcon" `
    --version-file "$versionFile" `
    --collect-all PySide6 `
    --add-data "configs\default.yaml;configs" `
    --add-data "configs;configs" `
    --add-data "assets\icons;assets/icons" `
    gui/app.py

  Write-Host "PyInstaller build completed: dist/gdlex-pct-validator/"
}
finally {
  if ($backupBuildInfo -and (Test-Path $backupBuildInfo)) {
    Copy-Item $backupBuildInfo $buildInfoPath -Force
    Remove-Item $backupBuildInfo -Force
  }
  elseif (Test-Path $buildInfoPath) {
    Remove-Item $buildInfoPath -Force
  }
}
