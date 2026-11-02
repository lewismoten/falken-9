"""Assembled graphics gates. GETIN queue shim is not browser/ROM evidence."""
from pathlib import Path
import hashlib
import json
from scripts.build_graphical_app import build, ROOT
from scripts.verify_runtime import AuditedMemory
from py65.devices.mpu6502 import MPU


class GraphicalMachine:
    def __init__(self,built,prg=None):
        self.build=built;self.labels=built['labels'];self.queue=[];self.neural_calls=0;self.steps=0;self.phases=[]
        regions=built['memory_map']+[
            dict(start=1,end=2,writable=True),dict(start=0xf7,end=0xff,writable=True),
            dict(start=0xd011,end=0xd012,writable=True),dict(start=0xd016,end=0xd019,writable=True),
            dict(start=0xd020,end=0xd022,writable=True),dict(start=0xdd00,end=0xdd01,writable=True),
            dict(start=0xcc,end=0xcd,writable=True),dict(start=0x800,end=0x810,writable=True)]
        regions += [dict(start=0x5480,end=0x5500,writable=True)]
        mem=AuditedMemory(regions);self.cpu=MPU(memory=mem)
        raw=Path(built['prg_path']).read_bytes() if prg is None else prg
        start=int.from_bytes(raw[:2],'little');assert start==0x801
        mem[start:start+len(raw)-2]=raw[2:]
        mem[1]=0x37;mem[0xc6]=0;self.cpu.sp=255;self.cpu.pc=0x8000
        self.cpu.p=self.cpu.UNUSED|self.cpu.INTERRUPT|self.cpu.DECIMAL
        self.original_core=(Path(built['path']).parent/'core/runtime.bin').read_bytes()[:self.labels['code_end']-0x800]
        self.original_model=bytes(mem[0x4000:0x4000+5195])
        self.original_app=bytes(mem[0x8000:self.labels['app_end']])
        self.original_art=bytes(mem[0xa000:start+len(raw)-2])
        self.booted=False;self.zp_before=None
        mem.begin()

    def get(self,name,index=0): return self.cpu.memory[self.labels[name]+index]
    def text(self,row):
        decode={v:k for k,v in self.build['charset_codes'].items()}
        return ''.join(decode.get(v,'?') for v in self.cpu.memory[0x400+row*40:0x400+(row+1)*40])
    def status_text(self):return self.build['statuses'][self.get('status_index')]
    def planes(self):return tuple(bytes(self.cpu.memory[a:a+n]) for a,n in [(0x400,1000),(0xd800,1000)])
    def immutable_intact(self):
        mem=self.cpu.memory
        return (bytes(mem[0x800:self.labels['code_end']])==self.original_core and bytes(mem[0x4000:0x4000+5195])==self.original_model and bytes(mem[0x8000:self.labels['app_end']])==self.original_app and bytes(mem[0xa000:0xa000+len(self.original_art)])==self.original_art)
    def expected_board_planes_match(self):
        packed=Path(self.build['path']).parent.joinpath('graphics.bin').read_bytes()
        regions=self.build['graphics']['regions']
        expected={}
        for plane,name in [('bitmap','board_bitmap'),('screen','board_screen'),('color','board_color')]:
            r=regions[name];expected[plane]=bytearray(packed[r['offset']:r['offset']+r['length']])
        for i,c in enumerate('abcdefghi'):
            mark=self.get('original_board',i)
            if not mark:
                label=self.build['numeric_labels'][i]
                cell=label['cell']
                expected['bitmap'][cell*8:cell*8+8]=bytes.fromhex(label['glyph_hex'])
                expected['screen'][cell]=label['screen_value']
                continue
            for plane,p in self.build['graphics']['cells'][c]['planes'].items():
                r=regions[p['values']['x' if mark==1 else 'o']]
                for j,d in enumerate(p['destination_offsets']):expected[plane][d]=packed[r['offset']+j]
        # All board rows through y111: native marks and grid, before UI footer.
        return (bytes(self.cpu.memory[0x2000:0x2000+14*320])==expected['bitmap'][:14*320] and bytes(self.cpu.memory[0x400:0x400+14*40])==expected['screen'][:14*40] and bytes(self.cpu.memory[0xd800:0xd800+14*40])==expected['color'][:14*40])

    def step(self):
        cpu=self.cpu;mem=cpu.memory;pc=cpu.pc
        if pc==0xffe4:
            assert not cpu.p&cpu.INTERRUPT
            self.zp_before=None
            value=self.queue.pop(0) if self.queue else 0
            mem.active=False
            for i in range(0x20,0x80):mem[i]=(i+value)&255
            mem.active=True
            cpu.a=value;cpu.x=0x5a;cpu.y=0xa6;cpu.FlagsNZ(value)
            cpu.pc=(cpu.stPopWord()+1)&65535
            return
        assert 0x800<=pc<self.labels['code_end'] or 0x5500<=pc<self.labels['services_end'] or 0x8000<=pc<self.labels['app_end'],f'PC outside code ${pc:04x}'
        if pc==self.labels['neural_begin']:self.zp_before=bytes(mem[0x20:0x80]);self.neural_calls+=1
        if 'activity_tick' in self.labels and pc==self.labels['activity_tick']:self.phases.append(self.get('activity_phase'))
        cpu.step();self.steps+=1
    def until_input(self,stop_at=None):
        target=self.labels['input_wait'] if stop_at is None else self.labels[stop_at]
        self.step()
        for _ in range(60000000):
            if self.cpu.pc==target:
                if not self.booted:
                    self.cpu.memory.allowed[0x800:0x810]=bytes(16);self.booted=True
                if stop_at is None:
                    assert self.cpu.sp==255
                    assert self.cpu.memory[1]==0x37
                    if self.zp_before is not None:assert bytes(self.cpu.memory[0x20:0x80])==self.zp_before
                return
            self.step()
        raise AssertionError(f'input loop budget pc={self.cpu.pc:04x}')
    def key(self,key,stop_at=None):
        self.queue.append(ord(key) if isinstance(key,str) else key);self.until_input(stop_at)


def verify_games(built,output,prg=None):
    from scripts.verify_app import fixture_records
    from falken9.symmetry import canonicalize
    fixtures,_=fixture_records()
    game=GraphicalMachine(built,prg);game.until_input()
    title=game.planes();requests=[];matches=[]
    game.key('I');assert game.get('view')==1
    game.key('Q');assert game.planes()==title
    for keys,outcome in [('52497',3),('124',2)]:
        game.key('1');assert game.get('mode')==1
        for key in keys:
            prior=game.get('history_length');calls=game.neural_calls
            game.key(key,stop_at='neural_begin' if not (outcome==3 and key==keys[-1]) else None)
            if game.cpu.pc==game.labels['neural_begin']:
                assert game.get('history_length')==prior+1
                assert game.expected_board_planes_match()
                assert game.status_text()=='NEURAL FORWARD - WAIT'
                original=tuple(game.get('original_board',i) for i in range(9))
                canonical,transform=canonicalize(original)
                gold=fixtures[canonical]
                game.until_input()
                logits=[int.from_bytes(bytes(game.cpu.memory[game.labels['logits']+4*i:game.labels['logits']+4*i+4]),'little',signed=True) for i in range(9)]
                assert logits==gold['stages']['logits']
                choices={i for i in range(9) if not original[i] and logits[transform[i]]>=0}
                chosen=next(i for i in [4,1,3,5,7,2,6,8,0] if i in choices)
                assert game.get('selected_move')==chosen and game.get('move_result')==chosen+1
                requests.append(dict(history=''.join(chr(game.get('history',i)) for i in range(prior+1)),selected=chr(97+chosen),logits=logits,canonical_index=gold['canonical_index']))
                assert game.neural_calls==calls+1
            assert game.expected_board_planes_match()
            length=game.get('history_length');calls=game.neural_calls
            for invalid in [key,'0','!']:
                game.key(invalid)
                assert game.get('history_length')==length and game.neural_calls==calls and game.get('move_result')==0
        assert game.get('terminal')==outcome
        matches.append(dict(human_keys=list(keys),outcome=outcome,history=''.join(chr(game.get('history',i)) for i in range(game.get('history_length')))))
        game.key('R');assert game.get('history_length')==0
        game.key('Q');assert game.get('view')==0 and game.planes()==title
        game.key('I');game.key('Q');assert game.planes()==title
    two=[]
    for keys,outcome in [('14253',1),('152347',2),('532846917',3)]:
        game.key('2');before=game.neural_calls
        for key in keys:game.key(key)
        assert game.get('terminal')==outcome,(keys,game.get('terminal'))
        assert game.neural_calls==before and game.expected_board_planes_match()
        two.append(outcome);game.key('Q');assert game.get('view')==0
    before=game.neural_calls;game.key('0')
    assert game.get('terminal')==3 and game.get('history_length')==9
    auto_calls=game.neural_calls-before
    assert auto_calls==9 and game.expected_board_planes_match()
    auto_history=''.join(chr(game.get('history',i)) for i in range(9))
    game.key('Q');game.key('I');game.key('Q')
    for _ in range(8):game.key('2');game.key('R');game.key('Q')
    assert game.immutable_intact()
    assert game.get('activity_phase')==0
    result=dict(status='passed',boundary='packaged input-loop NMOS Py65 + GETIN-only queue shim; NOT stock ROM/browser/physical keys',prg_sha256=built['prg_sha256'],matches=matches,requests=requests,human_model_outcomes=[m['outcome'] for m in matches],two_human_outcomes=two,auto_outcome=3,auto_neural_calls=auto_calls,auto_history=auto_history,executed_neural_calls=game.neural_calls,draws=1,model_wins=1,code_model_art_immutable=True,kernal_zp_restored=True,cpu_port_preserved=True,stack_final=game.cpu.sp,stack_low_water=game.cpu.memory.stack_low_water,activity_ticks=len(game.phases),board_planes_exact=True)
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    (output/'games.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def _parity_shard(task):
    from scripts.verify_app import AppMachine
    built, rows, output, shard = task
    m=AppMachine(built,audit=True)
    immutable=[(a,bytes(m.cpu.memory[a:b])) for a,b in [(0x800,m.labels['code_end']),(0x4000,0x4000+5195),(0x8000,m.labels['app_end']),(0xa000,0xa000+Path(built['path']).parent.joinpath('runtime-graphics.bin').stat().st_size)]]
    allowed=set()
    for region in built['core']['memory_map']:
        if region['writable']:allowed.update(range(region['start'],region['end']))
    allowed.update([m.labels['activity_phase'],m.labels['packet_value'],*(0x400+c for c in built['activity_cells'])])
    allowed.update([m.labels['activity_prng'],m.labels['audio_pending']])
    allowed.update(range(m.labels['progress_active'],m.labels['progress_pattern']+1))
    meter_cells=[0x63e+i for i in range(13) if i!=5]
    allowed.update(meter_cells)
    allowed.update(0x2000+(a-0x400)*8+i for a in meter_cells for i in range(8))
    path=Path(output)/f'shard-{shard}.jsonl'
    with path.open('w') as stream:
        for count,row in enumerate(rows,1):
            m.put('activity_phase',0,1)
            m.put('progress_active',1,1)
            m.put('progress_event_index',0,1)
            m.put('progress_filled',0,1)
            m.put('progress_color',0x20 if sum(v!=0 for v in row['board'])%2==0 else 0x60,1)
            for i,v in enumerate(row['board']):m.put(m.labels['board']+i,v,1)
            result=m.call('graphical_forward')
            assert result['carry']==0 and not m.cpu.p&m.cpu.DECIMAL
            assert m.get('progress_event_index',1,False)==32
            assert m.get('progress_filled',1,False)==46
            assert m.cpu.memory.addresses <= allowed, sorted(m.cpu.memory.addresses-allowed)
            actual={}
            for name,values in row['stages'].items():
                width=1 if name=='routes' else 4
                flat=sum(values,[]) if isinstance(values[0],list) else values
                got=[m.get(m.labels[name]+i*width,width) for i in range(len(flat))]
                assert got==flat,(row['canonical_index'],name,got,flat)
                actual[name]=got
            for address,raw in immutable:assert bytes(m.cpu.memory[address:address+len(raw)])==raw
            record=dict(canonical_index=row['canonical_index'],board=row['board'],execution=result,stages=actual,activity_ticks=m.get('activity_phase',1,False))
            assert record['activity_ticks']>=18
            stream.write(json.dumps(record)+'\n');stream.flush()
            if count%32==0:print(json.dumps(dict(shard=shard,completed=count,total=len(rows))),flush=True)
    return str(path)


def verify_parity(built,output,workers=4,limit=627):
    import concurrent.futures
    from scripts.verify_app import fixture_records
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    fixtures,hashes=fixture_records()
    rows=sorted(fixtures.values(),key=lambda r:r['canonical_index'])[:limit]
    assert 1<=workers<=8 and 1<=limit<=627
    tasks=[(built,rows[i::workers],str(output),i) for i in range(workers)]
    if workers==1:paths=[_parity_shard(tasks[0])]
    else:
        with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:paths=list(pool.map(_parity_shard,tasks))
    collected=[json.loads(line) for p in paths for line in Path(p).read_text().splitlines()]
    collected.sort(key=lambda r:r['canonical_index'])
    assert [r['canonical_index'] for r in collected]==list(range(limit))
    summary=dict(status='passed',scope='relocated presentation orchestration vs frozen original whole-forward checkpoints; every saved intermediate/logit/route',boards=limit,full_domain=limit==627,prg_sha256=built['prg_sha256'],core_sha256=built['core']['image_sha256'],model_sha256=built['core']['model_sha256'],stage_mismatches=0,code_model_art_immutable=True,callback_writes_restricted=True,fixture_sha256=hashes,evidence_sha256={Path(p).name:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths},minimum_activity_ticks=min(r['activity_ticks'] for r in collected),stack_low_water=min(r['execution']['stack_low_water'] for r in collected))
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    return summary


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--parity',action='store_true')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--workers',type=int,default=4)
    parser.add_argument('--limit',type=int,default=627)
    args=parser.parse_args()
    if args.parity:print(json.dumps(verify_parity(build(),args.output,args.workers,args.limit),indent=2))
