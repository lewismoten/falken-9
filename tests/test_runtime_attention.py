"""Whole-board assembled attention from resident parameters, not injected QKV."""
import random
from test_runtime_math import runtime
from test_runtime_frontend import oracle,rd
from falken9.canonical_integer_export import load
from scripts.build_runtime import MODEL


def attention_oracle(c,board):
    side=sum(a!=0 for a in board)%2
    local=[oracle(c,a,i,side) for i,a in enumerate(board)]
    q=[a['query'] for a in local];k=[a['key'] for a in local];v=[a['value'] for a in local]
    scores=[[rd(rd(sum(a*b for a,b in zip(qi,kj)),2048)*11585,32768) for kj in k] for qi in q]
    probabilities=[];attended=[]
    table=c['tables']['exp']
    for row in scores:
        maximum=max(row);ex=[]
        for a in row:
            i,r=divmod(min(32768,maximum-a),64)
            ex.append(rd(table[i]*(64-r)+table[min(i+1,512)]*r,64))
        total=sum(ex);p=[a*32768//total for a in ex]
        p[row.index(maximum)]+=32768-sum(p)
        probabilities.append(p)
        attended.append([rd(sum(pj*vj[l] for pj,vj in zip(p,v)),32768) for l in range(8)])
    return dict(board_embedding=[a['embedding'] for a in local],board_normalized=[a['normalized'] for a in local],board_query=q,board_key=k,board_value=v,attention_scores=scores,attention_probs=probabilities,attended=attended)


def projection_oracle(c,board):
    expected=attention_oracle(c,board)
    t=c['tensors']['projection.weight']; w=t['codes'].tolist()
    projected=[[rd(sum(a*b for a,b in zip(row,wr)),1<<-e) for wr,e in zip(w,t['exponents'])] for row in expected['attended']]
    residual=[[a+b for a,b in zip(x,p)] for x,p in zip(expected['board_embedding'],projected)]
    expected.update(projected=projected,attention_residual=residual)
    return expected


def test_whole_board_frontend_attention_matches_independent_scalar():
    m=runtime()
    assert 'board_attention' in m.labels, 'whole board attention missing'
    c=load(MODEL)
    rng=random.Random(123)
    boards=[[0]*9,[1,2,0,0,1,0,2,0,0],[1,2,1,2,1,2,0,0,0]]+[[rng.randrange(3) for _ in range(9)] for _ in range(5)]
    for board in boards:
        for i,v in enumerate(board):m.put(m.labels['board']+i,v,1)
        result=m.call('board_attention')
        assert result['carry']==0,board
        for n,rows in attention_oracle(c,board).items():
            actual=[[m.get(m.labels[n]+4*(i*len(rows[0])+j),4) for j in range(len(rows[0]))] for i in range(9)]
            assert actual==rows,(board,n,actual,rows)
        assert bytes(m.cpu.memory[0x4000:0x4000+6110])==MODEL.read_bytes()


def test_attention_projection_residual_from_board_entry():
    m=runtime()
    assert 'board_attention_block' in m.labels, 'attention projection/residual missing'
    c=load(MODEL)
    for board in [[0]*9,[1,2,0,0,1,0,2,0,0],[1,2,1,2,1,2,0,0,0]]:
        for i,v in enumerate(board):m.put(m.labels['board']+i,v,1)
        assert not m.call('board_attention_block')['carry']
        for n,rows in projection_oracle(c,board).items():
            actual=[[m.get(m.labels[n]+4*(i*len(rows[0])+j),4) for j in range(len(rows[0]))] for i in range(9)]
            assert actual==rows,(board,n)
