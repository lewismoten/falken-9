"""Board-state research policy; floating arithmetic, no target-runtime claim."""
from dataclasses import dataclass
import math
import torch
from torch import nn
from torch.nn import functional as F

TIE_ORDER = (4, 1, 3, 5, 7, 2, 6, 8, 0)

@dataclass
class ModelConfig:
    width: int = 8
    expert_width: int = 8
    precision: str = 'float'


def select_moves(logits, boards):
    order = torch.tensor(TIE_ORDER, device=logits.device)
    masked = logits.masked_fill(boards != 0, -torch.inf)
    return order[masked[:, order].argmax(dim=-1)]


def quantize_weight(weight, precision):
    """STE mixed-precision weights, FP32 scales per projection/expert."""
    if precision == 'float':
        return weight
    scale = weight.detach().abs().mean(dim=(-2,-1),keepdim=True).clamp_min(1e-8)
    if precision == 'binary':
        quantized = torch.where(weight.detach()>=0,1.,-1.)*scale
    elif precision == 'ternary':
        quantized = torch.sign(weight.detach())*(weight.detach().abs()>=.7*scale)*scale
    else:
        raise ValueError(f'unknown precision {precision}')
    # Exact quantized forward, identity backward without cancellation roundoff.
    return quantized + (weight-weight.detach())


class CompactPolicy(nn.Module):
    """Nine occupancy tokens, self-attention, global top-2 of nine experts.

    Only selected expert matrices are gathered and multiplied. Routing ties use
    stable lower-ID ordering. No chronology or history-dependent state exists.
    """
    def __init__(self, config):
        super().__init__()
        self.config = config
        d, h = config.width, config.expert_width
        self.occupancy = nn.Embedding(3, d)
        self.position = nn.Parameter(torch.randn(9, d) * .1)
        self.side = nn.Embedding(2, d)
        self.norm1 = nn.LayerNorm(d)
        self.query = nn.Linear(d, d, bias=False)
        self.key = nn.Linear(d, d, bias=False)
        self.value = nn.Linear(d, d, bias=False)
        self.projection = nn.Linear(d, d, bias=False)
        self.readout = nn.Linear(9*d, d)
        self.norm2 = nn.LayerNorm(d)
        self.router = nn.Linear(d, 9)
        self.expert_w1 = nn.Parameter(torch.randn(9,d,h)/math.sqrt(d))
        self.expert_b1 = nn.Parameter(torch.zeros(9,h))
        self.expert_w2 = nn.Parameter(torch.randn(9,h,d)/math.sqrt(h))
        self.expert_b2 = nn.Parameter(torch.zeros(9,d))
        self.output = nn.Linear(d,9)

    def forward(self, boards, return_routes=False):
        side = ((boards != 0).sum(-1) % 2).long()
        x = self.occupancy(boards) + self.position + self.side(side)[:,None,:]
        z = self.norm1(x)
        quant = lambda w: quantize_weight(w, self.config.precision)
        q, k, v = (F.linear(z, quant(layer.weight)) for layer in (self.query,self.key,self.value))
        attention = (q @ k.transpose(-1,-2) / math.sqrt(self.config.width)).softmax(-1)
        x = x + F.linear(attention @ v, quant(self.projection.weight))
        x = F.gelu(self.readout(x.flatten(1)))
        z = self.norm2(x)
        scores = self.router(z)
        routes = torch.argsort(scores, dim=-1, descending=True, stable=True)[:,:2]
        gates = scores.gather(1,routes).softmax(-1)
        hidden = F.gelu(torch.einsum('bd,bkdh->bkh', z, quant(self.expert_w1)[routes]) + self.expert_b1[routes])
        experts = torch.einsum('bkh,bkhd->bkd', hidden, quant(self.expert_w2)[routes]) + self.expert_b2[routes]
        logits = self.output(x + (experts*gates[:,:,None]).sum(1))
        return (logits, routes) if return_routes else logits
