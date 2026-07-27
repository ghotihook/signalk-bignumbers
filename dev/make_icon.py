#!/usr/bin/env python3
"""Regenerate public/icon.png, the tile SignalK shows in its Webapps list.

Not a build step -- the webapp ships the PNG, and nothing runs this at
install time. It exists so the icon can be changed without hand-editing a
binary, and so it keeps using the same face as the instrument itself.

    python3 dev/make_icon.py

Two stacked bands with inverted colours, each with its label top-left,
which is what a two-value display actually looks like. A single big
number on a tile was the obvious icon and is already taken -- KIP's looks
like that -- so the bands are doing the work of telling the two apart at
thumbnail size.

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

# One entry per band, top to bottom: label, value, and whether the band has
# a light background.
BANDS = [
    ("STW", "8.4", True),
    ("TWA", "143", False),
]

# Digits are sized against the space left under the label, not the whole
# band, so the two can't collide the way they did when this was tuned by
# eye against the band height.
FILL = 0.72         # fraction of that remaining space the digits occupy
SIDE = 0.08         # fraction of the tile kept clear left and right
LABEL = 0.14        # label cap height, as a fraction of band height
LABEL_PAD = 0.10    # label inset from the band's top-left, same fraction
LABEL_GAP = 0.04    # clearance under the label before digits may start
LABEL_ALPHA = 0.6   # matches .title's opacity in instrument.html
TRACKING = 0.2      # matches .title's letter-spacing, in em


def fitted_font(draw, text, max_w, max_h):
    """Largest font size whose rendered `text` fits both bounds."""
    size = 8
    while True:
        candidate = ImageFont.truetype(str(FONT), size + 1)
        left, top, right, bottom = draw.textbbox((0, 0), text, font=candidate)
        if right - left > max_w or bottom - top > max_h:
            return ImageFont.truetype(str(FONT), size)
        size += 1


def draw_tracked(draw, xy, text, font, fill, tracking):
    """PIL has no letter-spacing, so step the pen between glyphs."""
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += draw.textlength(ch, font=font) + font.size * tracking


def blend(fg, bg, alpha):
    return tuple(round(f * alpha + b * (1 - alpha)) for f, b in zip(fg, bg))


def main():
    img = Image.new("RGB", (SIZE, SIZE), BLACK)
    draw = ImageDraw.Draw(img)

    band_h = SIZE / len(BANDS)
    max_w = SIZE * (1 - 2 * SIDE)

    # One size for every band, so the tile reads as one instrument the way
    # fitDisplay() makes the real screen do.
    label_font = fitted_font(draw, "M", SIZE, band_h * LABEL)

    # Space under the label is what the digits actually get.
    digits_top = band_h * (LABEL_PAD + LABEL + LABEL_GAP)
    digits_h = band_h - digits_top

    font = min(
        (fitted_font(draw, v, max_w, digits_h * FILL) for _, v, _ in BANDS),
        key=lambda f: f.size,
    )

    for i, (label, value, light) in enumerate(BANDS):
        top = round(i * band_h)
        bottom = round((i + 1) * band_h)
        bg, fg = (WHITE, BLACK) if light else (BLACK, WHITE)
        draw.rectangle([0, top, SIZE, bottom - 1], fill=bg)

        pad = band_h * LABEL_PAD
        draw_tracked(
            draw, (pad, top + pad), label, label_font,
            blend(fg, bg, LABEL_ALPHA), TRACKING,
        )

        # Centre on the ink, not the font's line box: digits have no
        # descenders, so the leading would push them visibly high.
        l, t, r, b = draw.textbbox((0, 0), value, font=font)
        draw.text(
            ((SIZE - (r - l)) / 2 - l, top + digits_top + (digits_h - (b - t)) / 2 - t),
            value,
            font=font,
            fill=fg,
        )

    img.save(OUT, optimize=True)
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size} bytes, {SIZE}x{SIZE})")


if __name__ == "__main__":
    main()
