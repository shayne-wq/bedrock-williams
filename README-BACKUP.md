# What is in this repo

The Williams deck as delivered, and everything needed to rebuild it — **except
the client data room**, which is not committed. The extractors expect it at
`../OMega/99-Williams Data Room/`.

**This repo is public, and it contains Omega Pacific's derived drill assays
(5,234 sampled intervals), geochemistry, geophysics and tenure.** Published at
the issuer's direction. Anyone can clone it; treat every figure in `data/` as
disclosed.

    williams/
      index.html            the deck
      diag.html             device graphics diagnostic
      extract.py            drilling + geochemistry  → data/*.json
      rasters.py            geophysics GeoTIFF       → data/geophys/*.png
      claims.py             BC mineral tenure (live) → data/claims.geojson
      logos.py              neighbour logo plates    → data/logos/
      capture.mjs           chapter stills           → data/slides/*.png
      optimise_slides.py    …as shippable JPEG
      data/                 everything the deck loads

## Embedding it

Press **Embed** in the deck for a copy-paste snippet — shape, opening slide,
autoplay, and the disclosure line. Paste into a WordPress **Custom HTML** block
or an Elementor **HTML** widget.

The aspect ratio uses percentage padding rather than CSS `aspect-ratio`, because
page builders strip or override newer CSS in places. `?embed=1` hides the
authoring controls; Sources stays, because provenance is the point. The
"no mineral resource has been estimated" line is written into the snippet as
well as shown on-slide, so it survives being pasted into someone else's page.

Live at <https://bedrock-fawn.vercel.app/williams/> — deployed as a subpath of
the Bedrock Vercel project so the Elk demo keeps the root.
