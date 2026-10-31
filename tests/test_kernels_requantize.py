import importlib
import importlib.util
import unittest


class RequantizeKernelTests(unittest.TestCase):
    def test_signed_rounding_and_saturation_match_independent_integer_oracle(self):
        self.assertIsNotNone(importlib.util.find_spec('scripts.benchmark_requantize'), 'assembled requantization helper is missing')
        bench = importlib.import_module('scripts.benchmark_requantize')
        image = bench.assemble()
        values = [-2147483648, -2147483647, -65537, -65535, -32769, -32768,
                  -257, -5, -3, -1, 0, 1, 3, 5, 257, 32767, 32768, 65535,
                  65537, 2147483647]
        for shift in range(32):
            for value in values:
                with self.subTest(value=value, shift=shift):
                    magnitude = abs(value)
                    rounded = magnitude if shift == 0 else (magnitude + (1 << (shift - 1))) >> shift
                    rounded = -rounded if value < 0 else rounded
                    expected = max(-32768, min(32767, rounded))
                    actual = bench.execute(image, value, shift)
                    self.assertEqual(actual['value'], expected)
                    self.assertEqual(actual['saturated'], int(expected != rounded))
                    self.assertEqual(actual['unexpected_writes'], [])
                    self.assertEqual(actual['input_preserved'], True)
                    self.assertEqual(actual['decimal'], 0)


if __name__ == '__main__':
    unittest.main()
