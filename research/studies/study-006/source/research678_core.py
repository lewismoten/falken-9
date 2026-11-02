"""Isolated frozen-model research 006-008; no deployment changes."""
import copy
import numpy as np
import torch
from falken9.integer_model import round_div
from falken9.canonical_integer import CanonicalIntegerPolicy

def mix_exact(x, expert_outputs, pairs, gates):
    if pairs.shape!=gates.shape or pairs.ndim!=2 or pairs.shape[1]!=2 or bool((gates<0).any()) or not bool((gates.sum(1)==32768).all()):
        raise ValueError('invalid top2 Q15 gates')
    if bool((pairs[:,0]==pairs[:,1]).any()) or bool((pairs<0).any()) or bool((pairs>=expert_outputs.shape[1]).any()):raise ValueError('invalid pair')
    chosen=expert_outputs[torch.arange(len(x))[:,None],pairs]
    return (x+round_div((chosen*gates[:,:,None]).sum(1),32768)).clamp(-(1<<31),(1<<31)-1)

def patch_outputs(receiver,donor,experts):
    if receiver.shape!=donor.shape or receiver.ndim!=3 or any(e<0 or e>=receiver.shape[1] for e in experts):raise ValueError('invalid expert-ID patch')
    out=receiver.clone();out[:,list(experts)]=donor[:,list(experts)];return out

def mutate_code(c,name,coord,delta):
    if delta not in (-1,1):raise ValueError('one code only')
    t=c['tensors'][name];old=int(t['codes'][coord]);new=old+delta;bits=t['bits']
    if not -(1<<(bits-1))<=new<(1<<(bits-1)):raise ValueError('stored code overflow')
    out=copy.deepcopy(c);out['tensors'][name]['codes'][coord]=new;return out

def sign_census(old,new,legal):
    a=np.asarray(old)>=0;b=np.asarray(new)>=0;l=np.asarray(legal,dtype=bool)
    return dict(negative_to_nonnegative=int((~a&b&l).sum()),nonnegative_to_negative=int((a&~b&l).sum()),occupied_sign_flips=int(((a!=b)&~l).sum()))

def all_experts(c,z):
    q=CanonicalIntegerPolicy(copy.deepcopy(c));outputs=[];hidden=[]
    for e in range(c['experts']):
        h=q.gelu(q.linear(z,'expert_w1','expert_b1',e));hidden.append(h)
        outputs.append(q.linear(h,'expert_w2','expert_b2',e))
    return torch.stack(outputs,1),torch.stack(hidden,1)
