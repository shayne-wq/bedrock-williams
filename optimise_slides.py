#!/usr/bin/env python3
"""Bedrock — turn captured chapter stills into shippable JPEGs.

    python3 williams/optimise_slides.py

Run after capture.mjs. PNG is the wrong container for a satellite photograph;
these are ~8x smaller as JPEG and the difference is invisible on a handset,
which is the only device that will ever load them.
"""
from pathlib import Path
from PIL import Image

OUT = Path(__file__).resolve().parent / "data" / "slides"
WIDE = 1100          # plenty on a phone at 2-3x, and a third of the bytes of 1320
total = 0
for png in sorted(OUT.glob("*.png")):
    im = Image.open(png).convert("RGB")
    if im.width > WIDE:
        im = im.resize((WIDE, round(im.height * WIDE / im.width)), Image.LANCZOS)
    jpg = png.with_suffix(".jpg")
    im.save(jpg, quality=82, optimize=True, progressive=True)
    png.unlink()
    total += jpg.stat().st_size
    print(f"  {jpg.name}  {im.width}x{im.height}  {jpg.stat().st_size/1024:.0f} KB")
print(f"{len(list(OUT.glob('*.jpg')))} stills, {total/1048576:.2f} MB total")
