"""Study005 only: CPU-copy attention interventions, no deployment imports."""
import copy
import numpy as np
import torch
from falken9.strategy_diagnostics import DiagnosticPolicy
Q15=32768
LINES=tuple(tuple(3*r+c for c in range(3)) for r in range(3))+tuple(tuple(3*r+c for r in range(3)) for c in range(3))+((0,4,8),(2,4,6))

def apportion(weights,total):
    """Exact nonnegative integer mass. Floor then largest remainder, low-index tie."""
    w=np.asarray(weights,dtype=np.int64)
    if w.ndim!=1 or np.any(w<0) or total<0:raise ValueError('invalid mass')
    if not len(w):
        if total:raise ValueError('empty support')
        return w.copy()
    den=int(w.sum())
    if not den:w=np.ones(len(w),dtype=np.int64);den=len(w)
    n=w*int(total);v=n//den;rem=n%den
    for j in sorted(range(len(w)),key=lambda j:(-int(rem[j]),j))[:int(total-v.sum())]:v[j]+=1
    assert int(v.sum())==total
    return v

def masks(lines):
    m=np.zeros((9,9),dtype=bool)
    for line in lines:
        for q in line:
            for k in line:
                if k!=q:m[q,k]=True
    control=np.zeros_like(m)
    for q in range(9):
        n=int(m[q].sum());pool=[k for k in range(9) if k!=q and not m[q,k]]
        if n>len(pool):raise ValueError('no disjoint size control')
        control[q,pool[:n]]=True
    return m,control

def relocate_mass(p,target,control,which,dose):
    """Equal target/control moved mass, per-row matched cardinality. No zeroing display."""
    p=np.asarray(p,dtype=np.int64);out=p.copy();m=target if which=='target' else control
    budgets=np.zeros(p.shape[:-1],dtype=np.int64)
    for i in range(len(p)):
        for q in range(9):
            a=np.flatnonzero(target[q]);b=np.flatnonzero(control[q]);src=np.flatnonzero(m[q]);dst=np.flatnonzero(~m[q])
            budget=min(int(p[i,q,a].sum()),int(p[i,q,b].sum()))*dose//2
            budgets[i,q]=budget
            if not budget:continue
            removed=apportion(p[i,q,src],budget)
            assert np.all(removed<=p[i,q,src])
            out[i,q,src]-=removed
            out[i,q,dst]+=apportion(p[i,q,dst],budget)
    assert np.all(out>=0) and np.all(out.sum(-1)==Q15)
    return out,budgets

def candidate_labels(b):
    side=1+sum(v!=0 for v in b)%2;out=[]
    for s in range(9):
        d={k:False for k in ('win','threat','fork')}
        if not b[s]:
            for mark,key in ((side,'win'),(3-side,'threat')):
                d[key]=any(s in line and sum(b[k]==mark for k in line)==2 and sum(b[k]==0 for k in line)==1 for line in LINES)
            after=list(b);after[s]=side
            wins={k for line in LINES if sum(after[j]==side for j in line)==2 and sum(after[j]==0 for j in line)==1 for k in line if after[k]==0}
            d['fork']=not d['win'] and len(wins)>=2
        out.append(d)
    return out

class Attention005(DiagnosticPolicy):
    def __init__(self,c,mode='noop',meanp=None,meanv=None,meanproj=None,group=None,which=None,dose=2):
        super().__init__(copy.deepcopy(c));self.mode=mode;self.meanp=meanp;self.meanv=meanv;self.meanproj=meanproj;self.group=group;self.which=which;self.dose=dose
        self.actual_probs=None;self.effective_probs=None;self.moved=None
    def softmax(self,scores):
        p=super().softmax(scores)
        if scores.ndim!=3:return p
        self.actual_probs=p.numpy().copy();v=self.actual_probs.copy()
        if self.mode=='uniform':v[:]=apportion(np.ones(9,dtype=np.int64),Q15)
        elif self.mode=='identity':v[:]=np.eye(9,dtype=np.int64)*Q15
        elif self.mode=='positionmean':v[:]=self.meanp
        elif self.mode=='halfpositionmean':
            v=np.array([[apportion(row,Q15) for row in board] for board in v+self.meanp])
        elif self.mode=='edges':v,self.moved=relocate_mass(v,*self.group,self.which,self.dose)
        self.effective_probs=v.copy();r=torch.from_numpy(v.copy());self._prob=r
        self.stages['attention_probs']=r.clone()
        return r
    def linear(self,x,name,bias=None,expert=None):
        r=super().linear(x,name,bias,expert)
        if name=='value.weight' and self.mode=='valuemean':
            r=torch.from_numpy(np.broadcast_to(self.meanv,r.shape).copy());self._v=r;self.stages['board_value']=r.clone()
        if name=='projection.weight' and self.mode=='projectionmean':
            r=torch.from_numpy(np.broadcast_to(self.meanproj,r.shape).copy());self.stages['projected']=r.clone()
        return r
