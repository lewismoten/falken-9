#!/usr/bin/env python3
"""Derive presentation-only SVG/PNG pairs; never rewrite research evidence."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET

COLOR_ATTRIBUTES = frozenset({'fill', 'stroke', 'color', 'stop-color', 'flood-color', 'lighting-color'})
CANVAS = '#11151a'
PANEL = '#181e26'
INK = '#e7e8e4'
MUTED = '#a6b0b7'
GRID = '#3b4652'
# Fixed hues preserve each local scientific legend: approved green, errors red,
# original intervals orange, certified box green, original codes blue, expert
# classes purple/green/ochre/blue, X blue / O vermilion.
PALETTE = {
    '#f5f7fb': CANVAS, '#f5f7fa': CANVAS, 'white': PANEL, '#ffffff': PANEL,
    '#17283f': INK, '#172938': INK, '#172438': INK, '#203443': INK,
    '#66778a': MUTED, '#687785': MUTED, '#617583': MUTED, '#566377': MUTED,
    '#687987': MUTED, '#53616c': MUTED, '#8b94a1': MUTED,
    '#c8d1df': GRID, '#bcc9d8': GRID, '#bbc8d4': GRID, '#b8c6d4': GRID,
    '#c6d0d9': GRID, '#9dabb8': GRID, '#d1d9e0': GRID, '#d6dce6': GRID,
    '#7b8798': GRID, '#b0bac8': GRID,
    '#d6f0df': '#244b3b', '#d8efe4': '#244b3b', '#e2f4ed': '#244b3b',
    '#d9ebfb': '#253e54', '#f6d3cc': '#55352e', '#ffded7': '#55352e',
    '#edf2f8': '#202a36', '#eff2f4': PANEL,
    '#467965': '#82d5a1', '#248553': '#82d5a1', '#18715b': '#82d5a1',
    '#158364': '#82d5a1', '#116c55': '#82d5a1', '#126b56': '#82d5a1',
    '#218772': '#82d5a1', '#2061a6': '#7fb7e3', '#2356bd': '#7fb7e3',
    '#3267a8': '#7fb7e3', '#15618c': '#7fb7e3', '#247da1': '#7fb7e3',
    '#567998': '#7fb7e3', '#cf7333': '#eda85f', '#9a6021': '#eda85f',
    '#975519': '#eda85f', '#a2550c': '#eda85f', '#b64d32': '#e6a08d',
    '#ad4b45': '#e6a08d', '#ffe2bd': '#59432b', '#dce6f2': '#304254',
    '#eadff4': '#42384f', '#e4eedc': '#344936', '#f2e8d7': '#51452f',
    '#dceaf5': '#2c4356', '#d5dce5': '#303c49', '#dbe1e6': '#303c49',
    '#e1e5ec': '#252e39', '#c4dfd9': '#365e55', '#e8d4cc': '#65483d',
    'none': 'none',
}
PAINT_RE = re.compile(r'\b(' + '|'.join(sorted(COLOR_ATTRIBUTES)) + r')=("|\')(.*?)(\2)')
OUTPUT = Path('assets/interpretability/publication-dark')
ATTENTION_GRID = '#56718d'
ORIGINAL_ATTENTION_LEGEND = 'White 0 → dark blue 1; every row sums to 32768.'
ATTENTION_LEGEND = 'Dark 0 → bright blue 1 (√ scale); rows sum to 32768.'

def attention_values(root):
    import numpy as np
    source = root / 'research/studies/study-010-011/evidence/study-010-final/baseline010.npz'
    if sha256(source) != 'ec81bed1e5bcb42b1cc78688e48106b457ae3ddd6302946b577d39ed00c1c317':
        raise ValueError('Frozen attention baseline changed')
    info = json.loads((root / 'docs/research/study-010-011-walkthrough/walkthrough1011.json').read_text())
    with np.load(source, allow_pickle=False) as saved:
        values = saved['attention_probs'][info['canonical_id']].reshape(-1).tolist()
    if len(values) != 81 or any(sum(values[i:i+9]) != 32768 for i in range(0,81,9)):
        raise ValueError('Invalid original Q15 attention matrix')
    return values

def attention_color(value):
    if not 0 <= value <= 32768: raise ValueError('Q15 value out of range')
    t = math.sqrt(value / 32768)
    low, high = (24,43,66), (131,201,255)
    return '#' + ''.join(f'{round(a+(b-a)*t):02x}' for a,b in zip(low,high))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def report_sources(root):
    found = [p for p in re.findall(r'!\[[^\]]*\]\(([^)]+)\)', (root / 'report.md').read_text())
             if re.search(r'study-0(?:09|1[0-6])', p)]
    return [p.replace(OUTPUT.as_posix() + '/', 'docs/research/', 1)
            if p.startswith(OUTPUT.as_posix() + '/') else p for p in found]


def normalized(svg):
    """Remove only allowed paint attributes; retain every other XML semantic."""
    tree = ET.fromstring(svg.replace(ATTENTION_LEGEND, ORIGINAL_ATTENTION_LEGEND))
    tree.attrib.pop('{http://www.w3.org/XML/1998/namespace}space', None)
    for element in tree.iter():
        for attr in COLOR_ATTRIBUTES:
            element.attrib.pop(attr, None)
    return ET.tostring(tree, encoding='unicode')


def recolor(source, attention_q15=None):
    """Change literal paint values only, retaining original XML bytes elsewhere."""
    tree = ET.fromstring(source)
    changes = []
    attention_index = 0
    for index, element in enumerate(tree.iter()):
        for attr, before in list(element.attrib.items()):
            if attr not in COLOR_ATTRIBUTES:
                continue
            if index == 1 and element.tag.endswith('rect') and attr == 'fill':
                after, rule = CANVAS, 'canvas'
            elif (attr == 'fill' and element.get('stroke') == '#b8c6d4'):
                if attention_q15 is None: raise ValueError('Original Q15 values required')
                after, rule = attention_color(attention_q15[attention_index]), 'attention-dark-q15'
                attention_index += 1
            elif attr == 'stroke' and before == '#b8c6d4':
                after, rule = ATTENTION_GRID, 'attention-cell-grid'
            else:
                if before not in PALETTE:
                    raise ValueError(f'Unreviewed source paint: {before}')
                after, rule = PALETTE[before], 'fixed-semantic-palette'
            changes.append({'element_index': index, 'attribute': attr,
                            'before': before, 'after': after, 'rule': rule})
    replacements = iter(changes)
    def replace(match):
        change = next(replacements)
        if (match[1], match[3]) != (change['attribute'], change['before']):
            raise ValueError('XML attribute order does not match paint-token order')
        return f'{match[1]}={match[2]}{change["after"]}{match[2]}'
    result = PAINT_RE.sub(replace, source)
    if attention_q15 is not None:
        assert attention_index == 81
        result = result.replace(ORIGINAL_ATTENTION_LEGEND, ATTENTION_LEGEND)
    # Original SVG text stores column spacing literally; explicitly preserve it
    # so a real SVG renderer does not collapse numeric tables into prose.
    if 'xml:space=' not in result.split('>', 1)[0]:
        result = result.replace('<svg ', '<svg xml:space="preserve" ', 1)
    assert normalized(source) == normalized(result), 'Non-presentation XML changed'
    return result, changes


def build(root):
    import cairosvg
    import cairocffi
    from PIL import Image, ImageDraw
    inputs = report_sources(root)
    if len(inputs) != 22 or len(set(inputs)) != 22:
        raise ValueError('Expected exactly 22 unique study009–016 inline PNGs')
    out = root / OUTPUT
    out.mkdir(parents=True, exist_ok=True)
    figures = []
    for original_png in inputs:
        png = Path(original_png)
        svg = png.with_suffix('.svg')
        dest_png = OUTPUT / png.parent.name / png.name
        dest_svg = dest_png.with_suffix('.svg')
        (root / dest_svg).parent.mkdir(parents=True, exist_ok=True)
        q15 = attention_values(root) if svg.name == 'forward-attention1011.svg' else None
        rendered, changes = recolor((root / svg).read_text(), q15)
        temporary_svg = (root / dest_svg).with_suffix('.svg.tmp')
        temporary_svg.write_text(rendered)
        temporary_svg.replace(root / dest_svg)
        temporary_png = (root / dest_png).with_suffix('.png.tmp')
        cairosvg.svg2png(bytestring=rendered.encode(), write_to=str(temporary_png))
        temporary_png.replace(root / dest_png)
        def identity(path):
            return {'path': path.as_posix(), 'sha256': sha256(root / path)}
        figures.append({'original': {'svg': identity(svg), 'png': identity(png)},
                        'derived': {'svg': identity(dest_svg), 'png': identity(dest_png)},
                        'transformations': changes})
    manifest = {'schema_version': 1, 'identity': 'presentation derivative, not scientific evidence',
                'renderer': {'name': 'CairoSVG', 'version': cairosvg.__version__,
                             'cairo_version': cairocffi.cairo_version_string()},
                'palette': {'canvas': CANVAS, 'panel': PANEL, 'ink': INK,
                            'muted': MUTED, 'grid': GRID, 'semantic_mapping': PALETTE},
                'normalization': 'All geometry, fonts, numbers and original scientific data are unchanged. Presentation changes: paint, root xml:space=preserve, and the single attention color-scale legend updated to describe dark-to-bright-blue square-root display mapping.',
                'attention_color_scale': {'input':'Original frozen Q15 attention values / 32768','display':'sqrt(value/32768), dark #182b42 to bright blue #83c9ff','grid':ATTENTION_GRID,'legend':ATTENTION_LEGEND,'values_changed':False},
                'figures': figures}
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    sheet = Image.new('RGB', (1600, 6 * 360), CANVAS)
    draw = ImageDraw.Draw(sheet)
    for i, figure in enumerate(figures):
        entry = figure['derived']['png']['path']
        image = Image.open(root / entry).convert('RGB')
        image.thumbnail((390, 325))
        x, y = (i % 4) * 400, (i // 4) * 360
        sheet.paste(image, (x, y + 25))
        draw.text((x + 4, y + 4), str(Path(entry).relative_to(OUTPUT)), fill=INK)
    sheet.save(out / 'contact-sheet.png')
    print(f'Rendered {len(figures)} SVG/PNG pairs using CairoSVG {cairosvg.__version__}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    build(parser.parse_args().root)
