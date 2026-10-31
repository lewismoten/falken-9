import importlib
import torch
from falken9.integer_export import load
from falken9.integer_model import IntegerPolicy


def test_output_range_change_preserves_every_other_boundary():
    m=importlib.import_module('falken9.range_integer_model')
    c=load('artifacts/integer/w8-int8-q8/model.f9i')
    old=IntegerPolicy(c); revised=m.RangeIntegerPolicy(c)
    sample=torch.tensor([[0]*9,[1,2,0,0,1,0,2,0,0]])
    a,ra=old(sample,True); b,rb=revised(sample,True)
    assert torch.equal(ra,rb)
    assert torch.equal(a,b.clamp(-32768,32767))
    assert revised.stats['saturation_by_stage'].get('output.weight',0)==0
    assert revised.sat(torch.tensor([100000]),'output.weight').item()==100000
    assert revised.sat(torch.tensor([100000]),'readout.weight').item()==32767


def test_reproducible_range_diagnostic(tmp_path):
    import importlib.util
    spec=importlib.util.spec_from_file_location('range_evaluator','scripts/evaluate_canonical_integer.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    data=dict(boards=[[0]*9],labels=['e'],history_indices=torch.tensor([0]),histories=[''])
    result=module.diagnose_legacy(data,tmp_path)
    assert result['old_clamp_equals_wide'] and result['route_mismatches']==0
    assert result['source_sha256']==result['source_sha256_after']
