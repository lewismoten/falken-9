"""Measure exact-final-executable cancel checkpoint gaps, without IRQs.

Full-domain flat CPU gap measurement is separate from native VIC/CIA/XTest
latency. It is not a host or physical-key bound and omits raster/bus stealing.
"""
import json
from pathlib import Path
import concurrent.futures
from scripts.verify_app import AppMachine, fixture_records

def shard(task):
    built,rows,output,index=task
    m=AppMachine(built,audit=False);cpu=m.cpu;original_step=cpu.step
    points={v:k for k,v in m.labels.items() if k.startswith('quit_continue_')}
    last=[0,'entry'];gaps=[]
    def step():
        if cpu.pc in points:
            now=cpu.processorCycles
            gaps.append(dict(cycles=now-last[0],from_boundary=last[1],to_boundary=points[cpu.pc]))
            last[:]=[now,points[cpu.pc]]
        original_step()
    cpu.step=step
    records=[]
    for row in rows:
        for i,value in enumerate(row['board']):m.put(m.labels['board']+i,value,1)
        gaps.clear();last[:]=[cpu.processorCycles,'entry']
        result=m.call('graphical_forward');assert result['carry']==0
        records.append(dict(canonical_index=row['canonical_index'],board=row['board'],max_gap=max(gaps,key=lambda x:x['cycles']),checkpoint_visits=len(gaps),total_cycles=result['cycles']))
    p=Path(output)/f'shard-{index}.json';p.write_text(json.dumps(records,indent=2)+'\n');return records

def verify(built,output,workers=4):
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    fixtures,_=fixture_records();rows=sorted(fixtures.values(),key=lambda r:r['canonical_index'])
    tasks=[(built,rows[i::workers],str(out),i) for i in range(workers)]
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:records=sum(pool.map(shard,tasks),[])
    records.sort(key=lambda r:r['canonical_index']);assert [r['canonical_index'] for r in records]==list(range(627))
    worst=max(records,key=lambda r:r['max_gap']['cycles'])
    result=dict(status='passed',prg_sha256=built['prg_sha256'],canonical_boards=627,worst=worst,scope='No-IRQ Py65 processor-cycle gap between actual generated cancellation checkpoints over all 627 canonical forwards. IRQ/stock-ROM/VIC and host key dispatch measured separately; not a physical wall-time bound.')
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n');return result

if __name__=='__main__':
    import sys
    b=json.loads(Path(sys.argv[1]).read_text());print(json.dumps(verify(b,sys.argv[2]),indent=2))
