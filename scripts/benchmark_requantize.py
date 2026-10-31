#!/usr/bin/env python3
"""Measure actual assembled signed round/shift/saturate, not model accuracy."""
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from py65.devices.mpu6502 import MPU
from scripts.benchmark_kernels import assembler

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / 'artifacts/kernels'


def assemble():
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    output = ARTIFACTS / 'requantize.bin'
    result = subprocess.run([assembler(), '--nostart', '--labels=' + str(ARTIFACTS / 'requantize.lbl'),
                             '-o', str(output), str(ROOT / 'src/kernels/requantize.asm')],
                            text=True, capture_output=True, check=True)
    (ARTIFACTS / 'requantize-assembly.log').write_text(result.stdout + result.stderr)
    return output.read_bytes()


def execute(image, value, shift):
    if not -(1 << 31) <= value < (1 << 31) or not 0 <= shift <= 31:
        raise ValueError('expected signed INT32 value and shift in 0..31')
    cpu = MPU(memory=[0xa5] * 65536, pc=0x2000)
    cpu.memory[0x2000:0x2000 + len(image)] = image
    inputs = value.to_bytes(4, 'little', signed=True) + bytes([shift])
    cpu.memory[0xe0:0xe5] = inputs
    cpu.sp = 0xfd
    cpu.memory[0x1fe:0x200] = [0xfe, 0x02]
    cpu.p |= cpu.DECIMAL
    before = list(cpu.memory)
    for _ in range(10000):
        cpu.step()
        if cpu.pc == 0x02ff:
            break
    else:
        raise RuntimeError('6502 instruction watchdog')
    unexpected = [i for i, (a, b) in enumerate(zip(before, cpu.memory))
                  if a != b and not (0xe5 <= i <= 0xec or 0x100 <= i <= 0x1ff)]
    return {'value': int.from_bytes(bytes(cpu.memory[0xe5:0xe7]), 'little', signed=True),
            'saturated': cpu.p & 1, 'cycles': cpu.processorCycles,
            'input_preserved': bytes(cpu.memory[0xe0:0xe5]) == inputs,
            'decimal': int(bool(cpu.p & cpu.DECIMAL)), 'unexpected_writes': unexpected}


def main():
    image = assemble()
    values = [-2147483648, -2147483647, -65537, -65535, -32769, -32768,
              -257, -5, -3, -1, 0, 1, 3, 5, 257, 32767, 32768, 65535,
              65537, 2147483647]
    timings = []
    for shift in range(32):
        cycles = []
        for value in values:
            magnitude = abs(value)
            rounded = magnitude if shift == 0 else (magnitude + (1 << (shift - 1))) >> shift
            rounded = -rounded if value < 0 else rounded
            expected = max(-32768, min(32767, rounded))
            result = execute(image, value, shift)
            assert result['value'] == expected and result['saturated'] == int(expected != rounded)
            assert result['input_preserved'] and not result['unexpected_writes'] and result['decimal'] == 0
            cycles.append(result['cycles'])
        timings.append({'shift': shift, 'vectors': len(cycles), 'mean_cycles': statistics.mean(cycles),
                        'worst_observed_cycles': max(cycles)})
    report = {'scope': 'isolated signed INT32 right-shift, nearest/ties-away rounding, INT16 saturation',
              'code_bytes': len(image), 'cases': sum(row['vectors'] for row in timings),
              'source_sha256': hashlib.sha256((ROOT / 'src/kernels/requantize.asm').read_bytes()).hexdigest(),
              'image_sha256': hashlib.sha256(image).hexdigest(),
              'cycle_boundary': 'entry through RTS; excludes caller JSR, interrupts, VIC stalls and I/O',
              'all_integer_inputs_exhaustively_tested': False, 'timings': timings}
    (ROOT / 'results/requantize-summary.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'code_bytes': len(image), 'cases': report['cases'], 'timings': timings[::8]}, indent=2))


if __name__ == '__main__':
    main()
