from __future__ import annotations

import argparse
import io
import shutil
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
SRC_SVG = ROOT / "assets" / "icons" / "gdlex-pct-validator.svg"


def _draw_fallback(size: int = 512) -> Image.Image:
    img = Image.new("RGBA", (size, size), (16, 53, 104, 255))
    d = ImageDraw.Draw(img)
    pad = size // 16
    d.rounded_rectangle((pad, pad, size - pad, size - pad), radius=size // 6, fill=(23, 74, 146, 255), outline=(86, 141, 220, 255), width=max(3, size // 64))
    d.text((size * 0.2, size * 0.3), "GD", fill=(234, 242, 255, 255))
    d.ellipse((size * 0.62, size * 0.62, size * 0.94, size * 0.94), fill=(34, 163, 90, 245), outline=(26, 122, 66, 255), width=max(3, size // 80))
    d.line([(size * 0.70, size * 0.77), (size * 0.77, size * 0.84), (size * 0.88, size * 0.70)], fill=(236, 255, 244, 255), width=max(6, size // 36))
    return img


def _render_svg_to_image(size: int) -> Image.Image:
    try:
        import cairosvg  # type: ignore

        png_bytes = cairosvg.svg2png(url=str(SRC_SVG), output_width=size, output_height=size)
        return Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    except Exception:
        return _draw_fallback(size)


def generate_icons(output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    linux_dir = output_dir / "linux"
    windows_dir = output_dir / "windows"

    linux_dir.mkdir(parents=True, exist_ok=True)
    windows_dir.mkdir(parents=True, exist_ok=True)

    shutil.copy2(SRC_SVG, linux_dir / "gdlex-pct-validator.svg")

    sizes = [16, 24, 32, 48, 64, 128, 256]
    rendered = _render_svg_to_image(512)
    for size in sizes:
        rendered.resize((size, size), Image.Resampling.LANCZOS).save(linux_dir / f"gdlex-pct-validator-{size}.png", format="PNG")

    (windows_dir / "app.ico").parent.mkdir(parents=True, exist_ok=True)
    rendered.save(windows_dir / "app.ico", format="ICO", sizes=[(s, s) for s in sizes])

    return {
        "svg": linux_dir / "gdlex-pct-validator.svg",
        "png_256": linux_dir / "gdlex-pct-validator-256.png",
        "ico": windows_dir / "app.ico",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Linux/Windows application icons from SVG source")
    parser.add_argument("--output-dir", default="dist-installer/assets", help="Output folder for generated assets")
    parser.add_argument("--check", action="store_true", help="Fail if required generated assets are missing")
    args = parser.parse_args()

    out_dir = (ROOT / args.output_dir).resolve() if not Path(args.output_dir).is_absolute() else Path(args.output_dir)

    generated = generate_icons(out_dir)
    for key, path in generated.items():
        print(f"{key}: {path}")

    if args.check:
        missing = [str(path) for path in generated.values() if not path.exists()]
        if missing:
            raise SystemExit(f"Missing generated icon assets: {', '.join(missing)}")


if __name__ == "__main__":
    main()
