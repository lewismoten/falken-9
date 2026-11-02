"""Learned canonical optimal-set policy, with explicit coordinate restoration.

No oracle, lookup table, or fallback move is used in inference. Host FP32
attention/nonlinear arithmetic is retained even for low-bit weight variants.
"""
from dataclasses import dataclass
import struct
import torch
from falken9.model import CompactPolicy, ModelConfig, quantize_weight

BULK = {'query.weight', 'key.weight', 'value.weight', 'projection.weight', 'expert_w1', 'expert_w2'}
ISLANDS = {'position', 'occupancy.weight', 'side.weight', 'readout.weight', 'router.weight', 'output.weight'}


@dataclass
class CanonicalConfig(ModelConfig):
    island_precision: str = 'float'


def quantize_island(weight, precision):
    if precision == 'float':
        return weight
    bits = {'int8': 8, 'int4': 4}[precision]
    maximum = (1 << (bits-1))-1
    scale = weight.detach().abs().max().clamp_min(1e-8) / maximum
    rounded = (weight.detach()/scale).round().clamp(-maximum, maximum)*scale
    return rounded + (weight-weight.detach())
from falken9.policy import board_from_history
from falken9.symmetry import canonicalize, restore_moves


class CanonicalPolicy(CompactPolicy):
    """Reuse the actual nine-token attention / stable-top2 nine-expert model.

    Nine output logits are independent optimal-set membership scores, NOT a
    selected canonical target. A score >= 0 predicts membership, with occupied
    cells masked. Training uses every published optimal move as a positive.
    """

    def forward(self, boards, return_routes=False, _effective=False):
        precision = getattr(self.config, 'island_precision', 'float')
        if precision == 'float' or _effective:
            return super().forward(boards, return_routes=return_routes)
        # Functional replacement preserves actual CompactPolicy operations and
        # state-dict names, while STE gradients reach FP32 master parameters.
        effective = {name: quantize_island(p, precision) for name, p in self.named_parameters() if name in ISLANDS}
        return torch.func.functional_call(self, effective, (boards,),
                                          dict(return_routes=return_routes, _effective=True))

    @torch.no_grad()
    def predict_history(self, history):
        board = board_from_history(history)
        canonical, transform = canonicalize(board)
        device = next(self.parameters()).device
        logits = self(torch.tensor([canonical], dtype=torch.long, device=device))[0]
        moves = restore_prediction(logits, canonical, transform)
        return moves[0]


def predict_sets(logits, boards):
    if logits.shape != boards.shape or logits.shape[-1] != 9:
        raise ValueError('expected matching nine-square logits and boards')
    if not bool(torch.isfinite(logits).all()):
        raise ValueError('expected finite logits')
    return (logits >= 0) & (boards == 0)


def restore_prediction(logits, canonical_board, transform):
    board = torch.as_tensor(canonical_board, device=logits.device)
    membership = predict_sets(logits, board)
    moves = [chr(97 + i) for i in membership.nonzero().flatten().tolist()]
    restored = restore_moves(moves, transform)
    if not restored:
        raise ValueError('empty learned optimal set; no fallback policy')
    return restored


@torch.no_grad()
def encode_model(model):
    """Fixed-schema F9C1 packet; packed weights with every FP32 island counted.

    Header and square permutations occupy 97 bytes. Tensor order is exactly
    CompactPolicy.named_parameters(). Each quantized tensor starts with its
    FP32 scales, followed by LSB-first codes (no padding except final bits).
    """
    from falken9.symmetry import TRANSFORMS
    precision = {'float': 0, 'binary': 1, 'ternary': 2}[model.config.precision]
    island_bits = {'float': 32, 'int8': 8, 'int4': 4}[getattr(model.config, 'island_precision', 'float')]
    count = sum(p.numel() for p in model.parameters())
    payload = bytearray(struct.pack('<4sBBBBII', b'F9C1', model.config.width, model.config.expert_width, precision, island_bits, count, 0))
    payload.extend(x for transform in TRANSFORMS for x in transform)
    payload.extend(ord(m)-97 for m in 'ebdfhcgia')
    inventory=[]
    for name, master in model.named_parameters():
        weight = master.detach().cpu()
        scales=[]; bits=32
        if name in BULK and precision:
            bits=precision
            scale=weight.abs().mean(dim=(-2,-1),keepdim=True).clamp_min(1e-8)
            scales=scale.flatten().tolist()
            if bits == 1:
                codes=(weight>=0).long().flatten().tolist()
            else:
                codes=torch.where(weight.abs()<.7*scale, 0, torch.where(weight>=0,1,2)).flatten().tolist()
        elif name in ISLANDS and island_bits != 32:
            bits=island_bits
            maximum=(1<<(bits-1))-1
            scale=weight.abs().max().clamp_min(1e-8)/maximum
            scales=[scale.item()]
            codes=((weight/scale).round().clamp(-maximum,maximum).long() & ((1<<bits)-1)).flatten().tolist()
        start=len(payload)
        if bits == 32:
            payload.extend(struct.pack('<'+'f'*weight.numel(), *weight.flatten().tolist()))
        else:
            payload.extend(struct.pack('<'+'f'*len(scales), *scales))
            packed=bytearray((weight.numel()*bits+7)//8)
            for i, code in enumerate(codes):
                packed[i*bits//8] |= int(code) << ((i*bits)%8)
            payload.extend(packed)
        inventory.append(dict(name=name,shape=list(weight.shape),elements=weight.numel(),bits=bits,
                              scale_count=len(scales),bytes=len(payload)-start))
    return bytes(payload), inventory


def decode_model(payload):
    """Materialize decoded FP32 weights; never re-quantize decoded values."""
    from falken9.symmetry import TRANSFORMS
    if len(payload)<97:
        raise ValueError('truncated packet')
    magic, width, hidden, precision, island_bits, count, reserved = struct.unpack_from('<4sBBBBII', payload)
    if magic != b'F9C1' or precision not in (0,1,2) or island_bits not in (4,8,32) or reserved:
        raise ValueError('invalid packet header')
    expected_wrapper=bytes([x for transform in TRANSFORMS for x in transform]+[ord(m)-97 for m in 'ebdfhcgia'])
    if payload[16:97] != expected_wrapper:
        raise ValueError('invalid coordinate wrapper')
    model=CanonicalPolicy(CanonicalConfig(width,hidden,'float','float'))
    if count != sum(p.numel() for p in model.parameters()):
        raise ValueError('invalid parameter count')
    state={}; offset=97
    try:
        for name, target in model.named_parameters():
            n=target.numel(); bits=32; scales=[]
            if name in BULK and precision:
                bits=precision
                scale_count=target.shape[0] if target.ndim==3 else 1
            elif name in ISLANDS and island_bits != 32:
                bits=island_bits; scale_count=1
            if bits == 32:
                values=struct.unpack_from('<'+'f'*n,payload,offset)
                offset+=4*n
            else:
                scales=struct.unpack_from('<'+'f'*scale_count,payload,offset)
                offset+=4*scale_count
                size=(n*bits+7)//8
                if offset+size>len(payload): raise ValueError('truncated tensor')
                codes=payload[offset:offset+size]; offset+=size
                values=[]
                for i in range(n):
                    code=(codes[(i*bits)//8] >> ((i*bits)%8)) & ((1<<bits)-1)
                    if bits==1: value=1 if code else -1
                    elif bits==2:
                        if code==3: raise ValueError('reserved ternary code')
                        value=(0,1,-1)[code]
                    else: value=code-(1<<bits) if code & (1<<(bits-1)) else code
                    values.append(value*scales[i//(n//scale_count)])
            state[name]=torch.tensor(values,dtype=torch.float32).reshape(target.shape)
    except struct.error as error:
        raise ValueError('truncated tensor') from error
    if offset != len(payload): raise ValueError('trailing packet bytes')
    model.load_state_dict(state)
    return model
