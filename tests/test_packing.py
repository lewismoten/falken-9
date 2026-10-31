import importlib
import itertools
import pytest


def test_lsb_codebooks_and_strict_padding():
    p = importlib.import_module('falken9.packing')
    assert p.pack([-1,1,-1,1,1,-1,-1,1,1], 'binary') == b'\x9a\x01'
    assert p.pack([0,1,-1,0], 'ternary') == b'\x24'
    for kind, values in [('binary',[-1,1]), ('ternary',[-1,0,1])]:
        for n in range(1,6):
            for row in itertools.product(values, repeat=n):
                assert p.unpack(p.pack(row,kind), n,kind) == list(row)
    with pytest.raises(ValueError): p.unpack(b'\x03',1,'ternary')
    with pytest.raises(ValueError): p.unpack(b'\x81',1,'binary')
    with pytest.raises(ValueError): p.pack([0],'binary')
    with pytest.raises(ValueError): p.unpack(b'',1,'binary')
