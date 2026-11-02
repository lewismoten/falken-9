"""F9J2 integer-only canonical full-set neural inference; no oracle/fallback."""
import torch
from falken9.integer_model import IntegerPolicy,round_div
from falken9.policy import board_from_history
from falken9.symmetry import canonicalize,restore_moves


class CanonicalIntegerPolicy(IntegerPolicy):
    def eval(self): return self
    def to(self,device):
        if str(device)!='cpu': raise ValueError('CPU integer reference only')
        return self

    def sat(self,x,name):
        bits=self.c['output_bits'] if name=='output.weight' else self.c['activation_bits']
        lo=-(1<<(bits-1)); hi=(1<<(bits-1))-1
        self.observe(x,name+'.preclamp')
        n=int(((x<lo)|(x>hi)).sum()); self.stats['saturations']+=n
        stages=self.stats['saturation_by_stage']; stages[name]=stages.get(name,0)+n
        return x.clamp(lo,hi)

    def linear(self,x,name,bias=None,expert=None):
        t=self.t[name]; w=t['codes']
        if expert is not None: w=w[expert].T
        # Measure sequential accumulation prefixes, not only final canceled dots.
        products=x.unsqueeze(-2)*w
        self.observe(products.cumsum(-1),name+'.prefix')
        bound=int(x.abs().max())*int(w.abs().max())*x.shape[-1]
        bounds=self.stats.setdefault('matrix_dot_envelope_bounds',{})
        bounds[name]=max(bounds.get(name,0),bound)
        return super().linear(x,name,bias,expert)

    def lookup(self,x,table,offset=0):
        if not self.c['interpolate']:
            return table[(round_div(x*32,self.S)+offset).clamp(0,512)]
        u=(x*32+offset*self.S).clamp(0,512*self.S)
        i=u//self.S; remainder=u%self.S
        return round_div(table[i]*(self.S-remainder)+table[(i+1).clamp_max(512)]*remainder,self.S)

    def softmax(self,scores):
        exp=self.lookup(scores.max(-1,keepdim=True).values-scores,self.exp)
        total=exp.sum(-1,keepdim=True)
        numer=self.observe(exp*32768,'softmax.numerator'); p=numer//total
        p.scatter_add_(-1,scores.argmax(-1,keepdim=True),32768-p.sum(-1,keepdim=True))
        return p

    def gelu(self,x):
        return self.sat(torch.where(x>8*self.S,x,torch.where(x< -8*self.S,0,self.lookup(x,self.gelu_table,256))),'gelu')

    def attention_scores(self,dots):
        if self.c['attention_mode']=='early':
            scaled=self.observe(round_div(dots,self.S)*self.c['attention_factor'],'attention.scaled')
            scores=round_div(scaled,self.c['attention_denominator'])
        else:
            scaled=self.observe(dots*self.c['attention_factor'],'attention.scaled')
            scores=round_div(scaled,self.S*self.c['attention_denominator'])
        return self.sat(scores,'attention.score')

    def __call__(self,boards,return_routes=False):
        if boards.dtype!=torch.int64 or boards.ndim!=2 or boards.shape[1]!=9 or bool(((boards<0)|(boards>2)).any()): raise ValueError('boards must be INT64 Bx9 occupancy')
        side=(boards!=0).sum(-1)%2
        x=self.sat(self.t['occupancy.weight']['codes'][boards]+self.t['position']['codes']+self.t['side.weight']['codes'][side,None,:],'embedding')
        z=self.norm(x,'norm1')
        q,k,v=[self.linear(z,n+'.weight') for n in ('query','key','value')]
        scores=self.attention_scores(self.observe(q@k.transpose(-1,-2),'attention.dot'))
        p=self.softmax(scores)
        attended=self.sat(round_div(self.observe(p@v,'attention.weighted'),32768),'attention.value')
        x=self.sat(x+self.linear(attended,'projection.weight'),'attention.residual')
        x=self.gelu(self.linear(x.flatten(1),'readout.weight','readout.bias'))
        z=self.norm(x,'norm2'); scores=self.linear(z,'router.weight','router.bias')
        routes=torch.argsort(scores,descending=True,stable=True)[:,:self.c['topk']]
        gates=self.softmax(scores.gather(1,routes))
        experts=torch.zeros((len(x),self.c['topk'],self.d),dtype=torch.int64)
        for expert in range(self.c['experts']):
            rows,slots=(routes==expert).nonzero(as_tuple=True)
            if not len(rows): continue
            hidden=self.gelu(self.linear(z[rows],'expert_w1','expert_b1',expert))
            experts[rows,slots]=self.linear(hidden,'expert_w2','expert_b2',expert)
        mix=self.observe((experts*gates[:,:,None]).sum(1),'expert.weighted')
        merged=self.sat(x+round_div(mix,32768),'expert.residual')
        logits=self.linear(merged,'output.weight','output.bias')
        return (logits,routes) if return_routes else logits

    def predict_history(self,history):
        board=board_from_history(history); canonical,transform=canonicalize(board)
        logits=self(torch.tensor([canonical],dtype=torch.int64))[0]
        members=[chr(97+i) for i in range(9) if canonical[i]==0 and int(logits[i])>=0]
        restored=restore_moves(members,transform)
        if not restored: raise ValueError('empty learned optimal set; no fallback')
        return restored[0]
