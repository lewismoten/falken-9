"""Independent row/expert indexing and immutable-copy checks for study003."""
import copy
import numpy as np
import pytest
import torch
from falken9.strategy_diagnostics import DiagnosticPolicy
from falken9.strategy_patching import PatchPolicy, donor_values
from falken9.flexible_integer_export import load
from scripts.build_runtime import FOUR_MODEL
from scripts.verify_app import fixture_records


def fixture():
    torch.set_num_threads(1)
    rows=sorted(fixture_records()[0].values(),key=lambda r:r['canonical_index'])
    b=torch.tensor([r['board'] for r in rows])
    c=load(FOUR_MODEL);p=DiagnosticPolicy(c);y=p(b)
    return b,c,p,y


def test_donor_alignment_reversed_batch_and_inactive_rejection():
    # Unique values make row, expert and unit swaps independently observable.
    bank=np.arange(6*4*4,dtype=np.int64).reshape(6,4,4)+100
    routes=np.array([[0,1],[2,1],[1,3],[3,0],[2,0],[3,2]])
    ids=np.array([2,0,1,-1,-1,-1])
    values=donor_values(bank,routes,ids,1,3)
    assert values[:3]==[bank[2,1,3],bank[0,1,3],bank[1,1,3]]
    assert values[3] is None
    with pytest.raises(ValueError):donor_values(bank,routes,np.array([3,-1,-1,-1,-1,-1]),1,3)
    with pytest.raises(ValueError):donor_values(bank,routes,np.array([-1,-1,-1,0,-1,-1]),1,3)


def test_identity_and_actual_patch_are_indexed_by_global_receiver_rows():
    b,c,p,y=fixture();bank=p.stages['expert_hidden'].numpy();routes=p.stages['routes'].numpy()
    identity=[dict(expert=e,unit=u,values=[int(bank[i,e,u]) if e in routes[i] else None for i in range(len(b))]) for e in range(4) for u in range(4)]
    q=PatchPolicy(c,patches=identity);assert torch.equal(q(b),y)
    for name in p.stages:assert torch.equal(p.stages[name],q.stages[name]),name
    e,u=1,0;active=np.flatnonzero((routes==e).any(1))
    # Deliberately reversed/noncontiguous global receivers, not expert-local row IDs.
    targets=[int(active[-1]),int(active[2]),int(active[0])]
    vals=[None]*len(b)
    for n,i in enumerate(targets):vals[i]=123+n*177
    q=PatchPolicy(c,patches=[dict(expert=e,unit=u,values=vals)]);q(b)
    got=q.stages['expert_hidden'].numpy()
    for n,i in enumerate(targets):assert got[i,e,u]==123+n*177
    keep=np.ones(len(b),dtype=bool);keep[targets]=False
    assert np.array_equal(got[keep],bank[keep])
    assert np.array_equal(q.stages['routes'].numpy(),routes)
    assert torch.equal(q.stages['gates'],p.stages['gates'])


def test_integer_dose_and_model_bank_immutability():
    from falken9.integer_model import round_div
    b,c,p,y=fixture();old=copy.deepcopy(c)
    q=PatchPolicy(c,doses=[(1,0,3)]);q(b)
    active=(p.stages['routes']==1).any(1)
    assert torch.equal(q.stages['expert_hidden'][active,1,0],round_div(p.stages['expert_hidden'][active,1,0]*3,4))
    for name,t in c['tensors'].items():assert torch.equal(t['codes'],old['tensors'][name]['codes'])
    assert torch.equal(DiagnosticPolicy(c)(b),y)
    assert torch.equal(p.stages['logits'],y)
