#!/usr/bin/env python3
"""Actual 6502 INT16-activation/binary-weight microbenchmark, not full inference."""
import hashlib
import json
from pathlib import Path
import random
import statistics
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from py65.devices.mpu6502 import MPU
from falken9.packing import pack
from scripts.benchmark_kernels import assembler

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / 'artifacts/kernels'


def assemble():
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    output = ARTIFACTS / 'binary16.bin'
    result = subprocess.run([assembler(), '--nostart', '--labels=' + str(ARTIFACTS / 'binary16.lbl'),
                             '-o', str(output), str(ROOT / 'src/kernels/binary16.asm')],
                            text=True, capture_output=True, check=True)
    (ARTIFACTS / 'binary16-assembly.log').write_text(result.stdout + result.stderr)
    return output.read_bytes()


def execute(image, activations, weights):
    if len(activations) != len(weights) or len(weights) > 32:
        raise ValueError('equal vector lengths in 0..32 required')
    if any(not -32768 <= value <= 32767 for value in activations):
        raise ValueError('activation outside INT16')
    packed = pack(weights, 'binary')
    data = b''.join(int(value).to_bytes(2, 'little', signed=True) for value in activations)
    cpu = MPU(memory=[0xa5] * 65536, pc=0x2000)
    cpu.memory[0x2000:0x2000 + len(image)] = image
    cpu.memory[0x3000:0x3000 + len(data)] = data
    cpu.memory[0x3100:0x3100 + len(packed)] = packed
    cpu.memory[0xe0] = len(weights)
    cpu.memory[0x1fe:0x200] = [0xfe, 0x02]
    cpu.sp = 0xfd
    cpu.p |= cpu.DECIMAL
    before = list(cpu.memory)
    for _ in range(100000):
        cpu.step()
        if cpu.pc == 0x02ff:
            break
    else:
        raise RuntimeError('6502 instruction watchdog')
    unexpected = [i for i, (a, b) in enumerate(zip(before, cpu.memory))
                  if a != b and not (0xe1 <= i <= 0xe8 or 0x100 <= i <= 0x1ff)]
    return {'value': int.from_bytes(bytes(cpu.memory[0xe1:0xe5]), 'little', signed=True),
            'cycles': cpu.processorCycles, 'carry': cpu.p & 1,
            'decimal': int(bool(cpu.p & cpu.DECIMAL)),
            'stack_pointer': cpu.sp, 'unexpected_writes': unexpected}


def main():
    image = assemble()
    results = []
    for n in (8, 12, 16, 24, 32):
        rng = random.Random(1102 + n)
        cases = [([-32768] * n, [-1] * n), ([32767] * n, [1] * n),
                 ([-32768] * n, [1] * n), ([0] * n, [1] * n),
                 ([32767 if i % 2 else -32768 for i in range(n)],
                  [1 if i % 2 else -1 for i in range(n)])]
        cases += [([rng.randrange(-32768, 32768) for _ in range(n)],
                   [rng.choice((-1, 1)) for _ in range(n)]) for _ in range(5)]
        cycles = []
        for xs, ws in cases:
            actual = execute(image, xs, ws)
            assert actual['value'] == sum(x * w for x, w in zip(xs, ws))
            assert not actual['unexpected_writes'] and actual['carry'] == actual['decimal'] == 0
            cycles.append(actual['cycles'])
        results.append({'dimension': n, 'vectors': len(cases), 'mean_cycles': statistics.mean(cycles),
                        'worst_observed_cycles': max(cycles), 'activation_bytes': 2 * n,
                        'weight_bytes': (n + 7) // 8, 'accumulator_bytes': 4})
    report = {'scope': 'isolated INT16 activation/binary dot products, not full inference or game residency',
              'cycle_boundary': 'entry through RTS inclusive; excludes caller JSR, interrupts, VIC stalls and I/O',
              'code_bytes': len(image), 'image_sha256': hashlib.sha256(image).hexdigest(),
              'source_sha256': hashlib.sha256((ROOT / 'src/kernels/binary16.asm').read_bytes()).hexdigest(),
              'maximum_accumulator_magnitude_at_32_lanes': 32 * 32768,
              'dimensions': results}
    (ROOT / 'results/kernel16-summary.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
