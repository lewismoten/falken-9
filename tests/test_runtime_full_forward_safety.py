"""Additional E4-specific domain and pointer regressions (not E9 bounds)."""
import random
from test_runtime_full_forward import FOUR,four_runtime
from test_runtime_frontend import oracle,rd
from falken9.canonical_integer_export import load


def test_four_model_all54_local_vectors_and_scalar_widths():
    c=load(FOUR);m=four_runtime()
    maxima={}
    for side in range(2):
        for position in range(9):
            for occupancy in range(3):
                for name,v in [('token_occ',occupancy),('token_pos',position),('token_side',side)]:m.put(name,v,1)
                assert not m.call('token_frontend')['carry']
                expected=oracle(c,occupancy,position,side)
                for name,values in expected.items():
                    if isinstance(values,list):
                        assert [m.get(m.labels[name]+4*i,4) for i in range(8)]==values,(name,side,position,occupancy)
                        maxima[name]=max(maxima.get(name,0),max(map(abs,values)))
                    else:
                        assert m.get(name,5)==values
    assert maxima==dict(embedding=8156,normalized=6289,query=11875,key=9065,value=6775)
    assert maxima['key']<32768 and maxima['value']<32768
    assert maxima['normalized']<8388608


def test_readout_last_input_beyond_byte_offset255_is_live():
    c=load(FOUR);m=four_runtime()
    rng=random.Random(429)
    for vector in [[0]*71+[12345],[rng.randrange(-20000,20001) for _ in range(72)]]:
        for i,a in enumerate(vector):m.put(m.labels['attention_residual']+4*i,a,4)
        assert not m.call('readout_only')['carry']
        tensor=c['tensors']['readout.weight']
        expected=[rd(sum(a*b for a,b in zip(vector,w)),1<<-e)+bias for w,e,bias in zip(tensor['codes'].tolist(),tensor['exponents'],c['tensors']['readout.bias']['codes'].tolist())]
        assert [m.get(m.labels['readout_pre']+4*i,4) for i in range(8)]==expected


def test_norm2_rejects_centered_values_outside_signed16():
    m=four_runtime()
    for i,a in enumerate([100000,-100000]*4):m.put(m.labels['readout_gelu']+4*i,a,4)
    assert m.call('norm2')['carry']==1
