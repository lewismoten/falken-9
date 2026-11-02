import research678_core as r
import numpy as np
import torch
from falken9.integer_model import round_div

def test_route_mix_exact_order_and_gate_contract():
    assert hasattr(r,'mix_exact'), 'missing exact offline router recomposition'
    x=torch.tensor([[5,-5]],dtype=torch.int64)
    e=torch.tensor([[[3,-3],[7,-7],[9,-9]]],dtype=torch.int64)
    pair=torch.tensor([[0,1]])
    g=torch.tensor([[16384,16384]])
    assert r.mix_exact(x,e,pair,g).tolist()==[[10,-10]]
    assert torch.equal(r.mix_exact(x,e,pair,g),r.mix_exact(x,e,pair.flip(1),g.flip(1)))
    assert r.mix_exact(x,e,pair,torch.tensor([[32768,0]])).tolist()==[[8,-8]]
    try:r.mix_exact(x,e,pair,torch.tensor([[1,0]]))
    except ValueError:pass
    else:assert False,'reject invalid Q15 total'
    assert round_div(torch.tensor([-3,-1,1,3]),2).tolist()==[-2,-1,1,2]

def test_path_patch_preserves_identity_and_expert_ids():
    assert hasattr(r,'patch_outputs'), 'missing bounded path intervention'
    a=torch.tensor([[[1,2],[3,4],[5,6]]]);d=a+10
    out=r.patch_outputs(a,d,[2]);assert out.tolist()==[[[1,2],[3,4],[15,16]]]
    assert torch.equal(r.patch_outputs(a,a,[0,2]),a)
    assert torch.equal(a,torch.tensor([[[1,2],[3,4],[5,6]]]))
    try:r.patch_outputs(a,d,[3])
    except ValueError:pass
    else:assert False

def test_parameter_code_boundary_copy_and_zero_sign():
    assert hasattr(r,'mutate_code'), 'missing validated one-code perturbation'
    c={'tensors':{'a':{'bits':4,'codes':torch.tensor([7,-8,0]),'exponents':[-2]}}}
    d=r.mutate_code(c,'a',(2,),1)
    assert d['tensors']['a']['codes'].tolist()==[7,-8,1]
    assert c['tensors']['a']['codes'].tolist()==[7,-8,0]
    assert d['tensors']['a']['exponents']==[-2]
    for coord,delta in [((0,),1),((1,),-1)]:
        try:r.mutate_code(c,'a',coord,delta)
        except ValueError:pass
        else:assert False,'overflow must be rejected'
    assert hasattr(r,'sign_census'), 'missing membership-boundary census'
    old=np.array([[-1,0,1,-2]]);new=np.array([[0,-1,0,3]]);legal=np.array([[True,True,True,False]])
    assert r.sign_census(old,new,legal)==dict(negative_to_nonnegative=1,nonnegative_to_negative=1,occupied_sign_flips=1)
