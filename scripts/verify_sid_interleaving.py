"""Adversarial IRQ interleavings against original numerical fixtures.

Executes the exact stock ROM IRQ prologue/epilogue in flat Py65. Device pending
bits are injected; this is NOT a VIC/CIA timing model or physical-hardware gate.
"""
from pathlib import Path
import hashlib
import json
from scripts.verify_app import AppMachine, fixture_records
from scripts.verify_graphical_stock_rom import DEFAULT_VICE_ROOT

ROM = DEFAULT_VICE_ROOT/'usr/share/vice/C64/kernal-901227-03.bin'


def verify(built, output, limit=24):
    records,_=fixture_records()
    ordered=sorted(records.values(),key=lambda r:r['canonical_index'])
    selected={}
    for row in ordered:selected.setdefault(sum(bool(v) for v in row['board']),row)
    rows=list(selected.values())
    for row in ordered[::23]:
        if row not in rows:rows.append(row)
    rows=rows[:limit]
    reports=[];rom=ROM.read_bytes()
    for n,row in enumerate(rows):
        m=AppMachine(built,audit=True);cpu=m.cpu;mem=cpu.memory;labels=m.labels
        mem[0xe000:0x10000]=rom;mem[0x314:0x316]=labels['audio_irq'].to_bytes(2,'little')
        for name,value in [('audio_enabled',1),('audio_protected',1),('audio_period',30 if n%2==0 else 36),('audio_frames',1),('audio_step',31),('audio_pending',0),('audio_sfx_left',0),('audio_cooldown',0),('audio_ntsc',n%2),('progress_active',0)]:m.put(name,value,1)
        mem[1]=0x36 if n%2 else 0x37
        for i,v in enumerate(row['board']):m.put(labels['board']+i,v,1)
        image_regions=[(a,bytes(mem[a:b])) for a,b in [(0x800,labels['code_end']),(0x4000,0x544b),(0x5500,labels['services_end']),(0x7900,0x8000),(0x8000,labels['app_end']),(0xa000,0xa000+Path(built['path']).parent.joinpath('runtime-graphics.bin').stat().st_size)]]
        real_step=cpu.step;next_irq=cpu.processorCycles+37+n*103;first=True;count=0;max_cycles=0
        def step():
            nonlocal next_irq,first,count,max_cycles
            if first:cpu.p &= ~cpu.INTERRUPT;first=False
            if cpu.processorCycles>=next_irq and not cpu.p&cpu.INTERRUPT:
                before=(cpu.pc,cpu.sp,cpu.p&~cpu.BREAK,cpu.a,cpu.x,cpu.y)
                zp=bytes(mem[:256]);port=mem[1]
                active=mem.active;mem.active=False;mem[0xd019]=int(count%3!=1);mem.active=active
                start=cpu.processorCycles;cpu.irq()
                for _ in range(2000):
                    assert cpu.pc not in (0xea31,0xea87),'KERNAL touched protected neural ZP'
                    real_step()
                    if cpu.pc==before[0]:break
                else:raise AssertionError('IRQ did not return')
                assert (cpu.pc,cpu.sp,cpu.p&~cpu.BREAK,cpu.a,cpu.x,cpu.y)==before
                assert bytes(mem[:256])==zp and mem[1]==port
                max_cycles=max(max_cycles,cpu.processorCycles-start);count+=1
                next_irq=cpu.processorCycles+16381+(n%7)*13
            return real_step()
        cpu.step=step
        execution=m.call('graphical_forward')
        for name,values in row['stages'].items():
            width=1 if name=='routes' else 4
            flat=sum(values,[]) if isinstance(values[0],list) else values
            assert [m.get(labels[name]+i*width,width) for i in range(len(flat))]==flat,(n,name)
        for address,raw in image_regions:assert bytes(mem[address:address+len(raw)])==raw
        assert count>100
        reports.append(dict(canonical_index=row['canonical_index'],board=row['board'],interruptions=count,max_irq_cycles=max_cycles,execution=execution,port=mem[1],stages_routes_logits_equal=True))
    result=dict(status='passed',scope=__doc__,prg_sha256=built['prg_sha256'],rom_sha256=hashlib.sha256(rom).hexdigest(),boards=len(reports),irq_count=sum(r['interruptions'] for r in reports),max_irq_cycles=max(r['max_irq_cycles'] for r in reports),records=reports)
    Path(output).write_text(json.dumps(result,indent=2)+'\n')
    return result

if __name__=='__main__':
    import sys
    built=json.loads(Path(sys.argv[1]).read_text())
    print(json.dumps(verify(built,sys.argv[2]),indent=2))
