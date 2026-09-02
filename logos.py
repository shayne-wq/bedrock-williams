#!/usr/bin/env python3
"""Bedrock — neighbour logo plates for the Williams district map.

    python3 williams/logos.py

Each supplied logo is trimmed, sized and composited onto a plate so it reads on
a dark satellite basemap. Whether the plate is light or dark is decided from the
logo's own pixels, not guessed: a white-on-transparent mark on a white plate is
an empty rectangle, and a black wordmark on a dark plate is the same rectangle.

Logos are matched to REGISTERED HOLDERS, which is not always the name on the
logo. AuRORA Minerals Ltd is the Freeport (60 %) / Amarc (40 %) joint venture
that holds the JOY district titles, so the register says AuRORA and the operator
is Amarc. That distinction is kept in the payload rather than flattened.
"""
import json, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
SRC  = ROOT.parent / "OMega" / "Neighbouring Logos"
OUT  = ROOT / "data" / "logos"
OUT.mkdir(parents=True, exist_ok=True)

# registered holder  ->  logo file
LOGOS = {
  "OMEGA PACIFIC RESOURCES INC":  "@mark",     # the gold mark, as on the watermark
  "THESIS GOLD & SILVER INC.":    "thesis-gold-inc-logo.webp",
  "EAGLE PLAINS RESOURCES LTD.":  "eagle_plains_resources_ltd_epl__logo.jpeg",
  "AURICO METALS INC.":           "Centerra_Gold_Logo.svg",
  "TDG BC ASSETS CORP.":          "TDG_logo.webp",
  "AURORA MINERALS LTD.":         "AMARC.png",      # Freeport/Amarc JV — holds JOY
}

H       = 88          # logo height inside the plate (2x the rendered size)
PAD_X   = 26
PAD_Y   = 20
RADIUS  = 10
LIGHT   = (242, 243, 240, 250)
DARK    = (9, 12, 13, 242)

def load(name):
    if name == "@mark":
        return Image.open(ROOT / "data" / "omega-mark.png").convert("RGBA")
    p = SRC / name
    if p.suffix.lower() == ".svg":
        # No cairosvg here; macOS Quick Look renders it faithfully enough for a
        # 44 px plate and needs no new dependency.
        with tempfile.TemporaryDirectory() as td:
            subprocess.run(["qlmanage", "-t", "-s", "1200", "-o", td, str(p)],
                           check=True, capture_output=True)
            return Image.open(next(Path(td).glob("*.png"))).convert("RGBA").copy()
    im = Image.open(p).convert("RGBA")
    if im.mode == "RGBA" and p.suffix.lower() in (".jpg", ".jpeg"):
        pass
    return im

def opaque_everywhere(im):
    """True when the file carries no usable transparency. JPEG never does, but
    neither do plenty of PNGs and Quick Look's SVG render — and those are the
    ones that silently arrive as a white rectangle on a dark plate."""
    a = im.getchannel("A")
    return a.getextrema()[0] > 250

def dewhite(im, thresh=244):
    """A baked white background would sit on the plate as a hard rectangle.
    Near-white is punched to transparent — only near-white, because a pale tint
    inside a mark is part of the mark."""
    px = im.load()
    w, h = im.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if r >= thresh and g >= thresh and b >= thresh:
                px[x, y] = (r, g, b, 0)
    return im

def luminance(im):
    """Mean luminance of the mark's own opaque pixels — decides the plate."""
    px = im.load(); w, h = im.size
    tot = n = 0
    for y in range(0, h, 2):
        for x in range(0, w, 2):
            r, g, b, a = px[x, y]
            if a > 120:
                tot += .2126*r + .7152*g + .0722*b; n += 1
    return tot / n if n else 128

man = {}
for holder, fname in LOGOS.items():
    if fname != "@mark" and not (SRC / fname).exists():
        print(f"  missing: {fname}"); continue
    im = load(fname)
    if fname != "@mark" and opaque_everywhere(im):
        im = dewhite(im)
    bb = im.getbbox()
    if bb: im = im.crop(bb)
    w0, h0 = im.size
    im = im.resize((max(1, round(w0 * H / h0)), H), Image.LANCZOS)
    # A very wide mark would make a plate the size of a claim block.
    if im.size[0] > H * 4.2:
        f = H * 4.2 / im.size[0]
        im = im.resize((round(im.size[0]*f), round(im.size[1]*f)), Image.LANCZOS)

    lum = luminance(im)
    plate = DARK if lum > 168 else LIGHT
    pw, ph = im.size[0] + PAD_X*2, im.size[1] + PAD_Y*2
    card = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
    d = ImageDraw.Draw(card)
    d.rounded_rectangle([0, 0, pw-1, ph-1], RADIUS, fill=plate)
    card.alpha_composite(im, (PAD_X, PAD_Y))

    key = "".join(c if c.isalnum() else "-" for c in holder.lower()).strip("-")
    while "--" in key: key = key.replace("--", "-")
    card.save(OUT / f"{key}.png", optimize=True)
    man[holder] = {"file": f"data/logos/{key}.png", "w": pw, "h": ph,
                   "plate": "dark" if plate is DARK else "light"}
    print(f"  {holder:32s} {pw}x{ph}  {man[holder]['plate']:5s} plate  (lum {lum:.0f})")

json.dump(man, open(ROOT / "data" / "logos.json", "w"), indent=1)
print(f"logos.json  {len(man)} plates")
