"""Independent F9F1 packing and materialized-forward gates."""
import struct
import pytest
import torch
from falken9.flexible_model import FlexibleConfig, FlexiblePolicy


def test_all_matrix_int8_forward_matches_independent_codes():
    from falken9.flexible_model import effective_weight
    x = torch.tensor([[-1., .5], [.2, -.7]], requires_grad=True)
    expected = torch.tensor([[-127., 64.], [25., -89.]])/127
    assert torch.equal(effective_weight(x, 'int8'), expected)
    effective_weight(x, 'int8').sum().backward()
    assert torch.equal(x.grad, torch.ones_like(x))


@pytest.mark.parametrize('experts,active,precision', [(4,2,'float'),(3,2,'int8'),(2,1,'int8')])
def test_versioned_roundtrip_exhaustive_tensor_parity(experts, active, precision):
    from falken9.flexible_export import encode_model, decode_model
    from falken9.flexible_model import effective_weight
    torch.manual_seed(11)
    model = FlexiblePolicy(FlexibleConfig(experts=experts,active=active,precision=precision))
    payload, inventory = encode_model(model)
    assert payload[:4] == b'F9F1'
    assert payload[4:9] == bytes([1,8,4,experts,active])
    assert sum(x['bytes'] for x in inventory)+105 == len(payload)
    decoded = decode_model(payload)
    assert decoded.config.experts == experts and decoded.config.active == active
    for name, p in model.named_parameters():
        expected = effective_weight(p,precision) if p.ndim >= 2 else p
        assert torch.equal(decoded.state_dict()[name], expected)
    boards = torch.randint(0,3,(627,9))
    a, ar = model(boards,return_routes=True)
    b, br = decoded(boards,return_routes=True)
    assert torch.equal(a,b) and torch.equal(ar,br)
    for broken in (payload[:-1], payload+b'\0', b'F9C1'+payload[4:], payload[:7]+b'\0'+payload[8:]):
        with pytest.raises(ValueError):
            decode_model(broken)
