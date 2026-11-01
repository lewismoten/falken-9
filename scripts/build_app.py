"""Build an app against the pinned, byte-identical accepted neural core."""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.build_runtime import ROOT, FOUR_MODEL, build as build_runtime

OUT = ROOT/'build/app'
APP_STAGE = '002-numeric'
APP_STEM = f'falken9-{APP_STAGE}'


def build(output=None):
    out = OUT if output is None else Path(output)
    out.mkdir(parents=True, exist_ok=True)
    core = build_runtime(model=FOUR_MODEL, output=out/'core')
    assert core['image_sha256'] == '838aa62a854aa58bd603c7525b52dc67c4c4b01ea0f50f58982475959ec61961'
    (out/'core-labels.inc').write_text('\n'.join(f'{k} = ${v:04x}' for k,v in core['labels'].items())+'\n')
    core_bytes = (out/'core/runtime.bin').read_bytes()
    (out/'core-backup.bin').write_bytes(core_bytes[:16])
    def codes(text):
        return bytes(ord(c)-64 if 'A'<=c<='Z' else ord(c) for c in text)
    screen = bytearray([32]*1024)
    def row(y,text):
        assert len(text)<=40
        x=(40-len(text))//2
        screen[y*40+x:y*40+x+len(text)]=codes(text)
    row(2,'FALKEN-9 / RESIDENT NEURAL TIC-TAC-TOE')
    row(4,'YOU: X     MODEL: O')
    for y,text in [(7,'1   2   3'),(8,'---------'),(9,'4   5   6'),(10,'---------'),(11,'7   8   9')]:row(y,text)
    row(20,'1-9: MOVE     R: REPLAY')
    row(22,'ALL MODEL WEIGHTS STAY IN RAM')
    (out/'screen.bin').write_bytes(screen)
    statuses=['YOUR TURN - 1 TO 9','INVALID / OCCUPIED - TRY 1-9','NEURAL FORWARD - PLEASE WAIT','NEURAL DONE - COMMITTING MOVE','X WINS - R TO REPLAY','O WINS - R TO REPLAY','DRAW - R TO REPLAY','NEURAL ERROR - R TO REPLAY']
    (out/'statuses.bin').write_bytes(b''.join(codes(s.ljust(32)) for s in statuses))
    assembler = os.environ.get('TASS64', str(ROOT/'build/tools/64tass/usr/bin/64tass'))
    run = subprocess.run([assembler,'--m6502','--long-branch','--case-sensitive','--nostart','-I',str(out),'--labels='+str(out/'app.lbl'),'--list='+str(out/'app.lst'),'-o',str(out/'app.bin'),str(ROOT/'src/app/app.asm')],capture_output=True,text=True)
    (out/'assembly.log').write_text(run.stdout+run.stderr)
    if run.returncode: raise RuntimeError(run.stdout+run.stderr)
    labels = dict(core['labels'])
    for line in (out/'app.lbl').read_text().splitlines():
        match = re.match(r'(\w+)\s*=\s*\$([0-9a-fA-F]+)',line)
        if match: labels[match[1]] = int(match[2],16)
    image = bytearray((out/'app.bin').read_bytes())
    start = 0x800
    full = bytearray(labels['app_end']-start)
    core_bytes = (out/'core/runtime.bin').read_bytes()
    full[:len(core_bytes)] = core_bytes
    full[0x8000-start:0x8000-start+len(image)] = image
    (out/'combined.bin').write_bytes(full)
    # Standard BASIC line 10 SYS32768, terminating next-line link.
    stub = bytes([0x0c,0x08,10,0,0x9e])+b'32768'+bytes([0,0,0])
    prg = bytearray(full[1:])
    prg[:len(stub)] = stub
    prg_path=out/f'{APP_STEM}.prg'
    prg_path.write_bytes(bytes([1,8])+prg)
    info = dict(prg_path=str(prg_path),prg_sha256=hashlib.sha256(prg_path.read_bytes()).hexdigest(),path=str(out/'combined.bin'),load=start,labels=labels,core=core,
                image_sha256=hashlib.sha256(full).hexdigest(),
                memory_map=core['memory_map']+[dict(name='app_state',start=0x7800,end=0x7900,writable=True)],
                app_code_start=0x8000,app_code_end=labels['app_end'])
    (out/'build.json').write_text(json.dumps(info,indent=2)+'\n')
    return info

def disk_geometry():
    counts=[0]+[21]*17+[19]*7+[18]*6+[17]*5
    offsets={};at=0
    for track in range(1,36):
        for sector in range(counts[track]):offsets[track,sector]=at;at+=256
    assert at==174848
    return counts,offsets


def extract_disk(path):
    raw=Path(path).read_bytes();counts,offsets=disk_geometry()
    assert len(raw)==174848
    entry=offsets[18,1]+2
    assert raw[entry]==0x82
    track,sector=raw[entry+1:entry+3]
    visited={(18,0),(18,1)};chunks=[];blocks=0
    while track:
        assert (track,sector) in offsets and track!=18 and (track,sector) not in visited
        visited.add((track,sector));blocks+=1
        at=offsets[track,sector];nt,ns=raw[at:at+2]
        chunks.append(raw[at+2:at+256] if nt else raw[at+2:at+1+ns])
        track,sector=nt,ns
    assert blocks==int.from_bytes(raw[entry+28:entry+30],'little')
    bam=offsets[18,0]
    used=set()
    for track in range(1,36):
        at=bam+4*track;free=0
        for sector in range(counts[track]):
            available=bool(raw[at+1+sector//8]&(1<<(sector%8)))
            if available:free+=1
            else:used.add((track,sector))
        assert free==raw[at]
    assert used==visited,'BAM has unreachable allocations'
    return b''.join(chunks)


def package_disk(built,gate,output=None,*,stem=APP_STEM,title='FALKEN9 NUMERIC'):
    """Only package an exact PRG which has passed complete live NN games."""
    prg=Path(built['prg_path']).read_bytes()
    assert gate['status']=='passed' and gate['prg_sha256']==hashlib.sha256(prg).hexdigest()
    assert gate['draws']>=1 and gate['model_wins']>=1 and gate['executed_neural_calls']>=7
    assert re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*',stem),'unsafe disk filename'
    assert re.fullmatch(r'[A-Z0-9 -]{1,16}',title),'unsafe disk title'
    output=OUT if output is None else Path(output);output.mkdir(parents=True,exist_ok=True)
    counts,offsets=disk_geometry();disk=bytearray(174848)
    order=[17,19,16,20,15,21,14,22,13,23,12,24,11,25,10,26,9,27,8,28,7,29,6,30,5,31,4,32,3,33,2,34,1,35]
    available=[(t,s) for t in order for s in range(counts[t])]
    chunks=[prg[i:i+254] for i in range(0,len(prg),254)]
    chain=available[:len(chunks)];used={(18,0),(18,1),*chain}
    for index,chunk in enumerate(chunks):
        at=offsets[chain[index]]
        disk[at:at+2]=bytes(chain[index+1] if index+1<len(chain) else (0,len(chunk)+1))
        disk[at+2:at+2+len(chunk)]=chunk
    directory=offsets[18,1];disk[directory:directory+2]=bytes([0,255])
    entry=directory+2;disk[entry:entry+3]=bytes([0x82,*chain[0]])
    disk[entry+3:entry+19]=b'FALKEN9'.ljust(16,b'\xa0')
    disk[entry+28:entry+30]=len(chain).to_bytes(2,'little')
    bam=offsets[18,0];disk[bam:bam+4]=bytes([18,1,0x41,0])
    for track in range(1,36):
        at=bam+4*track
        for sector in range(counts[track]):
            if (track,sector) not in used:
                disk[at]+=1;disk[at+1+sector//8]|=1<<(sector%8)
    disk[bam+0x90:bam+0xa0]=title.encode('ascii').ljust(16,b'\xa0')
    disk[bam+0xa0:bam+0xab]=b'\xa0\xa0F9\xa02A\xa0\xa0\xa0\xa0'
    path=output/f'{stem}.d64';path.write_bytes(disk)
    assert extract_disk(path)==prg
    if path.resolve().is_relative_to(ROOT):
        assert subprocess.run(['git','check-ignore','-q',str(path)],cwd=ROOT).returncode==0,'generated D64 must be ignored'
    result=dict(path=str(path),sha256=hashlib.sha256(disk).hexdigest(),prg_sha256=hashlib.sha256(prg).hexdigest(),blocks=len(chain),bytes=len(disk),extracted_identical=True,bam_reachability_verified=True)
    (output/'disk.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__ == '__main__': print(json.dumps(build(),indent=2))
