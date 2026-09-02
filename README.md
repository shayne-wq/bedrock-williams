# Williams — Omega Pacific Resources

**Live:** https://bedrock-fawn.vercel.app/williams/

Deployed as a subpath of the Bedrock project rather than as its own, so it sits
on the Bedrock domain and leaves the Elk Gold demo at the root untouched. To
redeploy after changing anything here:

    cd Bedrock && rm -rf orebody/williams && mkdir -p orebody/williams \
      && cp williams/index.html orebody/williams/ \
      && cp -R williams/data orebody/williams/data \
      && cd orebody && vercel --prod --yes

`orebody/williams/` is a build copy — never edit it; the source is here.
The page carries `noindex, nofollow`: the URL is unlisted, not private.

## Editing a slide

Press **Edit** in the deck. Per slide you can:

* **Lock the camera** — fly the view by hand, press Lock, and that slide keeps
  exactly what you framed. A locked slide bypasses `frameFor()` and the aim
  shift entirely and flies straight to the stored position: what you framed and
  what the deck flies to are then the same computation, which is the point.
  Unlock returns it to the built-in camera.
* **Edit the caption** — eyebrow, title, body. The caption repaints as you type
  and the chapter rail picks up retitles.

Edits save to `localStorage` as you work. **Copy changes** emits a
`CAM_FIXED` / `TEXT_FIXED` block; paste it over the placeholders in
`index.html` so the deck ships with them instead of depending on one browser.
Re-run `capture.mjs` + `optimise_slides.py` afterwards so the no-WebGL stills
match.

`diag.html` runs four escalating graphics tests on a device, with a copy button.

**Framing is checked by walking the deck IN ORDER**, not by jumping to chapters:
the aim shift depends on the destination camera, and a bug there is invisible
to a test that arrives from the wrong place. The check reads the real DOM
rectangles of the chrome and counts subject points hidden behind them.

**The no-WebGL fallback is a slide deck, not an error page.** Every chapter is
pre-rendered by `capture.mjs` and shown above its own caption and figures, so a
device that cannot run Cesium still sees what Cesium would have drawn. Re-run
`capture.mjs` + `optimise_slides.py` whenever a chapter's camera or layers
change, or the stills will quietly describe an older deck than the text does.

`?ctxfail=N` forces the first N WebGL context attempts to fail, so the mobile
fallback ladder and the text mode can be exercised on a desktop.
`?ctxfail=3` renders the deck as text: same chapters, same figures, same
sources, no globe. The chapter data is computed above the renderer precisely
so both modes read from one place.

A Bedrock deck built from a real client data room, running in **exploration
mode**: drilling, geochemistry, magnetics and IP, no block model, and therefore
no tonnage, no contained metal and no economics anywhere in it.

    cd Bedrock/williams
    python3 extract.py     # drilling + geochemistry  → data/*.json
    python3 rasters.py     # geophysics GeoTIFFs      → data/geophys/*.png
    python3 claims.py      # BC mineral tenure (live) → data/claims.geojson
    python3 logos.py       # neighbour logo plates    → data/logos/
    node   capture.mjs             # chapter stills   → data/slides/*.png
    python3 optimise_slides.py     # …as shippable JPEG (1.5 MB for twelve)
    python3 -m http.server 8899 && open http://127.0.0.1:8899/

Requires `pyproj` and `Pillow`. Source data lives in `../OMega/99-Williams Data
Room/` and is not committed.

## What is in it

| Layer | Count | Source |
|---|---|---|
| Drill holes | 45 drilled (13,056 m) + 17 planned (5,750 m) | `q_ddh_collar/survey/desurvey.csv` |
| Assays | 5,234 sampled intervals, 1983–2024 | `q_ddh_samp_int_assay_i1.csv` |
| Soil geochem | 4,503 samples, 1973–2021 | `q_samp_pt_assay_soil.csv` |
| Rock geochem | 1,023 of 1,025 samples | `q_samp_pt_assay_rock.csv` |
| Magnetics | TMI / RTP / CVG, 2020 heliborne, 25 m | GeoTIFF, EPSG:32609 |
| Induced polarisation | CHG + RES depth slices, 2021 ground DCIP | GeoTIFF, EPSG:3156 |
| VTEM | RTP magnetics, 2021 | GeoTIFF, EPSG:32609 |
| Mineral tenure | 11 subject; 16 district holders / 705 tenures | BC MTO, live WFS |
| Zones | GIC (12 holes) and T-Bill (33 holes) | hull of drilled collars |

## The deck

12 chapters in five sections: **the district** (who else holds ground in the
Toodoggone) → **the property** (the claim block, then GIC and T-Bill) → **the
evidence** (magnetics, geochem, IP) → **what has been drilled** → **what is
next**.

Chapter 1 opens on British Columbia and flies in, waiting on
`globe.tilesLoaded` rather than a fixed delay so it does not fly out of a blur.

The magnetic vertical gradient, the 2026 planned holes and the untested-ground
view are all still loaded and toggleable from the Layers panel; they just do not
have chapters of their own.

Layout: Omega Pacific mark and chapter rail top-left, *powered by Bedrock*
bottom-left, caption and transport right, layer controls behind a **Layers**
dropdown, legends bottom-left.

## Three things worth knowing

**The compositing rule was recovered, not chosen.** Candidate rules were run
against the two intervals Omega Pacific has published and the one that
reproduces them was kept: 0.5 g/t Au cut, at most 3 m of continuous internal
dilution, length-weighted, never ending on waste. WM22-02 comes back as
96.92 m @ 2.16 g/t and WM24-01 as 18.98 m @ 6.22 g/t — both exact. A deck whose
headline disagrees with the news release gives a reader no way to tell which one
is wrong.

**The acreage audits.** The register returns 11 tenures totalling 11,490 ha for
OMEGA PACIFIC RESOURCES INC; the company reports 11,490 ha. Neighbours are
looked up rather than supplied, because a company cannot assert its neighbours'
tenure, and the query date travels with the data because tenures lapse.

**Every hole fits in one corner.** 45 holes over four decades occupy a 2.6 ×
3.7 km box inside a 15 km claim block. That figure is measured off the collars
and the tenure boundary in the browser, not typed into a slide.

## Rendering notes

- **Ground translucency is confined to a rectangle** over the property. Applied
  globally it makes the far side of the Earth visible through the hillside —
  the first build drew the Mediterranean under the GIC drill fan.
- **Each geophysics product drapes on its own extent**, never the union: the
  2020 airborne block is 23 km across and the 2021 ground IP is 4.5 km.
- **Geochem is draped on the DEM.** Four fifths of the samples carry no recorded
  elevation, so none of them use the recorded value — mixing surveyed and
  interpolated heights in one layer produces a surface that is neither.
- **The camera aims at the clear area, not the canvas centre.** A chapter rail
  holds the left ~240 px, a caption card the right ~470 px and the bottom
  ~420 px, so a subject centred on the canvas lands under the paragraph
  describing it. The aim point is shifted in both axes, in metres derived from
  the range and field of view, so it holds at 1.5 km and at 200 km. The vertical
  term carries a `sin(pitch)` factor because ground distance per screen pixel
  grows as the camera flattens; a chapter showing grade callouts also reserves
  a card-width on the left, since callouts all extend that way.
- **Slide copy is investor-facing; methodology lives in Sources.** Every figure
  in the copy is computed from the data at load, not typed in.
- **Chapters declare a target and a range**, not a camera position; the position
  is derived. Declaring the position means every pitch change silently re-aims
  the shot.
- **Neither magnetic survey covers the claim block alone**; their union does, so
  the Magnetics layer draws both, each on its own extent. They were flown a year
  apart and levelled separately, so colour is not comparable across the seam.
- **Only the subject block is outlined.** The dissolved boundary was correct and
  still wrong to draw for fourteen holders — the edges competed with the fills,
  the logos and the names on a slide whose job is who is next door. The
  boundary is still computed, for the subject, by the method below.
- **The district map is consolidated: one fill per holder, and the outline is
  the dissolved outer edge.** MTO tenure cells are a grid and abutting parcels
  share edges exactly, so an edge appearing twice is interior and an edge
  appearing once is the boundary — counting them dissolves the block for
  drawing while leaving the parcels intact as data. Outlining every tenure
  redrew the filing grid the consolidated fill exists to remove. Where two
  parcels meet along edges that are not vertex-for-vertex equal, that seam
  survives as a short interior line.
- **Name chips take their block's colour**, with text picked from the chip's own
  relative luminance rather than assumed — half the palette is dark enough for
  cream text and half is not, and getting it wrong makes a name unreadable on
  the one slide whose whole job is the names.
- **The property name is the primary element on the district map**, not the
  company mark: warm cream, larger than the holder, and it does not shrink with
  distance. A place name legible only after you zoom in is not doing its job on
  the slide it appears on.
- **District labels de-collide.** Centerra's Kemess and Coast Copper's ground
  are 20 km apart and their marks overlapped so completely that the KEMESS chip
  read as the caption to the Coast Copper logo — a wrong attribution, not a
  crowded map. Biggest holder holds its position; smaller ones are pushed clear.
  Tilt matters here: a ground separation that clears at plan view does not at
  -64°, where the top of the frame is compressed.
- **District labels are laid out in screen space, every frame.** Spacing in
  degrees only works at the zoom it was tuned for — the same 25 km is 300 px at
  60 km range and 40 px at 400 km. Each label is anchored to a real point on its
  holder's ground, projected, spiral-searched in pixels until its rectangle is
  free, unprojected back onto the globe, and given a leader if it had to travel.
  The layout is solved **once**, on arrival at the opening frame, and then
  frozen — a district map is read, not explored, and labels that slide as the
  camera moves never look finished. Pixels are still the right unit for that one
  solve; degrees would be wrong at the opening frame too.
- **`PREFER` picks which of a holder's separate blocks carries the label**, by
  compass direction — Eagle Plains has 24 parcels west and 10 north-east, and
  Theory / Orbit is the north-eastern ground.
- **One holder can work several named properties.** `SPLITS` in `claims.py`
  divides a holder's ground by geography — Finlay's PIL and ATTY are 15 km
  apart — and the logo goes on the largest block only.
- **Grade callouts extend away from the caption, never alternating**, and a hole
  named in a callout drops its collar chip.
- **Company marks are the issuer's supply, and only theirs.** A logo is a
  trademark, so one is drawn only where Omega Pacific provided the file and only
  against the holder whose ground it is; every other block carries the
  registered name as text. Plates are light or dark depending on the mark's own
  mean luminance — a white-on-transparent mark on a white plate is an empty
  rectangle, and so is a black wordmark on a dark one.
- **Registered holder ≠ operator.** The register is the only thing on the
  district map that is sourced; operator and project names (Sun Summit on
  Theory, Centerra on Kemess) are editorial and labelled as such.
- **Zone outlines are the extent of drilling**, not a mapped contact — the
  convex hull of each zone's collars pushed out 300 m.
- **Globe translucency is confined to a 45 km box, and switched off entirely
  above 0.98 alpha.** The rectangle's edge is a hard seam between translucent
  and solid ground; a box drawn tight to the property put that seam through the
  middle of every property-scale shot.
- **Every trace is drawn twice** — a wide near-black halo, then the zone colour
  on top. That is what makes a thin line readable on any background rather than
  on the one it was tuned against.
- **A zone chapter draws only that zone's drilling.** Line geometry is bucketed
  by zone at build time, because a Cesium `Primitive` is all-or-nothing — you
  cannot hide one instance inside it — so one collection per zone is the only
  way to keep the other zone's rods out of the corner of the frame.
- **Label fades are near-binary.** A dark-backed label at 15 % alpha still shows
  its background over bright terrain but not its cream text, so a fading card
  reads as an empty box. The transition band is now 1 %: legible, or gone.
- **The next chapter's raster is prefetched.** An IP slice is a 1.5 MB PNG that
  must be fetched, decoded and uploaded; a 2.5 s flight is not long enough, and
  the deck was arriving at geophysics slides with no geophysics on them.

## Not read yet

VTEM and DCIP voxels (`.omf`), magnetic and chargeability isosurfaces (`.dxf`,
1.4 GB), the 2005 IP survey as a georeferenced map sheet, and 279 MB of raw
magnetic line data. All renderable; none of it is in the deck.
