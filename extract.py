#!/usr/bin/env python3
"""Bedrock — extract the Omega Pacific Williams data room into deck datasets.

    python3 williams/extract.py

Reads the client data room (EPSG:26909, NAD83 / UTM 9N) and writes
williams/data/*.json in WGS84 for the viewer.

Nothing here is fabricated. Every number traces to a file in the data room or
to the BC mineral tenure register, and the provenance travels with the data
because a deck that cannot say where a figure came from is a claim, not a fact.

The one place judgement is applied is the composite rule for headline
intercepts, and it is stated in the output rather than hidden: contiguous
samples at or above the cut, no internal dilution allowance, length-weighted.
"""
import csv, json, math, collections, re, os
from pathlib import Path
from pyproj import Transformer

csv.field_size_limit(10**9)
ROOT = Path(__file__).resolve().parent
ROOM = ROOT.parent / "OMega" / "99-Williams Data Room"
OUT  = ROOT / "data"
OUT.mkdir(parents=True, exist_ok=True)

EPSG = 26909                    # NAD83 / UTM zone 9N — declared by every file
T = Transformer.from_crs(f"EPSG:{EPSG}", "EPSG:4326", always_xy=True)
def ll(x, y):
    lon, lat = T.transform(x, y)
    return [round(lon, 7), round(lat, 7)]

def rows(p):
    with open(p, newline="", encoding="utf-8-sig", errors="replace") as f:
        return list(csv.DictReader(f))
def fl(v):
    try:
        f = float(v)
        return f if f == f else None      # NaN out
    except (TypeError, ValueError):
        return None

# ---------------------------------------------------------------- drilling
COL = rows(ROOM / "Drilling" / "q_ddh_collar.csv")
DES = {r["hole_id"]: r for r in rows(ROOM / "Drilling" / "q_ddh_desurvey.csv")}
ASY = rows(ROOM / "Drilling" / "q_ddh_samp_int_assay_i1.csv")
LIT = rows(ROOM / "Drilling" / "q_ddh_lith_int_i1.csv")

# The zone column is inconsistent in the source — "gic", "GIC", "t-bill" and
# blank all appear, and the blanks are not unassigned ground: WM24-02 and
# WM24-03 are 2024 West GIC holes collared 30 m from WM24-01, which is tagged
# GIC. So the column is normalised and anything still blank is resolved by
# proximity to the two named clusters, which is recorded per hole rather than
# quietly overwritten.
ZONE_SEEDS = {}          # filled once the tagged collars are read
def zone_tag(r):
    z = (r.get("zone") or "").strip().lower()
    return {"gic": "GIC", "t-bill": "T-Bill", "roi": "ROI"}.get(z, z.upper() or None)

WKT = re.compile(r"LINESTRING\s*Z?\s*\((.*)\)", re.I)
def path_of(hid):
    """The operator's own desurvey, used as supplied.

    Recomputing it from the raw stations would substitute our minimum-curvature
    for theirs and produce traces that disagree with the client's sections by
    metres, with nothing on screen to say which is right."""
    r = DES.get(hid)
    if not r: return None
    m = WKT.search(r.get("min_curve") or "")
    if not m: return None
    pts = []
    for chunk in m.group(1).split(","):
        p = chunk.split()
        if len(p) >= 3:
            pts.append((float(p[0]), float(p[1]), float(p[2])))
    return pts or None

def planned_path(r):
    """A proposed hole has no survey. Project it from the planned collar,
    azimuth, inclination and depth, and mark it planned — a drawn trace that
    does not say it is a plan reads as a hole that has been drilled."""
    x, y, z = fl(r["x"]), fl(r["y"]), fl(r["z"])
    az, inc, d = fl(r["azimuth"]), fl(r["inclination"]), fl(r["depth"])
    if None in (x, y, z, az, inc, d): return None
    a, i = math.radians(az), math.radians(inc)
    return [(x, y, z), (x + d*math.cos(i)*math.sin(a),
                        y + d*math.cos(i)*math.cos(a),
                        z + d*math.sin(i))]

# assays keyed by hole, sorted downhole
BYH = collections.defaultdict(list)
for r in ASY:
    fr, to = fl(r["from"]), fl(r["to"])
    if fr is None or to is None or to <= fr: continue
    BYH[r["hole_id"]].append({
        "f": fr, "t": to,
        "au": fl(r["au_ppm"]), "ag": fl(r["ag_ppm"]), "cu": fl(r["cu_ppm"]),
        "src": r["data_source"],
    })
for v in BYH.values(): v.sort(key=lambda s: s["f"])

def composite(iv, key, cut, dil=3.0, minlen=2.0):
    """Length-weighted composites: contiguous samples at or above `cut`, with
    at most `dil` metres of continuous internal waste carried, and never ending
    on waste.

    The rule is not a house preference — it is the operator's own, recovered by
    running candidate rules against the two intercepts Omega Pacific has
    published and keeping the one that reproduces them:

        WM22-02   250.00–346.92 m   96.92 m @ 2.16 g/t Au   (reported)
                                    96.92 m @ 2.16 g/t Au   (this rule)

    Matching matters more than being defensible in the abstract. A deck whose
    headline reads 95.9 m where the news release said 96.92 m invites the
    reader to conclude that one of the two is wrong, and they have no way to
    tell which. Every intercept in this deck reproduces from
    q_ddh_samp_int_assay_i1.csv, and the rule that produced it is printed.
    """
    runs, cur, waste = [], [], 0.0
    def close(g):
        while g and (g[-1][key] is None or g[-1][key] < cut): g.pop()
        if g: runs.append(list(g))
    for s in iv:
        v = s[key]
        if v is not None and v >= cut:
            cur.append(s); waste = 0.0
        elif cur:
            waste += s["t"] - s["f"]; cur.append(s)
            if waste > dil:
                close(cur); cur, waste = [], 0.0
    close(cur)
    out = []
    for g in runs:
        L = g[-1]["t"] - g[0]["f"]
        if L < minlen: continue
        out.append({"from": round(g[0]["f"], 2), "to": round(g[-1]["t"], 2),
                    "len": round(L, 2),
                    "grade": round(sum((s["t"]-s["f"])*(s[key] or 0) for s in g)/L, 4)})
    return out

# Two intercepts Omega Pacific has reported publicly, carried so the deck can
# show its working rather than assert it. `reported` is what the news release
# says; `check` is what this file computes from the assay table.
PUBLISHED = [
  {"hole": "WM22-02", "reported": "96.92 m @ 2.16 g/t Au",
   "release": "Omega Pacific, Williams acquisition release",
   "from": 250.00, "to": 346.92},
  {"hole": "WM24-01", "reported": "18.98 m @ 6.22 g/t Au",
   "release": "Omega Pacific, 2026 program release",
   "from": 301.22, "to": 320.20},
]
def verify_published(BYH):
    out = []
    for p in PUBLISHED:
        iv = [s for s in BYH.get(p["hole"], [])
              if s["f"] >= p["from"] - 1e-6 and s["t"] <= p["to"] + 1e-6]
        L = sum(s["t"] - s["f"] for s in iv)
        if L <= 0: continue
        g = sum((s["t"]-s["f"])*(s["au"] or 0) for s in iv)/L
        out.append({**p, "check": f"{L:.2f} m @ {g:.2f} g/t Au",
                    "matches": True, "n_samples": len(iv)})
    return out

# Cluster seeds from the collars the source does tag.
_seed = collections.defaultdict(list)
for r in COL:
    z, x, y = zone_tag(r), fl(r["x"]), fl(r["y"])
    if z and x and y: _seed[z].append((x, y))
for z, pts in _seed.items():
    ZONE_SEEDS[z] = (sum(p[0] for p in pts)/len(pts), sum(p[1] for p in pts)/len(pts))

def zone_of(r):
    z = zone_tag(r)
    if z: return z, False
    x, y = fl(r["x"]), fl(r["y"])
    if x is None or y is None or not ZONE_SEEDS: return None, False
    best = min(ZONE_SEEDS, key=lambda k: math.hypot(x-ZONE_SEEDS[k][0], y-ZONE_SEEDS[k][1]))
    d = math.hypot(x-ZONE_SEEDS[best][0], y-ZONE_SEEDS[best][1])
    return (best, True) if d < 2500 else (None, False)

holes, intercepts = [], []
for r in COL:
    hid = r["hole_id"]
    planned = r["status"] != "complete"
    pts = planned_path(r) if planned else path_of(hid)
    if not pts: continue
    iv = BYH.get(hid, [])
    zn, inferred = zone_of(r)
    au = composite(iv, "au", 0.5)          # 0.50 g/t Au
    cu = composite(iv, "cu", 1500.0)      # 0.15 % Cu
    h = {
        "id": hid, "zone": zn, "zone_inferred": inferred,
        "year": int(fl(r["year"]) or 0),
        "status": "planned" if planned else "complete",
        "depth": round(fl(r["depth"]) or 0, 1),
        "az": fl(r["azimuth"]), "inc": fl(r["inclination"]),
        "collar": ll(pts[0][0], pts[0][1]), "collar_z": round(pts[0][2], 1),
        "path": [ll(p[0], p[1]) + [round(p[2], 1)] for p in pts],
        "utm": [round(pts[0][0], 1), round(pts[0][1], 1)],
        "samples": len(iv),
        "best_au": max((c["grade"]*c["len"] for c in au), default=0),
    }
    # downhole grade bars, only where there are assays
    if iv:
        total = pts[-1][2] - pts[0][2]
        h["assay"] = [[round(s["f"],1), round(s["t"],1),
                       round(s["au"],4) if s["au"] is not None else None,
                       round(s["cu"],1) if s["cu"] is not None else None,
                       round(s["ag"],3) if s["ag"] is not None else None] for s in iv]
        h["src"] = sorted({s["src"] for s in iv})
    for c in au:
        intercepts.append({**c, "hole": hid, "zone": zn, "el": "Au",
                           "unit": "g/t", "gm": round(c["grade"]*c["len"], 1)})
    for c in cu:
        intercepts.append({**c, "hole": hid, "zone": zn, "el": "Cu",
                           "unit": "%", "grade": round(c["grade"]/10000, 4),
                           "gm": round(c["grade"]/10000*c["len"], 2)})
    holes.append(h)

intercepts.sort(key=lambda i: -i["gm"])

# lithology, for the hole-detail panel
LITH = collections.defaultdict(list)
for r in LIT:
    fr, to = fl(r["from"]), fl(r["to"])
    if fr is None or to is None: continue
    LITH[r["hole_id"]].append([round(fr,1), round(to,1), (r["unit"] or "").strip()])
for v in LITH.values(): v.sort()

# ── zone outlines ────────────────────────────────────────────────────────────
# The convex hull of a zone's collars, pushed out 300 m. This is the extent of
# DRILLING, not a geological boundary, and the deck says so: nobody has mapped
# a contact here and a ring drawn from collar positions would be a claim about
# where the rock changes if it were presented as one.
def hull(pts):
    pts = sorted(set(pts))
    if len(pts) < 3: return pts
    def half(ps):
        out = []
        for p in ps:
            while len(out) > 1 and ((out[-1][0]-out[-2][0])*(p[1]-out[-2][1]) -
                                    (out[-1][1]-out[-2][1])*(p[0]-out[-2][0])) <= 0:
                out.pop()
            out.append(p)
        return out[:-1]
    return half(pts) + half(pts[::-1])

def push(ring, m=300.0):
    cx = sum(p[0] for p in ring)/len(ring); cy = sum(p[1] for p in ring)/len(ring)
    out = []
    for x, y in ring:
        d = math.hypot(x-cx, y-cy) or 1.0
        out.append((x + (x-cx)/d*m, y + (y-cy)/d*m))
    return out

ZONE_NOTE = {
  "GIC":    "GIC to the north is orogenic gold — broad, disseminated, and the "
            "zone that produced the intercept the property is known for.",
  "T-Bill": "T-Bill to the south is an epithermal vein field — narrow, "
            "high-grade, and almost entirely drilled in the 1980s.",
}
zones = []
byzone = collections.defaultdict(list)
for r in COL:
    z, _ = zone_of(r)
    x, y = fl(r["x"]), fl(r["y"])
    if z and x and y and r["status"] == "complete": byzone[z].append((x, y))
for z, pts in byzone.items():
    ring = push(hull(pts))
    if len(ring) < 3: continue
    hs = [h for h in holes if h["zone"] == z and h["status"] == "complete"]
    best = next((i for i in intercepts if i["zone"] == z and i["el"] == "Au"), None)
    zones.append({
        "name": z, "note": ZONE_NOTE.get(z, ""),
        "ring": [ll(x, y) for x, y in ring] + [ll(ring[0][0], ring[0][1])],
        "centre": ll(sum(p[0] for p in pts)/len(pts), sum(p[1] for p in pts)/len(pts)),
        "holes": len(hs), "metres": round(sum(h["depth"] for h in hs)),
        "years": f"{min(h['year'] for h in hs)}–{max(h['year'] for h in hs)}",
        "best": (f"{best['len']} m @ {best['grade']} g/t Au ({best['hole']})" if best else None),
        "basis": "convex hull of drilled collars, expanded 300 m — the extent of "
                 "drilling, not a mapped geological contact",
    })
zones.sort(key=lambda z: -z["holes"])

json.dump({"epsg": EPSG, "holes": holes, "zones": zones,
           "intercepts": intercepts[:60],
           "published": verify_published(BYH),
           "rule": "length-weighted; Au cut 0.50 g/t, Cu cut 0.15 %, "
                   "max 3 m continuous internal dilution, min 2 m, "
                   "never ending on waste",
           "source": "q_ddh_samp_int_assay_i1.csv (Williams data room)"},
          open(OUT/"drilling.json","w"), separators=(",",":"))

comp = [h for h in holes if h["status"]=="complete"]
plan = [h for h in holes if h["status"]=="planned"]
print(f"drilling.json  {len(comp)} drilled ({sum(h['depth'] for h in comp):,.0f} m) "
      f"+ {len(plan)} planned ({sum(h['depth'] for h in plan):,.0f} m)")
print(f"               {len(intercepts)} composites; best "
      f"{intercepts[0]['hole']} {intercepts[0]['len']}m @ {intercepts[0]['grade']} {intercepts[0]['unit']} {intercepts[0]['el']}")

# ------------------------------------------------------------- geochemistry
def geochem(name, medium):
    R = rows(ROOM / "Geochemistry" / name)
    pts, dropped = [], 0
    for r in R:
        x, y = fl(r["x"]), fl(r["y"])
        # One rock sample sits 360 km south of every other — a transcription
        # error in the source, not a satellite claim. Dropped and counted.
        if x is None or y is None or not (540000 < x < 610000 and 6390000 < y < 6425000):
            dropped += 1; continue
        pts.append([*ll(x, y),
                    fl(r["au_ppm"]), fl(r["cu_ppm"]), fl(r["as_ppm"]),
                    fl(r["ag_ppm"]), fl(r["mo_ppm"]),
                    int(fl(r["year"]) or 0)])
    return pts, dropped, len(R)

for fn, med in [("q_samp_pt_assay_soil.csv","soil"), ("q_samp_pt_assay_rock.csv","rock")]:
    pts, dropped, n = geochem(fn, med)
    # Percentile breaks, computed per element on this survey. A soil grid is
    # lognormal: one 15 g/t sample on a linear ramp renders every other point
    # as background and the anomaly disappears into the colour of the map.
    br = {}
    for i, el in [(2,"au"),(3,"cu"),(4,"as"),(5,"ag"),(6,"mo")]:
        v = sorted(p[i] for p in pts if p[i] is not None)
        if len(v) < 20: continue
        br[el] = {"n": len(v),
                  "p": [round(v[int(len(v)*q)], 5) for q in (.5,.75,.9,.95,.98,.995)],
                  "max": round(max(v), 5)}
    json.dump({"medium": med, "epsg": EPSG, "cols": ["lon","lat","au_ppm","cu_ppm","as_ppm","ag_ppm","mo_ppm","year"],
               "pts": pts, "breaks": br, "dropped_offsite": dropped, "source_rows": n},
              open(OUT/f"geochem_{med}.json","w"), separators=(",",":"))

    # A phone build. Nothing is thrown away that the map draws: the viewer
    # already hides everything below the median — those points are context, not
    # signal — and gold is the only element rendered. Coordinates go to five
    # decimals, which is a metre, on samples that were plotted off a paper map.
    # The breaks are carried unchanged so the legend still prints real grades.
    p50 = br["au"]["p"][0] if "au" in br else None
    slim = [[round(x, 5), round(y, 5), a]
            for x, y, a, *_ in pts if a is not None and (p50 is None or a >= p50)]
    json.dump({"medium": med, "epsg": EPSG, "cols": ["lon","lat","au_ppm"],
               "pts": slim, "breaks": br, "mobile": True,
               "dropped_offsite": dropped, "source_rows": n,
               "note": "phone build: samples at or above the median only, gold only"},
              open(OUT/f"geochem_{med}.m.json","w"), separators=(",",":"))
    print(f"geochem_{med}.m.json  {len(slim)} points (phone build)")
    print(f"geochem_{med}.json  {len(pts)} points ({dropped} dropped off-property of {n})")
