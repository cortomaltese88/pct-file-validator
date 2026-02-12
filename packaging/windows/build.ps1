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

$stableIcon = Join-Path $root "packaging/windows/assets/app.ico"
$tmpIcon = Join-Path $root "dist-installer/tmp/gdlex-pct-validator.ico"

$iconGenerator = @'
from pathlib import Path
from PIL import Image, ImageDraw
import io

root = Path.cwd()
svg_path = root / "assets" / "icons" / "gdlex-pct-validator.svg"
png_candidates = [
    root / "assets" / "icons" / "gdlex-pct-validator.png",
    root / "assets" / "icons" / "gdlex-pct-validator-256.png",
]

stable = root / "packaging" / "windows" / "assets" / "app.ico"
tmp = root / "dist-installer" / "tmp" / "gdlex-pct-validator.ico"
stable.parent.mkdir(parents=True, exist_ok=True)
tmp.parent.mkdir(parents=True, exist_ok=True)

img = None
src_png = next((p for p in png_candidates if p.exists()), None)
if src_png:
    img = Image.open(src_png).convert("RGBA")
elif svg_path.exists():
    try:
        import cairosvg  # optional
        png_bytes = cairosvg.svg2png(url=str(svg_path), output_width=256, output_height=256)
        img = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    except Exception:
        img = None

if img is None:
    img = Image.new("RGBA", (256, 256), (24, 32, 43, 255))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((16, 16, 240, 240), radius=28, fill=(31, 38, 48, 255), outline=(75, 94, 115, 255), width=4)
    d.ellipse((70, 96, 186, 212), fill=(31, 122, 69, 235))
    d.line((98, 156, 122, 180), fill=(233, 255, 241, 255), width=14)
    d.line((122, 180, 164, 132), fill=(233, 255, 241, 255), width=14)

sizes = [(16,16), (24,24), (32,32), (48,48), (64,64), (128,128), (256,256)]
img.save(stable, format="ICO", sizes=sizes)
img.save(tmp, format="ICO", sizes=sizes)
print(f"Stable icon: {stable}")
print(f"Temp icon: {tmp}")
'@

& $py -c $iconGenerator

if (-not (Test-Path $stableIcon)) {
  throw "Installer icon not found after generation: $stableIcon"
}

& $py -m PyInstaller `
  --noconfirm `
  --clean `
  --windowed `
  --name "GDLEX-PCT-Validator" `
  --icon "$stableIcon" `
  --collect-all PySide6 `
  --add-data "configs\default.yaml;configs" `
  --add-data "configs;configs" `
  gui/app.py

Write-Host "PyInstaller build completed: dist/GDLEX-PCT-Validator/"
Write-Host "Installer icon path: $stableIcon"
