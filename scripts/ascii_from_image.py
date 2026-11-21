"""Turn an image into ascii_dark.txt and ascii_light.txt for the profile card.

Needs Pillow:  pip install pillow
Usage:         python scripts/ascii_from_image.py photo.jpg [--cols 42] [--gamma 1.0] [--ramp " .:-=+*#%@"]

Works best with a tightly cropped photo on a plain background, or a high-contrast game frame.
In the dark card, bright pixels become dense characters; the light card gets the inverse,
so the picture reads the right way round in both themes.
"""
import argparse
import pathlib

from PIL import Image, ImageOps

ROOT = pathlib.Path(__file__).resolve().parent.parent
CHAR_ASPECT = 0.6 * 12 / 14.6  # char width / line height used in render.py


def convert(img, cols, ramp, gamma, stretch=True):
    img = ImageOps.exif_transpose(img).convert("L")
    if stretch:
        img = ImageOps.autocontrast(img, cutoff=2)
    rows = max(1, round(cols * img.height / img.width * CHAR_ASPECT))
    img = img.resize((cols, rows), Image.BOX)  # area average: crisp cell edges
    px = img.load()
    dark, light = [], []
    n = len(ramp) - 1
    for y in range(rows):
        d_row, l_row = [], []
        for x in range(cols):
            v = (px[x, y] / 255) ** gamma
            d_row.append(ramp[round(v * n)])          # bright -> dense (light text on dark)
            l_row.append(ramp[round((1 - v) * n)])    # dark -> dense (dark text on light)
        dark.append("".join(d_row).rstrip())
        light.append("".join(l_row).rstrip())
    return "\n".join(dark) + "\n", "\n".join(light) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--cols", type=int, default=42)
    ap.add_argument("--gamma", type=float, default=1.0)
    ap.add_argument("--ramp", default=" .:-=+*#%@")
    ap.add_argument("--no-stretch", action="store_true",
                    help="keep the image's own brightness instead of auto-stretching the contrast")
    ap.add_argument("--no-invert", action="store_true",
                    help="use the same art in both themes (for logos and graphics rather than photos)")
    a = ap.parse_args()
    dark, light = convert(Image.open(a.image), a.cols, a.ramp, a.gamma, not a.no_stretch)
    (ROOT / "ascii_dark.txt").write_text(dark, encoding="utf-8")
    (ROOT / "ascii_light.txt").write_text(dark if a.no_invert else light, encoding="utf-8")
    print(dark)


if __name__ == "__main__":
    main()
