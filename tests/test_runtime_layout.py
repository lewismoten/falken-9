"""Standalone minimal-harness allocation and every-write gate."""
from test_runtime_math import runtime
from scripts.build_runtime import MODEL


class Writes(list):
    def __init__(self,values):
        super().__init__(values); self.addresses=set()
    def __setitem__(self,key,value):
        if isinstance(key,slice):
            self.addresses.update(range(*key.indices(len(self))))
        else:self.addresses.add(key)
        super().__setitem__(key,value)


def test_disjoint_live_layout_and_no_writes_to_model_code_screen():
    m=runtime()
    assert 'memory_map' in m.build, 'compiled runtime memory ledger missing'
    regions=sorted(m.build['memory_map'],key=lambda v:v['start'])
    for a,b in zip(regions,regions[1:]):assert a['end']<=b['start'],(a,b)
    assert m.build['model_bytes']==6110
    m.cpu.memory=Writes(m.cpu.memory)
    for i,v in enumerate([1,2,0,0,1,0,2,0,0]):m.put(m.labels['board']+i,v,1)
    before=bytes(m.cpu.memory)
    r=m.call('board_attention_block')
    assert not r['carry'] and not r['decimal']
    writable=[r for r in regions if r['writable']]
    unexpected=[a for a in m.cpu.memory.addresses if not any(r['start']<=a<r['end'] for r in writable)]
    assert unexpected==[]
    assert bytes(m.cpu.memory[0x4000:0x4000+6110])==MODEL.read_bytes()
    assert bytes(m.cpu.memory[0x400:0x800])==before[0x400:0x800]
