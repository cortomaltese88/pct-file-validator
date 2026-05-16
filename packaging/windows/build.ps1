$ErrorActionPreference = "Stop"

function Get-LicenseArtifactRoots {
  param(
    [string[]]$SitePackages,
    [string]$PackageName
  )

  $roots = New-Object System.Collections.Generic.List[string]
  foreach ($sitePath in $SitePackages) {
    if (-not (Test-Path $sitePath)) { continue }

    $packageDir = Join-Path $sitePath $PackageName
    if (Test-Path $packageDir) {
      $roots.Add((Resolve-Path $packageDir).Path)
    }

    foreach ($pattern in @("$PackageName*.dist-info", "$PackageName*.egg-info")) {
      Get-ChildItem -Path $sitePath -Directory -Filter $pattern -ErrorAction SilentlyContinue | ForEach-Object {
        $roots.Add($_.FullName)
      }
    }
  }

  $roots | Select-Object -Unique
}

function Copy-LicenseArtifacts {
  param(
    [string[]]$SitePackages,
    [string]$PackageName,
    [string]$DestinationDir,
    [switch]$Required
  )

  $roots = @(Get-LicenseArtifactRoots -SitePackages $SitePackages -PackageName $PackageName)
  if ($roots.Count -eq 0) {
    if ($Required) { throw "Required package roots not found for $PackageName in build environment." }
    Write-Warning "Package roots not found for $PackageName; skipping explicit license artifact collection."
    return 0
  }

  $patterns = @(
    '^LICENSE([._ -].*)?$',
    '^COPYING([._ -].*)?$',
    '^NOTICE([._ -].*)?$',
    'LGPL',
    'GPL',
    '^PKG-INFO$',
    '^METADATA$'
  )
  $textExtensions = @('.txt', '.md', '.rst', '.html')
  $matched = New-Object System.Collections.Generic.List[string]

  foreach ($root in $roots) {
    Get-ChildItem -Path $root -Recurse -File -ErrorAction SilentlyContinue | ForEach-Object {
      $leaf = $_.Name
      $extension = $_.Extension.ToLowerInvariant()
      $isMatch = $false

      foreach ($pattern in $patterns) {
        if ($leaf -match $pattern) {
          $isMatch = $true
          break
        }
      }

      if (-not $isMatch -and $leaf -match 'Qt' -and $textExtensions -contains $extension) {
        $isMatch = $true
      }

      if ($isMatch) {
        $matched.Add($_.FullName)
      }
    }
  }

  $copiedCount = 0
  foreach ($sourcePath in ($matched | Sort-Object -Unique)) {
    $rootForRelative = $roots | Where-Object { $sourcePath.StartsWith($_, [System.StringComparison]::OrdinalIgnoreCase) } | Sort-Object Length -Descending | Select-Object -First 1
    $relative = if ($rootForRelative) {
      $sourcePath.Substring($rootForRelative.Length).TrimStart('\')
    } else {
      Split-Path $sourcePath -Leaf
    }
    $safeRelative = ($relative -replace '[\\/:*?"<>| ]', '_')
    $destinationName = "{0}_{1}" -f $PackageName, $safeRelative
    Copy-Item $sourcePath (Join-Path $DestinationDir $destinationName) -Force
    $copiedCount += 1
  }

  if ($Required -and $copiedCount -eq 0) {
    throw "No license or metadata artifacts found for required package $PackageName."
  }

  if (-not $Required -and $copiedCount -eq 0) {
    Write-Warning "No license or metadata artifacts found for optional package $PackageName."
  }

  return $copiedCount
}

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

  $bundleDir = Join-Path $root "dist/gdlex-pct-validator"
  $docsToBundle = @("LICENSE", "THIRD_PARTY_LICENSES.md", "README.md")
  foreach ($doc in $docsToBundle) {
    $sourcePath = Join-Path $root $doc
    if (-not (Test-Path $sourcePath)) { throw "Required documentation file missing: $sourcePath" }
    Copy-Item $sourcePath (Join-Path $bundleDir $doc) -Force
  }

  $sitePackages = @(
    (& $py -c "import sysconfig; print(sysconfig.get_paths()['purelib']); print(sysconfig.get_paths()['platlib'])")
  ) | Where-Object { $_ -and $_.Trim() -ne "" } | ForEach-Object { $_.Trim() } | Select-Object -Unique

  $licensesDir = Join-Path $bundleDir "licenses"
  New-Item -ItemType Directory -Force -Path $licensesDir | Out-Null

  $licenseSummary = Join-Path $licensesDir "README-licenses.txt"
  @"
This directory contains license notices and metadata collected from the Python
packages present in the Windows build environment for gdlex-pct-validator.

The collected files are provided to improve traceability for bundled runtime
dependencies such as PySide6 and shiboken6. They complement, and do not replace,
the official license terms and notices published by the respective upstream
projects.
"@ | Out-File -FilePath $licenseSummary -Encoding utf8

  $copiedArtifacts = [ordered]@{}
  $copiedArtifacts["PySide6"] = Copy-LicenseArtifacts -SitePackages $sitePackages -PackageName "PySide6" -DestinationDir $licensesDir -Required
  $copiedArtifacts["shiboken6"] = Copy-LicenseArtifacts -SitePackages $sitePackages -PackageName "shiboken6" -DestinationDir $licensesDir
  $copiedArtifacts["PySide6_Addons"] = Copy-LicenseArtifacts -SitePackages $sitePackages -PackageName "PySide6_Addons" -DestinationDir $licensesDir
  $copiedArtifacts["PySide6_Essentials"] = Copy-LicenseArtifacts -SitePackages $sitePackages -PackageName "PySide6_Essentials" -DestinationDir $licensesDir

  $summaryLines = @(
    "Collected artifact counts:"
  ) + ($copiedArtifacts.GetEnumerator() | ForEach-Object { "{0}: {1}" -f $_.Key, $_.Value })
  Add-Content -Path $licenseSummary -Value ""
  Add-Content -Path $licenseSummary -Value $summaryLines

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
