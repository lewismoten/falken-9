"""Frozen study016 offline analysis only, never runtime code."""
def pick(board, raw_logits, policy):
 order=(4,1,3,5,7,2,6,8,0)
 legal=[i for i in order if board[i]==0 and raw_logits[i]>=0]
 if not legal:raise ValueError('empty approved set')
 if policy=='accepted':return legal[0]
 if policy=='reversed':return legal[-1]
 if policy=='largest_score':return max(legal,key=lambda i:raw_logits[i])
 raise ValueError(policy)

from functools import lru_cache
from fractions import Fraction as F
PERMS=((0,1,2,3,4,5,6,7,8),(2,5,8,1,4,7,0,3,6),(8,7,6,5,4,3,2,1,0),(6,3,0,7,4,1,8,5,2),(2,1,0,5,4,3,8,7,6),(8,5,2,7,4,1,6,3,0),(6,7,8,3,4,5,0,1,2),(0,3,6,1,4,7,2,5,8))
LINES=((0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6))
def winner(b):return next((b[a] for a,c,d in LINES if b[a] and b[a]==b[c]==b[d]),0)
def after(b,s):
 assert b[s]==0
 v=list(b);v[s]=1+(9-b.count(0))%2;return tuple(v)
def canonical(b):
 choices=[]
 for p in PERMS:
  v=[0]*9
  for i,x in enumerate(b):v[p[i]]=x
  choices.append(tuple(v))
 k=min(range(8),key=lambda k:choices[k]);return choices[k],PERMS[k]
def domain():
 seen=set()
 def walk(b):
  if winner(b) or 0 not in b or b in seen:return
  seen.add(b)
  for s,v in enumerate(b):
   if v==0:walk(after(b,s))
 walk((0,)*9);return sorted(seen)
def make_dp(policy,role,selector):
 @lru_cache(None)
 def dp(b):
  w=winner(b)
  if w or 0 not in b:
   k=0 if w==role else 1 if not w else 2
   return tuple(F(int(i==k)) for i in range(3)),F(0),tuple(int(i==k) for i in range(3))
  moves=[selector(b,policy)] if 1+(9-b.count(0))%2==role else [i for i,v in enumerate(b) if v==0]
  children=[dp(after(b,s)) for s in moves];n=len(moves)
  return tuple(sum(c[0][k] for c in children)/n for k in range(3)),1+sum(c[1] for c in children)/n,tuple(sum(c[2][k] for c in children) for k in range(3))
 return dp

import argparse,hashlib,io,json,sys,zipfile
from pathlib import Path
from collections import Counter,defaultdict
ROOT=Path(__file__).resolve().parent
PACKET=Path('artifacts/flexible-integer/q11-w16-a32-early-interp/model.f9j')
POLICIES=('accepted','reversed','largest_score')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,v):
 Path(p).write_text(json.dumps(v,sort_keys=True,indent=2,allow_nan=False,default=lambda x:x.tolist() if hasattr(x,'tolist') else str(x) if isinstance(x,F) else int(x))+'\n')
def pack(p,arrays):
 import numpy as np
 with zipfile.ZipFile(p,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for k,v in sorted(arrays.items()):
   b=io.BytesIO();np.save(b,np.asarray(v),allow_pickle=False);info=zipfile.ZipInfo(k+'.npy',(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16;z.writestr(info,b.getvalue(),compresslevel=9)
def run(out):
 import numpy as np
 import torch
 from falken9.canonical_integer_export import load
 from falken9.strategy_diagnostics import DiagnosticPolicy,offline_optimal_set
 torch.set_num_threads(1);out=Path(out);out.mkdir(exist_ok=False)
 m=json.loads((ROOT/'manifest016.json').read_text())
 for n,h in m['bound_sha256'].items():assert sha(ROOT/n)==h,n
 assert sha(ROOT/PACKET)==m['packet_sha256']
 raw=domain();boards=sorted({canonical(b)[0] for b in raw});assert (len(raw),len(boards))==(4520,627)
 # Exactly one real whole-network observation for each canonical input, in one batch.
 q=DiagnosticPolicy(load(ROOT/PACKET));q(torch.tensor(boards,dtype=torch.int64))
 stages={k:v.numpy().copy() for k,v in q.stages.items()};idx={b:i for i,b in enumerate(boards)}
 pack(out/'domain016.npz',dict(stages,boards=boards))
 records={};wrong=0
 for b in raw:
  cb,p=canonical(b);j=idx[cb];y=[int(stages['logits'][j,p[i]]) for i in range(9)]
  members=[i for i in range(9) if b[i]==0 and y[i]>=0]
  choices={policy:pick(b,y,policy) for policy in POLICIES}
  # Offline oracle checked only AFTER all policy choices are fixed.
  optimal=sorted(offline_optimal_set(b));wrong+=members!=optimal
  records[b]=dict(board=b,canonical=cb,canonical_index=j,permutation=p,raw_logits=y,approved=members,optimal_audit=optimal,choices=choices,routes=stages['routes'][j].tolist(),gates=stages['gates'][j].tolist())
 assert wrong==0
 selector=lambda b,p:records[b]['choices'][p]
 panels=[];allreachable=set();modelreachable=set();dps={}
 for role in (1,2):
  for policy in POLICIES:
   dp=make_dp(policy,role,selector);dps[role,policy]=dp;v,e,counts=dp((0,)*9)
   reach={(0,)*9};prefixes=Counter({(0,)*9:1});mreach=set();routecount=Counter();routeprefix=Counter();rows=[]
   # Forward DAG propagation counts histories, not probabilities or neural calls.
   for ply in range(10):
    layer=sorted(b for b in reach if 9-b.count(0)==ply)
    for b in layer:
     if winner(b) or 0 not in b:continue
     ismodel=1+ply%2==role
     if ismodel:
      mreach.add(b);route=tuple(records[b]['routes']);routecount[route]+=1;routeprefix[route]+=prefixes[b]
     moves=[selector(b,policy)] if ismodel else [i for i in range(9) if b[i]==0]
     for s in moves:
      c=after(b,s);reach.add(c);prefixes[c]+=prefixes[b]
     pv,pe,pc=dp(b)
     rows.append(dict(board=b,is_model=ismodel,history_prefix_count=prefixes[b],moves=moves,win=str(pv[0]),draw=str(pv[1]),loss=str(pv[2]),expected_additional_marks=str(pe),supported_by_outcome=pc))
   decisions={b for b in reach if not winner(b) and 0 in b};terminal=reach-decisions
   assert sum(prefixes[b] for b in terminal)==sum(counts)
   allreachable|=decisions;modelreachable|=mreach
   panel=dict(role='XO'[role-1],policy=policy,win=str(v[0]),draw=str(v[1]),loss=str(v[2]),expected_terminal_marks=str(e),supported_games=sum(counts),supported_by_outcome=counts,reachable_raw_decisions=len(decisions),reachable_canonical_decisions=len({canonical(b)[0] for b in decisions}),reachable_raw_model_decisions=len(mreach),reachable_canonical_model_decisions=len({canonical(b)[0] for b in mreach}),reachable_raw_terminal_boards=len(terminal),model_history_prefixes=sum(prefixes[b] for b in mreach),routes=[dict(route=r,raw_model_boards=routecount[r],model_history_prefixes=routeprefix[r],canonical_model_boards=len({canonical(b)[0] for b in mreach if tuple(records[b]['routes'])==r})) for r in sorted(routecount)])
   panels.append(panel);put(out/f'dag-{role}-{policy}016.json',rows)
 # Fixed example selection rule in manifest: no extra policy or optimizer.
 candidates=[]
 for b in sorted(modelreachable,key=lambda b:(9-b.count(0),b)):
  role=1+(9-b.count(0))%2;choices=records[b]['choices']
  if len(set(choices.values()))<2:continue
  cond={p:dps[role,p](b) for p in POLICIES}
  candidates.append((len({z[0][0] for z in cond.values()})>1,b,role,cond))
 preferred=next((c for c in candidates if c[0]),candidates[0] if candidates else None)
 example=None
 if preferred:
  _,b,role,cond=preferred;example=dict(records[b],role='XO'[role-1],conditional=[dict(policy=p,move=selector(b,p),win=str(cond[p][0][0]),draw=str(cond[p][0][1]),loss=str(cond[p][0][2]),expected_additional_marks=str(cond[p][1]),supported_by_outcome=cond[p][2]) for p in POLICIES])
 put(out/'example016.json',example);put(out/'raw-bindings016.json',list(records.values()))
 result=dict(study='016',packet_sha256=sha(ROOT/PACKET),manifest_sha256=sha(ROOT/'manifest016.json'),neural_binding_boards=627,production_batch_calls=1,raw_expansion_boards=4520,minimax_wrong_sets=wrong,offline_cached_branching=True,branch_traversals_are_not_forwards=True,panels=panels,example_exists=example is not None,union_raw_decisions=len(allreachable),union_canonical_decisions=len({canonical(b)[0] for b in allreachable}),union_raw_model_decisions=len(modelreachable),union_canonical_model_decisions=len({canonical(b)[0] for b in modelreachable}),imports={n:str(Path(mod.__file__).resolve()) for n,mod in sys.modules.items() if n.startswith('falken9') and getattr(mod,'__file__',None)})
 assert all(str(ROOT/'falken9') in p for p in result['imports'].values())
 put(out/'results016.json',result);return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('output');a=p.parse_args();print(json.dumps(run(a.output),indent=2))
