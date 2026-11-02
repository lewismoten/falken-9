# Indexed report previews

Lossy display-only derivatives of the 39 inline report PNGs. Scientific full-color PNG/SVG sources remain authoritative and untouched by this script. No new scientific evidence, pixel-lossless claim, model reconstruction, game-photo optimization, or transport-byte optimization is implied.

Native dimensions are preserved: no resampling, cropping or dithering of the previews. Pillow MEDIANCUT retains populated continuous heatmap/visual-weight levels; MAXCOVERAGE protects categorical extremes in other figures. Each figure uses the same quantizer for both candidates, recorded in the metrics. The seven most frequent exact source colors are pinned before fixed-palette mapping. Sixteen entries use PNG color type 3 / 4-bit indices; 32 entries use type 3 / 8-bit indices. Compression level 9, optimize=False. Reproduction is byte-exact with the encoder versions recorded in manifest.json.

`manifest.json` is the source-to-preview alias map. Its figures list includes both real 16/32 candidates, bytes, SHA-256 hashes, measured RGB errors and selection rationale. Candidates are retained under `candidates/{16,32}/` for native-size comparison; they and the contact sheets are review aids, not additional report figures. `input-preservation.json` records source inputs, native screenshots, and SVG hashes. Full-color source SVGs are not quantized.

Metrics use decoded RGB, 0–255 units: channel MAE/RMSE, foreground (max channel distance from dominant canvas >24), neutral bright-text proxy (mean RGB >=150, channel spread <=90), edge proxy (adjacent max channel difference >32), and common saturated-color nearest-palette coverage. Foreground/text/edge masks are derived only from original pixels. Salient-color counts are diagnostics, not semantic class counts or a proof of legibility. Text/legend readability also requires native-size visual review. Antialiased pixels remain geometrically intact but their colors are approximated.

Default is 16 colors. Dense continuous heatmaps/visual weight maps use 32; additional exceptions trigger when 16-color foreground MAE >14 or text-proxy MAE >15. Metrics are display-review heuristics, not scientific acceptance criteria. The small contact sheets alone cannot establish text readability.

Regenerate from repository root: `.venv/bin/python scripts/prepare_indexed_report_figures.py`.

Complete: True. Figures: 39; 35 × 16, 4 × 32. Source PNG bytes 5,811,684; selected PNG bytes 1,723,870; saved 4,087,814 (70.34%). Review/candidate files excluded from this comparison.

| Source | Colors | Original bytes | Selected bytes | Foreground MAE 16 / 32 | Text MAE 16 / 32 |
|---|---:|---:|---:|---:|---:|
| assets/interpretability/model-inspection/tensor-workflow.png | 32 | 190462 | 51665 | 15.498 / 8.978 | 7.272 / 7.348 |
| assets/interpretability/model-inspection/netron-dark.png | 16 | 168178 | 32716 | 1.557 / 1.007 | 3.707 / 2.841 |
| assets/interpretability/strategy-circuit-map.png | 32 | 138156 | 45583 | 14.885 / 6.710 | 9.022 / 6.375 |
| assets/interpretability/strategy-board-comparisons.png | 16 | 132675 | 49581 | 8.512 / 5.010 | 6.392 / 4.031 |
| assets/interpretability/study-003/necessity-context.png | 16 | 140736 | 41281 | 7.280 / 4.018 | 5.579 / 4.031 |
| assets/interpretability/study-003/patch-and-restoration.png | 16 | 125960 | 41626 | 6.938 / 3.899 | 4.521 / 3.623 |
| assets/interpretability/study-004/square-paths.png | 16 | 189547 | 53587 | 8.208 / 5.308 | 6.523 / 3.848 |
| assets/interpretability/study-004/position-contrasts.png | 16 | 163763 | 50989 | 6.838 / 4.163 | 4.519 / 3.531 |
| assets/interpretability/study-005/attention-overview005.png | 16 | 162343 | 49199 | 2.992 / 1.719 | 3.413 / 2.132 |
| assets/interpretability/study-005/attention-contrasts005.png | 32 | 173315 | 54945 | 16.292 / 6.461 | 21.302 / 8.247 |
| docs/research/study-006/overview006.png | 16 | 76105 | 24763 | 2.178 / 1.285 | 3.412 / 2.148 |
| docs/research/study-006/cases006.png | 16 | 115847 | 28280 | 4.568 / 2.363 | 2.284 / 1.700 |
| docs/research/study-007/overview007.png | 16 | 121665 | 43131 | 4.539 / 2.301 | 3.677 / 2.299 |
| docs/research/study-007/cases007.png | 16 | 129306 | 39534 | 4.590 / 2.458 | 5.290 / 2.395 |
| docs/research/study-007/matched-controls007.png | 16 | 125357 | 41638 | 4.355 / 2.275 | 3.006 / 1.884 |
| docs/research/study-008/overview008.png | 16 | 89820 | 32309 | 3.045 / 1.809 | 1.505 / 1.029 |
| docs/research/study-008/cases008.png | 16 | 152504 | 49057 | 4.946 / 2.520 | 4.547 / 1.965 |
| assets/interpretability/publication-dark/study-009/overview009.png | 16 | 151091 | 46915 | 9.745 / 7.279 | 8.132 / 7.012 |
| assets/interpretability/publication-dark/study-009/mechanism009.png | 16 | 162551 | 49302 | 10.413 / 6.534 | 11.569 / 7.372 |
| assets/interpretability/publication-dark/study-009/restoration-damage009.png | 16 | 160610 | 50026 | 10.371 / 6.507 | 11.448 / 7.282 |
| assets/interpretability/publication-dark/study-009/raw-alignment009.png | 16 | 132879 | 42969 | 9.444 / 5.665 | 11.197 / 6.942 |
| assets/interpretability/publication-dark/study-009/robust009.png | 16 | 157939 | 48261 | 6.267 / 4.159 | 11.349 / 7.199 |
| assets/interpretability/publication-dark/study-010-011-walkthrough/forward-attention1011.png | 32 | 165803 | 46184 | 12.136 / 5.694 | 14.966 / 7.917 |
| assets/interpretability/publication-dark/study-010-011-walkthrough/forward-experts1011.png | 16 | 208540 | 54722 | 11.788 / 8.039 | 8.631 / 6.592 |
| assets/interpretability/publication-dark/study-010/overview010.png | 16 | 121544 | 32618 | 7.588 / 5.385 | 5.685 / 3.590 |
| assets/interpretability/publication-dark/study-010/orbits010.png | 16 | 97112 | 27133 | 3.904 / 2.760 | 8.963 / 7.050 |
| assets/interpretability/publication-dark/study-011/cardinality011.png | 16 | 143940 | 31530 | 1.867 / 1.107 | 0.940 / 0.529 |
| assets/interpretability/publication-dark/study-011/collisions011.png | 16 | 151350 | 46211 | 6.109 / 4.212 | 10.072 / 6.508 |
| assets/interpretability/publication-dark/study-012/overview012.png | 16 | 132865 | 38601 | 10.678 / 7.058 | 8.020 / 6.887 |
| assets/interpretability/publication-dark/study-012/case012.png | 16 | 105094 | 30192 | 5.026 / 3.062 | 9.444 / 5.366 |
| assets/interpretability/publication-dark/study-013/intervals013.png | 16 | 156123 | 51705 | 8.871 / 5.943 | 7.648 / 6.680 |
| assets/interpretability/publication-dark/study-013/witnesses013.png | 16 | 172052 | 46171 | 9.746 / 6.474 | 11.021 / 6.605 |
| assets/interpretability/publication-dark/study-014/joint014.png | 16 | 113110 | 34683 | 3.267 / 2.110 | 9.744 / 5.776 |
| assets/interpretability/publication-dark/study-014/witness014.png | 16 | 154879 | 40873 | 12.967 / 9.271 | 11.308 / 8.026 |
| assets/interpretability/publication-dark/study-015/paths015.png | 16 | 249493 | 73876 | 7.126 / 4.842 | 8.704 / 5.518 |
| assets/interpretability/publication-dark/study-015/routes015.png | 16 | 248516 | 69357 | 2.836 / 2.053 | 12.113 / 8.522 |
| assets/interpretability/publication-dark/study-015/sampler015.png | 16 | 148377 | 45617 | 3.440 / 2.482 | 9.410 / 7.672 |
| assets/interpretability/publication-dark/study-016/roles-outcomes016.png | 16 | 127102 | 39509 | 6.733 / 4.412 | 6.664 / 3.618 |
| assets/interpretability/publication-dark/study-016/branching-example016.png | 16 | 154975 | 47531 | 13.235 / 8.715 | 11.719 / 9.073 |
