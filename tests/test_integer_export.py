import importlib
from pathlib import Path
import struct
import torch

SOURCE = Path('artifacts/training/float-search/w8-h8-float/best.pt')


def test_materialized_tensor_bytes_have_independent_decoder(tmp_path):
    e = importlib.import_module('falken9.integer_export')
    c = torch.load(SOURCE,map_location='cpu',weights_only=False)
    candidate = e.convert(c, bulk_bits=4, frac=9)
    path = tmp_path/'model.f9i'
    report = e.save(candidate,path)
    decoded = e.load(path)
    raw = path.read_bytes()
    assert raw[:4] == b'F9I1'
    assert report['total_bytes'] == len(raw)
    assert report['total_bytes'] == sum(report[k] for k in ['header_bytes','descriptor_bytes','parameter_bytes','lut_bytes'])
    for name,entry in decoded['tensors'].items():
        d = next(d for d in decoded['descriptors'] if d['name']==name)
        payload = raw[d['offset']:d['offset']+d['length']]
        if d['bits']==4:
            codes = [(byte >> shift)&15 for byte in payload for shift in (0,4)][:entry['codes'].numel()]
            values = [v-16 if v>=8 else v for v in codes]
        else:
            values = list(struct.unpack('<'+{8:'b',16:'h'}[d['bits']]*entry['codes'].numel(),payload))
        assert values == candidate['tensors'][name]['codes'].flatten().tolist()
        assert torch.equal(entry['codes'],candidate['tensors'][name]['codes'])
        assert entry['exponents'] == candidate['tensors'][name]['exponents']
    assert decoded['tables'] == candidate['tables']
    bad = bytearray(raw); bad[0]=0
    path.write_bytes(bad)
    import pytest
    with pytest.raises(ValueError): e.load(path)


def test_decoder_rejects_malformed_layout_and_truncation(tmp_path):
    from falken9.integer_export import convert,save,load
    import pytest
    c=torch.load(SOURCE,map_location='cpu',weights_only=False)
    path=tmp_path/'model.f9i'; save(convert(c),path); raw=path.read_bytes()
    # First descriptor belongs to position [9,width]; incompatible shape cannot
    # be trusted merely because its payload count happens to be valid.
    bad=bytearray(raw); bad[14]=8
    path.write_bytes(bad)
    with pytest.raises(ValueError): load(path)
    for size in [0,9,10,13,100,len(raw)-1,len(raw)+1]:
        path.write_bytes((raw+b'\x00')[:size])
        with pytest.raises(ValueError): load(path)
