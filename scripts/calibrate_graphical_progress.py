"""Measure completed resident work boundaries; no wall-time/IEC extrapolation."""
from pathlib import Path
import hashlib
import json
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.build_graphical_app import build, ROOT
from scripts.verify_app import AppMachine, fixture_records


def calibrate(output):
    built = build()
    records, hashes = fixture_records()
    # One deterministic representative of every reachable nonterminal ply.
    selected = {}
    for row in sorted(records.values(), key=lambda r:r['canonical_index']):
        selected.setdefault(sum(v != 0 for v in row['board']), row)
    measurements = []
    for ply, row in sorted(selected.items()):
        m = AppMachine(built)
        for i,v in enumerate(row['board']):m.put(m.labels['board']+i, v, 1)
        m.put('progress_active', 0, 1)
        cpu=m.cpu;cpu.pc=m.labels['graphical_forward'];cpu.sp=0xfd
        cpu.memory[0x1fe:0x200]=[0xff,1]
        cpu.p=cpu.UNUSED|cpu.INTERRUPT
        start=cpu.processorCycles;previous=start;events=[]
        while cpu.pc != 0x200:
            if cpu.pc == m.labels['progress_event']:
                events.append(cpu.processorCycles-previous);previous=cpu.processorCycles
            cpu.step()
        assert len(events)==32 and not cpu.p&cpu.CARRY
        measurements.append(dict(ply=ply,canonical_index=row['canonical_index'],board=row['board'],cycles=cpu.processorCycles-start,event_cycle_deltas=events))
    totals=[sum(row['event_cycle_deltas'][i] for row in measurements) for i in range(32)]
    denominator=sum(totals);accumulated=0;fills=[]
    for work in totals:
        accumulated+=work
        # The right outline owns the final native column. Keep an interior
        # gap as well: logical 47 would otherwise LOOK identical to full 48.
        fills.append(min(46,accumulated*47//denominator))
    result=dict(schema='resident-work-calibration-v1', scope='mean measured NMOS Py65 cycles at 32 completed semantic boundaries; one board per ply, not elapsed-time percentage; 48 reserved for visible legal commit',
                calibration_prg_sha256=built['prg_sha256'],core_sha256=built['core']['image_sha256'],
                model_sha256=built['core']['model_sha256'],fixture_sha256=hashes, fills=fills, measurements=measurements)
    Path(output).write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    result=calibrate(sys.argv[1])
    print(json.dumps({k:result[k] for k in ['scope','fills','calibration_prg_sha256']}))
