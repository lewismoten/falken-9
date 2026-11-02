# Dark report presentation derivatives

These 22 SVG/PNG pairs are **presentation derivatives**, not replacements for
scientific evidence. They cover the exact inline study009–016 PNGs in the root
report, including both study-010-011-walkthrough figures. Study directories and
basenames are retained. No report links or publication packages are changed here.

## Rebuild and verify

From the repository root, using Python with CairoSVG and Pillow installed:

```sh
.venv/bin/python scripts/prepare_dark_report_figures.py
.venv/bin/python -m pytest tests/test_dark_report_figures.py -q
```

Renderer used: CairoSVG 2.9.1 (underlying Cairo version is recorded in
`manifest.json`). Dependencies were installed only in the existing local virtual
environment, not globally. Fonts and text/font sizes are those requested by each
original SVG; font rasterization may vary with system/font/renderer versions.

## Theme and scientific meaning

The canvas/panel/ink/muted/grid colors are `#11151a`, `#181e26`, `#e7e8e4`,
`#a6b0b7`, `#3b4652`, respectively, taken from the actual publication stylesheet.
Accents echo early dark study figures: green `#82d5a1`, blue `#7fb7e3`, orange
`#eda85f`, vermilion `#e6a08d`. Approved membership remains green where originally
green; errors remain reddish, independent rectangles orange, certified rectangles
green and original codes blue. Local expert-class and sampler palettes retain
separate muted purple/green/ochre/blue or neutral/teal/rust categories. Green
membership fills and brighter chosen-cell outlines remain distinct.

**Attention display:** the 81 heatmap cell fills are generated from the original
frozen Q15 attention values with a dark-to-bright-blue **square-root** display
transfer. The legend is “Dark 0 → bright blue 1 (√ scale); rows sum to 32768.”
The original numeric values, row normalization, cell geometry and ordering are
unchanged. This explicitly labeled presentation transfer replaces the earlier
white-to-blue rendering; it is not a change to the model or measured attention.

## Preservation and provenance

- `manifest.json` maps every original PNG/SVG identity to its separate derivative
  PNG/SVG identity with SHA-256 hashes, renderer versions, palette, and every
  paint attribute transformation by XML element index (including preserved paint).
- `source-preservation.json` records the worker's original 198 input hashes.
  The 196 files under `docs/research` and `research/inventory.json` remain
  unchanged. The exact former `report.md` is retained as `source-report.md`,
  matching its original digest; the canonical report is now the parent-owned
  integration output with restored model views and updated presentation links.
  The generator never silently refreshes this historical snapshot.
- `contact-sheet.png` is a review aid, not a report figure or evidence artifact.
- All manifest paths are repository-relative; there are no private paths/URLs.

The generator substitutes literal SVG paint attributes and adds root
`xml:space="preserve"` so real SVG renderers retain the original numeric-table
column spaces. It does not reconstruct geometry or invert pixels. XML tests
preserve tags, element order, text, tails, paths, coordinates, fonts, line widths,
opacities and titles, except for the explicitly updated attention display-scale
legend described above. Its 81 colors are checked against the frozen Q15 values.
Tests independently compare these
semantics for all 22 pairs, verify original/derived hashes, exact counts, canvas
pixels/dimensions, all reviewed palette transformations, and PNG equality with a
fresh real SVG render.

Native/detail review covered the study009 mechanism boards, attention walkthrough,
and study014 feasible bands; the complete contact sheet was reviewed. Existing
layout density and wording (including “Pale” feasible bands) are intentionally
retained; no geometry/text cleanup was performed. Source PNGs sometimes came from
a different renderer than their paired SVGs; these new PNGs intentionally follow
the preserved SVG geometry rather than trying to reproduce Pillow typography.

Five focused derivative tests cover geometry/text preservation, original input
hashes, complete pairs, real PNG rendering, palette/heatmap semantics and literal
table spacing. CairoSVG 2.9.1 uses Cairo 1.18.4. The initial worker's full root
suite exceeded 180 seconds and was not claimed complete. Parent integration
separately exercises the publication, media, inventory, screenshot and diagram
suites; operational verification logs remain outside the consumer payload.
