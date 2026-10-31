#!/usr/bin/env python3
"""Assemble and execute isolated kernels; no full-inference timing claim."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from py65.devices.mpu6502 import MPU

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / 'artifacts/kernels'


def assembler():
    """Prefer an explicitly selected or normal PATH assembler."""
    configured = os.environ.get('TASS64') or shutil.which('64tass')
    if configured:
        return configured
    # Self-contained project toolchain; do not depend on another checkout.
    pinned = ROOT / 'build/tools/64tass/usr/bin/64tass'
    if pinned.is_file():
        return str(pinned)
    raise RuntimeError('64tass missing: run sh scripts/bootstrap_64tass.sh, install it, or set TASS64')


def assemble(kind):
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    target = ARTIFACTS / (kind + '.bin')
    labels = ARTIFACTS / (kind + '.lbl')
    command = [assembler(), '--nostart', '--labels=' + str(labels),
               '-o', str(target), str(ROOT / 'src/kernels' / (kind + '.asm'))]
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    (ARTIFACTS / (kind + '-assembly.log')).write_text(result.stdout + result.stderr)
    return target.read_bytes()


def execute(image, activations, packed, output_bits=16):
    """Cycles: first entry opcode through RTS inclusive; no caller JSR."""
    if len(activations) > 32:
        raise ValueError('experiment supports at most 32 lanes')
    cpu = MPU(memory=[0xa5] * 65536, pc=0x2000)
    cpu.memory[0x2000:0x2000+len(image)] = image
    cpu.memory[0x3000:0x3000+len(activations)] = [x & 255 for x in activations]
    cpu.memory[0x3100:0x3100+len(packed)] = packed
    cpu.memory[0xe0] = len(activations)
    cpu.sp = 0xfd
    cpu.memory[0x1fe:0x200] = [0xfe, 0x02]  # RTS -> $02ff.
    cpu.p |= cpu.DECIMAL  # Kernel must explicitly establish binary arithmetic.
    before = list(cpu.memory)
    for _ in range(100000):
        cpu.step()
        if cpu.pc == 0x02ff:
            break
    else:
        raise RuntimeError('kernel instruction watchdog')
    unexpected = [i for i,(a,b) in enumerate(zip(before,cpu.memory))
                  if a != b and not (0xe1 <= i <= 0xef or 0x100 <= i <= 0x1ff)]
    raw = bytes(cpu.memory[0xe1:0xe1 + output_bits//8])
    return {'value': int.from_bytes(raw, 'little', signed=True),
            'raw_hex': raw.hex(), 'cycles': cpu.processorCycles,
            'carry': cpu.p & 1, 'decimal': int(bool(cpu.p & cpu.DECIMAL)),
            'stack_pointer': cpu.sp, 'unexpected_writes': unexpected}


def run_benchmarks():
    """Ten deterministic cases per dimension, including actual packed decode."""
    import random
    import statistics
    import importlib.metadata
    report = {
        'scope': 'isolated dot products, not full inference',
        'cycle_boundary': 'entry opcode through RTS inclusive; excludes caller JSR, interrupts, VIC stalls and I/O',
        'assembler_version': subprocess.check_output([assembler(), '--version'], text=True).strip(),
        'py65_version': importlib.metadata.version('py65'),
        'seed': 90210,
        'kernels': {},
    }
    vectors = []
    for kind in ['binary', 'ternary', 'int8']:
        image = assemble(kind)
        dimensions = []
        for n in [8,12,16,24,32]:
            rng = random.Random(90210 + n)
            magnitude = 128 if kind == 'int8' else 1
            positive = 127 if kind == 'int8' else 1
            cases = [
                ('zero_x', [0]*n, [positive]*n),
                ('min_negative', [-128]*n, [-magnitude]*n),
                ('max_positive', [127]*n, [positive]*n),
                ('min_positive', [-128]*n, [positive]*n),
                ('max_negative', [127]*n, [-magnitude]*n),
                ('alternating', [-128 if i%2 else 127 for i in range(n)],
                 [-magnitude if i%2 else positive for i in range(n)]),
                ('zero_or_balanced_weights', list(range(n)),
                 [(-1 if i%2 else 1) if kind == 'binary' else 0 for i in range(n)]),
                ('sparse_or_binary', [127]*n,
                 [1 if i%4 == 0 else (-1 if kind == 'binary' else 0) for i in range(n)]),
            ]
            for index in range(2):
                xs = [rng.randrange(-128,128) for _ in range(n)]
                ws = ([rng.randrange(-128,128) for _ in range(n)] if kind == 'int8'
                      else [rng.choice([-1,1] if kind == 'binary' else [-1,0,1]) for _ in range(n)])
                cases.append(('seeded_' + str(index), xs, ws))
            cycles = []
            for name, xs, ws in cases:
                if kind == 'int8':
                    packed = bytes(w & 255 for w in ws)
                else:
                    bits = 1 if kind == 'binary' else 2
                    codebook = {-1:0,1:1} if kind == 'binary' else {0:0,1:1,-1:2}
                    packed = bytearray((n*bits+7)//8)
                    for i,w in enumerate(ws):
                        packed[i*bits//8] |= codebook[w] << (i*bits%8)
                actual = execute(image,xs,packed,32 if kind == 'int8' else 16)
                oracle = sum(x*w for x,w in zip(xs,ws))
                if actual['value'] != oracle or actual['carry'] or actual['unexpected_writes']:
                    raise AssertionError((kind,n,name,actual,oracle))
                cycles.append(actual['cycles'])
                vectors.append({'kernel':kind,'dimension':n,'case':name,
                                'activations':xs,'weights':ws,'packed_hex':bytes(packed).hex(),
                                'oracle':oracle,'actual':actual.pop('value'),**actual})
            dimensions.append({'dimension':n,'vectors':len(cycles),
                               'min_cycles':min(cycles), 'mean_cycles':statistics.mean(cycles),
                               'worst_cycles':max(cycles),
                               'activation_bytes':n,
                               'weight_bytes':(n+7)//8 if kind == 'binary' else ((n+3)//4 if kind == 'ternary' else n),
                               'output_bytes':4 if kind == 'int8' else 2})
        report['kernels'][kind] = {'sha256':hashlib.sha256(image).hexdigest(),
                                   'source_sha256':hashlib.sha256((ROOT/'src/kernels'/ (kind+'.asm')).read_bytes()).hexdigest(),
                                   'code_bytes':len(image), 'code_start':8192,
                                   'code_end_exclusive':8192+len(image),
                                   'zero_page_bytes_including_length':13 if kind == 'int8' else 8,
                                   'dimensions':dimensions}
    report['vectors_sha256'] = hashlib.sha256(json.dumps(vectors,sort_keys=True).encode()).hexdigest()
    return report, vectors


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    report, vectors = run_benchmarks()
    (ROOT/'results').mkdir(exist_ok=True)
    (ROOT/'results/kernel-summary.json').write_text(json.dumps(report,indent=2)+'\n')
    (ARTIFACTS/'vectors.json').write_text(json.dumps(vectors,indent=2)+'\n')
    print(json.dumps(report,indent=2))
