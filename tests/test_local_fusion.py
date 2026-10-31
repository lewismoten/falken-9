import importlib
import importlib.util
import unittest
import torch
from falken9.canonical_model import CanonicalPolicy, CanonicalConfig
from falken9.canonical_integer import CanonicalIntegerPolicy
from falken9.canonical_integer_export import convert


class LocalFusionTests(unittest.TestCase):
    def test_weight_derived_local_tables_preserve_full_integer_forward(self):
        self.assertIsNotNone(importlib.util.find_spec('falken9.local_fusion'), 'local constant folding is not implemented')
        fusion = importlib.import_module('falken9.local_fusion')
        torch.set_num_threads(1)
        torch.manual_seed(17)
        source = CanonicalPolicy(CanonicalConfig(4, 2, 'float', 'float'))
        candidate = convert(source, frac=10, matrix_bits=16, activation_bits=32, attention_mode='early')
        normal = CanonicalIntegerPolicy(candidate)
        optimized = fusion.LocalFusionPolicy(candidate)
        boards = torch.tensor([[0] * 9, [0, 0, 0, 0, 1, 0, 0, 0, 0],
                               [1, 0, 0, 0, 2, 0, 0, 0, 0]], dtype=torch.int64)
        a, routes_a = normal(boards, return_routes=True)
        b, routes_b = optimized(boards, return_routes=True)
        self.assertTrue(torch.equal(a, b))
        self.assertTrue(torch.equal(routes_a, routes_b))
        self.assertNotIn('norm1.square_sum', optimized.stats['accumulators'])
        self.assertNotIn('query.weight.dot', optimized.stats['accumulators'])
        self.assertEqual(optimized.local_qkv.shape, (2, 9, 3, 3, 4))
        with self.assertRaises(ValueError):
            optimized(torch.tensor([[3] * 9], dtype=torch.int64))


    def test_norm_only_fusion_preserves_projection_math_and_removes_first_norm(self):
        fusion = importlib.import_module('falken9.local_fusion')
        self.assertTrue(hasattr(fusion, 'LocalNormPolicy'), 'norm-only constant folding is not implemented')
        torch.set_num_threads(1)
        torch.manual_seed(19)
        source = CanonicalPolicy(CanonicalConfig(4, 2, 'float', 'float'))
        candidate = convert(source, frac=10, matrix_bits=16, activation_bits=32, attention_mode='early')
        normal = CanonicalIntegerPolicy(candidate)
        optimized = fusion.LocalNormPolicy(candidate)
        boards = torch.tensor([[0] * 9, [1, 0, 0, 0, 2, 0, 0, 0, 0]], dtype=torch.int64)
        a, ar = normal(boards, return_routes=True)
        b, br = optimized(boards, return_routes=True)
        self.assertTrue(torch.equal(a, b))
        self.assertTrue(torch.equal(ar, br))
        self.assertNotIn('norm1.square_sum', optimized.stats['accumulators'])
        self.assertIn('query.weight.dot', optimized.stats['accumulators'])
        self.assertEqual(optimized.local_norm.shape, (2, 9, 3, 4))


    def test_saved_fusion_report_declares_integer_runtime(self):
        from pathlib import Path
        import json
        report = json.loads((Path(__file__).resolve().parents[1] / 'results' / 'local-fusion-summary.json').read_text())
        for variant in report['variants']:
            self.assertIn('whole-integer', variant['gate']['arithmetic'])
            self.assertNotIn('FP32', variant['gate']['arithmetic'])

    def test_local_fusion_audit_cli_is_available(self):
        from pathlib import Path
        import subprocess
        import sys
        script = Path(__file__).resolve().parents[1] / 'scripts' / 'audit_local_fusion.py'
        self.assertTrue(script.exists(), 'local fusion audit CLI is missing')
        result = subprocess.run([sys.executable, str(script), '--help'], capture_output=True, text=True, check=True)
        self.assertIn('--source', result.stdout)


if __name__ == '__main__':
    unittest.main()
