"""Fewer-expert, nine-token canonical neural MoE research architecture."""
from dataclasses import dataclass
import math
import torch
from torch import nn
from torch.nn import functional as F



@dataclass
class FlexibleConfig:
    width: int = 8
    expert_width: int = 4
    experts: int = 4
    active: int = 2
    precision: str = 'float'

    def __post_init__(self):
        if self.width < 1 or self.expert_width < 1 or not 2 <= self.experts <= 255 or not 1 <= self.active <= self.experts:
            raise ValueError('invalid dimensions/expert routing')
        if self.precision not in ('float', 'int8'):
            raise ValueError('invalid weight precision')


def effective_weight(weight, precision):
    """Symmetric signed INT8, one FP32 scale per matrix/expert; identity STE."""
    if precision == 'float':
        return weight
    scale = weight.detach().abs().amax(dim=(-2,-1),keepdim=True).clamp_min(1e-8)/127
    quantized = (weight.detach()/scale).round().clamp(-127,127)*scale
    return quantized + (weight-weight.detach())


class FlexiblePolicy(nn.Module):
    """Nine actual tokens, one attention head, global learned sparse MoE.

    K=1 uses the selected probability from the FULL E-way softmax, without
    renormalizing that singleton. This preserves router gradients; both
    training and deployment evaluate only K selected expert banks.
    K>1 uses selected-score softmax, matching the canonical reference.
    """
    def __init__(self, config):
        super().__init__()
        self.config = config
        d, h, e = config.width, config.expert_width, config.experts
        self.occupancy = nn.Embedding(3, d)
        self.position = nn.Parameter(torch.randn(9, d)*.1)
        self.side = nn.Embedding(2, d)
        self.norm1 = nn.LayerNorm(d)
        self.query = nn.Linear(d, d, bias=False)
        self.key = nn.Linear(d, d, bias=False)
        self.value = nn.Linear(d, d, bias=False)
        self.projection = nn.Linear(d, d, bias=False)
        self.readout = nn.Linear(9*d, d)
        self.norm2 = nn.LayerNorm(d)
        self.router = nn.Linear(d, e)
        self.expert_w1 = nn.Parameter(torch.randn(e,d,h)/math.sqrt(d))
        self.expert_b1 = nn.Parameter(torch.zeros(e,h))
        self.expert_w2 = nn.Parameter(torch.randn(e,h,d)/math.sqrt(h))
        self.expert_b2 = nn.Parameter(torch.zeros(e,d))
        self.output = nn.Linear(d, 9)

    def forward(self, boards, return_routes=False, _effective=False):
        if self.config.precision != 'float' and not _effective:
            weights = {name: effective_weight(p,self.config.precision) for name,p in self.named_parameters() if p.ndim >= 2}
            return torch.func.functional_call(self,weights,(boards,),dict(return_routes=return_routes,_effective=True))
        side = ((boards != 0).sum(-1)%2).long()
        x = self.occupancy(boards) + self.position + self.side(side)[:,None,:]
        z = self.norm1(x)
        q, k, v = (layer(z) for layer in (self.query, self.key, self.value))
        attention = (q @ k.transpose(-1,-2)/math.sqrt(self.config.width)).softmax(-1)
        x = x + self.projection(attention @ v)
        x = F.gelu(self.readout(x.flatten(1)))
        z = self.norm2(x)
        scores = self.router(z)
        routes = torch.argsort(scores,dim=-1,descending=True,stable=True)[:,:self.config.active]
        gates = (scores.softmax(-1).gather(1,routes) if self.config.active == 1
                 else scores.gather(1,routes).softmax(-1))
        hidden = F.gelu(torch.einsum('bd,bkdh->bkh',z,self.expert_w1[routes])+self.expert_b1[routes])
        experts = torch.einsum('bkh,bkhd->bkd',hidden,self.expert_w2[routes])+self.expert_b2[routes]
        logits = self.output(x+(experts*gates[:,:,None]).sum(1))
        return (logits,routes) if return_routes else logits

    @torch.no_grad()
    def predict_history(self, history):
        from falken9.policy import board_from_history
        from falken9.symmetry import canonicalize
        from falken9.canonical_model import restore_prediction
        canonical,transform=canonicalize(board_from_history(history))
        logits=self(torch.tensor([canonical],dtype=torch.long,device=self.position.device))[0]
        return restore_prediction(logits,canonical,transform)[0]
