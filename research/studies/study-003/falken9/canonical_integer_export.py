"""F9J2 materialized integer packet. Floating math is OFFLINE conversion only."""
import math
import struct
from pathlib import Path
import torch
from falken9.integer_export import NAMES, MATRICES
from falken9.symmetry import TRANSFORMS

HEADER='<4s10BHH'
MODES=('legacy','early','rational')
WRAPPER=bytes([v for p in TRANSFORMS for v in p]+[ord(m)-97 for m in 'ebdfhcgia'])


def convert(model,frac=10,matrix_bits=16,activation_bits=32,attention_mode='rational',interpolate=True):
    if frac not in range(6,12) or matrix_bits not in (8,16) or activation_bits not in (16,32) or attention_mode not in MODES:
        raise ValueError('unsupported contract')
    tensors={}; S=1<<frac
    for name,x in model.state_dict().items():
        x=x.detach().cpu()
        if name in MATRICES:
            rows=x.transpose(-1,-2) if name.startswith('expert_w') else x
            exps=torch.ceil(torch.log2(rows.abs().amax(-1).clamp_min(1e-12)/((1<<(matrix_bits-1))-1))).long()
            q=torch.sign(rows)*torch.floor(rows.abs()/(2.**exps)[...,None]+.5)
            codes=q.long().transpose(-1,-2) if name.startswith('expert_w') else q.long()
            bits=matrix_bits; exponents=exps.flatten().tolist()
        else:
            codes=(torch.sign(x)*torch.floor(x.abs()*S+.5)).long(); bits=16; exponents=[-frac]
        if bool(((codes<-(1<<(bits-1)))|(codes>(1<<(bits-1))-1)).any()): raise ValueError('parameter overflow '+name)
        tensors[name]=dict(codes=codes,bits=bits,exponents=exponents)
    d=model.config.width
    # 181/512 approximates 1/sqrt(8); general widths use Q9 nearest.
    factor=int((512 if attention_mode=='rational' else 32768)/math.sqrt(d)+.5)
    denominator=512 if attention_mode=='rational' else 32768
    tables=dict(exp=[int(math.exp(-i/32)*32768+.5) for i in range(513)],gelu=[])
    for i in range(-256,257):
        value=(i/32)*(1+math.erf(i/32/math.sqrt(2)))/2*S
        tables['gelu'].append(int(math.copysign(math.floor(abs(value)+.5),value)))
    return dict(frac=frac,width=d,expert_width=model.config.expert_width,experts=tensors['expert_w1']['codes'].shape[0],topk=2,activation_bits=activation_bits,output_bits=32,attention_mode=attention_mode,attention_factor=factor,attention_denominator=denominator,interpolate=interpolate,tensors=tensors,tables=tables,wrapper=WRAPPER)


def save(c,path):
    header=struct.pack(HEADER,b'F9J2',c['frac'],c['width'],c['expert_width'],c['experts'],c['topk'],c['activation_bits'],c['output_bits'],MODES.index(c['attention_mode']),int(c['interpolate']),len(NAMES),c['attention_factor'],c['attention_denominator'])
    descriptors=bytearray(); payload=bytearray()
    for name in NAMES:
        t=c['tensors'][name]; q=t['codes']; exps=t['exponents']
        descriptors.extend(struct.pack('<BBH',t['bits'],q.ndim,len(exps))); descriptors.extend(bytes(q.shape)); descriptors.extend(struct.pack('<'+'b'*len(exps),*exps))
        values=q.flatten().tolist(); payload.extend(struct.pack('<'+('b' if t['bits']==8 else 'h')*len(values),*values))
    tables=struct.pack('<513H513h',*c['tables']['exp'],*c['tables']['gelu'])
    raw=header+c['wrapper']+descriptors+payload+tables
    Path(path).parent.mkdir(parents=True,exist_ok=True); Path(path).write_bytes(raw)
    return dict(total_bytes=len(raw),header_bytes=len(header),wrapper_bytes=len(c['wrapper']),descriptor_and_scale_bytes=len(descriptors),parameter_bytes=len(payload),lut_bytes=len(tables),alignment_bytes=0)


def load(path):
    try: return _load(Path(path).read_bytes())
    except (struct.error,IndexError,RuntimeError,OverflowError) as exc: raise ValueError('malformed packet') from exc


def _load(raw):
    magic,F,d,h,E,K,ab,ob,mode,interp,count,factor,den=struct.unpack_from(HEADER,raw)
    if magic!=b'F9J2' or F not in range(6,12) or not d or not h or not 1<=K<=E or ab not in (16,32) or ob!=32 or mode>=len(MODES) or interp not in (0,1) or count!=len(NAMES) or not factor or den!=(512 if mode==2 else 32768): raise ValueError('invalid header')
    pos=struct.calcsize(HEADER); wrapper=raw[pos:pos+81]; pos+=81
    if wrapper!=WRAPPER: raise ValueError('invalid coordinate wrapper')
    descriptors=[]
    expected={'position':(9,d),'expert_w1':(E,d,h),'expert_w2':(E,h,d),'expert_b1':(E,h),'expert_b2':(E,d),'occupancy.weight':(3,d),'side.weight':(2,d),'readout.weight':(d,9*d),'router.weight':(E,d),'output.weight':(9,d),'router.bias':(E,),'output.bias':(9,)}
    for name in NAMES:
        bits,rank,n=struct.unpack_from('<BBH',raw,pos); pos+=4
        if bits not in (8,16) or rank not in (1,2,3) or not n: raise ValueError('invalid descriptor')
        shape=tuple(raw[pos:pos+rank]);pos+=rank
        exps=list(struct.unpack_from('<'+'b'*n,raw,pos));pos+=n
        shape_expected=expected.get(name,(d,d) if name in MATRICES else (d,))
        nc=(E*shape[-1] if name.startswith('expert_w') else shape[0]) if name in MATRICES else 1
        if shape!=shape_expected or n!=nc or any(e < -30 or e>8 for e in exps): raise ValueError('invalid tensor layout')
        if name not in MATRICES and (bits!=16 or exps!=[-F]): raise ValueError('invalid affine')
        descriptors.append((name,bits,shape,exps))
    tensors={}
    for name,bits,shape,exps in descriptors:
        size=math.prod(shape); values=struct.unpack_from('<'+('b' if bits==8 else 'h')*size,raw,pos);pos+=size*bits//8
        tensors[name]=dict(codes=torch.tensor(values,dtype=torch.int64).reshape(shape),bits=bits,exponents=exps)
    if len(raw)!=pos+2052: raise ValueError('packet length')
    exp=list(struct.unpack_from('<513H',raw,pos)); gelu=list(struct.unpack_from('<513h',raw,pos+1026))
    if exp[0]!=32768 or any(a<b for a,b in zip(exp,exp[1:])): raise ValueError('invalid exponent table')
    return dict(frac=F,width=d,expert_width=h,experts=E,topk=K,activation_bits=ab,output_bits=ob,attention_mode=MODES[mode],interpolate=bool(interp),attention_factor=factor,attention_denominator=den,tensors=tensors,tables=dict(exp=exp,gelu=gelu),wrapper=wrapper)
