"""Packed mixed-weight archive with independent host FP32 decoder.

Not an integer runtime: all activations, scales, norms, attention and decoding
are floating point. Binary/ternary applies to six named matrix groups only.
"""
from dataclasses import asdict
import json
from pathlib import Path
import struct
import torch
from falken9.model import CompactPolicy,ModelConfig

LOW_BIT_NAMES={'query.weight','key.weight','value.weight','projection.weight','expert_w1','expert_w2'}


def export_model(model,path):
    precision=model.config.precision
    if precision not in ('binary','ternary'): raise ValueError('low-bit model required')
    payload=bytearray(); entries=[]
    for name,value in model.state_dict().items():
        value=value.detach().cpu().float()
        item=dict(name=name,shape=list(value.shape),offset=len(payload),count=value.numel())
        if name in LOW_BIT_NAMES:
            scales=value.abs().mean(dim=(-2,-1),keepdim=True).clamp_min(1e-8)
            codes=(value>=0).to(torch.uint8) if precision=='binary' else (torch.sign(value)*(value.abs()>=.7*scales)+1).to(torch.uint8)
            bits=1 if precision=='binary' else 2
            raw=bytearray((value.numel()*bits+7)//8)
            for i,code in enumerate(codes.flatten().tolist()): raw[i*bits//8]|=code<<(i*bits%8)
            payload.extend(raw)
            item.update(kind=precision,bits=bits,bytes=len(raw),scales=scales.flatten().tolist(),scale_shape=list(scales.shape))
        else:
            raw=struct.pack('<'+'f'*value.numel(),*value.flatten().tolist());payload.extend(raw)
            item.update(kind='fp32',bytes=len(raw))
        entries.append(item)
    metadata=dict(format='F9Q1',config=asdict(model.config),entries=entries,payload_bytes=len(payload),integer_runtime=False,bit_order='LSB-first; binary 0=-1,1=+1; ternary 0=-1,1=0,2=+1',scale_format='JSON exact FP32 values; decoder FP32',target_accepted=False)
    header=json.dumps(metadata,separators=(',',':')).encode()
    path=Path(path);path.write_bytes(b'F9Q1'+struct.pack('<I',len(header))+header+payload)
    return dict(**metadata,header_bytes=8+len(header),encoded_bytes=path.stat().st_size)


def load_packed(path):
    raw=Path(path).read_bytes()
    if raw[:4]!=b'F9Q1': raise ValueError('invalid magic')
    header_length=struct.unpack('<I',raw[4:8])[0]
    metadata=json.loads(raw[8:8+header_length]); payload=raw[8+header_length:]
    if len(payload)!=metadata['payload_bytes']: raise ValueError('invalid payload size')
    config=dict(metadata['config']);config['precision']='float'
    model=CompactPolicy(ModelConfig(**config));state={}
    for item in metadata['entries']:
        segment=payload[item['offset']:item['offset']+item['bytes']]
        if item['kind']=='fp32': value=torch.tensor(struct.unpack('<'+'f'*item['count'],segment),dtype=torch.float32).reshape(item['shape'])
        else:
            bits=item['bits'];mask=(1<<bits)-1
            codes=[(segment[i*bits//8]>>(i*bits%8))&mask for i in range(item['count'])]
            if bits==2 and 3 in codes: raise ValueError('invalid ternary code')
            value=torch.tensor(codes,dtype=torch.float32).reshape(item['shape'])
            value=(value*2-1 if bits==1 else value-1)*torch.tensor(item['scales']).reshape(item['scale_shape'])
        state[item['name']]=value
    model.load_state_dict(state)
    return model.eval()
