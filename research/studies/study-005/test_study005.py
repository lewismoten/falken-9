"""Independent study005 tests: scalar oracles, indexing, saved evidence recount."""
import json,itertools,hashlib
from pathlib import Path
import numpy as np
import torch
import pytest
from study005_core import apportion,masks,relocate_mass,Attention005,candidate_labels,Q15
from falken9.flexible_integer_export import load
from falken9.strategy_diagnostics import DiagnosticPolicy
from scripts.build_runtime import FOUR_MODEL
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'artifacts/interpretability/study-005-final'

def scalar_apportion(w,n):
    w=list(map(int,w))
    if not sum(w):w=[1]*len(w)
    den=sum(w);q=[x*n//den for x in w];remainder=[x*n%den for x in w]
    for j in sorted(range(len(w)),key=lambda j:(-remainder[j],j))[:n-sum(q)]:q[j]+=1
    return q

def test_apportion_zero_and_leftovers005():
    assert apportion([0,0,0],5).tolist()==[2,2,1]
    assert apportion([1,1,1],2).tolist()==[1,1,0]
    assert apportion([3,1,0],3).tolist()==[2,1,0]
    for w in itertools.product(range(3),repeat=3):
        for n in range(12):assert apportion(w,n).tolist()==scalar_apportion(w,n)
    with pytest.raises(ValueError):apportion([],1)
    with pytest.raises(ValueError):apportion([-1],1)

def test_edges_inactive_identity_query_key_and_mass005():
    m,c=masks(((0,1,2),));assert set(np.flatnonzero(m[0]))=={1,2};assert set(np.flatnonzero(m[1]))=={0,2};assert not m[3:].any()
    assert np.array_equal(m.sum(1),c.sum(1)) and not (m&c).any()
    p=np.array([[apportion(np.arange(1,10)+q,Q15) for q in range(9)]])
    a,ma=relocate_mass(p,m,c,'target',2);b,mb=relocate_mass(p,m,c,'control',2)
    assert np.array_equal(ma,mb) and np.array_equal(a[:,3:],p[:,3:])
    assert a[0,0,1]<p[0,0,1] and a[0,1,0]<p[0,1,0]
    assert np.all(a.sum(-1)==Q15) and np.all(b.sum(-1)==Q15)
    # Full scalar oracle with independently implemented allocation.
    for q in range(9):
        src=np.flatnonzero(m[q]).tolist();dst=np.flatnonzero(~m[q]).tolist();budget=min(sum(int(p[0,q,k]) for k in src),sum(int(p[0,q,k]) for k in np.flatnonzero(c[q])))
        expected=p[0,q].copy()
        if budget:
            for k,x in zip(src,scalar_apportion(p[0,q,src],budget)):expected[k]-=x
            for k,x in zip(dst,scalar_apportion(p[0,q,dst],budget)):expected[k]+=x
        assert np.array_equal(a[0,q],expected)
    identity=np.tile(np.eye(9,dtype=np.int64)*Q15,(2,1,1));z,budget=relocate_mass(identity,m,c,'target',2)
    assert np.array_equal(z,identity) and not budget.any()
    # Zero complement weights exercises redistribution fallback without row-sum loss.
    p2=np.zeros((1,9,9),dtype=np.int64);p2[:,:,0]=Q15
    z,budget=relocate_mass(p2,m,c,'control',1);assert np.all(z.sum(-1)==Q15) and np.all(z>=0)

def independent_labels(board,s,mark):
    if board[s]:return False
    after=list(board);after[s]=mark
    rows=[after[i:i+3] for i in (0,3,6)]+[[after[c],after[c+3],after[c+6]] for c in range(3)]+[[after[0],after[4],after[8]],[after[2],after[4],after[6]]]
    return any(row==[mark]*3 for row in rows)

def test_candidate_labels_and_raw_alignment005():
    cases=json.loads((OUT/'baseline-vectors005.json').read_text());boards=cases['boards'];lab=cases['candidate_labels'];legal={tuple(r['raw_board']) for r in json.loads((OUT/'raw-alignment005.json').read_text())}
    for i,b in enumerate(boards):
        side=1+sum(x!=0 for x in b)%2
        for s in range(9):
            assert lab[i][s]['win']==independent_labels(b,s,side)
            assert lab[i][s]['threat']==independent_labels(b,s,3-side)
    pairs=json.loads((OUT/'matched-relocations005.json').read_text())
    p=np.array(cases['stages']['attention_probs']);q=np.array(cases['stages']['board_value'])
    for r in pairs:
        a=r['receiver_raw'];b=r['donor_raw'];t=r['donor_raw_to_canonical'];cb=boards[r['donor']]
        assert tuple(a) in legal and tuple(b) in legal and sum(x!=y for x,y in zip(a,b))==2
        assert sorted(a)==sorted(b) and a[r['candidate']]==b[r['candidate']]==0
        assert all(b[k]==cb[t[k]] for k in range(9))
        assert r['donor_candidate']==t[r['candidate']]
        if r is pairs[0]:
            for x in range(9):
                for k in range(9):assert p[r['donor']][np.ix_(t,t)][x,k]==p[r['donor'],t[x],t[k]]
        assert lab[r['receiver']][r['candidate']][r['task']] and not lab[r['donor']][r['donor_candidate']][r['task']]

def test_identity_full_stages_and_value_attention005():
    torch.set_num_threads(1);c=load(FOUR_MODEL);boards=torch.tensor([[0]*9,[0,0,0,0,1,0,0,0,0]],dtype=torch.int64)
    base=DiagnosticPolicy(c);y=base(boards);q=Attention005(c);yy=q(boards)
    assert torch.equal(yy,y)
    for k in base.stages:assert torch.equal(base.stages[k],q.stages[k])
    identity=Attention005(c,mode='identity');identity(boards)
    assert torch.equal(identity.stages['attended'],identity.stages['board_value'])
    # Original parameter tensors on caller's candidate remain byte-identical.
    for k in c['tensors']:assert torch.equal(c['tensors'][k]['codes'],q.c['tensors'][k]['codes'])

def test_fullset_wrapper_independent_recount005():
    cases=json.loads((OUT/'baseline-vectors005.json').read_text());rs=json.loads((OUT/'interventions005.json').read_text());vectors=json.loads((OUT/'intervention-vectors005.json').read_text());raw=json.loads((OUT/'raw-alignment005.json').read_text());priority=[4,1,3,5,7,2,6,8,0];baseline=cases['stages']['logits']
    assert len(vectors)==len(rs)==19
    for r,vec in zip(rs,vectors):
        assert r['id']==vec['id'];empty=bad=sets=moves=ties=0
        for rr in raw:
            board=rr['raw_board'];i=rr['canonical_id'];t=rr['raw_to_canonical'];members={s for s in range(9) if board[s]==0 and vec['logits'][i][t[s]]>=0};move=next((s for s in priority if s in members),-1)
            empty+=not members;bad+=move not in rr['optimal'];sets+=members!=set(rr['optimal']);moves+=move!=rr['move'];ties+=(move!=rr['move'] and move in rr['optimal'])
        assert (empty,bad,sets,moves,ties)==tuple(r['raw'][k] for k in ('empty','move_errors','set_changes','move_changes','optimal_tie_changes'))
        p=np.array(vec['effective_attention_probs']);assert np.all(p>=0) and np.all(p.sum(-1)==Q15)
        routes=np.array(vec['routes']);br=np.array(cases['stages']['routes']);assert int((routes!=br).any(1).sum())==r['route_order_changes']

def test_preservation_and_manifest005():
    from study005_run import prior,sha
    assert len(prior())==120
    m=json.loads((ROOT/'experiment-study005.json').read_text());assert m['intervention_count']==19
    for n,h in m['source_sha256'].items():assert sha(ROOT/n)==h
    assert (ROOT/'experiment-study005.json').read_bytes()==(OUT/'experiment-manifest005.json').read_bytes()
