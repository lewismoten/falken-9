"""Independent audit: scalar packet forward + bottom-up rational DP + full tree.
Does not import study016 or production neural/geometry/DP implementations.
"""
import argparse,hashlib,json,math
from pathlib import Path
from fractions import Fraction as Q
from collections import Counter
import numpy as np
from scalar_reference015 import decode,scalar,win,after,optimal
ROOT=Path(__file__).resolve().parent

def restore(b,y,p):return sorted(i for i,x in enumerate(b) if x==0 and y[p[i]]>=0)
def audit(out):
 out=Path(out);packet=(ROOT/'artifacts/flexible-integer/q11-w16-a32-early-interp/model.f9j').read_bytes();cfg=decode(packet)
 assert hashlib.sha256(packet).hexdigest()=='fe180f8a931f9d92d8aa39da337bc819d0dbe4e6d971edcba00324fbc18a91c1'
 geometric=set()
 for swap in (0,1):
  for sx in (-1,1):
   for sy in (-1,1):
    p=[]
    for i in range(9):
     r,c=divmod(i,3);r-=1;c-=1
     if swap:r,c=c,r
     p.append(3*(1+sx*r)+1+sy*c)
    geometric.add(tuple(p))
 assert geometric==set(cfg['perms']) and cfg['order']==(4,1,3,5,7,2,6,8,0)
 def canon(b):
  variants=[]
  for p in cfg['perms']:
   # Deliberately use inverse indexing rather than production scatter.
   variants.append(tuple(b[p.index(i)] for i in range(9)))
  j=variants.index(min(variants));return variants[j],cfg['perms'][j]
 seen=set();terminals=set();todo=[(0,)*9]
 while todo:
  b=todo.pop()
  if win(b) or all(b):terminals.add(b);continue
  if b in seen:continue
  seen.add(b);todo.extend(after(b,i) for i,x in enumerate(b) if not x)
 assert len(seen)==4520
 data=np.load(out/'domain016.npz');boards=list(map(tuple,data['boards'].tolist()));indices={b:i for i,b in enumerate(boards)}
 assert len(boards)==627 and set(boards)=={canon(b)[0] for b in seen}
 stage_arrays=0;stage_scalars=0
 for i,b in enumerate(boards):
  st=scalar(cfg,b)
  assert set(st)==set(data.files)-{'boards'}
  for name,v in st.items():
   assert np.array_equal(v,data[name][i]),(i,name)
   stage_arrays+=1;stage_scalars+=np.asarray(v).size
 saved={tuple(r['board']):r for r in json.loads((out/'raw-bindings016.json').read_text())};assert set(saved)==seen
 policies=('accepted','reversed','largest_score');moves={};sets=0
 for b in sorted(seen):
  cb,p=canon(b);j=indices[cb];y=data['logits'][j].tolist();members=restore(b,y,p);r=saved[b]
  assert list(cb)==r['canonical'] and list(p)==r['permutation'] and r['canonical_index']==j
  assert members==r['approved']==r['optimal_audit']==optimal(b);sets+=1
  rawscore=[y[p[i]] for i in range(9)];assert rawscore==r['raw_logits']
  order=[i for i in cfg['order'] if i in members]
  choices=dict(accepted=order[0],reversed=order[-1],largest_score=sorted(order,key=lambda i:(-rawscore[i],cfg['order'].index(i)))[0])
  assert choices==r['choices'];moves[b]=choices
  assert r['routes']==data['routes'][j].tolist() and r['gates']==data['gates'][j].tolist()
 result=json.loads((out/'results016.json').read_text());panels=[];all_decisions=set();all_model=set();all_dp={}
 universe=seen|terminals
 for panel in result['panels']:
  role=1 if panel['role']=='X' else 2;policy=panel['policy'];dp={}
  # Independent bottom-up rational state recurrence, including all legal replies.
  for b in sorted(universe,key=lambda b:b.count(0)):
   w=win(b)
   if w or all(b):
    k=0 if w==role else 1 if not w else 2;dp[b]=(tuple(Q(i==k) for i in range(3)),Q(0),tuple(int(i==k) for i in range(3)));continue
   actions=[moves[b][policy]] if (9-b.count(0))%2+1==role else [i for i,x in enumerate(b) if x==0]
   n=len(actions);prob=[Q(0)]*3;marks=Q(1);counts=[0]*3
   for i in actions:
    cp,ce,cc=dp[after(b,i)]
    for k in range(3):prob[k]+=cp[k]/n;counts[k]+=cc[k]
    marks+=ce/n
   dp[b]=(tuple(prob),marks,tuple(counts))
  p,e,c=dp[(0,)*9]
  assert [str(v) for v in p]==[panel[k] for k in ('win','draw','loss')] and str(e)==panel['expected_terminal_marks'] and list(c)==panel['supported_by_outcome']
  # Independent explicit adversarial complete-history tree: no memoization, no oracle selection.
  leaves=[0]*3;leafmass=[Q(0)]*3;lengthmass=Q(0);prefix=Counter();decision=set();model=set();terminalset=set();loss_witness=None
  def tree(b,sequence,mass):
   nonlocal lengthmass,loss_witness
   w=win(b)
   if w or all(b):
    k=0 if w==role else 1 if not w else 2;leaves[k]+=1;leafmass[k]+=mass;lengthmass+=mass*len(sequence);terminalset.add(b)
    if k==2:loss_witness=sequence
    return
   prefix[b]+=1;decision.add(b);side=1+len(sequence)%2
   if side==role:model.add(b);actions=[moves[b][policy]]
   else:actions=[i for i,x in enumerate(b) if not x]
   for i in actions:tree(after(b,i),sequence+(i,),mass/len(actions))
  tree((0,)*9,(),Q(1))
  assert tuple(leaves)==c and tuple(leafmass)==p and lengthmass==e
  assert panel['supported_games']==sum(leaves)
  assert panel['reachable_raw_decisions']==len(decision) and panel['reachable_raw_model_decisions']==len(model)
  assert panel['reachable_canonical_decisions']==len({canon(b)[0] for b in decision}) and panel['reachable_canonical_model_decisions']==len({canon(b)[0] for b in model})
  assert panel['reachable_raw_terminal_boards']==len(terminalset) and panel['model_history_prefixes']==sum(prefix[b] for b in model)
  routes={}
  for r in panel['routes']:
   matching={b for b in model if saved[b]['routes']==r['route']}
   assert len(matching)==r['raw_model_boards'] and len({canon(b)[0] for b in matching})==r['canonical_model_boards'] and sum(prefix[b] for b in matching)==r['model_history_prefixes']
   routes[tuple(r['route'])]=len(matching)
  assert sum(routes.values())==len(model)
  rows=json.loads((out/f'dag-{role}-{policy}016.json').read_text());assert {tuple(r['board']) for r in rows}==decision
  for r in rows:
   b=tuple(r['board']);pp,ee,cc=dp[b]
   assert r['history_prefix_count']==prefix[b] and r['is_model']==(b in model)
   assert [r[k] for k in ('win','draw','loss')]==list(map(str,pp)) and r['expected_additional_marks']==str(ee) and r['supported_by_outcome']==list(cc)
  all_decisions|=decision;all_model|=model;all_dp[role,policy]=dp
  panels.append(dict(role=panel['role'],policy=policy,adversarial_all_legal_human_replies=True,complete_history_leaves=sum(leaves),loss_leaves=leaves[2],loss_witness=loss_witness,independent_bottom_up_DP=True,independent_rational_leaf_sum=True,all_reachable_state_values_checked=len(rows),worst_case_from_empty='draw' if leaves[2]==0 and leaves[1]>0 else 'loss' if leaves[2] else 'win'))
 assert result['union_raw_decisions']==len(all_decisions) and result['union_canonical_decisions']==len({canon(b)[0] for b in all_decisions})
 assert result['union_raw_model_decisions']==len(all_model) and result['union_canonical_model_decisions']==len({canon(b)[0] for b in all_model})
 candidates=[]
 for b in sorted(all_model,key=lambda b:(9-b.count(0),b)):
  if len(set(moves[b].values()))<2:continue
  side=1+(9-b.count(0))%2
  differs=len({all_dp[side,p][b][0][0] for p in policies})>1
  candidates.append((differs,b))
 expected=next((b for differs,b in candidates if differs),candidates[0][1] if candidates else None)
 example=json.loads((out/'example016.json').read_text())
 assert (tuple(example['board']) if example else None)==expected
 if example:
  b=tuple(example['board']);role=1 if example['role']=='X' else 2
  # Conditional outcomes independently recomputed via explicit history enumeration.
  for r in example['conditional']:
   totals=[Q(0)]*3
   def conditional(b,mass):
    w=win(b)
    if w or all(b):totals[0 if w==role else 1 if not w else 2]+=mass;return
    actions=[moves[b][r['policy']]] if 1+(9-b.count(0))%2==role else [i for i,x in enumerate(b) if not x]
    for i in actions:conditional(after(b,i),mass/len(actions))
   conditional(b,Q(1));assert list(map(str,totals))==[r[k] for k in ('win','draw','loss')]
 return dict(passed=True,independent_packet_decoder=True,independent_arbitrary_int_full_forwards=627,stage_array_checks=stage_arrays,stage_scalar_checks=stage_scalars,raw_whole_set_minimax_inverse_tie_checks=sets,independent_geometry=True,independent_bottom_up_rational_DP=True,explicit_all_human_reply_adversarial_tree=True,panels=panels,native_execution=False)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('output');a=p.parse_args();print(json.dumps(audit(a.output),sort_keys=True,indent=2))
