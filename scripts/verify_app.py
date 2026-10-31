"""Application target gates. Frozen neural logits are TEST fixtures only."""
from pathlib import Path
import hashlib
import json
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.build_app import ROOT, build
from scripts.verify_runtime import Machine

FROZEN = ROOT/'artifacts/runtime/full-forward/q11-w16-e4'


class AppMachine(Machine):
    def call(self,name,limit=30000000):
        cpu = self.cpu
        cpu.sp=0xfd
        cpu.memory[0x1fe:0x200]=[0xff,0x01]
        cpu.pc=self.labels[name]
        cpu.p=cpu.UNUSED|cpu.DECIMAL|cpu.INTERRUPT
        before=cpu.processorCycles
        count=0
        if self.audit: cpu.memory.begin()
        while cpu.pc != 0x200:
            assert 0x800<=cpu.pc<self.labels['code_end'] or 0x8000<=cpu.pc<self.labels['app_end'], f'PC outside code ${cpu.pc:04x}'
            assert count<limit,(name,hex(cpu.pc))
            cpu.step();count+=1
        assert cpu.sp==0xff
        extra={}
        if self.audit:
            cpu.memory.active=False
            extra=dict(stack_low_water=cpu.memory.stack_low_water,writes=cpu.memory.writes_total)
        return dict(carry=int(bool(cpu.p&cpu.CARRY)),cycles=cpu.processorCycles-before,instructions=count,**extra)


def fixture_records():
    summary=json.loads((FROZEN/'summary.json').read_text())
    rows=[]
    hashes={}
    for name,expected_sha in sorted(summary['evidence_sha256'].items()):
        path=FROZEN/name
        raw=path.read_bytes();hashes[path.name]=hashlib.sha256(raw).hexdigest()
        assert hashes[path.name]==expected_sha
        rows.extend(json.loads(line) for line in raw.splitlines())
    assert len(rows)==627 and len({r['canonical_index'] for r in rows})==627
    assert summary['build']['image_sha256']=='838aa62a854aa58bd603c7525b52dc67c4c4b01ea0f50f58982475959ec61961'
    return {tuple(r['board']):r for r in rows},hashes


def verify_wrapper(output=None):
    built=build()
    m=AppMachine(built,audit=True)
    records,hashes=fixture_records()
    originals={}
    raw=(ROOT/'data/nonterminal-legal-histories.jsonl').read_bytes()
    for line in raw.splitlines():
        row=json.loads(line)
        originals.setdefault(row['board'],row)
    assert len(originals)==4520
    immutable=bytes(m.cpu.memory[0x800:built['labels']['code_end']])
    model=bytes(m.cpu.memory[0x4000:0x4000+5195])
    app_code=bytes(m.cpu.memory[0x8000:built['labels']['app_end']])
    cycles=[];low=0x200;actual_rows=[]
    from falken9.symmetry import canonicalize
    for row in originals.values():
        h=row['history']
        m.put('history_length',len(h),1)
        for i,c in enumerate(h):m.put(m.labels['history']+i,ord(c),1)
        execution=m.call('validate_history'); assert not execution['carry'],h
        low=min(low,execution['stack_low_water'])
        original=tuple(m.get(m.labels['original_board']+i,1,False) for i in range(9))
        assert original==tuple('.XO'.index(c) for c in row['board'] if c!='/')
        expected_board,expected_transform=canonicalize(original)
        execution=m.call('canonicalize_board'); assert not execution['carry'],h
        canonical=tuple(m.get(m.labels['board']+i,1,False) for i in range(9))
        assert canonical==expected_board
        assert tuple(m.get(m.labels['selected_transform']+i,1,False) for i in range(9))==expected_transform
        target=records[canonical]
        # Explicit composed proof: bypass NN ONLY IN THIS TEST fixture seam.
        # Production policy_request has no bypass and must execute full_forward.
        for i,v in enumerate(target['stages']['logits']):m.put(m.labels['logits']+4*i,v,4)
        execution=m.call('restore_set');assert not execution['carry'],h
        actual=[chr(97+i) for i in range(9) if m.get(m.labels['original_set']+i,1,False)]
        selected=chr(97+m.get('selected_move',1,False))
        assert set(actual)==set(row['optimal_moves']),(h,actual,row)
        assert selected==row['optimal_move'],(h,selected,row)
        low=min(low,execution['stack_low_water']);cycles.append(execution['cycles'])
        actual_rows.append(dict(history=h,canonical_index=target['canonical_index'],move=selected,moves=actual))
    assert bytes(m.cpu.memory[0x800:built['labels']['code_end']])==immutable
    assert bytes(m.cpu.memory[0x4000:0x4000+5195])==model
    assert bytes(m.cpu.memory[0x8000:built['labels']['app_end']])==app_code
    result=dict(status='passed',scope='4520 assembled history/canonical/full-set-inverse/legal-mask/tie wrappers composed with frozen 627 executed-target neural logits; NOT 4520 rerun neural forwards',boards=len(originals),canonical_boards=len(records),histories_in_dataset=len(raw.splitlines()),set_errors=0,move_errors=0,stack_low_water=low,code_model_immutable=True,fixture_sha256=hashes,dataset_sha256=hashlib.sha256(raw).hexdigest(),build_sha256=built['image_sha256'])
    if output:
        output=Path(output);output.mkdir(parents=True,exist_ok=True)
        (output/'wrapper-rows.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in actual_rows))
        (output/'wrapper-summary.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

class GameMachine:
    """Real packaged code with a deliberately narrow GETIN-only KERNAL shim."""
    def __init__(self,built,prg=None):
        from py65.devices.mpu6502 import MPU
        from scripts.verify_runtime import AuditedMemory
        self.build=built;self.labels=built['labels'];self.queue=[];self.neural_calls=0;self.steps=0
        regions=built['memory_map']+[
            dict(start=0x400,end=0x800,writable=True),dict(start=0xd800,end=0xdc00,writable=True),
            dict(start=0xd011,end=0xd012,writable=True),dict(start=0xd016,end=0xd017,writable=True),
            dict(start=0xd018,end=0xd019,writable=True),dict(start=0xd020,end=0xd022,writable=True),
            dict(start=0xdd00,end=0xdd01,writable=True),dict(start=0xcc,end=0xcd,writable=True),dict(start=0x800,end=0x810,writable=True)]
        memory=AuditedMemory(regions)
        self.cpu=MPU(memory=memory)
        raw=Path(built['prg_path']).read_bytes() if prg is None else prg
        assert raw[:2]==b'\x01\x08'
        assert raw[2:7]==bytes([0x0c,8,10,0,0x9e]) and raw[7:12]==b'32768'
        memory[0x801:0x801+len(raw)-2]=raw[2:]
        memory[1]=0x37
        self.cpu.pc=0x8000;self.cpu.sp=0xff
        self.cpu.p=self.cpu.UNUSED|self.cpu.DECIMAL|self.cpu.INTERRUPT
        self.booted=False;self.zp_before=None
        memory.begin()

    def get(self,name,index=0):return self.cpu.memory[self.labels[name]+index]
    def text(self,row):
        return ''.join(chr(v+64) if 1<=v<=26 else chr(v) for v in self.cpu.memory[0x400+40*row:0x400+40*(row+1)])
    def cell(self,i):return self.cpu.memory[0x400+(7+2*(i//3))*40+15+4*(i%3)]
    def color(self,i):return self.cpu.memory[0xd800+(7+2*(i//3))*40+15+4*(i%3)]

    def step(self):
        cpu=self.cpu;mem=cpu.memory;pc=cpu.pc
        if pc==0xffe4:
            # GETIN returns PETSCII with N/Z corresponding to A. Arbitrary
            # workspace clobber checks that NN restores the KERNAL ZP image.
            assert not cpu.p&cpu.INTERRUPT,'keyboard scanning must be IRQ-enabled'
            value=self.queue.pop(0) if self.queue else 0
            self.zp_before=None
            mem.active=False
            for i in range(0x20,0x80):mem[i]=(i+value)&255
            mem.active=True
            cpu.a=value;cpu.x=0x5a;cpu.y=0xa6
            cpu.FlagsNZ(cpu.a)
            cpu.pc=(cpu.stPopWord()+1)&0xffff
            return
        assert 0x800<=pc<self.labels['code_end'] or 0x8000<=pc<self.labels['app_end'],f'PC outside code ${pc:04x}'
        if pc==self.labels['neural_begin']:
            self.zp_before=bytes(mem[0x20:0x80])
        if pc==self.labels['full_forward']:
            assert cpu.p&cpu.INTERRUPT
            self.neural_calls+=1
        cpu.step();self.steps+=1

    def until_input(self,stop_at=None):
        target=self.labels['input_wait'] if stop_at is None else self.labels[stop_at]
        # At least one instruction lets key() advance from the previous wait.
        self.step()
        for _ in range(30000000):
            if self.cpu.pc==target:
                if not self.booted:
                    self.cpu.memory.allowed[0x800:0x810]=bytes(16)
                    self.booted=True
                if stop_at is None:
                    assert self.cpu.sp==0xff
                    assert self.cpu.memory[1]==0x37
                    if self.zp_before is not None:assert bytes(self.cpu.memory[0x20:0x80])==self.zp_before
                return
            self.step()
        raise AssertionError(f'input loop budget pc={self.cpu.pc:04x}')

    def key(self,key,stop_at=None):
        self.queue.append(ord(key) if isinstance(key,str) else key)
        self.until_input(stop_at)


def verify_games(output=None,prg=None):
    built=build()
    game=GameMachine(built,prg=prg);game.until_input()
    data={}
    for line in (ROOT/'data/nonterminal-legal-histories.jsonl').read_text().splitlines():
        row=json.loads(line);data.setdefault(row['board'],row)
    code=bytes(game.cpu.memory[0x800:built['labels']['code_end']])
    app_code=bytes(game.cpu.memory[0x8000:built['labels']['app_end']])
    model=bytes(game.cpu.memory[0x4000:0x4000+5195])
    records=[];outcomes=[];matches=[]
    for mode in ['optimal-human','deliberately-nonoptimal-human']:
        game.key('R');human_keys=[]
        while not game.get('terminal'):
            board=[game.get('original_board',i) for i in range(9)]
            text='/'.join(''.join('.XO'[v] for v in board[j:j+3]) for j in [0,3,6])
            gold=data[text]
            legal=[chr(97+i) for i,v in enumerate(board) if not v]
            choices=[c for c in legal if c not in gold['optimal_moves']]
            chosen=gold['optimal_move'] if mode=='optimal-human' else (choices or legal)[0]
            n=game.get('history_length');calls=game.neural_calls
            # Input only; no model data is substituted in this lifecycle gate.
            game.key(chosen.upper());human_keys.append(chosen.upper())
            after=game.get('history_length')
            assert after in [n+1,n+2]
            if after==n+2:
                prefix=''.join(chr(game.get('history',i)) for i in range(n+1))
                from falken9.policy import board_from_history
                b=board_from_history(prefix)
                t='/'.join(''.join('.XO'[v] for v in b[j:j+3]) for j in [0,3,6])
                move=chr(game.get('history',n+1))
                assert move==data[t]['optimal_move'],(prefix,move,data[t])
                assert game.neural_calls==calls+1
                records.append(dict(history=prefix,selected=move,logits=[int.from_bytes(bytes(game.cpu.memory[game.labels['logits']+4*i:game.labels['logits']+4*i+4]),'little',signed=True) for i in range(9)]))
            else:assert game.neural_calls==calls
            for i,v in enumerate([game.get('original_board',i) for i in range(9)]):
                assert game.cell(i)==(i+1 if v==0 else 24 if v==1 else 15)
                assert game.color(i)==(12 if v==0 else 10 if v==1 else 14)
        outcome=game.get('terminal');outcomes.append(outcome)
        matches.append(dict(mode=mode,human_keys=human_keys,outcome=outcome,history=''.join(chr(game.get('history',i)) for i in range(game.get('history_length')))))
        assert ('DRAW' if outcome==3 else 'O WINS' if outcome==2 else 'X WINS') in game.text(16)
        length=game.get('history_length');calls=game.neural_calls
        for c in ['A','i','!']:
            game.key(c);assert game.get('history_length')==length and game.neural_calls==calls
    assert outcomes==[3,2],outcomes
    for _ in range(16):game.key('R');assert game.get('history_length')==0
    assert bytes(game.cpu.memory[0x800:built['labels']['code_end']])==code
    assert bytes(game.cpu.memory[0x8000:built['labels']['app_end']])==app_code
    assert bytes(game.cpu.memory[0x4000:0x4000+5195])==model
    assert game.cpu.memory.stack_low_water>=0x180
    result=dict(status='passed',boundary='packaged PRG actual input loop + GETIN-only shim; every neural forward executed on NMOS6502, NOT real ROM/browser input',prg_sha256=built['prg_sha256'],matches=matches,draws=outcomes.count(3),model_wins=outcomes.count(2),executed_neural_calls=game.neural_calls,requests=records,code_model_immutable=True,stack_low_water=game.cpu.memory.stack_low_water,stack_final=game.cpu.sp,writes=game.cpu.memory.writes_total,cycles=game.cpu.processorCycles,replay_count=18,irq_disabled_during_neural=True,kernal_zp_restored=True,cpu_port_preserved=True,load_calls=0)
    if output:
        output=Path(output);output.mkdir(parents=True,exist_ok=True)
        (output/'games.json').write_text(json.dumps(result,indent=2)+'\n')
        (output/'final-screen.bin').write_bytes(bytes(game.cpu.memory[0x400:0x800]))
    return result


def verify_stock_rom(output,vice_root=None,image=None):
    """Local VICE/stock ROM only. Monitor supplies queue bytes, never logits."""
    import os
    import re
    import socket
    import subprocess
    import time
    root=Path(vice_root or os.environ['F9_VICE_ROOT'])
    rom=root/'usr/share/vice';exe=root/'usr/bin/x64'
    assert exe.exists() and (rom/'C64/kernal-901227-03.bin').exists()
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    built=build();labels=built['labels']
    seam=verify_games(output.parent/'py65')
    r,w=os.pipe()
    xlog=(output/'xvfb.log').open('w')
    xvfb=subprocess.Popen(['Xvfb','-displayfd',str(w),'-screen','0','800x600x24','-nolisten','tcp'],pass_fds=(w,),stdout=xlog,stderr=subprocess.STDOUT)
    os.close(w)
    with os.fdopen(r) as f:display=':'+f.readline().strip()
    with socket.socket() as probe:probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
    env=os.environ.copy();env['DISPLAY']=display;env['LD_LIBRARY_PATH']=str(root/'usr/lib/x86_64-linux-gnu')
    launch=Path(image) if image is not None else Path(built['prg_path'])
    is_disk=launch.suffix.lower()=='.d64'
    if is_disk:
        from scripts.build_app import extract_disk
        assert extract_disk(launch)==Path(built['prg_path']).read_bytes()
    cmd=[str(exe),'-default','-directory',str(rom),'-kernal',str(rom/'C64/kernal-901227-03.bin'),'-basic',str(rom/'C64/basic-901226-01.bin'),'-chargen',str(rom/'C64/chargen-901225-01.bin'),'+sound','-warp','-remotemonitor','-remotemonitoraddress',f'ip4://127.0.0.1:{port}']
    if is_disk:cmd+=['-drive8type','1541','-drive8truedrive','+virtualdev8']
    cmd+=['-autostart',str(launch)]
    vlog=(output/'vice.log').open('w');mlog=(output/'monitor.log').open('w')
    process=subprocess.Popen(cmd,env=env,stdout=vlog,stderr=subprocess.STDOUT)
    sock=None
    try:
        deadline=time.monotonic()+30
        while sock is None:
            try:sock=socket.create_connection(('127.0.0.1',port),timeout=.2)
            except OSError:
                assert process.poll() is None,'VICE startup exited'
                if time.monotonic()>deadline:raise TimeoutError('VICE monitor startup')
                time.sleep(.1)
        sock.settimeout(.2)
        prompt=rb'\(C:\$[0-9a-fA-F]+\)\s*$'
        def receive(timeout=120):
            data=b'';deadline=time.monotonic()+timeout;seen=False
            while time.monotonic()<deadline:
                try:
                    chunk=sock.recv(65536)
                    if not chunk:raise RuntimeError('VICE disconnected')
                    data+=chunk
                    seen=bool(re.search(prompt,data))
                except socket.timeout:
                    if seen:break
            else:raise TimeoutError(f'VICE response {data[-1000:]!r}')
            text=data.decode(errors='replace');mlog.write(text);mlog.flush()
            assert 'ERROR --' not in text,text
            return text
        def command(text,timeout=120):
            mlog.write('>>> '+text+'\n');mlog.flush();sock.sendall((text+'\n').encode());return receive(timeout)
        sock.sendall(b'\n');receive(15)
        command('sidefx off');command('delete')
        command(f"break {labels['input_wait']:04x}")
        command(f"break {labels['neural_begin']:04x}")
        command(f"break {labels['full_forward']:04x}")
        def registers():
            text=command('r');m=re.search(r'\.;([\da-fA-F]{4})\s+((?:[\da-fA-F]{2}\s+){6})',text)
            assert m,text
            return int(m[1],16),[int(x,16) for x in m[2].split()]
        def memory(address,count=1):
            text=command(f'm {address:04x} {address+count-1:04x}');result=[]
            for line in text.splitlines():
                if line.startswith('>C:'):
                    result.extend(int(x,16) for x in line[9:60].split() if re.fullmatch('[0-9a-fA-F]{2}',x))
            assert len(result)>=count,(address,count,text)
            return bytes(result[:count])
        def value(name):return memory(labels[name])[0]
        requests=0;acks=0
        def resume():
            nonlocal requests,acks
            while True:
                command('x');pc,regs=registers()
                if pc==labels['neural_begin']:
                    assert 'NEURAL FORWARD' in ''.join(chr(v+64) if 1<=v<=26 else chr(v) for v in memory(0x684,32))
                    h=memory(labels['history'],value('history_length'))
                    i=h[-1]-97
                    assert memory(0x400+(7+2*(i//3))*40+15+4*(i%3))==bytes([24])
                    assert regs[3]==255
                    acks+=1
                    continue
                if pc==labels['full_forward']:
                    requests+=1
                    continue
                assert pc==labels['input_wait'],hex(pc)
                assert regs[3]==0xff and regs[5]==0x37,regs
                assert memory(0x314,2)==bytes([0x31,0xea])
                return
        def key(c):
            command(f'> 0277 {ord(c):02x}');command('> 00c6 01');resume()
        resume()
        core=(ROOT/'build/app/core/runtime.bin').read_bytes()[:labels['code_end']-0x800]
        assert memory(0x800,len(core))==core
        assert value('history_length')==0
        key('!');assert value('history_length')==0
        observed=[];request_index=0
        for index,match in enumerate(seam['matches']):
            key('R')
            for human in match['human_keys']:
                prior=value('history_length');key(human);length=value('history_length')
                if length==prior+2:
                    expected=seam['requests'][request_index];request_index+=1
                    h=memory(labels['history'],length).decode()
                    logits=[int.from_bytes(memory(labels['logits']+4*i,4),'little',signed=True) for i in range(9)]
                    assert h[:-1]==expected['history'] and h[-1]==expected['selected']
                    assert logits==expected['logits']
                    observed.append(dict(history=h[:-1],selected=h[-1],logits=logits))
            assert value('terminal')==match['outcome']
            assert memory(labels['history'],value('history_length')).decode()==match['history']
            # Render at least one VIC frame before screenshot, while preserving
            # all normal code/ROM execution. Disable only observation breakpoints.
            for n in [1,2,3]:command(f'disable {n}')
            command('step $10000')
            command(f'screenshot "{output/("draw" if index==0 else "model-win")}.png" 2')
            for n in [1,2,3]:command(f'enable {n}')
            resume()
            before=value('history_length');key('A');assert value('history_length')==before
        key('R');assert value('history_length')==0
        assert memory(0x800,len(core))==core
        assert memory(0x4000,5195)==FOUR_MODEL_BYTES()
        assert requests==acks==len(observed)==7
        result=dict(status='passed',boundary='VICE x64 stock C64 ROM with genuine IRQ/GETIN, monitor-injected keyboard queue; NOT physical/browser input',prg_autostart=not is_disk,d64_true_drive_autostart=is_disk,launch_sha256=hashlib.sha256(launch.read_bytes()).hexdigest(),prg_sha256=built['prg_sha256'],draws=1,model_wins=1,requests=requests,immediate_human_acks=acks,full_logits_equal_to_py65=True,stack_final=255,cpu_port=55,irq_vector_unchanged=True,code_model_immutable=True,marks=observed,command=cmd,rom_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [rom/'C64/kernal-901227-03.bin',rom/'C64/basic-901226-01.bin',rom/'C64/chargen-901225-01.bin']})
        (output/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
        return result
    finally:
        if sock is not None:sock.close()
        if process.poll() is None:
            process.terminate()
            try:process.wait(5)
            except subprocess.TimeoutExpired:process.kill();process.wait()
        xvfb.terminate();xvfb.wait();xlog.close();vlog.close();mlog.close()


def FOUR_MODEL_BYTES():
    from scripts.build_runtime import FOUR_MODEL
    return FOUR_MODEL.read_bytes()


def verify_release(output=None,vice_root=None):
    import shutil
    from scripts.build_app import package_disk,extract_disk
    output=Path(output) if output is not None else ROOT/'artifacts/app/001-resident'
    output.mkdir(parents=True,exist_ok=True)
    built=build()
    wrapper=verify_wrapper(output/'wrapper')
    games=verify_games(output/'py65')
    disk=package_disk(built,games)
    # Same bytes extracted from the finished disk complete BOTH live NN games.
    extracted_games=verify_games(output/'extracted-prg',prg=extract_disk(disk['path']))
    if vice_root:
        verify_stock_rom(output/'vice',vice_root)
        verify_stock_rom(output/'vice-d64',vice_root,image=disk['path'])
    rom_evidence={}
    for name in ['vice','vice-d64']:
        path=output/name/'summary.json'
        if path.exists():
            record=json.loads(path.read_text())
            assert record['prg_sha256']==built['prg_sha256'],'stale ROM evidence'
            if name=='vice-d64':assert record['launch_sha256']==disk['sha256']
            rom_evidence[name]=dict(path=str(path.relative_to(ROOT)),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),requests=record['requests'],status=record['status'])
    for path in [Path(built['prg_path']),Path(disk['path']),ROOT/'build/app/build.json',ROOT/'build/app/app.lbl',ROOT/'build/app/app.lst',ROOT/'build/app/app.bin',ROOT/'build/app/core/runtime.bin',ROOT/'build/app/core/runtime.lbl']:
        target=output/path.name
        if target.exists() and path.suffix in ['.prg','.d64','.bin']:
            assert target.read_bytes()==path.read_bytes(),'numbered artifact already frozen; choose a new number'
        shutil.copy2(path,target)
    sources=output/'sources';sources.mkdir(exist_ok=True)
    paths=list((ROOT/'src/app').glob('*.asm'))+[ROOT/'scripts/build_app.py',ROOT/'scripts/verify_app.py',ROOT/'docs/APP.md']+list((ROOT/'tests').glob('test_app*.py'))
    source_hashes={}
    for path in paths:
        target=sources/path.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
        source_hashes[str(path.relative_to(ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest()
    summary=dict(status='assembled-wrapper-and-resident-game-passed',artifact=dict(prg=str((output/Path(built['prg_path']).name).relative_to(ROOT)),prg_sha256=built['prg_sha256'],prg_bytes=Path(built['prg_path']).stat().st_size,d64=str((output/Path(disk['path']).name).relative_to(ROOT)),d64_sha256=disk['sha256']),wrapper=wrapper,games={k:v for k,v in games.items() if k!='requests'},disk=disk,extracted_prg_complete_games=extracted_games['status'],stock_rom=rom_evidence,model_sha256=built['core']['model_sha256'],core_image_sha256=built['core']['image_sha256'],app_code_start=built['app_code_start'],app_code_end=built['app_code_end'],source_sha256=source_hashes,browser_tested=False,physical_hardware_tested=False,published=False,remaining=['target-browser launch and physical-keyboard acceptance','physical C64 acceptance','fine-grained layer progress: current honest full-forward busy phase only','optional AI-vs-AI/title mode not implemented'])
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    (ROOT/'results/app-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    return summary


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'artifacts/app/001-resident')
    parser.add_argument('--vice-root',type=Path)
    args=parser.parse_args()
    print(json.dumps(verify_release(args.output,args.vice_root),indent=2))
