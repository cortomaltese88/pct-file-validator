from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SOURCE_PNG = ROOT / "assets" / "icon.png"
PNG_SIZES = [256, 128, 64, 48, 32, 24, 16]
ICO_SIZES = [256, 128, 64, 48, 32, 16]
PADDING_RATIO = 0.12  # safe area to avoid KDE/Plasma icon crop perception


def _with_safe_area(img: Image.Image, ratio: float = PADDING_RATIO) -> Image.Image:
    base = img.convert("RGBA")
    w, h = base.size
    padded = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    inner_w = max(1, int(w * (1.0 - (2.0 * ratio))))
    inner_h = max(1, int(h * (1.0 - (2.0 * ratio))))
    scaled = base.resize((inner_w, inner_h), Image.Resampling.LANCZOS)
    x = (w - inner_w) // 2
    y = (h - inner_h) // 2
    padded.paste(scaled, (x, y), scaled)
    return padded


def generate_icons(output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    hicolor_root = output_dir / "hicolor"
    win_ico = output_dir / "app.ico"
    base = _with_safe_area(Image.open(SOURCE_PNG))

    for size in PNG_SIZES:
        out = hicolor_root / f"{size}x{size}" / "apps" / "gdlex-pct-validator.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        base.resize((size, size), Image.Resampling.LANCZOS).save(out, format="PNG")

    base.save(win_ico, format="ICO", sizes=[(s, s) for s in ICO_SIZES])

    return {
        "source_png": SOURCE_PNG,
        "png_256": hicolor_root / "256x256" / "apps" / "gdlex-pct-validator.png",
        "ico": win_ico,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Linux/Windows icons from assets/icon.png")
    parser.add_argument("--output-dir", default="dist/icons", help="Output directory for generated assets")
    parser.add_argument("--check", action="store_true", help="Fail when expected generated files are missing")
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir

    generated = generate_icons(out_dir)
    for name, path in generated.items():
        print(f"{name}: {path}")

    if args.check:
        missing = [str(path) for path in generated.values() if not path.exists()]
        if missing:
            raise SystemExit(f"Missing generated icon assets: {', '.join(missing)}")


if __name__ == "__main__":
    main()
