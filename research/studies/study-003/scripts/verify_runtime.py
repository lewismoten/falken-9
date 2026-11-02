"""Py65 target execution; no host callbacks or input-specific generated tensors."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from py65.devices.mpu6502 import MPU


class AuditedMemory(list):
    """Observe every emulator-visible CPU write; not physical bus cycles."""
    def __init__(self, memory_map):
        super().__init__([0xa5]*65536)
        self.allowed = bytearray(65536)
        for region in memory_map:
            if region['writable']:
                self.allowed[region['start']:region['end']] = bytes([1])*(region['end']-region['start'])
        self.active=False

    def begin(self):
        self.writes_total=0
        self.addresses=set()
        self.stack_low_water=0x200
        self.active=True

    def __setitem__(self, at, value):
        if self.active:
            assert isinstance(at,int), 'CPU unexpectedly wrote a slice'
            assert self.allowed[at], f'write outside writable arena: ${at:04x}'
            self.writes_total+=1
            self.addresses.add(at)
            if 0x100<=at<0x200: self.stack_low_water=min(self.stack_low_water,at)
        super().__setitem__(at,value)


class Machine:
    def __init__(self, build, audit=False):
        self.build = build
        self.labels = build['labels']
        self.audit=audit
        self.cpu = MPU(memory=AuditedMemory(build['memory_map']) if audit else [0xa5]*65536)
        image = Path(build['path']).read_bytes()
        self.cpu.memory[build['load']:build['load']+len(image)] = image

    def put(self,name,value,width):
        at = self.labels[name] if isinstance(name,str) else name
        value %= 1 << (width*8)
        self.cpu.memory[at:at+width] = value.to_bytes(width,'little')

    def get(self,name,width,signed=True):
        at = self.labels[name] if isinstance(name,str) else name
        return int.from_bytes(bytes(self.cpu.memory[at:at+width]),'little',signed=signed)

    def call(self,name,limit=30000000):
        cpu = self.cpu
        # Simulated caller JSR frame returns to $0200; not a ROM shim.
        cpu.sp = 0xfd
        cpu.memory[0x1fe:0x200] = [0xff,0x01]
        cpu.pc = self.labels[name]
        cpu.p = cpu.UNUSED | cpu.DECIMAL | cpu.INTERRUPT
        before = cpu.processorCycles
        count = 0
        if self.audit: cpu.memory.begin()
        while cpu.pc != 0x0200:
            if self.audit:
                assert self.build['load']<=cpu.pc<self.labels['code_end'], f'PC outside assembled code: {cpu.pc:04x}'
            if count >= limit: raise RuntimeError(f'{name} instruction budget PC={cpu.pc:04x}')
            cpu.step(); count += 1
        assert cpu.sp == 0xff
        extra={}
        if self.audit:
            cpu.memory.active=False
            extra=dict(writes_total=cpu.memory.writes_total,distinct_write_addresses=len(cpu.memory.addresses),
                       stack_low_water=cpu.memory.stack_low_water)
        return dict(carry=int(bool(cpu.p & cpu.CARRY)),decimal=int(bool(cpu.p & cpu.DECIMAL)),
                    cycles=cpu.processorCycles-before,instructions=count,**extra)


def verify(canonical_limit=64,output=None):
    """Bounded real-board block gate, independent scalar reference from tests."""
    import hashlib
    import json
    import random
    import shutil
    import torch
    from scripts.build_runtime import build,ROOT,MODEL
    from falken9.canonical_integer_export import load
    sys.path.insert(0,str(ROOT/'tests'))
    from test_runtime_attention import projection_oracle
    torch.set_num_threads(2)
    output=Path(output) if output is not None else ROOT/'artifacts/runtime/verified'
    output.mkdir(parents=True,exist_ok=True)
    built=build(); machine=Machine(built); candidate=load(MODEL)
    canonical_path=MODEL.parent/'canonical-results.json'
    source=canonical_path.read_bytes()
    boards=json.loads(source)['boards']
    if not 1<=canonical_limit<=len(boards):raise ValueError('canonical limit outside available boards')
    indices=sorted([0]+random.Random(61).sample(range(1,len(boards)),canonical_limit-1))
    records=[];cycles=[]
    model=MODEL.read_bytes()
    for index in indices:
        board=boards[index]
        for i,v in enumerate(board):machine.put(machine.labels['board']+i,v,1)
        execution=machine.call('board_attention_block')
        expected=projection_oracle(candidate,board)
        stages={}
        for name,rows in expected.items():
            actual=[[machine.get(machine.labels[name]+4*(i*len(rows[0])+j),4) for j in range(len(rows[0]))] for i in range(9)]
            stages[name]=actual
            if actual!=rows or execution['carry']:
                failure=dict(index=index,board=board,stage=name,actual=actual,expected=rows,execution=execution)
                (output/'counterexample.json').write_text(json.dumps(failure,indent=2)+'\n')
                raise AssertionError(f'target mismatch board {index} stage {name}')
        assert bytes(machine.cpu.memory[0x4000:0x4000+6110])==model
        records.append(dict(canonical_index=index,board=board,execution=execution,stages=stages))
        cycles.append(execution['cycles'])
        if len(records)%8==0:
            (output/'checkpoints.json').write_text(json.dumps(records,indent=2)+'\n')
    payload=(json.dumps(records,indent=2)+'\n').encode()
    (output/'checkpoints.json').write_bytes(payload)
    for name in ['runtime.bin','runtime.lbl','runtime.lst','build.json','model.inc','assembly.log']:
        shutil.copy2(ROOT/'build/runtime'/name,output/name)
    sources=output/'sources';sources.mkdir(exist_ok=True)
    for path in (ROOT/'src/runtime').glob('*.asm'):shutil.copy2(path,sources/path.name)
    summary=dict(status='verified-assembled-attention-block-only',full_forward_accepted=False,
        canonical_boards_checked=len(records),canonical_boards_available=len(boards),canonical_indices=indices,
        stage_mismatches=0,model_resident_unchanged=True,neural_stages=list(records[0]['stages']),
        remaining_stages=['flattened readout','GELU','norm2','stable top-2 router and gates','both selected expert MLPs','expert merge/residual','32-bit output scores','history/symmetry/set-selection wrapper','C64 UI/launch/game lifecycle'],
        cycles=dict(minimum=min(cycles),maximum=max(cycles),mean=sum(cycles)/len(cycles)),
        timing_scope='NMOS Py65 entry through RTS, no caller JSR/IRQ/VIC/ROM/disk/wall-time claims',
        checkpoints_sha256=hashlib.sha256(payload).hexdigest(),canonical_source_sha256=hashlib.sha256(source).hexdigest(),
        build=built,
        static_bounds=dict(embedding_abs=11478,centered_abs=22956,norm1_square_sum=8*22956**2,
            local_qkv_abs_exhaustive54=11272,attention_dot_abs=8*11272**2,
            attention_probability_sum=32768,attention_weighted_abs=32768*11272,
            projection_dot_abs=8*11272*30689,
            signed40_max=(1<<39)-1,mac_operand_abs_limit=(1<<23)-1),
        exclusions=['no policy lookup','no native host inference callbacks','no generated input-specific intermediates','no local-feature fusion table','no PRG or D64 or whole-model/game acceptance'])
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    return summary


def _full_shard(task):
    """One bounded CPU worker, real instruction execution and durable rows."""
    import hashlib
    import json
    import torch
    from scripts.build_runtime import ROOT
    from falken9.canonical_integer_export import load
    sys.path.insert(0,str(ROOT/'tests'))
    from test_runtime_full_forward import full_oracle,assert_stages
    from test_canonical_integer_model import scalar_oracle
    torch.set_num_threads(1)
    built,model_path,boards,indices,output,shard=task
    c=load(model_path)
    m=Machine(built,audit=True)
    immutable_code=bytes(m.cpu.memory[built['load']:built['labels']['code_end']])
    immutable_model=Path(model_path).read_bytes()
    path=Path(output)/f'shard-{shard}.jsonl'
    with path.open('w') as stream:
        for done,index in enumerate(indices,1):
            board=boards[index]
            for i,v in enumerate(board):m.put(m.labels['board']+i,v,1)
            execution=m.call('full_forward')
            expected,bounds=full_oracle(c,board)
            try:
                assert execution['carry']==execution['decimal']==0
                assert_stages(m,expected)
                logits,routes=scalar_oracle(c,board)
                assert expected['logits']==logits and expected['routes']==routes
                assert bytes(m.cpu.memory[built['load']:built['labels']['code_end']])==immutable_code
                assert bytes(m.cpu.memory[0x4000:0x4000+len(immutable_model)])==immutable_model
                assert execution['stack_low_water']>=0x180
            except AssertionError:
                (Path(output)/f'counterexample-{index}.json').write_text(json.dumps(dict(index=index,board=board,execution=execution,expected=expected),indent=2))
                raise
            stream.write(json.dumps(dict(canonical_index=index,board=board,execution=execution,stages=expected,bounds=bounds))+'\n')
            stream.flush()
            if done%8==0 or done==len(indices):print(json.dumps(dict(shard=shard,checked=done,total=len(indices),last_index=index)),flush=True)
    return str(path)


def _full_policy_gate(records,source):
    """Host symmetry expansion using only executed target logits, no inference."""
    import torch
    from scripts.build_runtime import ROOT
    from falken9.canonical_training import load_data
    from falken9.symmetry import restore_moves
    torch.set_num_threads(1)
    data=load_data(ROOT/'data/nonterminal-legal-histories.jsonl')
    assert data['canonical_boards'].tolist()==source['boards']
    masks=[]
    for r in records:
        masks.append([chr(97+i) for i,v in enumerate(r['stages']['logits']) if r['board'][i]==0 and v>=0])
    canonical_errors=sum(set(m)!=set(chr(97+i) for i,v in enumerate(target) if v) for m,target in zip(masks,data['targets'].tolist()))
    board_set_errors=[];board_move_errors=[]
    for ci,transform,expected_set,expected_move in zip(data['board_canonical_indices'],data['transforms'],data['sets'],data['labels']):
        restored=restore_moves(masks[ci],transform)
        board_set_errors.append(set(restored)!=set(expected_set))
        board_move_errors.append(not restored or restored[0]!=expected_move)
    history_set_errors=sum(board_set_errors[i] for i in data['history_indices'].tolist())
    history_move_errors=sum(board_move_errors[i] for i in data['history_indices'].tolist())
    result=dict(canonical_set_errors=canonical_errors,board_count=len(board_move_errors),history_count=len(data['histories']),
        board_set_errors=sum(board_set_errors),board_move_errors=sum(board_move_errors),history_set_errors=history_set_errors,
        history_move_errors=history_move_errors,dataset_sha256=data['dataset_sha256'],
        scope='target canonical logits; host-only symmetry inverse/full-set/original-coordinate tie expansion; wrapper NOT assembled')
    assert canonical_errors==sum(board_set_errors)==sum(board_move_errors)==history_set_errors==history_move_errors==0,result
    return result


def full_safety_audit(output):
    """Recompute E4-only finite-domain ceilings from executed checkpoint rows."""
    import hashlib
    import json
    from scripts.build_runtime import ROOT,FOUR_MODEL,FOUR_SHA
    from falken9.canonical_integer_export import load
    sys.path.insert(0,str(ROOT/'tests'))
    from test_runtime_frontend import oracle
    output=Path(output)
    rows=[json.loads(line) for path in sorted(output.glob('shard-*.jsonl')) for line in path.read_text().splitlines()]
    assert rows
    c=load(FOUR_MODEL)
    assert hashlib.sha256(FOUR_MODEL.read_bytes()).hexdigest()==FOUR_SHA
    def flatten(values):
        return [a for value in values for a in (flatten(value) if isinstance(value,list) else [value])]
    maxima={name:max(abs(a) for row in rows for a in flatten(row['stages'][name])) for name in rows[0]['stages']}
    inputs={'query.weight':('board_normalized',8),'key.weight':('board_normalized',8),
        'value.weight':('board_normalized',8),'projection.weight':('attended',8),
        'readout.weight':('attention_residual',72),'router.weight':('norm2_output',8),
        'expert_w1':('norm2_output',8),'expert_w2':('expert_hidden',4),'output.weight':('merged',8)}
    envelopes={name:maxima[stage]*int(c['tensors'][name]['codes'].abs().max())*fan for name,(stage,fan) in inputs.items()}
    local=[oracle(c,a,i,s) for a in range(3) for i in range(9) for s in range(2)]
    local_max={name:max(abs(a) for row in local for a in row[name]) for name in ['embedding','normalized','query','key','value']}
    centered=max(abs(a-row['mean']) for row in local for a in row['embedding'])
    contracts=['falken9/canonical_integer_export.py','falken9/integer_export.py','falken9/canonical_integer.py','falken9/integer_model.py']
    audit=dict(image_sha256=hashlib.sha256((output/'image/runtime.bin').read_bytes()).hexdigest(),
        canonical_count=len(rows),stage_maximum_abs=maxima,local54_maximum_abs=local_max,
        local54_centered_abs=centered,coarse_matrix_envelopes=envelopes,
        coarse_matrix_signed_bits={name:value.bit_length()+1 for name,value in envelopes.items()},
        norm2_centered_abs=max(row['bounds']['norm2_centered_abs'] for row in rows),
        signed40_positive_limit=(1<<39)-1,mac_operand_abs_limit=(1<<23)-1,
        decoder_and_host_contract_sha256={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in contracts})
    assert max(envelopes.values())<1<<39
    assert max(maxima.values())<8388608
    assert centered<=32767 and audit['norm2_centered_abs']<=32767
    assert local_max['key']<=32767 and local_max['value']<=32767
    (output/'safety-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    return audit


def verify_full(canonical_limit=627,workers=4,output=None):
    import concurrent.futures
    import hashlib
    import json
    import shutil
    from scripts.build_runtime import build,ROOT,FOUR_MODEL,FOUR_SHA
    if not 1<=workers<=4:raise ValueError('workers must be 1..4')
    output=Path(output) if output is not None else ROOT/'artifacts/runtime/full-forward/q11-w16-e4'
    frozen=(ROOT/'artifacts/runtime/verified').resolve()
    if output.resolve()==frozen or frozen in output.resolve().parents:raise ValueError('immutable earlier evidence')
    output.mkdir(parents=True,exist_ok=True)
    canonical_path=FOUR_MODEL.parent/'canonical-results.json'
    source=json.loads(canonical_path.read_text());boards=source['boards']
    if not 1<=canonical_limit<=len(boards):raise ValueError('canonical limit outside available boards')
    built=build(model=FOUR_MODEL,output=ROOT/'build/runtime-new/four')
    snapshot=output/'image';snapshot.mkdir(exist_ok=True)
    for filename in ['runtime.bin','runtime.lbl','runtime.lst','build.json','model.inc','model.f9j','assembly.log']:
        shutil.copy2(ROOT/'build/runtime-new/four'/filename,snapshot/filename)
    built['path']=str(snapshot/'runtime.bin')
    sources=output/'sources';sources.mkdir(exist_ok=True)
    for path in (ROOT/'src/runtime').glob('*.asm'):shutil.copy2(path,sources/path.name)
    for path in [Path(__file__),ROOT/'scripts/build_runtime.py',ROOT/'tests/test_runtime_full_forward.py',ROOT/'tests/test_runtime_attention.py',ROOT/'tests/test_runtime_frontend.py',ROOT/'tests/test_canonical_integer_model.py']:
        shutil.copy2(path,sources/path.name)
    workers=min(workers,canonical_limit)
    tasks=[(built,str(snapshot/'model.f9j'),boards,list(range(shard,canonical_limit,workers)),str(output),shard) for shard in range(workers)]
    if workers==1:paths=[_full_shard(tasks[0])]
    else:
        with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:paths=list(pool.map(_full_shard,tasks))
    records=[]
    for path in paths:
        records.extend(json.loads(line) for line in Path(path).read_text().splitlines())
    records.sort(key=lambda r:r['canonical_index'])
    assert [r['canonical_index'] for r in records]==list(range(canonical_limit))
    cycles=[r['execution']['cycles'] for r in records]
    prefixes={};envelopes={};usage=[0]*4
    for r in records:
        for key in ['prefixes','envelopes']:
            dest=prefixes if key=='prefixes' else envelopes
            for name,value in r['bounds'][key].items():dest[name]=max(dest.get(name,0),value)
        for expert in r['stages']['routes']:usage[expert]+=1
    assert max(prefixes.values())<1<<39 and max(envelopes.values())<1<<39
    accepted=canonical_limit==len(boards)==627
    policy=_full_policy_gate(records,source) if accepted else None
    summary=dict(status='verified-assembled-full-neural-forward' if accepted else 'verified-bounded-full-neural-forward',
        full_forward_accepted=accepted,canonical_boards_checked=len(records),canonical_boards_available=len(boards),
        stage_mismatches=0,scalar_logit_mismatches=0,scalar_route_mismatches=0,route_usage=usage,
        safety_audit=full_safety_audit(output),
        cycles=dict(minimum=min(cycles),maximum=max(cycles),mean=sum(cycles)/len(cycles)),
        memory_writes_total=sum(r['execution']['writes_total'] for r in records),
        stack_low_water=min(r['execution']['stack_low_water'] for r in records),model_and_code_immutable=True,
        memory_audit='every Py65 CPU write checked, including stack; no physical NMOS dummy-bus-write claim',
        prefixes=prefixes,prefix_absolute_product_envelopes=envelopes,
        prefix_proof='arbitrary-int ordered dot prefixes and sum-absolute-product envelopes on every checked board; mac40 runtime overflow guards',
        norm2_centered_abs=max(r['bounds']['norm2_centered_abs'] for r in records),
        policy=policy,build=built,model_sha256=FOUR_SHA,
        evidence_sha256={Path(path).name:hashlib.sha256(Path(path).read_bytes()).hexdigest() for path in paths},
        canonical_source_sha256=hashlib.sha256(canonical_path.read_bytes()).hexdigest(),
        source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sources.iterdir()},
        timing_scope='NMOS Py65 full_forward through RTS; CPU cycles only; no wall-time/IRQ/VIC/ROM/disk claims',
        remaining=['assembled symmetry/history/set-selection wrapper','C64 application and interactive lifecycle','physical/browser/hardware acceptance'],
        published=False)
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    return summary


if __name__=='__main__':
    import argparse
    import json
    from scripts.build_runtime import ROOT
    parser=argparse.ArgumentParser()
    parser.add_argument('--full-forward',action='store_true')
    parser.add_argument('--workers',type=int,default=4)
    parser.add_argument('--canonical-limit',type=int,default=64)
    parser.add_argument('--output',default=str(ROOT/'artifacts/runtime/verified'))
    parser.add_argument('--summary',default=str(ROOT/'results/runtime-summary.json'))
    args=parser.parse_args()
    if args.full_forward:
        if Path(args.output).resolve()==(ROOT/'artifacts/runtime/verified').resolve():
            args.output=str(ROOT/'artifacts/runtime/full-forward/q11-w16-e4')
        summary=verify_full(args.canonical_limit,args.workers,args.output)
    else: summary=verify(args.canonical_limit,args.output)
    Path(args.summary).write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({k:summary[k] for k in ['status','canonical_boards_checked','stage_mismatches','full_forward_accepted','cycles']},indent=2))
