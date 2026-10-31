import importlib
import pytest


def test_dot_bounds_and_little_endian_results():
    a = importlib.import_module('falken9.arithmetic')
    assert a.dot([-128]*32,[-1]*32) == 4096
    assert a.dot([-128]*32,[-128]*32, accumulator_bits=32) == 524288
    assert a.accumulator_bound(32,8,1) == 4096
    assert a.accumulator_bound(32,16,1) == 1048576
    assert a.encode_signed(-257,16) == b'\xff\xfe'
    with pytest.raises(OverflowError): a.dot([-128]*32,[-128]*32)
    with pytest.raises(ValueError): a.dot([128],[1])
    with pytest.raises(ValueError): a.dot([1],[])
