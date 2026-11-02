"""Presentation derivatives must never become replacement scientific evidence."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets/interpretability/publication-dark'
SCRIPT = ROOT / 'scripts/prepare_dark_report_figures.py'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sources():
    found = [p for p in re.findall(r'!\[[^\]]*\]\(([^)]+)\)', (ROOT / 'report.md').read_text())
            if re.search(r'study-0(?:09|1[0-6])', p)]
    return [p.replace('assets/interpretability/publication-dark/', 'docs/research/', 1)
            if p.startswith('assets/interpretability/publication-dark/') else p for p in found]


class DarkFiguresTests(unittest.TestCase):
    def test_public_presentation_metadata_matches_current_figures(self):
        manifest = json.loads((OUT / 'manifest.json').read_text())
        public = json.loads((OUT / 'presentation.json').read_text())
        self.assertEqual(public['figures'], [
            {key: row[key] for key in ('original', 'derived')}
            for row in manifest['figures']])
        self.assertEqual(public['attention_color_scale'], manifest['attention_color_scale'])
        self.assertFalse(public['attention_color_scale']['values_changed'])
        self.assertIn('square-root', (OUT / 'README.md').read_text())
        self.assertNotIn('retains its original white-to-blue', public['changes'])

    def test_literal_table_spacing_is_explicitly_preserved(self):
        svg = ET.parse(OUT / 'study-009/overview009.svg').getroot()
        self.assertEqual(svg.get('{http://www.w3.org/XML/1998/namespace}space'), 'preserve')

    def test_attention_grid_dark_scale_preserves_actual_q15_values(self):
        spec = importlib.util.spec_from_file_location('dark_figures', SCRIPT)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        source = ROOT / 'docs/research/study-010-011-walkthrough/forward-attention1011.svg'
        derived = OUT / 'study-010-011-walkthrough/forward-attention1011.svg'
        src, dst = ET.parse(source).getroot(), ET.parse(derived).getroot()
        values = module.attention_values(ROOT)
        self.assertEqual(len(values), 81)
        for row in range(9): self.assertEqual(sum(values[row*9:(row+1)*9]), 32768)
        index = 0
        for old, new in zip(src.iter(), dst.iter()):
            if old.get('stroke') == '#b8c6d4':
                self.assertEqual(new.get('fill'), module.attention_color(values[index]))
                self.assertEqual(new.get('stroke'), module.ATTENTION_GRID)
                index += 1
        self.assertEqual(index, 81)
        self.assertIn(module.ATTENTION_LEGEND, derived.read_text())
        self.assertNotIn('White 0', derived.read_text())
        self.assertEqual(module.attention_color(0), '#182b42')
        self.assertEqual(module.attention_color(32768), '#83c9ff')

    def test_preserved_source_snapshot(self):
        snapshot = json.loads((OUT / 'source-preservation.json').read_text())
        self.assertGreater(len(snapshot['files']), 190)
        for path, expected in snapshot['files'].items():
            # Canonical report.md is the parent-owned integration output; its
            # exact worker-input bytes are retained separately, never rehashed
            # under a false original identity after public links are updated.
            original = OUT / 'source-report.md' if path == 'report.md' else ROOT / path
            self.assertEqual(digest(original), expected, path)

    def test_pngs_are_real_renders_and_all_paint_is_reviewed(self):
        import cairosvg
        import io
        manifest = json.loads((OUT / 'manifest.json').read_text())
        mapping = manifest['palette']['semantic_mapping']
        for figure in manifest['figures']:
            svg = ROOT / figure['derived']['svg']['path']
            image = Image.open(ROOT / figure['derived']['png']['path']).convert('RGBA')
            rerender = Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg.read_bytes()))).convert('RGBA')
            self.assertEqual(image.tobytes(), rerender.tobytes())
            for change in figure['transformations']:
                self.assertRegex(change['after'], r'^(none|#[0-9a-f]{6})$')
                if change['rule'] == 'fixed-semantic-palette':
                    self.assertEqual(change['after'], mapping[change['before']])
                elif change['rule'] == 'attention-dark-q15':
                    self.assertRegex(change['after'], r'^#[0-9a-f]{6}$')
                elif change['rule'] == 'attention-cell-grid':
                    self.assertEqual(change['after'], '#56718d')
                else:
                    self.assertEqual(change['rule'], 'canvas')
                    self.assertEqual(change['after'], '#11151a')

    def test_discovery_and_complete_outputs(self):
        self.assertTrue(SCRIPT.exists(), 'dark figure generator is missing')
        spec = importlib.util.spec_from_file_location('dark_figures', SCRIPT)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.report_sources(ROOT), sources())
        self.assertEqual(len(sources()), 22)
        manifest = json.loads((OUT / 'manifest.json').read_text())
        self.assertEqual([r['original']['png']['path'] for r in manifest['figures']], sources())
        self.assertEqual(len(list(OUT.glob('study-*/*.svg'))), 22)
        self.assertEqual(len(list(OUT.glob('study-*/*.png'))), 22)
        for record in manifest['figures']:
            for kind in ('original', 'derived'):
                for fmt in ('svg', 'png'):
                    entry = record[kind][fmt]
                    self.assertFalse(Path(entry['path']).is_absolute())
                    self.assertEqual(digest(ROOT / entry['path']), entry['sha256'])
            src = ET.parse(ROOT / record['original']['svg']['path']).getroot()
            dst = ET.parse(ROOT / record['derived']['svg']['path']).getroot()
            self.assertEqual(len(list(src.iter())), len(list(dst.iter())))
            for a, b in zip(src.iter(), dst.iter()):
                self.assertEqual(a.tag, b.tag)
                actual_text = b.text.replace(module.ATTENTION_LEGEND, module.ORIGINAL_ATTENTION_LEGEND) if b.text else b.text
                self.assertEqual(a.text, actual_text)
                self.assertEqual(a.tail, b.tail)
                # Only paint values may differ, never sizes/geometry/opacities/text.
                presentational = module.COLOR_ATTRIBUTES | {'{http://www.w3.org/XML/1998/namespace}space'}
                aa = {k: v for k, v in a.attrib.items() if k not in presentational}
                bb = {k: v for k, v in b.attrib.items() if k not in presentational}
                self.assertEqual(aa, bb)
                self.assertEqual(set(a.attrib) - presentational, set(b.attrib) - presentational)
            image = Image.open(ROOT / record['derived']['png']['path']).convert('RGB')
            self.assertEqual(image.size, (int(src.get('width')), int(src.get('height'))))
            self.assertEqual(image.getpixel((0, 0)), (17, 21, 26))
        self.assertIn('CairoSVG', manifest['renderer']['name'])


if __name__ == '__main__':
    unittest.main()
