"""OFFLINE float conversion/LUT generation; runtime load only decodes integers."""
import math
import struct
from pathlib import Path
import torch

NAMES = ('position','expert_w1','expert_b1','expert_w2','expert_b2','occupancy.weight','side.weight','norm1.weight','norm1.bias','query.weight','key.weight','value.weight','projection.weight','readout.weight','readout.bias','norm2.weight','norm2.bias','router.weight','router.bias','output.weight','output.bias')
BULK = {'expert_w1','expert_w2','query.weight','key.weight','value.weight','projection.weight','readout.weight'}
MATRICES = BULK | {'router.weight','output.weight'}


def _round_float(x):
    return torch.sign(x)*torch.floor(x.abs()+.5)


def convert(checkpoint, bulk_bits=8, frac=8):
    """No training; per-output-row symmetric power-of-two matrix scales."""
    if bulk_bits not in (4,8) or frac not in range(6,11):
        raise ValueError('unsupported precision')
    cfg=checkpoint['config']; tensors={}
    for name in NAMES:
        x=checkpoint['state_dict'][name].detach().cpu()
        if name in MATRICES:
            bits=bulk_bits if name in BULK else 8
            # Expert storage preserves source [expert,input,output] orientation.
            rows=x.transpose(-1,-2) if name.startswith('expert_w') else x
            maximum=rows.abs().amax(-1).clamp_min(1e-12)
            exps=torch.ceil(torch.log2(maximum/((1<<(bits-1))-1))).to(torch.int64)
            q=_round_float(rows/(2.**exps)[...,None]).to(torch.int64)
            codes=q.transpose(-1,-2) if name.startswith('expert_w') else q
            exponents=exps.flatten().tolist()
        else:
            bits=16; exponents=[-frac]
            codes=_round_float(x*(1<<frac)).to(torch.int64)
        if bool((codes.abs()>(1<<(bits-1))-1).any()):
            raise ValueError('conversion overflow '+name)
        tensors[name]=dict(codes=codes,exponents=exponents,bits=bits)
    scale=1<<frac
    tables=dict(exp=[int(math.floor(math.exp(-i/32)*32768+.5)) for i in range(513)],
                gelu=[int(math.copysign(math.floor(abs((i/32)*(1+math.erf((i/32)/math.sqrt(2)))/2)*scale+.5),(i/32))) for i in range(-256,257)])
    return dict(frac=frac,width=cfg['width'],expert_width=cfg['expert_width'],attention_factor=int(32768/math.sqrt(cfg['width'])+.5),tensors=tensors,tables=tables)


def save(candidate,path):
    header=struct.pack('<4sBBBBH',b'F9I1',candidate['frac'],candidate['width'],candidate['expert_width'],len(NAMES),candidate['attention_factor'])
    descriptors=bytearray(); payload=bytearray()
    for name in NAMES:
        t=candidate['tensors'][name]; q=t['codes']; exps=t['exponents']; bits=t['bits']
        descriptors.extend(struct.pack('<BBH',bits,q.ndim,len(exps)))
        descriptors.extend(bytes(q.shape)); descriptors.extend(struct.pack('<'+'b'*len(exps),*exps))
        values=q.flatten().tolist()
        if bits==4:
            payload.extend(sum((values[j+k]&15)<<(4*k) for k in range(min(2,len(values)-j))) for j in range(0,len(values),2))
        else:
            payload.extend(struct.pack('<'+{8:'b',16:'h'}[bits]*len(values),*values))
    tables=struct.pack('<513H513h',*candidate['tables']['exp'],*candidate['tables']['gelu'])
    raw=header+descriptors+payload+tables
    Path(path).parent.mkdir(parents=True,exist_ok=True); Path(path).write_bytes(raw)
    return dict(total_bytes=len(raw),header_bytes=len(header),descriptor_bytes=len(descriptors),parameter_bytes=len(payload),lut_bytes=len(tables))


def load(path):
    """Reject malformed layouts before any inference uses decoded tensors."""
    try:
        return _load(path)
    except (struct.error,IndexError,RuntimeError,OverflowError) as exc:
        raise ValueError('malformed artifact') from exc


def _load(path):
    raw=Path(path).read_bytes()
    if len(raw)<10: raise ValueError('short artifact')
    magic,frac,d,h,count,factor=struct.unpack_from('<4sBBBBH',raw)
    if magic!=b'F9I1' or count!=len(NAMES) or not 6<=frac<=10 or not d or not h:
        raise ValueError('invalid header')
    pos=10; descriptors=[]
    for name in NAMES:
        bits,rank,n=struct.unpack_from('<BBH',raw,pos); pos+=4
        if bits not in (4,8,16) or rank not in (1,2,3) or not n: raise ValueError('invalid descriptor')
        shape=tuple(raw[pos:pos+rank]); pos+=rank
        exps=list(struct.unpack_from('<'+'b'*n,raw,pos)); pos+=n
        size=math.prod(shape); length=(size*bits+7)//8
        expected={
            'position':(9,d),'expert_w1':(9,d,h),'expert_w2':(9,h,d),
            'expert_b1':(9,h),'expert_b2':(9,d),'occupancy.weight':(3,d),
            'side.weight':(2,d),'readout.weight':(d,9*d),
            'router.weight':(9,d),'output.weight':(9,d),
            'router.bias':(9,),'output.bias':(9,),
        }.get(name,(d,d) if name in MATRICES else (d,))
        exponent_count=(9*shape[-1] if name.startswith('expert_w') else shape[0]) if name in MATRICES else 1
        if shape!=expected or n!=exponent_count or any(e< -24 or e>16 for e in exps):
            raise ValueError('incompatible tensor layout')
        if name not in MATRICES and (bits!=16 or exps!=[-frac]):
            raise ValueError('incompatible affine scale')
        if name in MATRICES and bits not in ((4,8) if name in BULK else (8,)):
            raise ValueError('incompatible matrix precision')
        descriptors.append(dict(name=name,bits=bits,shape=shape,exponents=exps,length=length,size=size))
    tensors={}
    for entry in descriptors:
        entry['offset']=pos; payload=raw[pos:pos+entry['length']];pos+=entry['length']
        bits=entry['bits']; size=entry['size']
        if bits==4:
            values=[(b>>s)&15 for b in payload for s in (0,4)][:size]
            values=[v-16 if v>=8 else v for v in values]
            if size%2 and payload[-1]&240: raise ValueError('nonzero nibble padding')
        else:
            values=struct.unpack('<'+{8:'b',16:'h'}[bits]*size,payload)
        tensors[entry['name']]=dict(codes=torch.tensor(values,dtype=torch.int64).reshape(entry['shape']),bits=bits,exponents=entry['exponents'])
    if len(raw)!=pos+2052: raise ValueError('artifact length')
    exp=list(struct.unpack_from('<513H',raw,pos)); gelu=list(struct.unpack_from('<513h',raw,pos+1026))
    return dict(frac=frac,width=d,expert_width=h,attention_factor=factor,tensors=tensors,tables=dict(exp=exp,gelu=gelu),descriptors=descriptors)
