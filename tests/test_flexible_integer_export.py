import importlib
from pathlib import Path
import hashlib
import pytest
import torch
from falken9.flexible_export import decode_model

SOURCE = Path('artifacts/flexible/refine-scratch/w8-h4-e4-k2-float-s23/packed/model.f9f')
SHA = '1dfbca8f62beeb000334c8a1163c0aaa3a50a858cbc3e5f3605ed4b589d6ce33'


def test_effective_four_expert_materialization_roundtrip(tmp_path):
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == SHA
    module = importlib.import_module('falken9.flexible_integer_export')
    model = decode_model(SOURCE.read_bytes())
    candidate = module.convert(model)
    assert (candidate['width'], candidate['expert_width'], candidate['experts'], candidate['topk']) == (8, 4, 4, 2)
    assert candidate['frac'] == 11
    path = tmp_path/'model.f9j'
    inventory = module.save(candidate, path)
    decoded = module.load(path)
    assert inventory['total_bytes'] == path.stat().st_size
    for name, tensor in candidate['tensors'].items():
        assert torch.equal(tensor['codes'], decoded['tensors'][name]['codes'])
        assert tensor['exponents'] == decoded['tensors'][name]['exponents']
    assert decoded['tables'] == candidate['tables']
    assert decoded['wrapper'] == candidate['wrapper']


def test_mixed_matrices_come_directly_from_effective_source():
    module = importlib.import_module('falken9.flexible_integer_export')
    model = decode_model(SOURCE.read_bytes())
    names = ('expert_w2', 'projection.weight', 'output.weight')
    mixed = module.convert(model, component_int8=names)
    high = module.convert(model)
    low = module.convert(model, matrix_bits=8)
    for name,tensor in mixed['tensors'].items():
        expected = (low if name in names else high)['tensors'][name]
        assert torch.equal(tensor['codes'], expected['codes'])
        assert tensor['bits'] == expected['bits']
        assert tensor['exponents'] == expected['exponents']
    with pytest.raises(ValueError, match='matrix'):
        module.convert(model, component_int8=['router.bias'])


def test_singleton_gate_contract_is_not_silently_reinterpreted():
    module = importlib.import_module('falken9.flexible_integer_export')
    model = decode_model(SOURCE.read_bytes())
    model.config.active = 1
    with pytest.raises(ValueError, match='top-2'):
        module.convert(model)
