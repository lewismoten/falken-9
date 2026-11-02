"""Build pinned accepted F9J2 model into a standalone NMOS 6502 image."""
from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import subprocess
import struct
import math

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT/'artifacts/canonical-integer/verified/q11-w16-a32-early-interp/model.f9j'
MODEL_SHA = '6c2b3dc6ec2a26fbdd28b1d7c78abbd0fcfd285c3f45bea4357fcb9f3fefa8c9'
OUT = ROOT/'build/runtime'


FOUR_MODEL = ROOT/'artifacts/flexible-integer/q11-w16-a32-early-interp/model.f9j'
FOUR_SHA = 'fe180f8a931f9d92d8aa39da337bc819d0dbe4e6d971edcba00324fbc18a91c1'


def build(model=None, output=None):
    model = MODEL if model is None else Path(model)
    OUT = globals()['OUT'] if output is None else Path(output)
    raw = model.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    assert (len(raw), digest) in [(6110, MODEL_SHA), (5195, FOUR_SHA)], 'unpinned runtime model'
    full = digest == FOUR_SHA
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'model.f9j').write_bytes(raw)
    # Static pointers only. Every weight remains in its original resident bytes.
    names = ('position','expert_w1','expert_b1','expert_w2','expert_b2','occupancy_weight','side_weight','norm1_weight','norm1_bias','query_weight','key_weight','value_weight','projection_weight','readout_weight','readout_bias','norm2_weight','norm2_bias','router_weight','router_bias','output_weight','output_bias')
    pos = 99
    descriptors = []
    constants = [f'FULL_FORWARD = {int(full)}', f'EXPERT_COUNT = {4 if full else 9}']
    for name in names:
        bits,rank,count = struct.unpack_from('<BBH',raw,pos)
        pos += 4
        shape = tuple(raw[pos:pos+rank]); pos += rank
        constants.append(f'{name}_exponents = ${0x4000+pos:04x}')
        pos += count
        descriptors.append((name,math.prod(shape)*bits//8))
    for name,size in descriptors:
        constants.append(f'{name}_data = ${0x4000+pos:04x}')
        pos += size
    assert pos+2052 == len(raw)
    constants += [f'exp_table = ${0x4000+pos:04x}',f'gelu_table = ${0x4000+pos+1026:04x}']
    (OUT/'model.inc').write_text('\n'.join(constants)+'\n')
    assembler = os.environ.get('TASS64',str(ROOT/'build/tools/64tass/usr/bin/64tass'))
    if not Path(assembler).exists(): assembler = shutil.which('64tass') or assembler
    cmd = [assembler,'--m6502','--case-sensitive','--nostart','-I',str(OUT),
           '--labels='+str(OUT/'runtime.lbl'),'--list='+str(OUT/'runtime.lst'),
           '-o',str(OUT/'runtime.bin'),str(ROOT/'src/runtime/runtime.asm')]
    p = subprocess.run(cmd,capture_output=True,text=True)
    (OUT/'assembly.log').write_text(p.stdout+p.stderr)
    if p.returncode: raise RuntimeError(p.stdout+p.stderr)
    labels = {}
    for line in (OUT/'runtime.lbl').read_text().splitlines():
        match = re.match(r'(\w+)\s*=\s*\$([0-9a-fA-F]+)',line)
        if match: labels[match[1]] = int(match[2],16)
    image = (OUT/'runtime.bin').read_bytes()
    assert image[0x4000-0x0800:0x4000-0x0800+len(raw)] == raw
    info = dict(path=str(OUT/'runtime.bin'),load=0x0800,labels=labels,
                image_sha256=hashlib.sha256(image).hexdigest(),model_sha256=digest,
                code_bytes=labels['code_end']-0x0800,model_bytes=len(raw),
                image_bytes=len(image))
    info['memory_map'] = [
        dict(name='math_and_pointer_zero_page',start=0x20,end=0x80,writable=True),
        dict(name='hardware_stack_reserved',start=0x100,end=0x200,writable=True),
        dict(name='screen_reserved_untouched',start=0x400,end=0x800,writable=False),
        dict(name='assembled_code_and_static_metadata',start=0x800,end=labels['code_end'],writable=False),
        dict(name='original_F9J2_with_all_LUTs',start=0x4000,end=labels['model_end'],writable=False),
        dict(name='activations_and_retained_stage_vectors',start=0x6000,end=0x6da0,writable=True),
        dict(name='ABI_control_and_softmax_scratch_reserved',start=0x7000,end=0x7100,writable=True),
    ]
    if full:
        info['memory_map'].append(dict(name='full_forward_vectors_and_controls',start=0x7200,end=0x7600,writable=True))
    info['source_sha256'] = {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'src/runtime').glob('*.asm'))}
    info['allocated_bytes'] = sum(r['end']-r['start'] for r in info['memory_map'])
    info['image_filled_gap_bytes'] = info['image_bytes']-info['code_bytes']-info['model_bytes']
    (OUT/'build.json').write_text(json.dumps(info,indent=2)+'\n')
    return info

if __name__ == '__main__': print(json.dumps(build(),indent=2))
