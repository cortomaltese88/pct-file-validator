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
& $pip install pyinstaller pillow

$tmpDir = Join-Path $root "dist-installer/tmp"
New-Item -ItemType Directory -Path $tmpDir -Force | Out-Null
$iconPath = Join-Path $tmpDir "gdlex-pct-validator.ico"

$iconGenerator = @'
from pathlib import Path
from PIL import Image, ImageDraw

root = Path.cwd()
out = root / "dist-installer" / "tmp" / "gdlex-pct-validator.ico"
out.parent.mkdir(parents=True, exist_ok=True)

png_candidates = [
    root / "assets" / "icons" / "gdlex-pct-validator.png",
    root / "assets" / "icons" / "gdlex-pct-validator-256.png",
]

src_png = next((p for p in png_candidates if p.exists()), None)
if src_png:
    img = Image.open(src_png).convert("RGBA")
else:
    # Fallback: generate an icon themed from existing SVG presence
    svg_path = root / "assets" / "icons" / "gdlex-pct-validator.svg"
    if not svg_path.exists():
        raise SystemExit("No icon source found (missing SVG/PNG in assets/icons)")
    img = Image.new("RGBA", (256, 256), (24, 32, 43, 255))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((16, 16, 240, 240), radius=28, fill=(31, 38, 48, 255), outline=(75, 94, 115, 255), width=4)
    d.ellipse((70, 96, 186, 212), fill=(31, 122, 69, 235))
    d.line((98, 156, 122, 180), fill=(233, 255, 241, 255), width=14)
    d.line((122, 180, 164, 132), fill=(233, 255, 241, 255), width=14)

sizes = [(16,16), (24,24), (32,32), (48,48), (64,64), (128,128), (256,256)]
img.save(out, format="ICO", sizes=sizes)
print(out)
'@

& $py -c $iconGenerator
if (-not (Test-Path $iconPath)) {
  throw "Generated icon not found: $iconPath"
}

& $py -m PyInstaller `
  --noconfirm `
  --clean `
  --windowed `
  --name "GDLEX-PCT-Validator" `
  --icon "$iconPath" `
  --collect-all PySide6 `
  gui/app.py

Write-Host "PyInstaller build completed: dist/GDLEX-PCT-Validator/"
Write-Host "Generated icon: $iconPath"
