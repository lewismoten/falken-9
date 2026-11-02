"""Independent scalar audits of saved intervention arithmetic and wrapper behavior."""
import json,copy
from pathlib import Path
import numpy as np
from falken9.flexible_integer_export import load
from scripts.build_runtime import FOUR_MODEL
from research678_run import put

def rnd(x,d):return (1 if x>=0 else -1)*((abs(int(x))+d//2)//d)
def sat(x,bits=32):return max(-(1<<(bits-1)),min((1<<(bits-1))-1,int(x)))
def scalar_linear(x,c,name,bias,expert=None):
    t=c['tensors'][name];w=t['codes'].tolist();exps=t['exponents']
    if expert is not None:
        w=[list(v) for v in zip(*w[expert])];exps=exps[expert*len(w):(expert+1)*len(w)]
    b=c['tensors'][bias]['codes'].tolist() if bias else [0]*len(w)
    if expert is not None:b=b[expert]
    out=[]
    for j,row in enumerate(w):
        acc=sum(int(a)*int(v) for a,v in zip(x,row));e=exps[j];acc=acc*(1<<e) if e>=0 else rnd(acc,1<<-e)
        out.append(sat(acc+b[j],c['output_bits'] if name=='output.weight' else c['activation_bits']))
    return out

def look(x,table,c,offset=0):
    S=1<<c['frac'];u=max(0,min(512*S,x*32+offset*S));i,r=divmod(u,S)
    return rnd(table[i]*(S-r)+table[min(i+1,512)]*r,S)
def gates(scores,c):
    hi=max(scores);ex=[look(hi-v,c['tables']['exp'],c) for v in scores];total=sum(ex);p=[v*32768//total for v in ex];p[scores.index(hi)]+=32768-sum(p);return p

def head(x,eo,pair,g,c):
    z=[sat(x[u]+rnd(sum(eo[e][u]*g[k] for k,e in enumerate(pair)),32768)) for u in range(len(x))]
    return scalar_linear(z,c,'output.weight','output.bias')

def wrapper(y,base):
    order=(4,1,3,5,7,2,6,8,0);stats=dict(n=len(base['raw_boards']),empty=0,nonoptimal_nonempty=0,move_errors=0,set_changes=0,optimal_tie_changes=0,move_changes=0)
    # Baseline full sets independently invert canonical membership using raw->canonical map.
    for raw,ci,tr in zip(base['raw_boards'],base['raw_to_canonical_id'],base['raw_to_canonical_transform']):
        actual={s for s in range(9) if raw[s]==0 and y[ci][tr[s]]>=0};gold={s for s in range(9) if raw[s]==0 and base['logits'][ci][tr[s]]>=0}
        move=next((s for s in order if s in actual),-1);bm=next(s for s in order if s in gold);bad=move not in gold
        stats['empty']+=not bool(actual);stats['nonoptimal_nonempty']+=bool(actual) and bad;stats['move_errors']+=bad;stats['set_changes']+=actual!=gold;stats['optimal_tie_changes']+=(move!=bm and not bad);stats['move_changes']+=move!=bm
    return stats

def audit(stage,out):
    out=Path(out);read=lambda n:json.loads((out/n).read_text());b=read('baseline.json');c=load(FOUR_MODEL);checked=0;experts=0;gatechecks=0;wrappers=0
    # Audit ALL offline expert evaluations, including normally unselected experts.
    S=1<<c['frac']
    for i in range(627):
        for e in range(4):
            hp=scalar_linear(b['norm2'][i],c,'expert_w1','expert_b1',e)
            h=[sat(v if v>8*S else 0 if v< -8*S else look(v,c['tables']['gelu'],c,256)) for v in hp]
            assert h==b['expert_hidden_offline'][i][e],(i,e,'hidden')
            assert scalar_linear(h,c,'expert_w2','expert_b2',e)==b['expert_outputs_offline'][i][e],(i,e,'output');experts+=1
    for i in range(627):assert head(b['readout'][i],b['expert_outputs_offline'][i],b['routes'][i],b['gates'][i],c)==b['logits'][i]
    if stage=='006':
        specs={r['id']:r for r in read('interventions.json')}
        for v in read('vectors.json'):
            for i in range(627):
                assert head(b['readout'][i],b['expert_outputs_offline'][i],v['pairs'][i],v['gates'][i],c)==v['logits'][i],(v['id'],i);checked+=1
                if v['id'].endswith('renormalized'):
                    scores=[b['router_scores'][i][e] for e in v['pairs'][i]];assert gates(scores,c)==v['gates'][i];gatechecks+=1
            got=wrapper(v['logits'],b)
            for k in got:assert got[k]==specs[v['id']]['raw'][k],(v['id'],k)
            wrappers+=len(b['raw_boards'])
    elif stage=='007':
        for r in read('outcomes.json'):
            a,j,e=r['receiver'],r['donor'],r['expert'];actual=b['expert_outputs_offline'][a];donor=b['expert_outputs_offline'][j];active=b['routes'][a];other=[v for v in active if v!=e];shared=[v for v in active if v in b['routes'][j]]
            for name,o in r['outcomes'].items():
                ee=copy.deepcopy(actual)
                if name in ('candidate-donor',):ee[e]=donor[e]
                if name in ('noncandidate-natural','restore-candidate'):
                    for v in other:
                        if v in shared:ee[v]=donor[v]
                if name=='all-shared-natural':
                    for v in shared:ee[v]=donor[v]
                if name in ('zero-noncandidate','restore-from-zero'):
                    for v in other:ee[v]=[0]*c['width']
                if name=='zero-all-selected':
                    for v in active:ee[v]=[0]*c['width']
                y=head(b['readout'][a],ee,b['routes'][a],b['gates'][a],c);assert y==o['logits'],(r['pair_id'],name);checked+=1
                members=[s for s in range(9) if not b['boards'][a][s] and y[s]>=0];assert members==o['set']
                gold={s for s in range(9) if not b['boards'][a][s] and b['logits'][a][s]>=0};move=next((s for s in (4,1,3,5,7,2,6,8,0) if s in members),-1);assert (move in gold)==o['correct']
                # Independently recount the exact raw orbit, including noncanonical tie order.
                view={k:[v[i] for i,ci in enumerate(b['raw_to_canonical_id']) if ci==a] for k,v in b.items() if k in ('raw_boards','raw_to_canonical_id','raw_to_canonical_transform')};view['logits']=b['logits'];full=copy.deepcopy(b['logits']);full[a]=y;got=wrapper(full,view)
                for k in got:assert got[k]==o['raw_orbit'][k],(r['pair_id'],name,k)
                wrappers+=got['n']
    else:
        specs={r['id']:r for r in read('interventions.json')}
        for v in read('vectors.json'):
            r=specs[v['id']];nn=r['tensor'];coord=tuple(r['coordinate']);delta=r['new_code']-r['old_code'];assert delta in (-1,1);cc=copy.deepcopy(c);cc['tensors'][nn]['codes'][coord]=r['new_code']
            if nn in ('output.bias','output.weight'):
                for i in range(627):
                    eo=b['expert_outputs_offline'][i];assert head(b['readout'][i],eo,b['routes'][i],b['gates'][i],cc)==v['logits'][i];checked+=1
            old=np.array(b['logits']);new=np.array(v['logits']);legal=np.array(b['boards'])==0
            assert int(((old<0)&(new>=0)&legal).sum())==r['negative_to_nonnegative'];assert int(((old>=0)&(new<0)&legal).sum())==r['nonnegative_to_negative'];assert int((((old>=0)!=(new>=0))&~legal).sum())==r['occupied_sign_flips']
            got=wrapper(v['logits'],b)
            for k in got:assert got[k]==r['raw'][k],(v['id'],k)
            wrappers+=got['n']
    result=dict(stage=stage,scalar_offline_expert_evaluations=experts,scalar_baseline_heads=627,scalar_intervention_heads=checked,independent_native_gate_checks=gatechecks,independent_raw_wrapper_outcomes=wrappers,passed=True)
    put(out/'independent-audit.json',result);return result
