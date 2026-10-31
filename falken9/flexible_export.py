"""Explicit F9F1 v1 schema; NEVER reinterpret a fixed-nine F9C1 packet."""
import struct
import torch
from falken9.flexible_model import FlexiblePolicy, FlexibleConfig
from falken9.symmetry import TRANSFORMS

HEADER = struct.Struct('<4s8BIII')  # 24 bytes; wrapper adds 81.
WRAPPER = bytes([x for t in TRANSFORMS for x in t]+[ord(m)-97 for m in 'ebdfhcgia'])


@torch.no_grad()
def encode_model(model):
    c = model.config
    precision = 8 if c.precision == 'int8' else 32
    count = sum(p.numel() for p in model.parameters())
    payload = bytearray(HEADER.pack(b'F9F1',1,c.width,c.expert_width,c.experts,c.active,precision,1,0,count,0,0))
    payload.extend(WRAPPER)
    inventory = []
    for name,p in model.named_parameters():
        p = p.detach().cpu(); start = len(payload); scales = 0; bits = 32
        if precision == 8 and p.ndim >= 2:
            bits = 8
            scale = p.abs().amax(dim=(-2,-1),keepdim=True).clamp_min(1e-8)/127
            scales = scale.numel()
            payload.extend(struct.pack('<'+'f'*scales,*scale.flatten().tolist()))
            codes = (p/scale).round().clamp(-127,127).to(torch.int8).flatten().tolist()
            payload.extend(bytes(x & 255 for x in codes))
        else:
            payload.extend(struct.pack('<'+'f'*p.numel(),*p.flatten().tolist()))
        inventory.append(dict(name=name,shape=list(p.shape),elements=p.numel(),bits=bits,scale_count=scales,bytes=len(payload)-start))
    return bytes(payload),inventory


def decode_model(payload):
    """Independent signed-byte decoding into a no-requantization FP32 runtime."""
    try:
        magic,version,d,h,e,k,bits,gate,reserved,count,r1,r2 = HEADER.unpack_from(payload)
        if magic != b'F9F1' or version != 1 or bits not in (8,32) or gate != 1 or reserved or r1 or r2:
            raise ValueError('invalid F9F1 header')
        if payload[24:105] != WRAPPER:
            raise ValueError('invalid wrapper')
        model = FlexiblePolicy(FlexibleConfig(d,h,e,k,'float'))
        if count != sum(p.numel() for p in model.parameters()):
            raise ValueError('invalid parameter count')
        offset = 105; state = {}
        for name,p in model.named_parameters():
            n = p.numel()
            if bits == 8 and p.ndim >= 2:
                ns = p.shape[0] if p.ndim == 3 else 1
                scales = struct.unpack_from('<'+'f'*ns,payload,offset); offset += ns*4
                codes = struct.unpack_from('<'+'b'*n,payload,offset); offset += n
                if any(x == -128 for x in codes) or any(not 0 < x < float('inf') for x in scales):
                    raise ValueError('invalid quantized tensor')
                values = [x*scales[i//(n//ns)] for i,x in enumerate(codes)]
            else:
                values = struct.unpack_from('<'+'f'*n,payload,offset); offset += 4*n
            tensor = torch.tensor(values,dtype=torch.float32).reshape(p.shape)
            if not torch.isfinite(tensor).all(): raise ValueError('nonfinite tensor')
            state[name] = tensor
        if offset != len(payload): raise ValueError('trailing packet bytes')
        model.load_state_dict(state)
        return model
    except (struct.error, IndexError) as error:
        raise ValueError('truncated packet') from error
