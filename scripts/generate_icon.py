"""
Generate assets/icon.ico and assets/icon.png.
Run: python scripts/generate_icon.py
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ASSETS_DIR = Path(__file__).parent.parent / "assets"
ASSETS_DIR.mkdir(exist_ok=True)

SIZES = [16, 32, 48, 64, 128, 256]
BG_COLOR = "#1a1a2e"
TEXT_COLOR = "white"


def make_frame(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), BG_COLOR)
    draw = ImageDraw.Draw(img)

    font_size = max(int(size * 0.40), 8)
    font = None
    for face in ("arial.ttf", "Arial.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf"):
        try:
            font = ImageFont.truetype(face, font_size)
            break
        except Exception:
            pass
    if font is None:
        font = ImageFont.load_default()

    text = "TF"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = (size - tw) / 2 - bbox[0]
    y = (size - th) / 2 - bbox[1]
    draw.text((x, y), text, fill=TEXT_COLOR, font=font)
    return img


def main():
    largest = make_frame(256)
    largest.save(str(ASSETS_DIR / "icon.png"))
    print(f"Saved {ASSETS_DIR / 'icon.png'}")

    frames = [make_frame(s) for s in SIZES]
    frames[-1].save(
        str(ASSETS_DIR / "icon.ico"),
        format="ICO",
        sizes=[(s, s) for s in SIZES],
        append_images=frames[:-1],
    )
    print(f"Saved {ASSETS_DIR / 'icon.ico'} ({', '.join(str(s) for s in SIZES)}px)")


if __name__ == "__main__":
    main()
