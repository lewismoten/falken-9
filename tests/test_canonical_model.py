import pytest
import torch
from falken9.model import CompactPolicy, ModelConfig
from falken9 import canonical_model as cm
from falken9.symmetry import canonicalize


@pytest.mark.parametrize('precision', ['float', 'binary', 'ternary'])
@pytest.mark.parametrize('islands', ['float', 'int8', 'int4'])
def test_canonical_packed_independent_decode_parity(precision, islands):
    import struct
    torch.manual_seed(23)
    config = cm.CanonicalConfig(4, 4, precision, islands)
    model = cm.CanonicalPolicy(config).eval()
    boards = torch.tensor([[0] * 9, [0, 0, 0, 0, 1, 0, 0, 0, 0]])
    payload, inventory = cm.encode_model(model)
    decoded = cm.decode_model(payload).eval()
    assert len(payload) == sum(x['bytes'] for x in inventory) + 97
    assert payload[:4] == b'F9C1'
    # Independent scalar decode, separate from production decoder.
    cursor = 97
    for record in inventory:
        n, bits, scale_count = record['elements'], record['bits'], record['scale_count']
        scales = struct.unpack_from('<' + 'f' * scale_count, payload, cursor)
        cursor += 4 * scale_count
        size = (n * bits + 7) // 8
        raw = payload[cursor:cursor+size]
        cursor += size
        if bits == 32:
            values = struct.unpack('<' + 'f' * n, raw)
        else:
            packed = int.from_bytes(raw, 'little')
            values = []
            for i in range(n):
                code = (packed >> (i*bits)) & ((1 << bits)-1)
                value = (2*code-1) if bits == 1 else ([0,1,-1][code] if bits == 2 else code-(1<<bits) if code >= (1<<(bits-1)) else code)
                values.append(value * scales[i//(n//scale_count)])
        expected = torch.tensor(values, dtype=torch.float32).reshape(record['shape'])
        assert torch.equal(decoded.state_dict()[record['name']], expected)
    assert cursor == len(payload)
    with torch.no_grad():
        assert torch.equal(model(boards), decoded(boards))
    with pytest.raises(ValueError):
        cm.decode_model(payload[:-1])
    with pytest.raises(ValueError):
        cm.decode_model(payload+b'x')


def test_canonical_inherits_actual_network_and_original_ties():
    torch.manual_seed(11)
    model = cm.CanonicalPolicy(ModelConfig(4, 4))
    assert isinstance(model, CompactPolicy)
    boards = torch.tensor([[0] * 9, [0, 0, 0, 0, 1, 0, 0, 0, 0]])
    logits, routes = model(boards, return_routes=True)
    assert logits.shape == (2, 9) and routes.shape == (2, 2)
    logits.sum().backward()
    for name in ['query.weight', 'key.weight', 'value.weight', 'router.weight', 'expert_w1', 'output.weight']:
        assert dict(model.named_parameters())[name].grad is not None
    board = (0, 0, 0, 0, 1, 0, 0, 0, 0)
    _, transform = canonicalize(board)
    scores = torch.full((9,), -1.)
    scores[[0, 2, 6, 8]] = 1
    assert cm.restore_prediction(scores, board, transform) == ['c', 'g', 'i', 'a']
    with pytest.raises(ValueError, match='empty'):
        cm.restore_prediction(torch.full((9,), -1.), board, transform)
    with pytest.raises(ValueError, match='finite'):
        cm.restore_prediction(torch.full((9,), float('nan')), board, transform)
