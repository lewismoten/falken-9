import importlib
import torch
from pathlib import Path
SOURCE=Path('artifacts/canonical/qat/w8-h4-float-islands-int8-refine-s23/packed/model.f9c')


def test_materialized_integer_packet_roundtrip_and_validation(tmp_path):
    m=importlib.import_module('falken9.canonical_integer_export')
    from falken9.canonical_model import decode_model
    source=decode_model(SOURCE.read_bytes())
    c=m.convert(source,frac=10,matrix_bits=16,activation_bits=32,attention_mode='rational',interpolate=True)
    path=tmp_path/'model.f9j'; inventory=m.save(c,path); decoded=m.load(path)
    assert inventory['total_bytes']==path.stat().st_size<=8192
    assert decoded['output_bits']==32 and decoded['experts']==9
    assert decoded['wrapper']==SOURCE.read_bytes()[16:97]
    for name,t in c['tensors'].items():
        assert torch.equal(t['codes'],decoded['tensors'][name]['codes'])
        assert t['exponents']==decoded['tensors'][name]['exponents']
    path.write_bytes(path.read_bytes()+b'x')
    import pytest
    with pytest.raises(ValueError): m.load(path)


def test_rejects_unrepresentable_lut_fraction():
    import pytest
    from falken9.canonical_integer_export import convert
    from falken9.canonical_model import decode_model
    with pytest.raises(ValueError,match='unsupported'):
        convert(decode_model(SOURCE.read_bytes()),frac=12)
