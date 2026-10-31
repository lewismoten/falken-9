"""Front-end gate covers every local occupancy/absolute-position/side input."""
import math
from test_runtime_math import runtime
from falken9.canonical_integer_export import load
from scripts.build_runtime import MODEL


def rd(a,b): return (1 if a>=0 else -1)*((abs(a)+b//2)//b)


def oracle(c,occ,pos,side):
    t={n:v['codes'].tolist() for n,v in c['tensors'].items()}
    x=[a+b+d for a,b,d in zip(t['occupancy.weight'][occ],t['position'][pos],t['side.weight'][side])]
    mean=rd(sum(x),8); centered=[a-mean for a in x]
    var=rd(sum(a*a for a in centered),8)+42; root=math.isqrt(var)
    z=[rd(rd(a*2048,root)*g,2048)+b for a,g,b in zip(centered,t['norm1.weight'],t['norm1.bias'])]
    result=dict(embedding=x,normalized=z,mean=mean,variance=var,norm_root=root)
    for n in ['query','key','value']:
        result[n]=[rd(sum(a*b for a,b in zip(z,row)),1<<-e) for row,e in zip(t[n+'.weight'],c['tensors'][n+'.weight']['exponents'])]
    return result


def test_all_54_local_inputs_execute_embedding_norm_qkv_from_resident_model():
    m=runtime()
    assert 'token_frontend' in m.labels, 'assembled neural front end missing'
    c=load(MODEL)
    for occ in range(3):
        for pos in range(9):
            for side in range(2):
                m.put('token_occ',occ,1);m.put('token_pos',pos,1);m.put('token_side',side,1)
                result=m.call('token_frontend')
                assert result['carry']==0,(occ,pos,side)
                expected=oracle(c,occ,pos,side)
                for n,values in expected.items():
                    actual=([m.get(m.labels[n]+4*i,4) for i in range(8)] if isinstance(values,list) else m.get(n,5))
                    assert actual==values,(occ,pos,side,n,actual,values)
                raw=MODEL.read_bytes()
                assert bytes(m.cpu.memory[0x4000:0x4000+len(raw)])==raw
    m.put('token_occ',3,1)
    assert m.call('token_frontend')['carry']==1
