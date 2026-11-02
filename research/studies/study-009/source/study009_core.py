"""Packet-derived study009 diagnostic helpers, not a deployment export."""
def coarsen_row(codes, exponent):
    def rounded(v,k):
        return (1 if v>=0 else -1)*((abs(v)+(1<<(k-1) if k else 0))//(1<<k))
    k=0
    while any(abs(rounded(int(v),k))>127 for v in codes): k+=1
    raw=[rounded(int(v),k) for v in codes]
    q=[max(-127,min(127,v)) for v in raw]
    assert -128<=exponent+k<=127
    return q,exponent+k,k,sum(a!=b for a,b in zip(raw,q))

import copy
import torch
from falken9.strategy_diagnostics import DiagnosticPolicy


def approximate(packet,name):
    out=copy.deepcopy(packet);t=packet['tensors'][name];codes=t['codes']
    assert t['bits']==16 and codes.ndim==2
    rows=[coarsen_row(row,int(e)) for row,e in zip(codes.tolist(),t['exponents'])]
    new=torch.tensor([r[0] for r in rows],dtype=torch.int64)
    exps=[r[1] for r in rows]
    out['tensors'][name]=dict(t,codes=new,exponents=exps,bits=8)
    meta=dict(name=name,shape=list(codes.shape),old_codes=codes.tolist(),old_exponents=t['exponents'],codes=new.tolist(),exponents=exps,shifts=[r[2] for r in rows],clipped=sum(r[3] for r in rows),old_tensor_payload_bytes=codes.numel()*2+len(exps),new_tensor_payload_bytes=codes.numel()+len(exps),hypothetical_packet_bytes=5195-codes.numel(),note='Packet-derived approximation; not historical float-master INT8 export. No deployment packet written.')
    return out,meta


class CutPolicy(DiagnosticPolicy):
    def __init__(self,packet,cut=None,value=None):
        super().__init__(packet);self.cut=cut;self.replacement=value
    def linear(self,x,name,bias=None,expert=None):
        result=super().linear(x,name,bias,expert)
        if name=='router.weight' and self.cut=='router_scores':
            assert self.replacement.shape==result.shape
            result=self.replacement.clone();self.stages['router_scores']=result.clone()
            self._routes=torch.argsort(result,descending=True,stable=True)[:,:self.c['topk']]
        return result
    def sat(self,x,name):
        result=super().sat(x,name)
        if name=='expert.residual' and self.cut=='merged':
            assert self.replacement.shape==result.shape
            result=self.replacement.clone();self.stages['merged']=result.clone()
        return result
