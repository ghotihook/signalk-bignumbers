#!/usr/bin/env python3
"""Regenerate public/icon.png, the tile SignalK shows in its Webapps list.

Not a build step -- the webapp ships the PNG, and nothing runs this at
install time. It exists so the icon can be changed without hand-editing a
binary, and so it keeps using the same face as the instrument itself.

    python3 dev/make_icon.py

Three stacked bands with inverted colours, which is what a three-value
display actually looks like. A single big number on a tile was the
obvious icon and is already taken -- KIP's looks like that -- so the
bands are doing the work of telling the two apart at thumbnail size.

Needs Pillow, which nothing else here does: pip install pillow
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONT = ROOT / "public" / "fonts" / "Roboto-Medium.ttf"
OUT = ROOT / "public" / "icon.png"

SIZE = 512          # well above SignalK's 72px minimum, so it scales down cleanly
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

# One entry per band, top to bottom: the number, and whether the band is
# inverted. Widths differ so the tile doesn't read as one repeated glyph.
BANDS = [
    ("8.4", False),
    ("132", True),
    ("16.2", False),
]

FILL = 0.62         # fraction of a band's height the digits occupy
SIDE = 0.08         # fraction of the tile kept clear left and right


def fitted_font(draw, text, max_w, max_h):
    """Largest font size whose rendered `text` fits both bounds."""
    size = 8
    while True:
        candidate = ImageFont.truetype(str(FONT), size + 1)
        left, top, right, bottom = draw.textbbox((0, 0), text, font=candidate)
        if right - left > max_w or bottom - top > max_h:
            return ImageFont.truetype(str(FONT), size)
        size += 1


def main():
    img = Image.new("RGB", (SIZE, SIZE), BLACK)
    draw = ImageDraw.Draw(img)

    band_h = SIZE / len(BANDS)
    max_w = SIZE * (1 - 2 * SIDE)

    # One size for every band, so the tile reads as one instrument the way
    # fitDisplay() makes the real screen do.
    font = min(
        (fitted_font(draw, text, max_w, band_h * FILL) for text, _ in BANDS),
        key=lambda f: f.size,
    )

    for i, (text, inverted) in enumerate(BANDS):
        top = round(i * band_h)
        bottom = round((i + 1) * band_h)
        bg, fg = (WHITE, BLACK) if inverted else (BLACK, WHITE)
        draw.rectangle([0, top, SIZE, bottom - 1], fill=bg)

        # Centre on the ink, not the font's line box: digits have no
        # descenders, so the leading would push them visibly high.
        l, t, r, b = draw.textbbox((0, 0), text, font=font)
        draw.text(
            ((SIZE - (r - l)) / 2 - l, top + (band_h - (b - t)) / 2 - t),
            text,
            font=font,
            fill=fg,
        )

    img.save(OUT, optimize=True)
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size} bytes, {SIZE}x{SIZE})")


if __name__ == "__main__":
    main()
