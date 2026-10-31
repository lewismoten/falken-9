import importlib
import pytest


def test_signed_rounding_and_saturation():
    a = importlib.import_module('falken9.arithmetic')
    assert [a.round_shift(x, 1) for x in [-5,-3,-1,0,1,3,5]] == [-3,-2,-1,0,1,2,3]
    assert a.requantize(255, 1, 8) == 127
    assert a.requantize(-257, 1, 8) == -128
    assert a.round_shift(-123, 0) == -123
    with pytest.raises(ValueError):
        a.round_shift(1, -1)
