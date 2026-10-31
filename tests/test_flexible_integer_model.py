import importlib
import torch
from test_flexible_integer_export import SOURCE
from falken9.flexible_export import decode_model
from falken9.flexible_integer_export import convert, save, load
from test_canonical_integer_model import scalar_oracle


def test_four_expert_integer_matches_independent_scalar_and_selected_execution(tmp_path):
    module = importlib.import_module('falken9.flexible_integer')
    torch.set_num_threads(1)
    boards = torch.tensor([[0]*9,[1,2,0,0,1,0,2,0,0]])
    c = convert(decode_model(SOURCE.read_bytes()))
    path = tmp_path/'model.f9j'; save(c,path)
    policy = module.FlexibleIntegerPolicy(load(path))
    logits, routes = policy(boards,True)
    for i, board in enumerate(boards.tolist()):
        expected, expected_routes = scalar_oracle(c,board)
        assert logits[i].tolist() == expected
        assert routes[i].tolist() == expected_routes
    assert policy.stats['expert_evaluations'] == 2*len(boards)
    assert policy.stats['accumulators']['norm1.numerator'] > 0
    assert policy.stats['accumulators']['attention.dot.prefix'] >= policy.stats['accumulators']['attention.dot']
    assert policy.stats['operation_envelope_bounds']['attention.dot'] >= policy.stats['accumulators']['attention.dot.prefix']
    for name in ('attention.weighted', 'expert.weighted'):
        assert policy.stats['accumulators'][name+'.prefix'] >= policy.stats['accumulators'][name]
        assert policy.stats['operation_envelope_bounds'][name] >= policy.stats['accumulators'][name+'.prefix']
