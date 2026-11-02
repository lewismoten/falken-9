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
from scripts.compile_graphics import compile_assets, C64_PALETTE

APP_STAGE = '011-graphical'
APP_STEM = 'falken-9-'+APP_STAGE
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
    # All copied orchestration frames are balanced RTS frames (no local pushes).
    # Check only after existing stage/subroutine boundaries. No core patch, no
    # IRQ stack manipulation; each canceled frame returns normally with C=1.
    assert not re.search(r'^\s*(pha|php|pla|plp)\s*$', text, re.M)
    checked=[];checkpoint=0
    for line in lines:
        checked.append(line)
        m=re.match(r'\s*jsr (\w+)\s*$',line)
        if m and (m[1].startswith('graph_') or m[1] in {'progress_event','activity_tick'}):
            checkpoint+=1
            label=f'quit_continue_{checkpoint}'
            checked.extend(['    php','    bit quit_pending',f'    bpl {label}',
                            '    plp','    sec','    rts',label+':','    plp'])
    return 'EXPERT_COUNT = 4\n'+'\n'.join(checked)+'\n'


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
    brand, version, brand_col = 'FALKEN-9', '1.0', 30
    overlay(title,tc,22,brand_col,brand,6)
    overlay(title,tc,23,brand_col+len(brand)-len(version),version,6)
    for row,text in [(22,'INFO'),(23,'QUIT')]:
        overlay(title,tc,row,2,text,12);tc[row*40+2]=1
    info=bytearray(paths['info_screen'].read_bytes());ic=bytearray(paths['info_color'].read_bytes())
    overlay(info,ic,1,6,'FALKEN-9 / MODEL INFO'.ljust(28),7)
    footer='SCROLL: UP/DOWN QUIT: Q'
    overlay(info,ic,23,10,footer,12)
    for col in list(range(18,25))+[32]:ic[23*40+col]=1
    # Same 29x18 viewport and Markdown palette as the original archive viewer.
    # Public destinations retain their intended repository spelling. Release
    # publication state is tracked privately, not presented as in-game copy.
    sections=[('FALKEN-9 1.0',1),('MODEL',7),('5195 BYTES - F9J2 INTEGER',1),
        ('4 EXPERTS / 2 ACTIVE',1),('Q11 / W16 / A32',1),('ATTENTION + ROUTED MLP',1),
        ('ALL WEIGHTS STAY IN RAM',1),('',1),('CONTROLS',7),
        ('1-9: SQUARES 123/456/789',1),('R: REPLAY   Q: TITLE',1),('M: MUTE / UNMUTE SID',1),
        ('1 PLAYER: YOU X / MODEL O',1),('2 PLAYERS: ALTERNATE X/O',1),
        ('0 PLAYERS: CONTINUOUS DEMO',1),('ALL AI MOVES RUN THE MODEL',1),
        ('FIRST GAME: FIXED OPENING TIE',1),('LATER OPENINGS: RANDOM TIES',1),
        ('ONLY FROM MODEL APPROVED SET',1),('FROZEN MODEL - NOT LEARNING',1),
        ('2 SECOND RESULT / AUTO REPLAY',1),('Q: CANCEL AT STAGE BOUNDARY',1),('',1),('DISPLAY',7),
        ('X / O: TURN OR WINNER',1),('D: DRAW   ?: INVALID',1),('!: ERROR - R OR Q',1),
        ('BAR: COMPLETED COMPUTE WORK',1),('RED X / BLUE O',1),
        ('LIGHTS: ACTIVITY NOT PROGRESS',1),('ORIGINAL SID: PATIENT',1),('CALCULATIONS - TWO VOICES',1),
        ('VOICE 3: QUIET UI / MARK SFX',1),('DECORATIVE - NOT STRATEGY',1),('',1),('LINEAGE',7),
        ('PALACE-9: GGUF / LOCAL LLM',1),('CRYSTAL-9: CUSTOM INT4',1),
        ('CRYSTAL PALACE: C64 PORT',1),('FALKEN-9: NEW C64-FIRST MODEL',1),
        ('WIDTH 8 / EXPERT WIDTH 4',1),('NOT REPACKED CRYSTAL WEIGHTS',1),('',1),('INSPIRATION',7),
        ('INSPIRED BY WARGAMES (1983)',1),('NAMED FOR DR. STEPHEN FALKEN',1),
        ('FICTIONAL RESEARCHER BEHIND',1),('JOSHUA - AI ON THE WOPR',1),
        ('WAR-SIMULATION COMPUTER',1),('THIS GAME: TIC-TAC-TOE ONLY',1),
        ('MILITARY SETTING IS FICTION',1),('',1),('MODEL AND SOURCE',7),
        ('HTTPS://GITHUB.COM/LEWISMOTEN/FALKEN-9',1),('',1),
        ('HTTPS://HUGGINGFACE.CO/LEWISMOTEN/FALKEN-9',1),('',1),('RUNTIME BOUNDARY',7),
        ('EMULATOR-TESTED ONLY',10),('NO PHYSICAL C64 ACCEPTANCE',1),
        ('NO HOSTED INFERENCE',1),('FIXED BOARD SYMMETRIES',1),
        ('ROTATE / REFLECT / INVERSE',1),('ARE NOT LEARNED WEIGHTS',1),
        ('FROZEN MODEL: MODEL-V1.0.0',1),('ARTIFACT SLUG: FALKEN-9',1)]
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
    # Bottom black pockets, outside people/console/meter. R owns its own cell.
    letters={'R':('110','101','110','101','101'),'E':('111','100','110','100','111'),
             'P':('110','101','110','100','100'),'L':('100','100','100','100','111'),
             'A':('010','101','111','101','101'),'Y':('101','101','010','010','010'),
             'Q':('010','101','101','011','001'),'U':('101','101','101','101','111'),
             'I':('111','010','010','010','111'),'T':('111','010','010','010','010')}
    def compact(text, first_separate=False):
        rows=[''.join(letters[ch][y]+('0' if not first_separate or i==0 else '') for i,ch in enumerate(text)) for y in range(5)]
        width=(len(rows[0])+3)//4
        return [bytes([0]+[sum(int(bit)<<(6-2*x) for x,bit in enumerate(row.ljust(width*4,'0')[4*c:4*c+4])) for row in rows]+[0,0]) for c in range(width)]
    replay=compact('REPLAY',True);quit_glyphs=compact('QUIT')
    footer_cells=[24*40+c for c in range(len(replay))]+[24*40+c for c in range(36,40)]
    glyphs=replay+quit_glyphs
    for cell,glyph in zip(footer_cells,glyphs):
        r=regions['board_bitmap'];assert packed[r['offset']+cell*8:r['offset']+cell*8+8]==bytes(8)
        # Replay is an end-of-game control, never baked into active/auto art.
        packed[r['offset']+cell*8:r['offset']+cell*8+8] = glyph if cell >= 24*40+36 else bytes(8)
        for plane,value in [('screen',0xc0 if cell==24*40+36 else 0x60),('color',0)]:
            packed[regions['board_'+plane]['offset']+cell]=value
    game_footer=dict(cells=footer_cells,glyphs=[g.hex() for g in glyphs],replay_cells=footer_cells[:5],quit_cells=footer_cells[5:])
    def linear(v):return v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4
    luminances=[sum(w*linear(v/255) for w,v in zip((.2126,.7152,.0722),rgb)) for rgb in C64_PALETTE]
    assert min(range(1,16),key=luminances.__getitem__)==6
    game_footer['palette_luminance']=luminances
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
    # Reviewed selector/color ownership: gold button pixels only. Selectors are
    # explicit; row16 uses both 01 (high nibble) and 10 (low nibble).
    light_specs=[(16,c,s) for c,s in [(7,2),(8,2),(11,1),(19,2),(20,2),(27,2),(28,1),(31,2)]]
    light_specs += [(19,c,1) for c in (0,7,12,13,20,26,27,32,39)]
    light_specs += [(21,c,1) for c in (8,9,24,25,34,35,38,39)]
    activity_cells=[row*40+c for row,c,_ in light_specs]
    screen=paths['board_screen'].read_bytes()
    light_masks=[0xf0 if s==1 else 0x0f for _,_,s in light_specs]
    assert all((screen[c] & mask)==(0x70 if mask==0xf0 else 7) for c,mask in zip(activity_cells,light_masks))
    services=['* = $5500','activity_prng = $54f0','activity_phase = $785d',
              'activity_tick:','    php','    pha','    txa','    pha','    tya','    pha','    cld',
              '    inc activity_phase','    lda activity_prng','    bne +','    lda #$b7','+',
              '    lsr a','    bcc +','    eor #$b8','+','    sta activity_prng']
    for i,(c,mask) in enumerate(zip(activity_cells,light_masks)):

        services += ['    lda activity_prng',f'    and #{1<<(i%8)}','    beq +',f'    lda #{screen[c]}','    bne ++','+',
                     f'    lda #{(screen[c]&(~mask&255))|(0x90 if mask==0xf0 else 9)}','+',f'    sta ${0x400+c:04x}']
    services += ['    lda #1','    jsr audio_event','    pla','    tay','    pla','    tax','    pla','    plp','    rts','activity_reset:','    lda #0','    sta activity_phase']
    for c in activity_cells:services += [f'    lda #{screen[c]}',f'    sta ${0x400+c:04x}']
    # Fixed application ABI: mode $7853, terminal $7819. Five contiguous cells.
    # Clear stale replay pixels on every nonterminal/automatic reset, not just ink.
    assert footer_cells[:5] == list(range(24*40,24*40+5))
    replay_bitmap = 0x2000+footer_cells[0]*8
    services += ['    rts','paint_footer:','    lda $7853','    beq footer_hide_replay',
                 '    lda $7819','    beq footer_hide_replay','    cmp #4','    bcs footer_hide_replay',
                 '    ldx #39','footer_show_pixels:','    lda footer_replay_glyphs,x',
                 f'    sta ${replay_bitmap:04x},x','    dex','    bpl footer_show_pixels',
                 '    lda #$10','    sta $07c0','    lda #$c0','    bne footer_replay_ink',
                 'footer_hide_replay:','    ldx #39','    lda #0','footer_hide_pixels:',
                 f'    sta ${replay_bitmap:04x},x','    dex','    bpl footer_hide_pixels',
                 '    sta $07c0','footer_replay_ink:']
    services += [f'    sta ${0x400+c:04x}' for c in footer_cells[1:5]]
    services += ['    lda #$c0',f'    sta ${0x400+footer_cells[5]:04x}','    lda #$60']
    services += [f'    sta ${0x400+c:04x}' for c in footer_cells[6:]]
    services += ['    rts','footer_replay_glyphs:','    .byte '+','.join(map(str,b''.join(replay))),
                 '    .include "sid_audio.asm"','    .include "auto_demo.asm"','    .include "quit_capture.asm"',
                 'services_end:','.cerror * > $6000, "services overlap neural scratch"']
    (out/'services.asm').write_text('\n'.join(services)+'\n')
    notes=[round((440*2**((40+i-69)/12))*2**24/clock) for clock in (985248,1022727) for i in range(32)]
    (out/'notes.inc').write_text('note_lo: .byte '+','.join(str(v&255) for v in notes)+'\nnote_hi: .byte '+','.join(str(v>>8) for v in notes)+'\n')
    calibration=ROOT/'src/app/progress-calibration.json'
    fills=json.loads(calibration.read_text())['fills'] if calibration.exists() else [min(46,(i+1)*47//32) for i in range(32)]
    assert len(fills)==32 and fills==sorted(fills) and max(fills)<=46
    includes += ['progress_thresholds:', '    .byte '+','.join(map(str,fills))]

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
    # Replay restores only the union of mark/label footprints, never full planes.
    # Store immutable dest/value records below I/O alongside bundled artwork.
    empty_ptrs=[];empty_counts=[];empty_records=bytearray()
    for i,c in enumerate('abcdefghi'):
        values={}
        for plane,p in graphics['cells'][c]['planes'].items():
            r=regions['board_'+plane]
            for dest in p['destination_offsets']:
                values[p['destination_base']+dest]=packed[r['offset']+dest]
        label=label_records[label_ptrs[i]:label_ptrs[i]+27]
        for j in range(0,len(label),3):values[int.from_bytes(label[j:j+2],'little')]=label[j+2]
        empty_ptrs.append(0x7900+len(empty_records));empty_counts.append(len(values))
        for address,value in sorted(values.items()):empty_records+=address.to_bytes(2,'little')+bytes([value])
    assert max(empty_counts)<256
    assert len(empty_records)<=0x700, 'empty patches must remain below application'
    (out/'empty-patches.bin').write_bytes(empty_records)
    includes += ['empty_pointers:', '    .word '+','.join(map(str,empty_ptrs)),
                 'empty_counts:', '    .byte '+','.join(map(str,empty_counts))]
    assert len(compressed)<=0x3000, 'compressed artwork and patches must remain below I/O'
    (out/'runtime-graphics.bin').write_bytes(compressed)
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
    svc=subprocess.run([assembler,'--m6502','--long-branch','--case-sensitive','--nostart','-I',str(out),'-I',str(ROOT/'src/app'),'--labels='+str(out/'services.lbl'),'-o',str(out/'services.bin'),str(out/'services.asm')],capture_output=True,text=True)
    if svc.returncode:raise RuntimeError(svc.stdout+svc.stderr)
    service_labels={m[1]:int(m[2],16) for line in (out/'services.lbl').read_text().splitlines() if (m:=re.match(r'(\w+)\s*=\s*\$([0-9a-fA-F]+)',line))}
    (out/'service-labels.inc').write_text('\n'.join(f'{k} = ${v:04x}' for k,v in service_labels.items() if k!='activity_phase')+'\n')
    run=subprocess.run([assembler,'--m6502','--long-branch','--case-sensitive','--nostart','-I',str(out),'-I',str(ROOT/'src/app'),'--labels='+str(out/'app.lbl'),'--list='+str(out/'app.lst'),'-o',str(out/'app.bin'),str(out/'entry.asm')],capture_output=True,text=True)
    (out/'assembly.log').write_text(run.stdout+run.stderr)
    if run.returncode:raise RuntimeError(run.stdout+run.stderr)
    labels=dict(core['labels'])
    labels.update(service_labels)
    for line in (out/'app.lbl').read_text().splitlines():
        m=re.match(r'(\w+)\s*=\s*\$([0-9a-fA-F]+)',line)
        if m:labels[m[1]]=int(m[2],16)
    full=bytearray(0xa000+len(compressed)-0x800)
    full[:len(core_bytes)]=core_bytes
    service_bytes=(out/'services.bin').read_bytes()
    full[0x5500-0x800:0x5500-0x800+len(service_bytes)]=service_bytes
    full[0x7900-0x800:0x7900-0x800+len(empty_records)]=empty_records
    app=(out/'app.bin').read_bytes();assert labels['app_end']<=0xa000
    full[0x8000-0x800:0x8000-0x800+len(app)]=app
    full[0xa000-0x800:]=compressed
    # Entire load stays below I/O and KERNAL; reads under BASIC bank it out
    # without hiding KERNAL/IRQ vectors or Color RAM.
    stub=bytes([12,8,10,0,0x9e])+b'32768'+bytes([0,0,0])
    prg=bytearray(full[1:]);prg[:len(stub)]=stub
    path=out/(APP_STEM+'.prg');path.write_bytes(b'\x01\x08'+prg)
    (out/'combined.bin').write_bytes(full)
    info=dict(prg_path=str(path),prg_sha256=sha(path.read_bytes()),path=str(out/'combined.bin'),load=0x800,labels=labels,core=core,image_sha256=sha(full),app_code_start=0x8000,app_code_end=labels['app_end'],graphics_paths={k:str(v) for k,v in paths.items()},graphics=graphics,numeric_labels=numeric_labels,charset_codes=code,statuses=STATUSES,activity_cells=activity_cells,activity_masks=light_masks,game_footer=game_footer,
              memory_map=core['memory_map']+[dict(name='service_state',start=0x5480,end=0x5500,writable=True),dict(name='sid',start=0xd400,end=0xd419,writable=True),dict(name='irq_vector',start=0x314,end=0x316,writable=True),dict(name='raster',start=0xd011,end=0xd013,writable=True),dict(name='vic_irq',start=0xd019,end=0xd01b,writable=True),dict(name='keyboard_count',start=0xc6,end=0xc7,writable=True),dict(name='keyboard_queue',start=0x277,end=0x281,writable=True),dict(name='app_state',start=0x7800,end=0x7900,writable=True),dict(name='bitmap_or_charset',start=0x2000,end=0x4000,writable=True),dict(name='screen',start=0x400,end=0x800,writable=True),dict(name='color',start=0xd800,end=0xdc00,writable=True)])
    (out/'build.json').write_text(json.dumps(info,indent=2)+'\n')
    return info


if __name__=='__main__':print(json.dumps(build(),indent=2))
