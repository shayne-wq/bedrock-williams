#!/usr/bin/env python3
"""Bedrock — georeferenced geophysics grids out of the Williams data room.

    python3 williams/rasters.py

A grid is an image plus the six numbers that place it. Those numbers are read
from each GeoTIFF's own tags — ModelPixelScale (33550) and ModelTiepoint
(33922) — and each product is draped on ITS OWN extent, never the union: the
2020 airborne survey and the 2021 ground IP cover different ground, and
stretching one to the other's corners moves the anomaly.

Every raster declares its own CRS in the GeoKey directory, and they are not the
same one: the airborne and VTEM products are WGS84 / UTM 9N (32609) and the
ground IP is NAD83(CSRS) / UTM 9N (3156). Reprojecting both from a single
assumed code is the kind of error that draws cleanly and is wrong.

Rotated grids are refused rather than approximated.
"""
import json, math
from pathlib import Path
from PIL import Image
from pyproj import Transformer

Image.MAX_IMAGE_PIXELS = None
ROOT = Path(__file__).resolve().parent
ROOM = ROOT.parent / "OMega" / "99-Williams Data Room" / "Geophysics"
OUT  = ROOT / "data" / "geophys"
OUT.mkdir(parents=True, exist_ok=True)

AIR = ROOM / "Airborne" / "2020 Airborne (E & W claims)" / "GeoTIFFs"
IP  = ROOM / "Ground" / "2021 IP survey"
VT  = ROOM / "Airborne" / "2021 VTEM" / "GeoTiffs"

PRODUCTS = [
  # key            file                                        label / what it shows
  ("mag_rtp",  AIR/"21198_EXT_RTP_25m.tif",
   "Magnetics — RTP", "2020 heliborne magnetics, reduced to pole. Magnetite "
   "destruction over the altered corridors reads as the magnetic low.", "2020 airborne (Precision GeoSurveys, 25 m grid)"),
  ("mag_cvg",  AIR/"21198_EXT_CVG_25m.tif",
   "Magnetics — vertical gradient", "The derivative sharpens contacts and "
   "structure that the total field smooths over.", "2020 airborne, 25 m grid"),
  ("mag_tmi",  AIR/"21198_EXT_TMI_25m.tif",
   "Magnetics — TMI", "Total magnetic intensity as flown.", "2020 airborne, 25 m grid"),
  ("ip_chg_50",  IP/"Copaur-Williams_Walcott-IP-2021_CHG-Depth-050m_nad83z09.tif",
   "IP chargeability — 50 m", "Chargeability is the sulphide proxy. This is "
   "the layer the 2021–2024 holes were sited on.", "2021 ground DCIP (Walcott lines), inverted"),
  ("ip_chg_100", IP/"Copaur-Williams_Walcott-IP-2021_CHG-Depth-100m_nad83z09.tif",
   "IP chargeability — 100 m", "The same volume one depth slice down: the "
   "anomaly strengthens rather than fades, which is why it was drilled.", "2021 ground DCIP, inverted"),
  ("ip_res_100", IP/"Copaur-Williams_Walcott-IP-2021_RES-Depth-100m_nad83z09.tif",
   "IP resistivity — 100 m", "Resistivity separates silicified rock from the "
   "conductive, clay-altered ground around it.", "2021 ground DCIP, inverted"),
  ("vtem_rtp", VT/"Copaur-Williams_VTEM-RMI-RTP_wgs84z9.tif",
   "VTEM magnetics — RTP", "The 2021 VTEM flight, wider than the 2020 block "
   "and the reason the ROI target is on the map at all.", "2021 VTEM Plus (Geotech), 10 m grid"),
]

MAXPX = 2400        # long edge; the source grids are up to 4557 px and a deck
                    # that ships 15 MB of raster to open one slide is a deck
                    # nobody waits for

def read(p):
    im = Image.open(p)
    t = im.tag_v2
    sx, sy = t.get(33550)[:2]
    tie = t.get(33922)
    if not tie or len(tie) < 6: raise SystemExit(f"{p.name}: no tiepoint")
    px, py, _, X, Y, _ = tie[:6]
    if t.get(34264):                      # ModelTransformation — may be rotated
        raise SystemExit(f"{p.name}: carries a full transform; refused rather "
                         "than assumed axis-aligned")
    epsg = None
    gk = t.get(34735)
    if gk:
        keys = list(gk)
        for i in range(4, len(keys), 4):
            if keys[i] == 3072: epsg = keys[i+3]
    if not epsg: raise SystemExit(f"{p.name}: no projected CRS geokey")
    # tiepoint is the CENTRE of pixel (px,py); the extent runs to the raster EDGE
    w, h = im.size
    west  = X - (px + 0.5) * sx
    north = Y + (py + 0.5) * sy
    east  = west + w * sx
    south = north - h * sy
    return im, epsg, (west, south, east, north), (sx, sy)

def transparent(im):
    """Grid images are matted on white. Left opaque, each product would erase
    the terrain and every product below it, so the mat is punched out — and
    only the mat: a near-white pixel inside a colour ramp is data."""
    im = im.convert("RGBA")
    px = im.load()
    w, h = im.size
    n = 0
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if r > 247 and g > 247 and b > 247:
                px[x, y] = (r, g, b, 0); n += 1
    return im, n

man = []
for key, path, label, body, prov in PRODUCTS:
    if not path.exists():
        print(f"  skip {key}: {path.name} not found"); continue
    im, epsg, (w_, s_, e_, n_), (sx, sy) = read(path)
    T = Transformer.from_crs(f"EPSG:{epsg}", "EPSG:4326", always_xy=True)
    (lw, ls), (le, ln) = T.transform(w_, s_), T.transform(e_, n_)
    if max(im.size) > MAXPX:
        f = MAXPX / max(im.size)
        im = im.resize((round(im.size[0]*f), round(im.size[1]*f)), Image.LANCZOS)
    im, cut = transparent(im)
    out = OUT / f"{key}.png"
    im.save(out, optimize=True)
    # A phone copy, long edge 900. A 2400 x 1522 grid is roughly 15 MB of
    # texture once uploaded; at 900 px it is about 2 MB. On a 6-inch screen the
    # grid is a few hundred pixels wide either way, so the detail was never
    # going to arrive — and texture allocation is one of the few things that
    # plausibly decides whether iOS keeps the context alive.
    MOBILE_MAX = 900          # long edge
    f = min(1.0, MOBILE_MAX / max(im.size))
    small = im.resize((max(1, round(im.size[0]*f)), max(1, round(im.size[1]*f))), Image.LANCZOS)
    small.save(OUT / f"{key}@m.png", optimize=True)
    man.append({"key": key, "label": label, "body": body,
                "file": f"data/geophys/{key}.png",
                "file_m": f"data/geophys/{key}@m.png",
                "epsg": epsg, "cell_m": round(sx, 2),
                "rect": [round(lw,7), round(ls,7), round(le,7), round(ln,7)],
                "utm_extent": [round(w_,1), round(s_,1), round(e_,1), round(n_,1)],
                "px": list(im.size), "provenance": prov,
                "matte_removed_px": cut, "source": path.name})
    print(f"  {key:12s} {im.size[0]}x{im.size[1]}  EPSG:{epsg}  {sx:.2f} m/px  "
          f"{(e_-w_)/1000:.1f} x {(n_-s_)/1000:.1f} km  {out.stat().st_size/1e6:.1f} MB")

json.dump({"products": man}, open(ROOT/"data"/"geophysics.json","w"), indent=1)
print(f"geophysics.json  {len(man)} products")
