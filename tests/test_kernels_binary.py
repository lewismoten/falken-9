"""Target-code tests; oracle and input packing intentionally independent."""
import importlib.util
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parents[1]


def harness():
    path = ROOT / 'scripts/benchmark_kernels.py'
    assert path.exists(), 'assembled kernel harness is not implemented'
    spec = importlib.util.spec_from_file_location('kernel_bench', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_binary_machine_code_signed_extremes_and_poison():
    bench = harness()
    image = bench.assemble('binary')
    rng = random.Random(9)
    for n in [0,1,7,8,12,16,24,31,32]:
        for case in range(12):
            xs = [rng.randrange(-128,128) for _ in range(n)]
            ws = [rng.choice([-1,1]) for _ in range(n)]
            if case < 4:
                xs = [[-128,127,-1,0][case]] * n
                ws = [-1 if case % 2 == 0 else 1] * n
            packed = bytearray((n+7)//8)
            for i,w in enumerate(ws): packed[i//8] |= (w == 1) << (i%8)
            result = bench.execute(image, xs, packed)
            assert result['value'] == sum(x*w for x,w in zip(xs,ws))
            assert result['carry'] == 0
            assert result['cycles'] > 0
            assert result['unexpected_writes'] == []
