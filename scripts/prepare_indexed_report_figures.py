#!/usr/bin/env python3
"""Lossy display-only indexed previews; never modify scientific source assets."""
from pathlib import Path
import re
import io
import argparse
import hashlib
import json
import platform
import zlib
from PIL import __version__ as PILLOW_VERSION
from PIL import ImageDraw, ImageFont
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = Path('assets/interpretability/publication-indexed')


def report_sources(root=ROOT):
    text = (root / 'report.md').read_text()
    sources = [Path(p) for p in re.findall(r'!\[[^\]]*\]\(([^)]+\.png)\)', text)]
    if len(sources) != 39 or len(set(sources)) != 39:
        raise ValueError('Expected exactly 39 unique inline report PNG previews')
    for p in sources:
        if p.is_absolute() or '..' in p.parts or not (root / p).is_file():
            raise ValueError(f'Invalid source {p}')
        if 'screenshot' in str(p).lower():
            raise ValueError('Game screenshots are not report figure inputs')
    return sources


def output_path(source):
    return OUTPUT / source.parent.name / source.name


def candidate(source, colors, quantizer='MAXCOVERAGE'):
    """Return true indexed PNG bytes plus decoded-RGB errors (0–255 units).

    No pixel location changes and no dithering. Median-cut preserves densely
    populated heatmap levels; maximum-coverage protects categorical extremes.
    Pin the seven most frequent exact source colors
    (usually canvas/panel/text/category fills), then map with Pillow, no dithering.
    """
    if colors not in (16, 32):
        raise ValueError('Only 16 or 32 palette entries are supported')
    source = source.convert('RGB')
    counts = source.getcolors(source.width * source.height)
    canvas = max(counts, key=lambda item: (item[0], item[1]))[1]
    counts.sort(reverse=True)
    if quantizer not in ('MEDIANCUT', 'MAXCOVERAGE'):
        raise ValueError('Expected MEDIANCUT or MAXCOVERAGE')
    palette_image = source.quantize(colors=colors, method=getattr(Image.Quantize, quantizer),
                                    kmeans=0, dither=Image.Dither.NONE)
    palette = np.array(palette_image.getpalette()[:colors * 3], dtype=np.int16).reshape(colors, 3)
    taken = []
    for count, rgb in counts[:7]:
        distances = np.linalg.norm(palette - rgb, axis=1)
        distances[taken] = np.inf
        index = int(distances.argmin())
        taken.append(index)
        palette[index] = rgb
    palette = palette.astype(np.uint8).ravel().tolist()
    palette_image.putpalette(palette)
    indexed = source.quantize(palette=palette_image, dither=Image.Dither.NONE)
    encoded = io.BytesIO()
    indexed.save(encoded, format='PNG', bits=4 if colors == 16 else 8,
                 optimize=False, compress_level=9)
    data = encoded.getvalue()
    original = np.asarray(source, dtype=np.float32)
    decoded = np.asarray(indexed.convert('RGB'), dtype=np.float32)
    error = np.abs(original - decoded)
    foreground = np.max(np.abs(original - np.array(canvas)), axis=2) > 24
    text = (original.mean(axis=2) >= 150) & (np.ptp(original, axis=2) <= 90)
    gradient = np.zeros(original.shape[:2], dtype=bool)
    gradient[1:] |= np.max(np.abs(original[1:] - original[:-1]), axis=2) > 32
    gradient[:, 1:] |= np.max(np.abs(original[:, 1:] - original[:, :-1]), axis=2) > 32
    saturated = [(n, rgb) for n, rgb in counts
                 if n >= max(64, source.width * source.height * 0.0001)
                 and max(rgb) - min(rgb) >= 45 and max(rgb) >= 80]
    saturated.sort(reverse=True)
    semantic = np.array([rgb for n, rgb in saturated[:24]], dtype=np.float32)
    palette_rgb = np.array(palette, dtype=np.float32).reshape(-1, 3)
    semantic_errors = []
    semantic_indices = []
    if len(semantic):
        distances = np.linalg.norm(semantic[:, None, :] - palette_rgb[None, :, :], axis=2)
        semantic_indices = distances.argmin(axis=1).tolist()
        semantic_errors = distances.min(axis=1).tolist()
    def mean(mask):
        return round(float(error[mask].mean()), 6) if mask.any() else 0.0
    metrics = {
        'quantizer': quantizer,
        'rgb_mae': round(float(error.mean()), 6),
        'rgb_rmse': round(float(np.sqrt(np.square(error).mean())), 6),
        'rgb_p95_channel_error': round(float(np.percentile(error, 95)), 6),
        'rgb_max_channel_error': int(error.max()),
        'foreground_pixels': int(foreground.sum()),
        'foreground_rgb_mae': mean(foreground),
        'foreground_rgb_rmse': round(float(np.sqrt(np.square(error[foreground]).mean())), 6),
        'foreground_p95_channel_error': round(float(np.percentile(error[foreground], 95)), 6),
        'text_pixels': int(text.sum()), 'text_rgb_mae': mean(text),
        'edge_pixels': int(gradient.sum()), 'edge_rgb_mae': mean(gradient),
        'canvas_rgb': list(canvas),
        'canvas_rgb_error': int(np.abs(decoded[np.all(original == canvas, axis=2)] - canvas).max()),
        'salient_chromatic_source_colors': len(semantic),
        'salient_chromatic_palette_indices': len(set(semantic_indices)),
        'salient_chromatic_max_nearest_rgb_distance': round(max(semantic_errors, default=0.0), 6),
        'used_palette_entries': len(indexed.getcolors()),
    }
    return data, metrics


COMPLEX = {
    'tensor-workflow.png': 'Decoded visual weight-map gradients and multiple tensor-category colors; this inspector is not reconstructable model data.',
    'strategy-circuit-map.png': 'Continuous-valued heatmap cells alongside circuit-category colors.',
    'attention-contrasts005.png': 'Attention-value contrasts need additional distinguishable intensity levels.',
    'forward-attention1011.png': 'Corrected panel-C Q15 grid uses dark-to-bright blue attention values; 32 entries preserve additional distinguishable grid levels.',
}


def identity(root, path):
    data = (root / path).read_bytes()
    return {'path': path.as_posix(), 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}


def write_json(root, path, value):
    (root / path).parent.mkdir(parents=True, exist_ok=True)
    (root / path).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def contact_sheet(root, figures):
    """Thumbnails are review aids only: selected PNGs remain native resolution."""
    font = ImageFont.load_default(size=14)
    cells = []
    for i, f in enumerate(figures, 1):
        cell = Image.new('RGB', (400, 330), '#101720')
        preview = Image.open(root / f['indexed']['path']).convert('RGB')
        preview.thumbnail((384, 276), Image.Resampling.LANCZOS)
        cell.paste(preview, ((400 - preview.width) // 2, 46))
        draw = ImageDraw.Draw(cell)
        draw.text((8, 6), f"{i:02d} {Path(f['original']['path']).parent.name}", fill='#edf2f6', font=font)
        draw.text((8, 24), f"{Path(f['original']['path']).name} [{f['indexed']['colors']} colors]", fill='#b4c4d4', font=font)
        cells.append(cell)
    sheet = Image.new('RGB', (1600, ((len(cells) + 3) // 4) * 330), '#101720')
    for i, cell in enumerate(cells):
        sheet.paste(cell, ((i % 4) * 400, (i // 4) * 330))
    sheet.save(root / OUTPUT / 'contact-sheet.png', compress_level=9)
    for start in range(0, len(cells), 12):
        section = Image.new('RGB', (1600, 990), '#101720')
        for j, cell in enumerate(cells[start:start + 12]):
            section.paste(cell, ((j % 4) * 400, (j // 4) * 330))
        target = root / OUTPUT / 'contact-sheets' / f'{start // 12 + 1:02d}.png'
        target.parent.mkdir(parents=True, exist_ok=True)
        section.save(target, compress_level=9)


def build(root=ROOT, deferred=()):
    sources = report_sources(root)
    if not set(deferred) <= {str(p) for p in sources}:
        raise ValueError('Deferred paths must be exact report inputs')
    figures = []
    snapshots = [identity(root, p) for p in sources if str(p) not in deferred]
    screenshots = [identity(root, p.relative_to(root)) for p in sorted((root / 'assets/screenshots').rglob('*')) if p.is_file()]
    pending_svgs = {str(Path(p).with_suffix('.svg')) for p in deferred}
    svgs = [identity(root, p.relative_to(root)) for directory in ('assets/interpretability', 'docs/research')
            for p in sorted((root / directory).rglob('*.svg'))
            if OUTPUT not in p.relative_to(root).parents and str(p.relative_to(root)) not in pending_svgs]
    for source in sources:
        if str(source) in deferred:
            continue
        original = identity(root, source)
        with Image.open(root / source) as opened:
            if 'A' in opened.getbands() and opened.getchannel('A').getextrema() != (255, 255):
                raise ValueError(f'Unexpected meaningful transparency in {source}')
            image = opened.convert('RGB')
        candidates = {}
        for colors in (16, 32):
            data, metrics = candidate(image, colors, quantizer='MEDIANCUT' if source.name in COMPLEX else 'MAXCOVERAGE')
            if source.name == 'forward-attention1011.png':
                centers = [(89 + 39 * x, 627 + 39 * y) for x in range(9) for y in range(9)]
                decoded = Image.open(io.BytesIO(data)).convert('RGB')
                metrics['attention_grid_source_distinct_center_colors'] = len({image.getpixel(p) for p in centers})
                metrics['attention_grid_distinct_center_colors'] = len({decoded.getpixel(p) for p in centers})
            target = OUTPUT / 'candidates' / str(colors) / source.parent.name / source.name
            (root / target).parent.mkdir(parents=True, exist_ok=True)
            (root / target).write_bytes(data)
            candidates[str(colors)] = dict(metrics, **identity(root, target))
        q16, q32 = candidates['16'], candidates['32']
        colors = 16
        reason = '16-color default: readable neutral text, dark canvas and category colors retained; additional 32-color shades are not necessary for this categorical/table diagram.'
        if source.name in COMPLEX:
            colors = 32
            reason = COMPLEX[source.name] + ' 16 colors discard useful intermediate shades; select 32.'
        elif q16['text_rgb_mae'] > 15 or q16['foreground_rgb_mae'] > 14:
            colors = 32
            reason = '32-color readability exception: 16-color foreground or neutral-text MAE exceeds the conservative display-review threshold (14 / 15 RGB units).'
        selected = candidates[str(colors)]
        if selected['text_rgb_mae'] >= 20 or selected['foreground_rgb_mae'] >= 20:
            raise ValueError(f'Neither compact palette is acceptable without review: {source}')
        reason += (f" Measured foreground MAE: 16={q16['foreground_rgb_mae']:.3f}, 32={q32['foreground_rgb_mae']:.3f}; "
                   f"neutral-text MAE: 16={q16['text_rgb_mae']:.3f}, 32={q32['text_rgb_mae']:.3f} (0–255 RGB units).")
        target = output_path(source)
        (root / target).parent.mkdir(parents=True, exist_ok=True)
        (root / target).write_bytes((root / selected['path']).read_bytes())
        figures.append({'original': original,
                        'indexed': dict(identity(root, target), colors=colors, bit_depth=4 if colors == 16 else 8),
                        'dimensions': list(image.size),
                        'quality_metrics': {'candidates': candidates, 'selected_colors': colors},
                        'reason': reason})
        print(f'{colors:2d} {source.name:32s} {original["bytes"]:7d} -> {selected["bytes"]:6d} fg={selected["foreground_rgb_mae"]:.3f} text={selected["text_rgb_mae"]:.3f}', flush=True)
    before = sum(f['original']['bytes'] for f in figures)
    after = sum(f['indexed']['bytes'] for f in figures)
    manifest = {'schema_version': 1, 'complete': not deferred,
                'deferred_sources': sorted(deferred), 'source_report': 'report.md',
                'scope': 'Lossy display-only report PNG previews, not scientific evidence or model/game transport.',
                'encoder': {'pillow': PILLOW_VERSION, 'numpy': np.__version__, 'python': platform.python_version(),
                            'zlib': zlib.ZLIB_VERSION, 'quantizer': 'Pillow MEDIANCUT for continuous heatmaps/visual weights, MAXCOVERAGE for categorical/table figures; pin seven most frequent source colors, then fixed-palette mapping',
                            'dither': 'NONE', 'compress_level': 9, 'optimize': False,
                            'resampling': False, 'cropping': False},
                'totals': {'figures': len(figures), 'colors_16': sum(f['indexed']['colors'] == 16 for f in figures),
                           'colors_32': sum(f['indexed']['colors'] == 32 for f in figures),
                           'original_bytes': before, 'indexed_bytes': after, 'saved_bytes': before - after,
                           'saved_percent': round(100 * (before - after) / before, 6)},
                'figures': figures}
    # Verify every snapshotted source and native screenshot before recording preservation.
    for item in snapshots + screenshots + svgs:
        if identity(root, Path(item['path'])) != item:
            raise RuntimeError(f'Protected input changed during conversion: {item["path"]}')
    write_json(root, OUTPUT / 'input-preservation.json', {'report_inputs': snapshots, 'protected_screenshots': screenshots,
                                                        'protected_svgs': svgs, 'deferred_sources': sorted(deferred)})
    write_json(root, OUTPUT / 'manifest.json', manifest)
    contact_sheet(root, figures)
    lines = ['# Indexed report previews', '',
             'Lossy display-only derivatives of the 39 inline report PNGs. Scientific full-color PNG/SVG sources remain authoritative and untouched by this script. No new scientific evidence, pixel-lossless claim, model reconstruction, game-photo optimization, or transport-byte optimization is implied.', '',
             'Native dimensions are preserved: no resampling, cropping or dithering of the previews. Pillow MEDIANCUT retains populated continuous heatmap/visual-weight levels; MAXCOVERAGE protects categorical extremes in other figures. Each figure uses the same quantizer for both candidates, recorded in the metrics. The seven most frequent exact source colors are pinned before fixed-palette mapping. Sixteen entries use PNG color type 3 / 4-bit indices; 32 entries use type 3 / 8-bit indices. Compression level 9, optimize=False. Reproduction is byte-exact with the encoder versions recorded in manifest.json.', '',
             '`manifest.json` is the source-to-preview alias map. Its figures list includes both real 16/32 candidates, bytes, SHA-256 hashes, measured RGB errors and selection rationale. Candidates are retained under `candidates/{16,32}/` for native-size comparison; they and the contact sheets are review aids, not additional report figures. `input-preservation.json` records source inputs, native screenshots, and SVG hashes. Full-color source SVGs are not quantized.', '',
             'Metrics use decoded RGB, 0–255 units: channel MAE/RMSE, foreground (max channel distance from dominant canvas >24), neutral bright-text proxy (mean RGB >=150, channel spread <=90), edge proxy (adjacent max channel difference >32), and common saturated-color nearest-palette coverage. Foreground/text/edge masks are derived only from original pixels. Salient-color counts are diagnostics, not semantic class counts or a proof of legibility. Text/legend readability also requires native-size visual review. Antialiased pixels remain geometrically intact but their colors are approximated.', '',
             'Default is 16 colors. Dense continuous heatmaps/visual weight maps use 32; additional exceptions trigger when 16-color foreground MAE >14 or text-proxy MAE >15. Metrics are display-review heuristics, not scientific acceptance criteria. The small contact sheets alone cannot establish text readability.', '',
             'Regenerate from repository root: `.venv/bin/python scripts/prepare_indexed_report_figures.py`.', '',
             f'Complete: {manifest["complete"]}. Figures: {len(figures)}; {manifest["totals"]["colors_16"]} × 16, {manifest["totals"]["colors_32"]} × 32. Source PNG bytes {before:,}; selected PNG bytes {after:,}; saved {before-after:,} ({manifest["totals"]["saved_percent"]:.2f}%). Review/candidate files excluded from this comparison.', '',
             '| Source | Colors | Original bytes | Selected bytes | Foreground MAE 16 / 32 | Text MAE 16 / 32 |',
             '|---|---:|---:|---:|---:|---:|']
    for f in figures:
        a, b = f['quality_metrics']['candidates']['16'], f['quality_metrics']['candidates']['32']
        lines.append(f"| {f['original']['path']} | {f['indexed']['colors']} | {f['original']['bytes']} | {f['indexed']['bytes']} | {a['foreground_rgb_mae']:.3f} / {b['foreground_rgb_mae']:.3f} | {a['text_rgb_mae']:.3f} / {b['text_rgb_mae']:.3f} |")
    if deferred:
        lines += ['', 'Pending authorized source-presentation correction; excluded from preservation hashes and selected outputs: ' + ', '.join(sorted(deferred))]
    (root / OUTPUT / 'README.md').write_text('\n'.join(lines) + '\n')
    print(json.dumps(manifest['totals'], sort_keys=True), flush=True)
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--defer', action='append', default=[], help='Exact input path pending an authorized source correction; partial output is marked incomplete')
    args = parser.parse_args()
    build(deferred=args.defer)
