import math
import importlib
import torch
from falken9.canonical_integer_export import convert,save,load
from falken9.canonical_model import decode_model
from test_canonical_integer_export import SOURCE


def scalar_oracle(c,board):
    """Independent Python arbitrary-int forward; no production arithmetic calls."""
    S=1<<c['frac']; d=c['width']; ts=c['tensors']
    def rd(a,b): return (1 if a>=0 else -1)*((abs(a)+b//2)//b)
    def sat(a,output=False):
        n=c['output_bits'] if output else c['activation_bits']
        return max(-(1<<(n-1)),min((1<<(n-1))-1,a))
    def vec(name): return ts[name]['codes'].tolist()
    def linear(x,name,expert=None,bias=None):
        w=vec(name); exps=ts[name]['exponents']
        if expert is not None:
            w=list(map(list,zip(*w[expert]))); exps=exps[expert*len(w):(expert+1)*len(w)]
        out=[]
        for row,e in zip(w,exps):
            dot=sum(a*b for a,b in zip(x,row)); out.append(dot*(1<<e) if e>=0 else rd(dot,1<<-e))
        if bias:
            b=vec(bias); b=b[expert] if expert is not None else b; out=[a+b for a,b in zip(out,b)]
        return [sat(a,name=='output.weight') for a in out]
    def norm(x,name):
        mean=rd(sum(x),d); z=[a-mean for a in x]
        root=math.isqrt(rd(sum(a*a for a in z),d)+max(1,(S*S+50000)//100000))
        return [sat(rd(rd(a*S,root)*g,S)+b) for a,g,b in zip(z,vec(name+'.weight'),vec(name+'.bias'))]
    def lookup(x,table,offset=0):
        if not c['interpolate']: return table[max(0,min(512,rd(x*32,S)+offset))]
        u=x*32+offset*S; i,r=divmod(max(0,min(512*S,u)),S)
        return table[512] if i==512 else rd(table[i]*(S-r)+table[i+1]*r,S)
    def soft(x):
        top=max(x); ex=[lookup(top-a,c['tables']['exp']) for a in x]; total=sum(ex)
        p=[a*32768//total for a in ex];p[x.index(top)]+=32768-sum(p); return p
    def gelu(x): return [sat(a if a>8*S else 0 if a< -8*S else lookup(a,c['tables']['gelu'],256)) for a in x]
    side=sum(a!=0 for a in board)%2
    x=[[sat(a+b+v) for a,b,v in zip(vec('occupancy.weight')[v],vec('position')[i],vec('side.weight')[side])] for i,v in enumerate(board)]
    z=[norm(a,'norm1') for a in x]
    q,k,v=([linear(a,n+'.weight') for a in z] for n in ('query','key','value'))
    attended=[]
    for qi in q:
        scores=[]
        for kj in k:
            dot=sum(a*b for a,b in zip(qi,kj))
            if c['attention_mode']=='early': score=rd(rd(dot,S)*c['attention_factor'],c['attention_denominator'])
            else: score=rd(dot*c['attention_factor'],S*c['attention_denominator'])
            scores.append(sat(score))
        p=soft(scores); attended.append([sat(rd(sum(pj*vj[l] for pj,vj in zip(p,v)),32768)) for l in range(d)])
    residual=[[sat(a+b) for a,b in zip(row,linear(att,'projection.weight'))] for row,att in zip(x,attended)]
    x=gelu(linear(sum(residual,[]),'readout.weight',bias='readout.bias'))
    z=norm(x,'norm2'); scores=linear(z,'router.weight',bias='router.bias')
    routes=sorted(range(c['experts']),key=lambda i:(-scores[i],i))[:c['topk']]; gates=soft([scores[i] for i in routes])
    experts=[linear(gelu(linear(z,'expert_w1',i,'expert_b1')),'expert_w2',i,'expert_b2') for i in routes]
    merged=[sat(a+rd(sum(g*e[l] for g,e in zip(gates,experts)),32768)) for l,a in enumerate(x)]
    return linear(merged,'output.weight',bias='output.bias'),routes


def test_integer_forward_matches_independent_scalar_and_packet(tmp_path):
    m=importlib.import_module('falken9.canonical_integer')
    boards=torch.tensor([[0]*9,[1,2,0,0,1,0,2,0,0]])
    for mode in ('legacy','early','rational'):
        c=convert(decode_model(SOURCE.read_bytes()),frac=10,attention_mode=mode)
        path=tmp_path/'model.f9j';save(c,path)
        runtime=m.CanonicalIntegerPolicy(load(path)); actual,routes=runtime(boards,True)
        assert torch.equal(actual,m.CanonicalIntegerPolicy(c)(boards))
        for i,board in enumerate(boards.tolist()):
            expected,route=scalar_oracle(c,board)
            assert actual[i].tolist()==expected
            assert routes[i].tolist()==route
        assert runtime.predict_history('') in 'ebdfhcgia'
        assert runtime.stats['accumulators']['output.weight.prefix'] >= runtime.stats['accumulators']['output.weight.dot']
        assert runtime.stats['matrix_dot_envelope_bounds']['output.weight'] >= runtime.stats['accumulators']['output.weight.prefix']
