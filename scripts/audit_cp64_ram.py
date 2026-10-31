"""Reproduce read-only CP64 layout evidence. Run with CP64_ROOT set."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil

root = Path(os.environ['CP64_ROOT'])
out = Path(__file__).resolve().parents[1] / 'artifacts/kernels'
out.mkdir(parents=True, exist_ok=True)
sources = [
    'build/cp64.lbl', 'build/release-018.lbl', 'build/ai_opening_bundle.lbl',
    'build/ai_opening_bundle.inc', 'build/ai_opening_bundle.asm',
    'src/art_embedded_title.asm', 'src/clock_pixel_probe.asm',
    'src/info_markdown.inc', 'src/progress_work.inc',
    'scripts/tensor_batching.py', 'scripts/export_c64_layers.py',
]
evidence = []
for relative in sources:
    src = root/relative
    target = out/'ram-evidence'/relative
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(src,target)
    evidence.append({'source':relative,'evidence':str(target.relative_to(out.parent.parent)),
                     'bytes':src.stat().st_size,'sha256':hashlib.sha256(src.read_bytes()).hexdigest()})
images = []
for relative in ['build/CP64.PRG','build/AIOPEN.PRG','build/ARCHIVE.PRG']:
    data = (root/relative).read_bytes()
    start = int.from_bytes(data[:2],'little')
    images.append({'source':relative,'sha256':hashlib.sha256(data).hexdigest(),
                   'file_bytes':len(data),'load_start':start,'payload_bytes':len(data)-2,
                   'end_exclusive':start+len(data)-2})
assets = []
for path in sorted((root/'build/assets').rglob('*.bin')):
    data = path.read_bytes()
    assets.append({'source':str(path.relative_to(root)),'bytes':len(data),
                   'sha256':hashlib.sha256(data).hexdigest()})
packets=[]
for path in sorted((root/'build/layers').glob('C9W*.PRG')):
    data=path.read_bytes()
    start=int.from_bytes(data[:2],'little')
    packets.append({'source':str(path.relative_to(root)),'load_start':start,
                    'payload_bytes':len(data)-2,'end_exclusive':start+len(data)-2})
symbols={}
for relative in ['build/release-018.lbl','build/ai_opening_bundle.lbl']:
    symbols[relative] = {m.group(1):int(m.group(2),16)
                         for m in re.finditer(r'^(\w+)\s*=\s*\$([0-9a-fA-F]+)',(root/relative).read_text(),re.M)}
# Layout proposal only: no assembled game using these allocations yet.
arenas = [
    {'name':'minimal_harness_model','start':0x4000,'end_exclusive':0x6000,'bytes':8192,'classification':'provisional'},
    {'name':'minimal_harness_activation','start':0xc000,'end_exclusive':0xd000,'bytes':4096,'classification':'provisional'},
]
# Deliberately disjoint, reserved regions of a NEW minimal harness only.
prototype_ledger = [
    {'name':name, 'start':start, 'end_exclusive':end, 'bytes':end-start,
     'classification':'provisional reservation'}
    for name,start,end in [
        ('system_zero_page_stack',0,0x400),
        ('screen_and_sprite_pointer_reservation',0x400,0x800),
        ('new_resident_code',0x800,0x2000),
        ('live_bitmap_reservation',0x2000,0x4000),
        ('model',0x4000,0x6000),
        ('activation_and_scratch',0xc000,0xd000),
        ('io_excluded',0xd000,0xe000),
        ('kernal_rom_excluded',0xe000,0x10000),
    ]
]
report={'scope':'read-only source/map audit; no C64 game residency acceptance',
        'prototype_ledger':prototype_ledger,
        'evidence':evidence,'images':images,'asset_files':assets,'tensor_packets':packets,
        'symbols':symbols,'candidate_arenas':arenas,
        'proven_free_bytes_in_existing_complete_game':0}
(out/'ram-audit.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'images':images,'largest_tensor_packet':max(packets,key=lambda p:p['payload_bytes']),
                  'arenas':arenas},indent=2))
