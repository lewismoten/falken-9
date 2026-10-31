import importlib
import math
import torch


def test_signed_rounding_and_exact_isqrt():
    m = importlib.import_module('falken9.integer_model')
    assert m.round_div(torch.tensor([-5,-3,-1,0,1,3,5]),2).tolist() == [-3,-2,-1,0,1,2,3]
    values = [0,1,2,3,4,2147483647,34359738368]
    assert m.integer_sqrt(torch.tensor(values)).tolist() == [math.isqrt(x) for x in values]


def test_whole_network_matches_independent_python_integer_oracle(tmp_path):
    from falken9.integer_export import convert,save,load
    from falken9 import integer_model as m
    c=torch.load('artifacts/training/float-search/w8-h8-float/best.pt',map_location='cpu',weights_only=False)
    candidate=convert(c,frac=6)
    path=tmp_path/'model.f9i'; save(candidate,path)
    boards=[[0]*9,[1,2,0,0,1,0,2,0,0],[1,2,1,2,1,2,0,0,0]]
    runtime=m.IntegerPolicy(load(path))
    logits,routes=runtime(torch.tensor(boards),return_routes=True)
    for i,board in enumerate(boards):
        expected,route=scalar_oracle(candidate,board)
        assert logits[i].tolist()==expected
        assert routes[i].tolist()==route
    assert m.select_moves(torch.zeros((1,9),dtype=torch.int64),torch.zeros((1,9),dtype=torch.int64)).item()==4
    assert runtime.stats['saturations']==0


def scalar_oracle(c,board):
    """Independent Python arbitrary-width forward, no production arithmetic."""
    S=1<<c['frac']; d=c['width']; ts=c['tensors']
    def rd(a,b): return (1 if a>=0 else -1)*((abs(a)+b//2)//b)
    def sat(a): return max(-32768,min(32767,a))
    def vec(name): return ts[name]['codes'].tolist()
    def linear(x,name,expert=None,bias=None):
        w=vec(name); exps=ts[name]['exponents']
        if expert is not None:
            w=list(map(list,zip(*w[expert]))); exps=exps[expert*len(w):(expert+1)*len(w)]
        result=[]
        for row,e in zip(w,exps):
            acc=sum(a*b for a,b in zip(x,row))
            result.append(acc*(1<<e) if e>=0 else rd(acc,1<<-e))
        if bias is not None:
            b=vec(bias); b=b[expert] if expert is not None else b
            result=[a+v for a,v in zip(result,b)]
        return [sat(a) for a in result]
    def norm(x,prefix):
        mean=rd(sum(x),d); centered=[v-mean for v in x]
        var=rd(sum(v*v for v in centered),d)+max(1,(S*S+50000)//100000)
        root=math.isqrt(var)
        return [sat(rd(rd(v*S,root)*g,S)+b) for v,g,b in zip(centered,vec(prefix+'.weight'),vec(prefix+'.bias'))]
    def soft(x):
        maximum=max(x); idx=[min(512,rd((maximum-v)*32,S)) for v in x]
        exp=[c['tables']['exp'][i] for i in idx]; total=sum(exp)
        p=[v*32768//total for v in exp]; p[x.index(maximum)]+=32768-sum(p)
        return p
    def gelu(x):
        return [sat(v if v>8*S else 0 if v< -8*S else c['tables']['gelu'][rd(v*32,S)+256]) for v in x]
    side=sum(v!=0 for v in board)%2
    x=[[sat(a+b+cc) for a,b,cc in zip(vec('occupancy.weight')[v],vec('position')[i],vec('side.weight')[side])] for i,v in enumerate(board)]
    z=[norm(row,'norm1') for row in x]
    q,k,v=([linear(row,name+'.weight') for row in z] for name in ['query','key','value'])
    attended=[]
    for qi in q:
        scores=[sat(rd(sum(a*b for a,b in zip(qi,kj))*c['attention_factor'],S*32768)) for kj in k]
        p=soft(scores)
        attended.append([sat(rd(sum(pj*vj[lane] for pj,vj in zip(p,v)),32768)) for lane in range(d)])
    residual=[[sat(a+b) for a,b in zip(row,linear(att,'projection.weight'))] for row,att in zip(x,attended)]
    x=gelu(linear(sum(residual,[]),'readout.weight',bias='readout.bias'))
    z=norm(x,'norm2'); scores=linear(z,'router.weight',bias='router.bias')
    routes=sorted(range(9),key=lambda i:(-scores[i],i))[:2]; gates=soft([scores[i] for i in routes])
    experts=[linear(gelu(linear(z,'expert_w1',i,'expert_b1')),'expert_w2',i,'expert_b2') for i in routes]
    merged=[sat(a+rd(sum(g*e[l] for g,e in zip(gates,experts)),32768)) for l,a in enumerate(x)]
    return linear(merged,'output.weight',bias='output.bias'),routes
