from __future__ import annotations

import io
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
SRC_SVG = ROOT / "assets" / "icon.svg"
SRC_PNG = ROOT / "assets" / "icon.png"
LINUX_SVG = ROOT / "assets" / "icons" / "gdlex-pct-validator.svg"
LINUX_PNG_256 = ROOT / "assets" / "icons" / "gdlex-pct-validator-256.png"
WINDOWS_ICO = ROOT / "packaging" / "windows" / "assets" / "app.ico"


def _draw_fallback(size: int = 512) -> Image.Image:
    img = Image.new("RGBA", (size, size), (24, 32, 43, 255))
    d = ImageDraw.Draw(img)
    pad = size // 16
    d.rounded_rectangle((pad, pad, size - pad, size - pad), radius=size // 10, fill=(31, 38, 48, 255), outline=(94, 117, 141, 255), width=max(3, size // 64))
    d.polygon([(size * 0.5, size * 0.24), (size * 0.33, size * 0.36), (size * 0.67, size * 0.36)], outline=(142, 163, 183, 255), fill=None, width=max(3, size // 80))
    d.line([(size * 0.38, size * 0.38), (size * 0.38, size * 0.56), (size * 0.62, size * 0.56), (size * 0.62, size * 0.38)], fill=(142, 163, 183, 255), width=max(3, size // 64))
    d.ellipse((size * 0.6, size * 0.58, size * 0.9, size * 0.88), fill=(31, 122, 69, 235), outline=(45, 154, 92, 255), width=max(3, size // 80))
    d.line([(size * 0.66, size * 0.73), (size * 0.72, size * 0.79), (size * 0.82, size * 0.67)], fill=(233, 255, 241, 255), width=max(6, size // 35))
    return img


def _load_base_image() -> Image.Image:
    if SRC_PNG.exists():
        return Image.open(SRC_PNG).convert("RGBA")

    if SRC_SVG.exists():
        try:
            import cairosvg  # type: ignore

            png_bytes = cairosvg.svg2png(url=str(SRC_SVG), output_width=512, output_height=512)
            return Image.open(io.BytesIO(png_bytes)).convert("RGBA")
        except Exception:
            pass

    return _draw_fallback(512)


def main() -> None:
    base = _load_base_image()

    SRC_PNG.parent.mkdir(parents=True, exist_ok=True)
    base.save(SRC_PNG, format="PNG")

    LINUX_SVG.parent.mkdir(parents=True, exist_ok=True)
    if SRC_SVG.exists():
        LINUX_SVG.write_text(SRC_SVG.read_text(encoding="utf-8"), encoding="utf-8")

    LINUX_PNG_256.parent.mkdir(parents=True, exist_ok=True)
    base.resize((256, 256), Image.Resampling.LANCZOS).save(LINUX_PNG_256, format="PNG")

    WINDOWS_ICO.parent.mkdir(parents=True, exist_ok=True)
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    base.save(WINDOWS_ICO, format="ICO", sizes=sizes)

    print(f"Generated: {SRC_PNG}")
    print(f"Generated: {LINUX_SVG}")
    print(f"Generated: {LINUX_PNG_256}")
    print(f"Generated: {WINDOWS_ICO}")


if __name__ == "__main__":
    main()
