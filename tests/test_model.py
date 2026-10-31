import unittest
import torch
from falken9.model import CompactPolicy, ModelConfig, select_moves


class ModelTests(unittest.TestCase):
    def test_compact_attention_sparse_experts_backward(self):
        torch.manual_seed(11)
        model = CompactPolicy(ModelConfig(width=8, expert_width=8))
        boards = torch.tensor([[0]*9, [1,2,0,0,0,0,0,0,0]])
        logits, route = model(boards, return_routes=True)
        self.assertEqual(tuple(logits.shape), (2,9))
        self.assertEqual(tuple(route.shape), (2,2))
        self.assertTrue(torch.all(route[:,0] != route[:,1]))
        logits.square().sum().backward()
        for name in ('query.weight','key.weight','value.weight','router.weight','expert_w1','expert_w2'):
            self.assertGreater(dict(model.named_parameters())[name].grad.abs().sum().item(), 0)
        self.assertEqual(select_moves(torch.zeros(2,9), boards).tolist(), [4,4])

    def test_low_bit_forward_matches_materialized_weights(self):
        from falken9.model import quantize_weight
        for precision in ('binary','ternary'):
            torch.manual_seed(17)
            fake = CompactPolicy(ModelConfig(8,8,precision))
            reference = CompactPolicy(ModelConfig(8,8,'float'))
            state = fake.state_dict()
            names = ['query.weight','key.weight','value.weight','projection.weight','expert_w1','expert_w2']
            for name in names:
                weight = state[name]
                scale = weight.abs().mean(dim=(-2,-1),keepdim=True).clamp_min(1e-8)
                expected = torch.where(weight>=0,1.,-1.)*scale if precision=='binary' else torch.sign(weight)*(weight.abs()>=.7*scale)*scale
                self.assertTrue(torch.equal(quantize_weight(weight,precision),expected))
                state[name] = expected
            reference.load_state_dict(state)
            boards = torch.randint(0,3,(7,9))
            self.assertTrue(torch.equal(fake(boards),reference(boards)))
            fake(boards).sum().backward()
            self.assertGreater(fake.query.weight.grad.abs().sum().item(),0)

if __name__ == '__main__':
    unittest.main()
