"""Integer-only host reference. Offline conversion is in integer_export."""
import torch

TIE_ORDER = (4,1,3,5,7,2,6,8,0)


def round_div(x, denominator):
    """Nearest integer, halfway away from zero; positive denominator."""
    return torch.sign(x) * ((x.abs() + denominator//2)//denominator)


def integer_sqrt(x):
    """Exact floor sqrt without floating initialization; input <= 2**62-1."""
    if bool((x < 0).any()) or bool((x >= 2**62).any()):
        raise ValueError('isqrt domain')
    root = torch.zeros_like(x)
    for bit in range(30,-1,-1):
        candidate = root | (1 << bit)
        root = torch.where(candidate*candidate <= x,candidate,root)
    return root


def select_moves(logits, boards):
    order=torch.tensor(TIE_ORDER)
    masked=logits.masked_fill(boards!=0,-(1<<62))
    return order[masked[:,order].argmax(-1)]


class IntegerPolicy:
    """INT64 host operations, INT16 stored activations; no floating inference."""
    def __init__(self,candidate):
        self.c=candidate; self.S=1<<candidate['frac']; self.d=candidate['width']
        self.t=candidate['tensors']
        self.exp=torch.tensor(candidate['tables']['exp'],dtype=torch.int64)
        self.gelu_table=torch.tensor(candidate['tables']['gelu'],dtype=torch.int64)
        self.stats=dict(saturations=0,maximum_abs_accumulator=0,accumulators={},saturation_by_stage={})

    def observe(self,x,name):
        maximum=int(x.abs().max()) if x.numel() else 0
        self.stats['maximum_abs_accumulator']=max(self.stats['maximum_abs_accumulator'],maximum)
        self.stats['accumulators'][name]=max(self.stats['accumulators'].get(name,0),maximum)
        return x

    def sat(self,x,name):
        n=int(((x< -32768)|(x>32767)).sum())
        self.stats['saturations']+=n
        self.stats['saturation_by_stage'][name]=self.stats['saturation_by_stage'].get(name,0)+n
        return x.clamp(-32768,32767)

    def linear(self,x,name,bias=None,expert=None):
        t=self.t[name]; w=t['codes']; exps=t['exponents']
        if expert is not None:
            w=w[expert].T
            exps=exps[expert*len(w):(expert+1)*len(w)]
        acc=self.observe(x@w.T,name+'.dot')
        e=torch.tensor(exps)
        # Exponents are offline constants. Clamp inactive shift arms to avoid
        # undefined negative shifts even though torch.where discards those arms.
        y=torch.where(e>=0,acc*(1<<e.clamp_min(0)),round_div(acc,1<<(-e).clamp_min(0)))
        if bias is not None:
            b=self.t[bias]['codes']; y=y+(b[expert] if expert is not None else b)
        return self.sat(y,name)

    def norm(self,x,prefix):
        mean=round_div(x.sum(-1,keepdim=True),self.d)
        centered=x-mean
        squares=self.observe((centered*centered).sum(-1,keepdim=True),prefix+'.square_sum')
        var=round_div(squares,self.d)+max(1,(self.S*self.S+50000)//100000)
        root=integer_sqrt(var)
        normalized=round_div(centered*self.S,root)
        affine=self.observe(normalized*self.t[prefix+'.weight']['codes'],prefix+'.affine')
        return self.sat(round_div(affine,self.S)+self.t[prefix+'.bias']['codes'],prefix)

    def softmax(self,scores):
        maximum=scores.max(-1,keepdim=True).values
        index=round_div((maximum-scores)*32,self.S).clamp(0,512)
        exp=self.exp[index]; total=exp.sum(-1,keepdim=True)
        numer=self.observe(exp*32768,'softmax.numerator')
        p=numer//total
        winner=scores.argmax(-1,keepdim=True)
        p.scatter_add_(-1,winner,32768-p.sum(-1,keepdim=True))
        return p

    def gelu(self,x):
        index=round_div(x*32,self.S).clamp(-256,256)+256
        return self.sat(torch.where(x>8*self.S,x,torch.where(x< -8*self.S,0,self.gelu_table[index])),'gelu')

    def __call__(self,boards,return_routes=False):
        if boards.dtype!=torch.int64 or boards.ndim!=2 or boards.shape[1]!=9 or bool(((boards<0)|(boards>2)).any()):
            raise ValueError('boards must be INT64 occupancy Bx9 in 0..2')
        side=(boards!=0).sum(-1)%2
        x=self.sat(self.t['occupancy.weight']['codes'][boards]+self.t['position']['codes']+self.t['side.weight']['codes'][side,None,:],'embedding')
        z=self.norm(x,'norm1')
        q,k,v=[self.linear(z,n+'.weight') for n in ['query','key','value']]
        dots=self.observe(q@k.transpose(-1,-2),'attention.dot')
        scaled=self.observe(dots*self.c['attention_factor'],'attention.scaled')
        scores=self.sat(round_div(scaled,self.S*32768),'attention.score')
        p=self.softmax(scores)
        attended=self.sat(round_div(self.observe(p@v,'attention.weighted'),32768),'attention.value')
        x=self.sat(x+self.linear(attended,'projection.weight'),'attention.residual')
        x=self.gelu(self.linear(x.flatten(1),'readout.weight','readout.bias'))
        z=self.norm(x,'norm2')
        scores=self.linear(z,'router.weight','router.bias')
        routes=torch.argsort(scores,descending=True,stable=True)[:,:2]
        gates=self.softmax(scores.gather(1,routes))
        experts=torch.zeros((len(x),2,self.d),dtype=torch.int64)
        for expert in range(9):
            rows,slots=(routes==expert).nonzero(as_tuple=True)
            if not len(rows): continue
            hidden=self.gelu(self.linear(z[rows],'expert_w1','expert_b1',expert))
            experts[rows,slots]=self.linear(hidden,'expert_w2','expert_b2',expert)
        mix=self.observe((experts*gates[:,:,None]).sum(1),'expert.weighted')
        merged=self.sat(x+round_div(mix,32768),'expert.residual')
        logits=self.linear(merged,'output.weight','output.bias')
        return (logits,routes) if return_routes else logits
