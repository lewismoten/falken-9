"""Build graphical application separately from frozen numeric 001/002."""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import sys
import textwrap
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.build_runtime import ROOT, FOUR_MODEL, build as build_runtime
from scripts.compile_graphics import compile_assets

APP_STAGE = '006-graphical'
APP_STEM = 'falken9-'+APP_STAGE
OUT = ROOT/'build/graphical'
CODE = {c:i+1 for i,c in enumerate('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}
CODE.update({c:i+27 for i,c in enumerate('0123456789')})
CODE.update({' ':0, '?':37, ':':38, '.':39, ',':40, '/':41, '-':42, '!':43, '>':44, '(':45, ')':46, "'":47, '=':48, '+':49})
STATUSES = ['YOUR TURN - 1 TO 9', 'INVALID / OCCUPIED', 'NEURAL FORWARD - WAIT', 'NEURAL DONE', 'X WINS - R REPLAY / Q TITLE', 'O WINS - R REPLAY / Q TITLE', 'DRAW - R REPLAY / Q TITLE', 'NEURAL ERROR - R OR Q', 'TWO PLAYERS - 1 TO 9']


def sha(raw): return hashlib.sha256(raw).hexdigest()


def pack_runs(raw):
    """Literal/run packets: high bit run, low seven bits length minus one."""
    result=bytearray();i=0
    while i<len(raw):
        run=1
        while i+run<len(raw) and raw[i+run]==raw[i] and run<128:run+=1
        if run>=3:
            result += bytes([0x80|run-1,raw[i]]);i+=run
        else:
            begin=i;i+=run
            while i<len(raw) and i-begin<128:
                if i+2<len(raw) and raw[i]==raw[i+1]==raw[i+2]:break
                i+=1
            result += bytes([i-begin-1])+raw[begin:i]
    return bytes(result)


def presentation_forward():
    """Relocate exact resident orchestration; insert state-preserving checkpoints.

    No arithmetic replacement, cached logits or data-dependent specialization.
    This separate execution path requires its own 627-vector parity gate.
    """
    ranges=[('experts.asm','full_forward:','; Input-major'),
            ('router.asm','board_router:','; Stable lower-index'),
            ('norm2.asm','board_norm2:','; source/dest'),
            ('forward.asm','board_readout:','; Row-major'),
            ('projection.asm','board_attention_block:','embedding_rows:'),
            ('attention.asm','board_attention:','load_key_weight:')]
    pieces=[]
    for file,start,end in ranges:
        text=(ROOT/'src/runtime'/file).read_text()
        assert text.count(start)==text.count(end)==1
        pieces.append(text.split(start,1)[1].split(end,1)[0].join([start,'']))
    text='\n'.join(pieces)
    labels=re.findall(r'^(\w+):',text,re.M)
    for label in sorted(labels,key=len,reverse=True):
        text=re.sub(r'\b'+re.escape(label)+r'\b','graph_'+label,text)
    # Announce only real boundaries. Preserve carry before the existing guard.
    calls={'token_frontend','matrix8','readout_only','gelu_vector','norm2','matrix_variable','route_top2','route_gates','expert_matrix','expert_merge','output_head'}
    lines=[]
    for line in text.splitlines():
        if line in ('graph_board_score_row:', 'graph_attention_softmax_row:'):
            lines.extend([line, '    jsr activity_tick'])
            continue
        m=re.match(r'\s*(jsr|jmp) (\w+)\s*$',line)
        if m and (m[2] in calls or m[2]=='graph_readout_only'):
            lines.extend(['    jsr '+m[2], '    jsr progress_event'])
            if m[1]=='jmp':lines.append('    rts')
        else:lines.append(line)
    return 'EXPERT_COUNT = 4\n'+'\n'.join(lines)+'\n'


def build(output=None):
    out = OUT if output is None else Path(output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    core = build_runtime(model=FOUR_MODEL, output=out/'core')
    assert core['image_sha256'] == '838aa62a854aa58bd603c7525b52dc67c4c4b01ea0f50f58982475959ec61961'
    paths, graphics = compile_assets(out/'graphics')
    packed = bytearray(paths['packed'].read_bytes())
    regions = graphics['regions']
    # Application overlays; indexed authority PNGs remain unchanged.
    charset = bytearray(paths['charset'].read_bytes())
    code = dict(CODE)
    def encode(text): return bytes(code[c] for c in text)
    def overlay(plane, colors, row, col, text, color):
        at=row*40+col;plane[at:at+len(text)] = encode(text);colors[at:at+len(text)] = bytes([color])*len(text)
    title = bytearray(paths['title_screen'].read_bytes());tc=bytearray(paths['title_color'].read_bytes())
    for row,text in [(20,'FALCON-9'),(21,'1.0')]:overlay(title,tc,row,30,text,6)
    for row,text in [(22,'INFO'),(23,'QUIT')]:
        overlay(title,tc,row,2,text,12);tc[row*40+2]=1
    info=bytearray(paths['info_screen'].read_bytes());ic=bytearray(paths['info_color'].read_bytes())
    overlay(info,ic,1,6,'FALCON-9 / MODEL INFO'.ljust(28),7)
    footer='SCROLL: UP/DOWN QUIT: Q'
    overlay(info,ic,23,10,footer,12)
    for col in list(range(18,25))+[32]:ic[23*40+col]=1
    # Same 29x18 viewport and Markdown palette as the original archive viewer.
    # URLs wrap without clipping. These are requested destinations, not a claim
    # of publication; model/artifact slugs intentionally retain frozen spelling.
    sections=[('FALCON-9 1.0',1),('MODEL',7),('5195 BYTES - F9J2 INTEGER',1),
        ('4 EXPERTS / 2 ACTIVE',1),('Q11 / W16 / A32',1),('ATTENTION + ROUTED MLP',1),
        ('ALL WEIGHTS STAY IN RAM',1),('',1),('CONTROLS',7),
        ('1-9: SQUARES 123/456/789',1),('R: REPLAY   Q: TITLE',1),
        ('1 PLAYER: YOU X / MODEL O',1),('2 PLAYERS: ALTERNATE X/O',1),
        ('0 PLAYERS: BOTH SIDES NEURAL',1),('',1),('DISPLAY',7),
        ('X / O: TURN OR WINNER',1),('D: DRAW   ?: INVALID',1),('!: ERROR - R OR Q',1),
        ('BAR: COMPLETED COMPUTE WORK',1),('RED X / BLUE O',1),
        ('LIGHTS: ACTIVITY NOT PROGRESS',1),('',1),('REPOSITORIES',7),
        ('REQUESTED - NOT YET PUBLISHED',1),
        ('HTTPS://GITHUB.COM/LEWISMOTEN/FALCON-9',1),('',1),
        ('HTTPS://HUGGINGFACE.CO/LEWISMOTEN/FALCON-9',1),('',1),('RUNTIME BOUNDARY',7),
        ('EMULATOR-TESTED ONLY',10),('NO PHYSICAL C64 ACCEPTANCE',1),
        ('NO HOSTED INFERENCE',1),('FIXED BOARD SYMMETRIES',1),
        ('ROTATE / REFLECT / INVERSE',1),('ARE NOT LEARNED WEIGHTS',1),
        ('FROZEN MODEL: MODEL-V1.0.0',1),('ARTIFACT SLUG: FALKEN9',1)]
    info_lines=[];info_colors=[]
    for text,color in sections:
        for line in textwrap.wrap(text,29,break_long_words=True,break_on_hyphens=False) or ['']:
            info_lines.append(line.ljust(29));info_colors.append(color)
    quit_screen=bytearray(info);quit_color=bytearray(ic)
    for row in range(3,22):overlay(quit_screen,quit_color,row,5,' '*28,14)
    overlay(quit_screen,quit_color,7,5,'SESSION ENDED'.center(28),14)
    overlay(quit_screen,quit_color,10,5,'RESET OR RELOAD TO PLAY'.center(28),14)
    overlay(quit_screen,quit_color,23,6,' '*28,5)
    for name,raw in [('charset',charset),('title_screen',title),('title_color',tc),('info_screen',info),('info_color',ic)]:
        r=regions[name];packed[r['offset']:r['offset']+r['length']]=raw
        (out/(name+'.bin')).write_bytes(raw)
    (out/'graphics.bin').write_bytes(packed)
    includes=[];compressed=bytearray()
    for name in ['charset','title_screen','title_color','info_screen','info_color','board_bitmap','board_screen','board_color']:
        r=regions[name]
        includes += [f'art_{name} = ${0xa000+len(compressed):04x}',f'art_{name}_length = {r["length"]}']
        compressed += pack_runs(packed[r['offset']:r['offset']+r['length']])
    for name,raw in [('quit_screen',quit_screen),('quit_color',quit_color)]:
        includes += [f'art_{name} = ${0xa000+len(compressed):04x}']
        compressed += pack_runs(raw)
    includes += [f'info_line_count = {len(info_lines)}',f'info_chars = ${0xa000+len(compressed):04x}']
    compressed += b''.join(encode(line) for line in info_lines)
    includes += [f'info_line_colors = ${0xa000+len(compressed):04x}']
    compressed += bytes(info_colors)
    source_info=paths['info_screen'].read_bytes();source_ic=paths['info_color'].read_bytes()
    includes += [f'info_track_glyph = {source_info[5*40+34]}',f'info_marker_glyph = {source_info[4*40+34]}',
        f'info_track_color = {source_ic[5*40+34]}',f'info_marker_color = {source_ic[4*40+34]}',
        'info_scroll_positions:', '    .byte '+','.join(str(round(i*17/(len(info_lines)-18))) for i in range(len(info_lines)-17)),
        'info_track_lo:', '    .byte '+','.join(str((0x400+(4+i)*40+34)&255) for i in range(18)),
        'info_track_hi:', '    .byte '+','.join(str((0x400+(4+i)*40+34)>>8) for i in range(18))]
    activity_cells=[19*40+c for c in (7,12,13,20,26,27,32)]
    screen=paths['board_screen'].read_bytes()
    assert all(screen[c]>>4==7 for c in activity_cells)
    includes += ['activity_base:', '    .byte '+','.join(str(screen[c]) for c in activity_cells),
        'activity_offsets:', '    .byte '+','.join(str(c-19*40) for c in activity_cells)]
    calibration=ROOT/'src/app/progress-calibration.json'
    fills=json.loads(calibration.read_text())['fills'] if calibration.exists() else [min(46,(i+1)*47//32) for i in range(32)]
    assert len(fills)==32 and fills==sorted(fills) and max(fills)<=46
    includes += ['progress_thresholds:', '    .byte '+','.join(map(str,fills))]
    assert len(compressed)<=0x3000, 'compressed artwork must remain below I/O'
    (out/'runtime-graphics.bin').write_bytes(compressed)
    # Compact patch bytecode avoids >8K straight-line code: dest/value records.
    records=bytearray();ptrs=[];counts=[]
    for c in 'abcdefghi':
        for mark in 'xo':
            ptrs.append(len(records));count=0
            for p in graphics['cells'][c]['planes'].values():
                r=regions[p['values'][mark]]
                for j,dest in enumerate(p['destination_offsets']):
                    records += (p['destination_base']+dest).to_bytes(2,'little')+bytes([packed[r['offset']+j]]);count+=1
            counts.append(count)
    (out/'mark-patches.bin').write_bytes(records)
    includes += ['mark_pointers:', '    .word '+','.join('mark_patch_data+'+str(p) for p in ptrs), 'mark_counts:', '    .byte '+','.join(map(str,counts))]
    # Separate declared application overlays, never edits to indexed source art.
    # 3x5 digits use selector 01 (screen high nibble = medium gray 12), with
    # black padding to one 8x8 VIC cell. All footprints are inside mark interiors.
    digit_rows = ('010110010010111', '111001111100111', '111001111001111',
                  '101101111001001', '111100111001111', '111100111101111',
                  '111001010010010', '111101111101111', '111101111001111')
    label_records = bytearray(); label_ptrs = []; numeric_labels = []
    layout = json.loads((ROOT/'assets/game-art/game/board/layout.json').read_text())
    blank_bitmap = paths['board_bitmap'].read_bytes()
    blank_screen = paths['board_screen'].read_bytes()
    for i, (row, col) in enumerate((r,c) for r in (5,8,11) for c in (16,20,23)):
        cell = row*40+col
        x,y,w,h = layout['cell_rectangles']['abcdefghi'[i]]['preview_xywh']
        assert x <= col*8 and col*8+8 <= x+w and y <= row*8 and row*8+8 <= y+h
        assert blank_bitmap[cell*8:cell*8+8] == bytes(8)
        glyph = bytes([0]+[sum(int(digit_rows[i][r*3+c]) << (6-2*c) for c in range(3)) for r in range(5)]+[0,0])
        screen = 0xc0 | (blank_screen[cell] & 15)
        writes = [(0x2000+cell*8+j,value) for j,value in enumerate(glyph)] + [(0x400+cell,screen)]
        label_ptrs.append(len(label_records))
        for address,value in writes:
            label_records += address.to_bytes(2,'little') + bytes([value])
        numeric_labels.append(dict(square=i+1, cell=cell, bitmap_address=0x2000+cell*8,
                                   screen_address=0x400+cell, glyph_hex=glyph.hex(), screen_value=screen,
                                   color=12, selectors='00 background / 01 screen high; Color RAM unchanged'))
    (out/'numeric-labels.bin').write_bytes(label_records)
    includes += ['numeric_label_pointers:', '    .word '+','.join('numeric_label_data+'+str(p) for p in label_ptrs)]
    # Text in bitmap mode uses native 2-bit pixels; 01 selects screen high color.
    font=bytearray()
    for glyph in range(50):
        for bits in charset[glyph*8:glyph*8+8]:
            font.append(sum(1<<(6-2*p) for p in range(4) if bits & (0xc0>>(2*p))))
    (out/'bitmap-font.bin').write_bytes(font)
    statuses=b''.join(encode(s.ljust(32)) for s in STATUSES)
    (out/'statuses.bin').write_bytes(statuses)
    (out/'controls.bin').write_bytes(encode('1-9 MOVE   R REPLAY   Q TITLE'.ljust(32)))
    (out/'presentation-forward.inc').write_text(presentation_forward())
    (out/'graphics.inc').write_text('\n'.join(includes)+'\n')
    (out/'core-labels.inc').write_text('\n'.join(f'{k} = ${v:04x}' for k,v in core['labels'].items())+'\n')
    core_bytes=(out/'core/runtime.bin').read_bytes();(out/'core-backup.bin').write_bytes(core_bytes[:16])
    # Preserve numeric sources; only change presentation and the forward symbol.
    entry=(ROOT/'src/app/app.asm').read_text()
    assert entry.count('.include "game.asm"')==1 and entry.count('.include "wrapper.asm"')==1
    entry=entry.replace('.include "game.asm"','.include "graphical_game.asm"').replace('.include "wrapper.asm"','.include "graphical-wrapper.inc"')
    (out/'entry.asm').write_text(entry)
    wrapper=(ROOT/'src/app/wrapper.asm').read_text()
    assert wrapper.count('jsr full_forward')==1
    (out/'graphical-wrapper.inc').write_text(wrapper.replace('jsr full_forward','jsr graphical_forward'))
    assembler=os.environ.get('TASS64',str(ROOT/'build/tools/64tass/usr/bin/64tass'))
    run=subprocess.run([assembler,'--m6502','--long-branch','--case-sensitive','--nostart','-I',str(out),'-I',str(ROOT/'src/app'),'--labels='+str(out/'app.lbl'),'--list='+str(out/'app.lst'),'-o',str(out/'app.bin'),str(out/'entry.asm')],capture_output=True,text=True)
    (out/'assembly.log').write_text(run.stdout+run.stderr)
    if run.returncode:raise RuntimeError(run.stdout+run.stderr)
    labels=dict(core['labels'])
    for line in (out/'app.lbl').read_text().splitlines():
        m=re.match(r'(\w+)\s*=\s*\$([0-9a-fA-F]+)',line)
        if m:labels[m[1]]=int(m[2],16)
    full=bytearray(0xa000+len(compressed)-0x800)
    full[:len(core_bytes)]=core_bytes
    app=(out/'app.bin').read_bytes();assert labels['app_end']<=0xa000
    full[0x8000-0x800:0x8000-0x800+len(app)]=app
    full[0xa000-0x800:]=compressed
    # Entire load stays below I/O and KERNAL; reads under BASIC bank it out
    # without hiding KERNAL/IRQ vectors or Color RAM.
    stub=bytes([12,8,10,0,0x9e])+b'32768'+bytes([0,0,0])
    prg=bytearray(full[1:]);prg[:len(stub)]=stub
    path=out/(APP_STEM+'.prg');path.write_bytes(b'\x01\x08'+prg)
    (out/'combined.bin').write_bytes(full)
    info=dict(prg_path=str(path),prg_sha256=sha(path.read_bytes()),path=str(out/'combined.bin'),load=0x800,labels=labels,core=core,image_sha256=sha(full),app_code_start=0x8000,app_code_end=labels['app_end'],graphics_paths={k:str(v) for k,v in paths.items()},graphics=graphics,numeric_labels=numeric_labels,charset_codes=code,statuses=STATUSES,activity_cells=activity_cells,
              memory_map=core['memory_map']+[dict(name='app_state',start=0x7800,end=0x7900,writable=True),dict(name='bitmap_or_charset',start=0x2000,end=0x4000,writable=True),dict(name='screen',start=0x400,end=0x800,writable=True),dict(name='color',start=0xd800,end=0xdc00,writable=True)])
    (out/'build.json').write_text(json.dumps(info,indent=2)+'\n')
    return info


if __name__=='__main__':print(json.dumps(build(),indent=2))
