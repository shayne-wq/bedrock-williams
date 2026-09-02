#!/usr/bin/env python3
"""Bedrock — the Williams claim block, and the Toodoggone around it.

    python3 williams/claims.py

Two windows, both from the public register:

  * **the property** — Omega Pacific's own tenure, drawn parcel by parcel;
  * **the district** — every significant holder within ~70 km, consolidated
    into one block per holder, which is how a neighbours map is read.

Looked up, never uploaded. A company does not hold its neighbours' tenure and
has no standing to assert it; only the register can say who owns the ground
along strike. It is also the most checkable thing in a mining deck — a reader
can put a tenure number into Mineral Titles Online and have an answer in a
minute — so real tenure is a credibility asset and a fabricated boundary is the
fabrication most likely to be caught. It already paid for itself here: the
register returns 11,490 ha for Omega Pacific and the company's release says
11,490 ha.

Tenures lapse, so the query timestamp travels with the data and is shown.

Source: WHSE_MINERAL_TENURE.MTA_ACQUIRED_TENURE_SVW via openmaps.gov.bc.ca,
Open Government Licence – British Columbia.
"""
import json, urllib.parse, urllib.request, datetime, math

COSLAT = math.cos(math.radians(57.2))
from pathlib import Path
from pyproj import Transformer

ROOT = Path(__file__).resolve().parent
ENDPOINT = "https://openmaps.gov.bc.ca/geo/pub/ows"
TYPENAME = "pub:WHSE_MINERAL_TENURE.MTA_ACQUIRED_TENURE_SVW"
SUBJECT  = "OMEGA PACIFIC RESOURCES INC"

PROPERTY = (880000, 1408000,  912000, 1442000)   # the claim block + ~8 km
DISTRICT = (859400, 1300967,  994099, 1453713)   # Williams down to Kemess

# ─────────────────────────────────────────────────────────────────────────────
# The register records the REGISTERED HOLDER. It does not record who is working
# the ground, and in the Toodoggone those are routinely different people: Sun
# Summit operates Theory and JD under option, so the register returns Eagle
# Plains; Kemess is Centerra's mine and the register returns AuRico Metals, the
# subsidiary that holds it.
#
# An investor looking at a neighbours map means the operator. So both are
# carried and they are kept apart: `holder` is what the register says and is
# verifiable; `operator` and `project` are EDITORIAL, marked as such in the
# payload, and shown in a lighter weight. Printing an operator as though the
# register had said it would be inventing a fact of exactly the kind this whole
# layer exists to avoid.
# ─────────────────────────────────────────────────────────────────────────────
EDITORIAL = {
  "OMEGA PACIFIC RESOURCES INC":  ("Omega Pacific",        "Williams"),
  "THESIS GOLD & SILVER INC.":    ("Thesis Gold",          "Lawyers–Ranch"),
  "EAGLE PLAINS RESOURCES LTD.":  ("Eagle Plains",         "Theory / Orbit"),
  "AURICO METALS INC.":           ("Centerra Gold",        "Kemess"),
  "TDG BC ASSETS CORP.":          ("TDG Gold",             "Baker–Shasta"),
  "NORTHWEST COPPER CORPORATION": ("Northwest Copper",     None),
  "AURORA MINERALS LTD.":         ("Amarc / Freeport JV",  "JOY district"),
  "ELECTRUM RESOURCE CORPORATION":("Electrum Resource",    None),
  "PROSPECT RIDGE RESOURCES CORP.":("Prospect Ridge",      None),
}
# One registered holder can work several named properties. Finlay's 65 parcels
# fall into two groups 15 km apart — PIL to the north, ATTY to the south — and a
# single label placed between them names neither. The split is by geography and
# the boundary is the gap itself, which is 15 km wide and unambiguous.
SPLITS = {}

# Where a block's label sits. Default is the middle of the holder's ground; the
# subject is anchored off its EASTERN edge so the mark and the property name sit
# beside the outline rather than on top of the one boundary that matters.
ANCHOR = { "OMEGA PACIFIC RESOURCES INC": "east" }

# A holder's ground can fall into several separate blocks, and the biggest is
# not always the one the label belongs on. Eagle Plains holds 24 parcels in the
# west and 10 in the north-east; the Theory / Orbit ground an investor is being
# shown is the north-eastern block. PREFER names a compass direction and the
# cluster furthest that way carries the label.
PREFER = { "EAGLE PLAINS RESOURCES LTD.": (1, 1) }      # (east, north)

MIN_HA = 2000          # district map: below this a holder is noise at 100 km

# The Toodoggone is a corridor, not a box. The district query returns coal
# ground to the southwest and scattered holdings well outside the belt; both
# are real and neither is a neighbour in the sense an investor means.
CORRIDOR = (-128.05, 56.85, -126.35, 57.90)
EXCLUDE  = ("COAL", "ZEAL", "COAST COPPER", "INTEGRATED MINERALS", "FINLAY")

def individual(name):
    """A registered holder with a comma in it is a person — "SCOTT, STEVEN
    JEFFREY" — and a prospector's two claims are not a neighbour an investor is
    weighing. Dropped from the district map, kept in the property count."""
    return "," in name

def fetch(bbox):
    q = urllib.parse.urlencode({
        "service": "WFS", "version": "2.0.0", "request": "GetFeature",
        "typeName": TYPENAME, "outputFormat": "json", "srsName": "EPSG:3005",
        "count": 20000, "bbox": ",".join(str(v) for v in bbox) + ",EPSG:3005"})
    with urllib.request.urlopen(f"{ENDPOINT}?{q}", timeout=300) as r:
        return json.load(r)

T = Transformer.from_crs("EPSG:3005", "EPSG:4326", always_xy=True)
def reproj(g, nd=6):
    def ring(rg): return [[round(v, nd) for v in T.transform(x, y)] for x, y in rg]
    if g["type"] == "Polygon":
        return {"type": "Polygon", "coordinates": [ring(r) for r in g["coordinates"]]}
    if g["type"] == "MultiPolygon":
        return {"type": "MultiPolygon", "coordinates": [[ring(r) for r in p] for p in g["coordinates"]]}
    return None
def outer(g):
    return g["coordinates"][0] if g["type"] == "Polygon" else \
           max(g["coordinates"], key=lambda p: len(p[0]))[0]

# ── the property ─────────────────────────────────────────────────────────────
src = fetch(PROPERTY)
asof = src.get("timeStamp") or datetime.datetime.utcnow().isoformat() + "Z"
feats, near = [], {}
for f in src["features"]:
    p, g = f["properties"], reproj(f["geometry"])
    if not g: continue
    owner = (p.get("OWNER_NAME") or "").strip()
    subject = owner.upper() == SUBJECT
    if subject:
        feats.append({"type": "Feature", "geometry": g, "properties": {
            "tenure": p.get("TENURE_NUMBER_ID"), "owner": owner,
            "ha": round(p.get("AREA_IN_HECTARES") or 0, 1),
            "issued": (p.get("ISSUE_DATE") or "")[:10],
            "good_to": (p.get("GOOD_TO_DATE") or "")[:10],
            "role": "subject"}})
    near[owner] = near.get(owner, 0) + (p.get("AREA_IN_HECTARES") or 0)

sub_ha = round(sum(f["properties"]["ha"] for f in feats), 1)
json.dump({"type": "FeatureCollection", "features": feats, "meta": {
    "synthetic": False, "subject": SUBJECT, "subject_tenures": len(feats),
    "subject_ha": sub_ha, "as_of": asof,
    "source": "WHSE_MINERAL_TENURE.MTA_ACQUIRED_TENURE_SVW",
    "licence": "Open Government Licence – British Columbia",
    "adjacent_holders": sorted(((k, round(v, 1)) for k, v in near.items()
                                if k.upper() != SUBJECT), key=lambda kv: -kv[1]),
}}, open(ROOT / "data" / "claims.geojson", "w"), separators=(",", ":"))
print(f"claims.geojson    {len(feats)} tenures · {sub_ha:,.0f} ha · as of {asof[:10]}")

# ── the district ─────────────────────────────────────────────────────────────
# Consolidated: every parcel a holder owns is drawn in one colour with no
# internal outlines, so the ground reads as a block rather than as a filing
# history. Not dissolved — the parcels are still each parcel, which is the
# honest version, because a dissolve would draw a boundary the register never
# issued.
dsrc = fetch(DISTRICT)
by = {}
for f in dsrc["features"]:
    p = f["properties"]
    owner = (p.get("OWNER_NAME") or "").strip()
    if not owner or individual(owner): continue
    g = reproj(f["geometry"], 5)
    if not g: continue
    b = by.setdefault(owner, {"ha": 0.0, "rings": [], "n": 0})
    b["ha"] += p.get("AREA_IN_HECTARES") or 0
    b["n"]  += 1
    b["rings"].append(outer(g))

def boundary(rings, nd=5):
    """The outer edge of a holder's ground, without a polygon library.

    MTO tenure cells are a grid and abutting parcels share their edges exactly,
    so an edge that appears TWICE is interior and an edge that appears ONCE is
    on the outside. Counting them dissolves the block for drawing purposes
    while leaving the parcels intact as data — which is the distinction that
    matters: outlining every tenure redraws the filing grid the consolidated
    fill exists to remove, and a real dissolve would invent a boundary the
    register never issued.

    Where two parcels meet along edges that are not vertex-for-vertex equal,
    that seam survives as a short interior line. Rare on a grid, and cheaper
    than the alternative.
    """
    seen = {}
    for r in rings:
        pts = [(round(x, nd), round(y, nd)) for x, y in r]
        for a, b in zip(pts, pts[1:]):
            if a == b: continue
            key = (a, b) if a <= b else (b, a)
            seen[key] = seen.get(key, 0) + 1
    return [[list(a), list(b)] for (a, b), n in seen.items() if n == 1]

_owner = [None]
def anchor(rings):
    """A point on the holder's OWN ground, near the middle of their main block.

    The centroid of every parcel a holder owns is not necessarily on any of
    them: TDG's ground is scattered and its centroid fell in a gap, and Eagle
    Plains' landed inside Evergold's block — which reads, correctly, as the two
    labels having been swapped. So: cluster the parcels, take the largest
    cluster by area, and if that cluster's centroid is not inside one of its
    own parcels, snap to the nearest parcel that contains a point.
    """
    cs = [(sum(x for x, _ in r) / len(r), sum(y for _, y in r) / len(r), r)
          for r in rings]
    # Single-linkage clustering at 9 km — closer than the gaps between separate
    # properties, wider than the gaps between abutting claim cells.
    TH = 9000 / 111320.0
    groups = []
    for c in cs:
        hit = [g for g in groups
               if any(math.hypot((c[0]-o[0]) * COSLAT, c[1]-o[1]) < TH for o in g)]
        if not hit:
            groups.append([c])
        else:
            merged = [c] + [x for g in hit for x in g]
            for g in hit: groups.remove(g)
            groups.append(merged)
    want = PREFER.get(_owner[0].upper()) if _owner else None
    if want and len(groups) > 1:
        def score(g):
            lo = sum(c[0] for c in g) / len(g); la = sum(c[1] for c in g) / len(g)
            return want[0] * lo * COSLAT + want[1] * la
        big = max(groups, key=score)
    else:
        big = max(groups, key=lambda g: sum(len(c[2]) for c in g))
    lon = sum(c[0] for c in big) / len(big)
    lat = sum(c[1] for c in big) / len(big)
    if any(point_in(lon, lat, c[2]) for c in big):
        return lon, lat
    near = min(big, key=lambda c: math.hypot((c[0]-lon) * COSLAT, c[1]-lat))
    return near[0], near[1]

def point_in(x, y, ring):
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]; xj, yj = ring[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside

def parts(owner, b):
    """One entry per named property, or one for the whole holding."""
    rule = SPLITS.get(owner.upper())
    if not rule:
        return [(None, b["rings"], b["ha"], b["n"])]
    out = []
    for name, lo, hi in rule:
        rings = [r for r in b["rings"]
                 if (lambda lat: (lo is None or lat >= lo) and (hi is None or lat < hi))(
                     sum(y for _, y in r) / len(r))]
        if not rings: continue
        share = len(rings) / max(1, b["n"])
        out.append((name, rings, b["ha"] * share, len(rings)))
    return out or [(None, b["rings"], b["ha"], b["n"])]

blocks = []
for owner, b in sorted(by.items(), key=lambda kv: -kv[1]["ha"]):
    if b["ha"] < MIN_HA and owner.upper() != SUBJECT: continue
    if any(w in owner.upper() for w in EXCLUDE): continue
    op, proj = EDITORIAL.get(owner.upper(), (None, None))
    for i, (pname, rings, pha, pn) in enumerate(parts(owner, b)):
        # Centroid of ALL the holder's parcels, not of its largest one. The
        # biggest single parcel is often on an edge — Thesis's was at the north
        # end of its ground, which put the logo off the block it names.
        _owner[0] = owner
        lon, lat = anchor(rings)
        if ANCHOR.get(owner.upper()) == "east":
            lon = max(x for r in rings for x, _ in r) + 0.012
        if not (CORRIDOR[0] <= lon <= CORRIDOR[2] and CORRIDOR[1] <= lat <= CORRIDOR[3]):
            continue
        blocks.append({"holder": owner, "operator": op,
                       "project": pname or proj,
                       "ha": round(pha), "tenures": pn,
                       "label_at": [round(lon, 5), round(lat, 5)],
                       # The true point on the holder's ground. If de-collision
                       # has to move the label, a leader is drawn back to this.
                       "anchor_at": [round(lon, 5), round(lat, 5)],
                       "subject": owner.upper() == SUBJECT,
                       # The logo goes on the holder's largest property only:
                       # the same mark twice on one map reads as two companies.
                       "logo": i == 0,
                       # Only the subject is outlined, so only the subject's
                       # boundary is shipped — fourteen holders' worth was
                       # 0.2 MB the viewer loaded and threw away.
                       "outline": boundary(rings) if owner.upper() == SUBJECT else None,
                       "rings": rings})
json.dump({"as_of": asof, "min_ha": MIN_HA,
           "note": "holder is the registered owner; operator and project are editorial",
           "blocks": blocks}, open(ROOT / "data" / "district.json", "w"),
          separators=(",", ":"))
print(f"district.json     {len(blocks)} holders ≥ {MIN_HA:,} ha, "
      f"{sum(b['tenures'] for b in blocks):,} tenures")
for b in blocks:
    tag = f"  [{b['operator']}{' · ' + b['project'] if b['project'] else ''}]" if b["operator"] else ""
    print(f"   {b['ha']:>7,} ha  {b['tenures']:>4} tenures  {b['holder']}{tag}")
