"""Exact finite-domain two-coordinate head certificates, no neural shortcut."""
import numpy as np

def rounded(a,d):
    a=np.asarray(a,dtype=np.int64)
    return np.where(a>=0,(np.abs(a)+d//2)//d,-((np.abs(a)+d//2)//d))

def extrema(other,activation,d,weights,biases):
    """Unclamped extrema; signed32 clamp cannot change membership sign."""
    dot0=other+activation*weights[0];dot1=other+activation*weights[1]
    return rounded(np.minimum(dot0,dot1),d)+biases[0],rounded(np.maximum(dot0,dot1),d)+biases[1]

def bias_bands(other,activation,d,members,weights,code_lo=-32768,code_hi=32767):
    lows=[];highs=[]
    for start in range(0,len(weights),512):
        ww=weights[start:start+512]
        scaled=rounded(other[None,:]+ww[:,None]*activation[None,:],d)
        lower=np.maximum(code_lo,(-scaled[:,members]).max(1))
        upper=np.minimum(code_hi,(-scaled[:,~members]-1).min(1))
        lows.extend(lower.tolist());highs.extend(upper.tolist())
    return np.array(lows,dtype=np.int64),np.array(highs,dtype=np.int64)

def shrink(interval,old,k):
    assert 0<=k<=16 and interval[0]<=old<=interval[1]
    return [old+(1 if v>=old else -1)*(abs(v-old)*k//16) for v in interval]
