import struct
import pytest
from falken9.canonical_integer_export import convert,save,load
from falken9.canonical_model import decode_model
from test_canonical_integer_export import SOURCE


@pytest.mark.parametrize('offset,value',[(0,0),(4,3),(8,10),(9,8),(10,16),(11,3),(12,7),(18,255)])
def test_rejects_malformed_contract_fields(tmp_path,offset,value):
    c=convert(decode_model(SOURCE.read_bytes()))
    path=tmp_path/'bad.f9j';save(c,path)
    raw=bytearray(path.read_bytes());raw[offset]=value;path.write_bytes(raw)
    with pytest.raises(ValueError): load(path)


def test_interpolation_preserves_grid_endpoints_and_empty_set_rejects():
    from falken9.canonical_integer import CanonicalIntegerPolicy
    import torch
    c=convert(decode_model(SOURCE.read_bytes()),frac=11,attention_mode='early')
    runtime=CanonicalIntegerPolicy(c)
    x=torch.tensor([0,64,128,32768])
    assert runtime.lookup(x,runtime.exp).tolist()==[c['tables']['exp'][i] for i in (0,1,2,512)]
    # Force the actual neural head negative; no inference fallback can supply a move.
    c['tensors']['output.weight']['codes'].zero_();c['tensors']['output.bias']['codes'].fill_(-1)
    with pytest.raises(ValueError,match='empty'): CanonicalIntegerPolicy(c).predict_history('')
