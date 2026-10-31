"""Four-expert target gates, independent arbitrary-int intermediate oracle."""
import math
from pathlib import Path
from scripts.build_runtime import ROOT, build
from scripts.verify_runtime import Machine
from falken9.canonical_integer_export import load

FOUR = ROOT/'artifacts/flexible-integer/q11-w16-a32-early-interp/model.f9j'
FOUR_SHA = 'fe180f8a931f9d92d8aa39da337bc819d0dbe4e6d971edcba00324fbc18a91c1'


def full_oracle(c, board):
    from test_runtime_attention import projection_oracle
    from test_runtime_frontend import rd
    stages = projection_oracle(c, board)
    t = c['tensors']
    prefixes = {}
    envelopes = {}
    def observe_prefix(name,products):
        total=0
        for product in products:
            total+=product
            prefixes[name]=max(prefixes.get(name,0),abs(total))
        envelopes[name]=max(envelopes.get(name,0),sum(map(abs,products)))
    for name in ['query','key','value','projection']:
        inputs=stages['attended'] if name=='projection' else stages['board_normalized']
        for x in inputs:
            for w in t[name+'.weight']['codes'].tolist():
                observe_prefix(name+'.weight',[a*b for a,b in zip(x,w)])
    for qi in stages['board_query']:
        for kj in stages['board_key']:
            products=[a*b for a,b in zip(qi,kj)]
            observe_prefix('attention.dot',products)
            observe_prefix('attention.scaled',[rd(sum(products),2048)*11585])
    for p in stages['attention_probs']:
        for lane in range(8):
            observe_prefix('attention.weighted',[g*v[lane] for g,v in zip(p,stages['board_value'])])
    for embedding in stages['board_embedding']:
        mean=rd(sum(embedding),8)
        observe_prefix('norm1.squares',[(a-mean)**2 for a in embedding])
    def linear(x, name, bias, expert=None):
        w = t[name]['codes'].tolist(); es = t[name]['exponents']
        if expert is not None:
            w = list(map(list, zip(*w[expert])))
            es = es[expert*len(w):(expert+1)*len(w)]
        y=[]
        for row,e in zip(w,es):
            total=0
            for a,b in zip(x,row):
                total+=a*b
                prefixes[name]=max(prefixes.get(name,0),abs(total))
            envelopes[name]=max(envelopes.get(name,0),sum(abs(a*b) for a,b in zip(x,row)))
            y.append(rd(total,1<<-e))
        b=t[bias]['codes'].tolist()
        if expert is not None: b=b[expert]
        return [a+b for a,b in zip(y,b)]
    def gelu(x):
        table=c['tables']['gelu']; out=[]
        for a in x:
            if a>16384: v=a
            elif a< -16384: v=0
            else:
                i,r=divmod(a+16384,64)
                v=rd(table[i]*(64-r)+table[min(512,i+1)]*r,64)
            out.append(v)
        return out
    pre=linear(sum(stages['attention_residual'],[]),'readout.weight','readout.bias')
    x=gelu(pre)
    mean=rd(sum(x),8); centered=[a-mean for a in x]
    observe_prefix("norm2.squares",[a*a for a in centered])
    variance=rd(sum(a*a for a in centered),8)+42
    root=math.isqrt(variance)
    z=[rd(rd(a*2048,root)*g,2048)+b for a,g,b in zip(centered,t['norm2.weight']['codes'].tolist(),t['norm2.bias']['codes'].tolist())]
    scores=linear(z,'router.weight','router.bias')
    routes=sorted(range(c['experts']),key=lambda i:(-scores[i],i))[:2]
    selected=[scores[i] for i in routes]; top=max(selected); ex=[]
    for a in selected:
        i,r=divmod(min(32768,top-a),64)
        table=c['tables']['exp']
        ex.append(rd(table[i]*(64-r)+table[min(i+1,512)]*r,64))
    gates=[a*32768//sum(ex) for a in ex]
    gates[selected.index(top)]+=32768-sum(gates)
    hp=[linear(z,'expert_w1','expert_b1',i) for i in routes]
    hidden=[gelu(a) for a in hp]
    experts=[linear(h,'expert_w2','expert_b2',i) for h,i in zip(hidden,routes)]
    for lane in range(8):
        observe_prefix('expert.weighted',[g*e[lane] for g,e in zip(gates,experts)])
    merged=[a+rd(sum(g*e[l] for g,e in zip(gates,experts)),32768) for l,a in enumerate(x)]
    logits=linear(merged,'output.weight','output.bias')
    stages.update(readout_pre=pre,readout_gelu=x,norm2_output=z,router_scores=scores,
                  routes=routes,gates=gates,expert_hidden_pre=hp,expert_hidden=hidden,
                  expert_outputs=experts,merged=merged,logits=logits)
    return stages,dict(prefixes=prefixes,envelopes=envelopes,norm2_centered_abs=max(map(abs,centered)),norm2_variance=variance)


def test_whole_forward_invalid_board_and_wide_merge_gates():
    from test_runtime_frontend import rd
    m=four_runtime()
    for i in range(9): m.put(m.labels['board']+i,0,1)
    m.put('board',3,1)
    assert m.call('full_forward')['carry']==1
    for gate0 in [0,1,16384,32767,32768]:
        for i in range(8):
            m.put(m.labels['expert_outputs']+4*i,277839-i*90000,4)
            m.put(m.labels['expert_outputs']+32+4*i,-277839+i*90000,4)
            m.put(m.labels['readout_gelu']+4*i,-348+i*2000,4)
        m.put('gates',gate0,4);m.put(m.labels['gates']+4,32768-gate0,4)
        assert not m.call('expert_merge')['carry']
        expected=[-348+i*2000+rd((277839-i*90000)*gate0+(-277839+i*90000)*(32768-gate0),32768) for i in range(8)]
        assert [m.get(m.labels['merged']+4*i,4) for i in range(8)]==expected
    m.put('expert_outputs',8388608,4)
    assert m.call('expert_merge')['carry']==1


def test_full_forward_varied_routes_ranges_and_write_audit():
    import json
    c=load(FOUR)
    boards=json.loads((ROOT/'artifacts/canonical-integer/verified/q11-w16-a32-early-interp/canonical-results.json').read_text())['boards']
    expected=[full_oracle(c,b)[0] for b in boards]
    indices={0}
    for expert in range(4):
        indices.add(next(i for i,s in enumerate(expected) if expert in s['routes']))
    for stage in ['readout_pre','norm2_output','merged','logits']:
        indices.add(max(range(len(boards)),key=lambda i:max(map(abs,expected[i][stage]))))
    m=Machine(build(model=FOUR,output=ROOT/'build/runtime-new/four'),audit=True)
    for index in sorted(indices):
        for i,v in enumerate(boards[index]): m.put(m.labels['board']+i,v,1)
        execution=m.call('full_forward')
        assert not execution['carry'],index
        assert execution['writes_total']>0
        assert execution['stack_low_water']>=0x180
        assert_stages(m,expected[index])
    # Bounds are enforced, not just compared after the run.
    m.cpu.memory.begin()
    import pytest
    with pytest.raises(AssertionError,match='write outside'):
        m.cpu.memory[0x4000]=0
    m.cpu.memory.active=False


def test_empty_board_complete_neural_forward_all_vectors():
    m=four_runtime()
    assert 'full_forward' in m.labels, 'assembled whole forward missing'
    board=[0]*9
    for i,v in enumerate(board): m.put(m.labels['board']+i,v,1)
    execution=m.call('full_forward')
    assert not execution['carry']
    expected,_=full_oracle(load(FOUR),board)
    assert_stages(m,expected)
    from test_canonical_integer_model import scalar_oracle
    assert expected['logits']==scalar_oracle(load(FOUR),board)[0]
    print('empty board',execution,'logits',expected['logits'],'routes',expected['routes'])


def assert_stages(m,expected):
    for name,values in expected.items():
        width=1 if name=='routes' else 4
        if isinstance(values[0],list): values=sum(values,[])
        actual=[m.get(m.labels[name]+width*i,width) for i in range(len(values))]
        assert actual==values,(name,actual,values)


def test_router_stable_top2_gates_and_board_vectors():
    m=four_runtime()
    assert 'board_router' in m.labels, 'assembled router missing'
    assert 'route_top2' in m.labels
    for scores in [[0,0,0,0],[-1,-2,-1,-3],[-2147483648,2147483647,0,-1],[4,4,5,5]]:
        for i,v in enumerate(scores): m.put(m.labels['router_scores']+4*i,v,4)
        assert not m.call('route_top2')['carry']
        assert [m.get(m.labels['routes']+i,1,False) for i in range(2)]==sorted(range(4),key=lambda i:(-scores[i],i))[:2]
    c=load(FOUR)
    for board in [[0]*9,[1,2,0,0,1,0,2,0,0],[1,2,1,2,1,2,0,0,0]]:
        for i,v in enumerate(board): m.put(m.labels['board']+i,v,1)
        assert not m.call('board_router')['carry']
        expected,_=full_oracle(c,board)
        for name,n,width in [('router_scores',4,4),('routes',2,1),('gates',2,4)]:
            assert [m.get(m.labels[name]+width*i,width) for i in range(n)]==expected[name],name


def test_readout_gelu_norm2_complete_vectors():
    m=four_runtime()
    assert 'board_norm2' in m.labels, 'assembled norm2 missing'
    c=load(FOUR)
    for board in [[0]*9,[1,2,0,0,1,0,2,0,0],[1,2,1,2,1,2,0,0,0]]:
        for i,v in enumerate(board): m.put(m.labels['board']+i,v,1)
        assert not m.call('board_norm2')['carry']
        expected,_=full_oracle(c,board)
        for name in ['readout_pre','readout_gelu','norm2_output']:
            assert [m.get(m.labels[name]+4*i,4) for i in range(8)]==expected[name],name


def test_signed_gelu_interpolation_and_tails():
    from test_runtime_frontend import rd
    m=four_runtime()
    assert 'gelu_interpolate' in m.labels, 'signed GELU missing'
    table=load(FOUR)['tables']['gelu']
    cases=[-2147483648,-16385,-16384,-16383,-2049,-2048,-1025,-1000,-65,-64,-63,-32,-1,0,1,31,32,63,64,2048,16383,16384,16385,2147483647]
    for a in cases:
        m.put('operand',a,4)
        assert not m.call('gelu_interpolate')['carry']
        i,r=divmod(max(0,min(32768,a+16384)),64)
        want=a if a>16384 else 0 if a< -16384 else rd(table[i]*(64-r)+table[min(512,i+1)]*r,64)
        assert m.get('acc',5)==want,(a,want,m.get('acc',5))


def four_runtime():
    return Machine(build(model=FOUR, output=ROOT/'build/runtime-new/four'))


def test_four_expert_build_identity_and_readout_72_inputs():
    m=four_runtime()
    assert m.build['model_sha256']==FOUR_SHA
    assert m.build['model_bytes']==5195
    assert 'board_readout' in m.labels, 'assembled flattened readout missing'
    for i,v in enumerate([0]*9): m.put(m.labels['board']+i,v,1)
    assert not m.call('board_readout')['carry']
    expected,_=full_oracle(load(FOUR),[0]*9)
    for name in ['readout_pre']:
        assert [m.get(m.labels[name]+4*i,4) for i in range(8)]==expected[name]
