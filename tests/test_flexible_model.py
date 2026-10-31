"""Configurable expert-bank tests; no fixed-nine subclassing."""
import pytest
import torch

torch.set_num_threads(1)


def test_config_declares_and_validates_expert_count():
    from falken9.flexible_model import FlexibleConfig
    assert FlexibleConfig(experts=3, active=2).experts == 3
    for kwargs in ({'experts': 1}, {'active': 0}, {'experts': 2, 'active': 3}, {'width': 0}, {'precision': 'bogus'}):
        with pytest.raises(ValueError):
            FlexibleConfig(**kwargs)


@pytest.mark.parametrize('experts,active', [(4,2), (3,2), (2,1), (3,1), (4,1), (2,2)])
def test_neural_routes_shape_gradient_and_actual_participation(experts, active):
    from falken9.flexible_model import FlexibleConfig, FlexiblePolicy
    torch.manual_seed(11)
    model = FlexiblePolicy(FlexibleConfig(experts=experts, active=active))
    boards = torch.randint(0, 3, (128, 9))
    logits, routes = model(boards, return_routes=True)
    assert logits.shape == (128, 9)
    assert routes.shape == (128, active)
    assert model.position.shape == (9, 8)
    assert model.expert_w1.shape == (experts, 8, 4)
    assert routes.unique().numel() > 1
    logits.square().mean().backward()
    assert model.router.weight.grad.abs().sum() > 0
    for name in ('query', 'key', 'value', 'projection', 'occupancy', 'readout', 'output'):
        assert getattr(model, name).weight.grad.abs().sum() > 0
    assert model.expert_w1.grad.abs().sum() > 0
    assert model.norm1.weight.grad.abs().sum() > 0
    with torch.no_grad():
        model.router.weight.zero_(); model.router.bias.zero_()
    _, tied = model(boards, return_routes=True)
    assert tied[0].tolist() == list(range(active))


def test_history_wrapper_restores_complete_set_and_never_falls_back():
    from falken9.flexible_model import FlexibleConfig, FlexiblePolicy
    model = FlexiblePolicy(FlexibleConfig())
    with torch.no_grad():
        model.output.weight.zero_(); model.output.bias.fill_(1)
    assert model.predict_history('') == 'e'
    assert model.predict_history('e') == 'b'
    with torch.no_grad():
        model.output.bias.fill_(-1)
    with pytest.raises(ValueError,match='empty learned'):
        model.predict_history('')
    with pytest.raises(ValueError):
        model.predict_history('aa')
