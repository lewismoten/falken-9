"""Py65 target execution; no host callbacks or input-specific generated tensors."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from py65.devices.mpu6502 import MPU


class Machine:
    def __init__(self, build):
        self.build = build
        self.labels = build['labels']
        self.cpu = MPU(memory=[0xa5]*65536)
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
        while cpu.pc != 0x0200:
            if count >= limit: raise RuntimeError(f'{name} instruction budget PC={cpu.pc:04x}')
            cpu.step(); count += 1
        assert cpu.sp == 0xff
        return dict(carry=int(bool(cpu.p & cpu.CARRY)),decimal=int(bool(cpu.p & cpu.DECIMAL)),
                    cycles=cpu.processorCycles-before,instructions=count)


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


if __name__=='__main__':
    import argparse
    import json
    from scripts.build_runtime import ROOT
    parser=argparse.ArgumentParser()
    parser.add_argument('--canonical-limit',type=int,default=64)
    parser.add_argument('--output',default=str(ROOT/'artifacts/runtime/verified'))
    parser.add_argument('--summary',default=str(ROOT/'results/runtime-summary.json'))
    args=parser.parse_args()
    summary=verify(args.canonical_limit,args.output)
    Path(args.summary).write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({k:summary[k] for k in ['status','canonical_boards_checked','stage_mismatches','full_forward_accepted','cycles']},indent=2))
