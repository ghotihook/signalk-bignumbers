#!/usr/bin/env python3
"""Regenerate public/icon.png, the tile SignalK shows in its Webapps list.

Not a build step -- the webapp ships the PNG, and nothing runs this at
install time. It exists so the icon can be changed without hand-editing a
binary, and so it keeps using the same face as the instrument itself.

    python3 dev/make_icon.py

Needs Pillow, which nothing else here does: pip install pillow
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONT = ROOT / "public" / "fonts" / "Roboto-Medium.ttf"
OUT = ROOT / "public" / "icon.png"

SIZE = 512          # well above SignalK's 72px minimum, so it scales down cleanly
TEXT = "8.8"        # every digit at its widest, like a segment-test pattern
MARGIN = 0.06       # fraction of the tile left clear on the tightest axis
BG = (0, 0, 0)
FG = (255, 255, 255)


def fitted_font(draw, text, box):
    """Largest font size whose rendered `text` still fits in `box` pixels."""
    size = 8
    while True:
        candidate = ImageFont.truetype(str(FONT), size + 1)
        left, top, right, bottom = draw.textbbox((0, 0), text, font=candidate)
        if right - left > box or bottom - top > box:
            return ImageFont.truetype(str(FONT), size)
        size += 1


def main():
    img = Image.new("RGB", (SIZE, SIZE), BG)
    draw = ImageDraw.Draw(img)

    font = fitted_font(draw, TEXT, int(SIZE * (1 - 2 * MARGIN)))

    # Centre on the ink, not the font's line box: the digits have no
    # descenders and the leading would otherwise push them visibly high.
    left, top, right, bottom = draw.textbbox((0, 0), TEXT, font=font)
    draw.text(
        ((SIZE - (right - left)) / 2 - left, (SIZE - (bottom - top)) / 2 - top),
        TEXT,
        font=font,
        fill=FG,
    )

    img.save(OUT, optimize=True)
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size} bytes, {SIZE}x{SIZE})")


if __name__ == "__main__":
    main()
