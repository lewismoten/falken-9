"""Contract tests for lossy display-only indexed report previews."""
import hashlib
import importlib.util
import io
import contextlib
import struct
import json
from PIL import Image
import numpy as np
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/prepare_indexed_report_figures.py'


def module():
    spec = importlib.util.spec_from_file_location('indexed_report', SCRIPT)
    assert spec is not None and spec.loader is not None
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


class IndexedReportTests(unittest.TestCase):
    def test_all_generated_files_reproduce_and_no_inputs_change(self):
        m = module()
        output = ROOT / m.OUTPUT
        self.assertTrue((output / 'manifest.json').is_file())
        def snapshot(paths):
            return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
        before_outputs = snapshot(sorted(p for p in output.rglob('*') if p.is_file()))
        protected = json.loads((output / 'input-preservation.json').read_text())
        protected_paths = [ROOT / e['path'] for group in ('report_inputs', 'protected_screenshots', 'protected_svgs') for e in protected[group]]
        before_inputs = snapshot(protected_paths)
        with contextlib.redirect_stdout(io.StringIO()):
            m.build(ROOT)
        self.assertEqual(before_outputs, snapshot(sorted(p for p in output.rglob('*') if p.is_file())))
        self.assertEqual(before_inputs, snapshot(protected_paths))

    def test_real_indexed_candidates_and_quality_metrics(self):
        m = module()
        self.assertTrue(hasattr(m, 'candidate'), 'candidate encoder is not implemented')
        source = Image.open(ROOT / 'assets/interpretability/strategy-circuit-map.png').convert('RGB')
        for colors in (16, 32):
            encoded, metrics = m.candidate(source, colors)
            self.assertEqual(encoded, m.candidate(source, colors)[0])
            self.assertEqual(encoded[24], 4 if colors == 16 else 8)
            self.assertEqual(encoded[25], 3)
            pos = 8
            palette_entries = None
            while pos < len(encoded):
                length = struct.unpack('>I', encoded[pos:pos + 4])[0]
                if encoded[pos + 4:pos + 8] == b'PLTE':
                    palette_entries = length // 3
                pos += length + 12
            self.assertEqual(palette_entries, colors)
            decoded = Image.open(io.BytesIO(encoded))
            self.assertEqual(decoded.size, source.size)
            self.assertEqual(decoded.mode, 'P')
            self.assertEqual(metrics['canvas_rgb_error'], 0)
            self.assertGreater(metrics['foreground_pixels'], 0)
            self.assertGreater(metrics['text_pixels'], 0)
            self.assertLess(metrics['rgb_mae'], 6)
            self.assertLess(metrics['foreground_rgb_mae'], 15)
            self.assertLess(metrics['text_rgb_mae'], 15)
            # Independently recompute a measured error (not just an asserted score).
            delta = np.abs(np.asarray(source, dtype=np.float32) - np.asarray(decoded.convert('RGB'), dtype=np.float32))
            self.assertAlmostEqual(metrics['rgb_mae'], float(delta.mean()), places=4)

    def test_attention_grid_detail_uses_32_color_median_cut(self):
        m = module()
        source = Image.open(ROOT / 'assets/interpretability/publication-dark/study-010-011-walkthrough/forward-attention1011.png').convert('RGB')
        import inspect
        self.assertIn('quantizer', inspect.signature(m.candidate).parameters, 'continuous-map quantizer choice is missing')
        colors_at_centers = []
        for colors in (16, 32):
            encoded, metrics = m.candidate(source, colors, quantizer='MEDIANCUT')
            decoded = Image.open(io.BytesIO(encoded)).convert('RGB')
            # Source panel C is an unchanged 9×9 grid with 39px cells at 70,608.
            samples = {decoded.getpixel((89 + 39 * x, 627 + 39 * y)) for x in range(9) for y in range(9)}
            colors_at_centers.append(len(samples))
            self.assertEqual(metrics['canvas_rgb_error'], 0)
        self.assertGreater(colors_at_centers[1], colors_at_centers[0])
        self.assertGreaterEqual(colors_at_centers[1], 12)

    def test_generated_manifest_integrity_and_preservation(self):
        m = module()
        manifest_path = ROOT / m.OUTPUT / 'manifest.json'
        self.assertTrue(manifest_path.exists(), 'conversion and manifest have not been implemented')
        manifest = json.loads(manifest_path.read_text())
        figures = manifest['figures']
        sources = m.report_sources(ROOT)
        self.assertTrue(manifest['complete'])
        self.assertEqual(manifest['deferred_sources'], [])
        self.assertEqual(len(figures), 39)
        self.assertEqual({f['original']['path'] for f in figures} | set(manifest['deferred_sources']), {str(p) for p in sources})
        self.assertEqual(len(figures) + len(manifest['deferred_sources']), 39)
        self.assertEqual(len({f['indexed']['path'] for f in figures}), len(figures))
        self.assertEqual(manifest['complete'], not manifest['deferred_sources'])
        before, after = 0, 0
        for figure in figures:
            original = figure['original']
            indexed = figure['indexed']
            for entry in (original, indexed):
                self.assertFalse(Path(entry['path']).is_absolute())
                data = (ROOT / entry['path']).read_bytes()
                self.assertEqual(hashlib.sha256(data).hexdigest(), entry['sha256'])
                self.assertEqual(len(data), entry['bytes'])
            source = Image.open(ROOT / original['path'])
            selected = Image.open(ROOT / indexed['path'])
            source.load()
            selected.load()
            self.assertEqual(list(source.size), figure['dimensions'])
            self.assertEqual(source.size, selected.size)
            encoded = (ROOT / indexed['path']).read_bytes()
            self.assertEqual(encoded[25], 3)
            self.assertEqual(encoded[24], 4 if indexed['colors'] == 16 else 8)
            palette = selected.getpalette()
            assert palette is not None
            self.assertEqual(len(palette) // 3, indexed['colors'])
            self.assertEqual(indexed['bit_depth'], encoded[24])
            self.assertTrue(figure['reason'])
            self.assertEqual(set(figure['quality_metrics']['candidates']), {'16', '32'})
            for colors in (16, 32):
                entry = figure['quality_metrics']['candidates'][str(colors)]
                data = (ROOT / entry['path']).read_bytes()
                self.assertEqual(hashlib.sha256(data).hexdigest(), entry['sha256'])
                self.assertEqual(len(data), entry['bytes'])
                self.assertEqual(data[25], 3)
                self.assertEqual(data[24], 4 if colors == 16 else 8)
                with Image.open(io.BytesIO(data)) as candidate:
                    self.assertEqual(candidate.size, source.size)
                    palette = candidate.getpalette()
                    assert palette is not None
                    self.assertEqual(len(palette) // 3, colors)
            quality = figure['quality_metrics']['candidates'][str(indexed['colors'])]
            self.assertEqual(quality['canvas_rgb_error'], 0)
            self.assertLess(quality['foreground_rgb_mae'], 20)
            self.assertLess(quality['text_rgb_mae'], 20)
            before += original['bytes']
            after += indexed['bytes']
        self.assertEqual(manifest['totals']['original_bytes'], before)
        self.assertEqual(manifest['totals']['indexed_bytes'], after)
        selected_files = [p for p in (ROOT / m.OUTPUT).glob('*/*.png') if p.parent.name not in ('contact-sheets', 'candidates')]
        self.assertEqual({str(p.relative_to(ROOT)) for p in selected_files}, {f['indexed']['path'] for f in figures})
        self.assertEqual(len(list((ROOT / m.OUTPUT / 'candidates').rglob('*.png'))), 78)
        self.assertEqual({Path(f['original']['path']).name for f in figures if f['indexed']['colors'] == 32}, set(m.COMPLEX))
        attention = next(f for f in figures if Path(f['original']['path']).name == 'forward-attention1011.png')
        q = attention['quality_metrics']['candidates']
        self.assertEqual(q['32']['attention_grid_distinct_center_colors'], 12)
        self.assertGreater(q['32']['attention_grid_distinct_center_colors'], q['16']['attention_grid_distinct_center_colors'])
        preserved = json.loads((ROOT / m.OUTPUT / 'input-preservation.json').read_text())
        self.assertEqual({e['path'] for e in preserved['report_inputs']}, {f['original']['path'] for f in figures})
        screenshots = sorted(str(p.relative_to(ROOT)) for p in (ROOT / 'assets/screenshots').rglob('*') if p.is_file())
        self.assertEqual(screenshots, [e['path'] for e in preserved['protected_screenshots']])
        for entry in preserved['report_inputs'] + preserved['protected_screenshots'] + preserved['protected_svgs']:
            self.assertEqual(hashlib.sha256((ROOT / entry['path']).read_bytes()).hexdigest(), entry['sha256'])

    def test_report_source_closure_and_unique_mapping(self):
        self.assertTrue(SCRIPT.exists(), 'indexed preview converter is not implemented')
        m = module()
        sources = m.report_sources(ROOT)
        self.assertEqual(len(sources), 39)
        self.assertEqual(len(set(sources)), 39)
        destinations = [m.output_path(p) for p in sources]
        self.assertEqual(len(set(destinations)), 39)
        for source, destination in zip(sources, destinations):
            self.assertTrue((ROOT / source).is_file())
            self.assertEqual(destination.parent.name, source.parent.name)
            self.assertEqual(destination.name, source.name)
            self.assertTrue(str(destination).startswith('assets/interpretability/publication-indexed/'))
            self.assertNotIn('screenshot', str(source).lower())


if __name__ == '__main__':
    unittest.main()
