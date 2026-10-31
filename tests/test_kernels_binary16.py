import importlib
import importlib.util
import random
import unittest


class Binary16KernelTests(unittest.TestCase):
    def test_signed_int16_binary_dot_executes_with_int32_accumulation(self):
        self.assertIsNotNone(importlib.util.find_spec('scripts.benchmark_int16_kernel'), 'INT16 activation kernel is not implemented')
        bench = importlib.import_module('scripts.benchmark_int16_kernel')
        image = bench.assemble()
        rng = random.Random(1102)
        for n in (0, 8, 12, 16, 24, 32):
            vectors = [([-32768] * n, [-1] * n), ([32767] * n, [1] * n),
                       ([-32768] * n, [1] * n), ([0] * n, [1] * n),
                       ([rng.randrange(-32768, 32768) for _ in range(n)],
                        [rng.choice((-1, 1)) for _ in range(n)])]
            for xs, ws in vectors:
                with self.subTest(n=n):
                    result = bench.execute(image, xs, ws)
                    self.assertEqual(result['value'], sum(x * w for x, w in zip(xs, ws)))
                    self.assertEqual(result['unexpected_writes'], [])
                    self.assertEqual(result['decimal'], 0)
                    self.assertEqual(result['carry'], 0)
                    self.assertEqual(result['stack_pointer'], 255)


if __name__ == '__main__':
    unittest.main()
