"""Executable acceptance tests for the derived integer ONNX inspection graph."""
from pathlib import Path
import importlib.util
import numpy as np
import onnx
import onnxruntime as ort
from onnx import helper as H, TensorProto as T
from falken9.canonical_integer_export import load
from test_canonical_integer_model import scalar_oracle

ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT/'artifacts/flexible-integer/q11-w16-a32-early-interp/model.f9j'


def exporter():
    path = ROOT/'scripts/export_inspection_graph.py'
    assert path.is_file(), 'inspection exporter is not implemented'
    spec = importlib.util.spec_from_file_location('inspection_export', path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_exact_integer_onnx_forward(tmp_path):
    model = exporter().build_model(PACKET)
    onnx.checker.check_model(model, full_check=True)
    session = ort.InferenceSession(model.SerializeToString(), providers=['CPUExecutionProvider'])
    candidate = load(PACKET)
    for board in ([0]*9, [1,2,0,0,1,0,2,0,0]):
        expected, routes = scalar_oracle(candidate, board)
        actual, actual_routes = session.run(None, {'board': np.array([board], dtype=np.int64)})
        assert actual.tolist() == [expected]
        assert actual_routes.tolist() == [routes]
    assert len(model.functions) >= 8
    assert len(model.graph.initializer) >= 21
    assert not any(n.op_type == 'MatMul' for f in model.functions for n in f.node)


def test_all_627_canonical_outputs_and_policy_sets(tmp_path):
    module = exporter()
    assert hasattr(module, 'validate_model'), 'exhaustive runtime validation missing'
    report = module.validate_model(module.build_model(PACKET))
    assert report['canonical_count'] == 627
    assert report['score_mismatch_boards'] == 0
    assert report['route_mismatch_boards'] == 0
    assert report['canonical_set_errors'] == 0
    assert report['independent_scalar_oracle'] is True


def test_half_away_rounding_above_signed_32bit():
    b = exporter().Builder()
    y = b.rd('x', 4096)
    model = H.make_model(H.make_graph(b.nodes, 'round', [H.make_tensor_value_info('x',T.INT64,[6])], [H.make_tensor_value_info(y,T.INT64,[6])]),opset_imports=[H.make_opsetid('',18)],ir_version=10)
    values = [2290000000, -2290000000, 2048, -2048, 0, 1 << 40]
    actual = ort.InferenceSession(model.SerializeToString()).run(None, {'x':np.array(values,dtype=np.int64)})[0]
    expected = [(1 if x >= 0 else -1)*((abs(x)+2048)//4096) for x in values]
    assert actual.tolist() == expected
