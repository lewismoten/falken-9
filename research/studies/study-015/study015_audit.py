"""Independent arbitrary-integer packet/forward/geometry/minimax audit.
No production decoder, arithmetic, wrapper or forward imports.
"""
import argparse,hashlib,json,struct,math,re
from functools import lru_cache
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parent
NAMES=('position','expert_w1','expert_b1','expert_w2','expert_b2','occupancy.weight','side.weight','norm1.weight','norm1.bias','query.weight','key.weight','value.weight','projection.weight','readout.weight','readout.bias','norm2.weight','norm2.bias','router.weight','router.bias','output.weight','output.bias')
def decode(raw):
 h=struct.unpack_from('<4s10BHH',raw);assert h[0]==b'F9J2';p=99;desc=[]
 for n in NAMES:
  bits,rank,k=struct.unpack_from('<BBH',raw,p);p+=4;shape=tuple(raw[p:p+rank]);p+=rank
  e=struct.unpack_from('<'+'b'*k,raw,p);p+=k;desc.append((n,bits,shape,e))
 t={}
 for n,bits,shape,e in desc:
  count=math.prod(shape);v=struct.unpack_from('<'+('h' if bits==16 else 'b')*count,raw,p);p+=count*bits//8
  t[n]=dict(codes=np.array(v,dtype=np.int64).reshape(shape),exponents=e)
 assert p+2052==len(raw)
 return dict(frac=h[1],width=h[2],experts=h[4],topk=h[5],activation_bits=h[6],output_bits=h[7],attention_mode=('legacy','early','rational')[h[8]],interpolate=bool(h[9]),attention_factor=h[11],attention_denominator=h[12],tensors=t,tables={'exp':struct.unpack_from('<513H',raw,p),'gelu':struct.unpack_from('<513h',raw,p+1026)},perms=[tuple(raw[18+k*9:18+(k+1)*9]) for k in range(8)],order=tuple(raw[90:99]))
def scalar(c,board):
 S=1<<c['frac'];d=c['width'];ts=c['tensors'];st={}
 def rd(a,b):return (1 if a>=0 else -1)*((abs(a)+b//2)//b)
 def sat(a,output=False):
  n=c['output_bits'] if output else c['activation_bits'];return max(-(1<<(n-1)),min((1<<(n-1))-1,a))
 def vec(n):return ts[n]['codes'].tolist()
 def linear(x,name,expert=None,bias=None):
  w=vec(name);exps=ts[name]['exponents']
  if expert is not None:w=list(map(list,zip(*w[expert])));exps=exps[expert*len(w):(expert+1)*len(w)]
  out=[]
  for row,e in zip(w,exps):
   dot=sum(a*b for a,b in zip(x,row));out.append(dot*(1<<e) if e>=0 else rd(dot,1<<-e))
  if bias:
   b=vec(bias);b=b[expert] if expert is not None else b;out=[a+b for a,b in zip(out,b)]
  return [sat(a,name=='output.weight') for a in out]
 def norm(x,name):
  mean=rd(sum(x),d);z=[a-mean for a in x];root=math.isqrt(rd(sum(a*a for a in z),d)+max(1,(S*S+50000)//100000))
  return [sat(rd(rd(a*S,root)*g,S)+b) for a,g,b in zip(z,vec(name+'.weight'),vec(name+'.bias'))]
 def lookup(x,table,offset=0):
  if not c['interpolate']:return table[max(0,min(512,rd(x*32,S)+offset))]
  i,r=divmod(max(0,min(512*S,x*32+offset*S)),S)
  return table[512] if i==512 else rd(table[i]*(S-r)+table[i+1]*r,S)
 def soft(x):
  top=max(x);ex=[lookup(top-a,c['tables']['exp']) for a in x];total=sum(ex);p=[a*32768//total for a in ex];p[x.index(top)]+=32768-sum(p);return p
 def gelu(x):return [sat(a if a>8*S else 0 if a< -8*S else lookup(a,c['tables']['gelu'],256)) for a in x]
 side=sum(a!=0 for a in board)%2
 x=[[sat(a+b+v) for a,b,v in zip(vec('occupancy.weight')[v],vec('position')[i],vec('side.weight')[side])] for i,v in enumerate(board)];st['board_embedding']=x
 z=[norm(a,'norm1') for a in x];st['board_normalized']=z
 q,k,v=([linear(a,n+'.weight') for a in z] for n in ('query','key','value'));st.update(board_query=q,board_key=k,board_value=v)
 scores=[];probs=[];attended=[]
 for qi in q:
  ss=[]
  for kj in k:
   dot=sum(a*b for a,b in zip(qi,kj));score=rd(rd(dot,S)*c['attention_factor'],c['attention_denominator']) if c['attention_mode']=='early' else rd(dot*c['attention_factor'],S*c['attention_denominator']);ss.append(sat(score))
  pp=soft(ss);scores.append(ss);probs.append(pp);attended.append([sat(rd(sum(pj*vj[l] for pj,vj in zip(pp,v)),32768)) for l in range(d)])
 projected=[linear(a,'projection.weight') for a in attended];residual=[[sat(a+b) for a,b in zip(row,pr)] for row,pr in zip(x,projected)]
 st.update(attention_scores=scores,attention_probs=probs,attended=attended,projected=projected,attention_residual=residual)
 pre=linear(sum(residual,[]),'readout.weight',bias='readout.bias');x=gelu(pre);z=norm(x,'norm2');scores=linear(z,'router.weight',bias='router.bias')
 routes=sorted(range(c['experts']),key=lambda i:(-scores[i],i))[:c['topk']];gates=soft([scores[i] for i in routes])
 st.update(readout_pre=pre,readout_gelu=x,norm2_output=z,router_scores=scores,routes=routes,gates=gates)
 hiddenpre=[[0]*4 for _ in range(4)];hidden=[[0]*4 for _ in range(4)];outputs=[[0]*d for _ in range(4)]
 for i in routes:
  hiddenpre[i]=linear(z,'expert_w1',i,'expert_b1');hidden[i]=gelu(hiddenpre[i]);outputs[i]=linear(hidden[i],'expert_w2',i,'expert_b2')
 merged=[sat(a+rd(sum(g*outputs[i][l] for g,i in zip(gates,routes)),32768)) for l,a in enumerate(x)]
 st.update(expert_hidden_pre=hiddenpre,expert_hidden=hidden,expert_outputs=outputs,merged=merged,logits=linear(merged,'output.weight',bias='output.bias'))
 return st
LINES=tuple(tuple(r*3+c for c in range(3)) for r in range(3))+tuple(tuple(r*3+c for r in range(3)) for c in range(3))+((0,4,8),(2,4,6))
def win(b):return next((b[a] for a,c,d in LINES if b[a] and b[a]==b[c]==b[d]),0)
def after(b,s):
 bb=list(b);bb[s]=1+(9-b.count(0))%2;return tuple(bb)
@lru_cache(None)
def value(b):
 if win(b):return -1
 if 0 not in b:return 0
 return max(-value(after(b,s)) for s in range(9) if not b[s])
def optimal(b):
 vals={s:-value(after(b,s)) for s in range(9) if not b[s]};best=max(vals.values());return [s for s,v in vals.items() if v==best]
def audit(out):
 out=Path(out);raw=(ROOT/'artifacts/flexible-integer/q11-w16-a32-early-interp/model.f9j').read_bytes();c=decode(raw)
 # Independently construct coordinate D4; align ordering to packet, validate source.
 geometric=set()
 for swap in (False,True):
  for sx in (-1,1):
   for sy in (-1,1):
    p=[]
    for s in range(9):
     r,col=divmod(s,3);r-=1;col-=1
     if swap:r,col=col,r
     p.append((sx*r+1)*3+sy*col+1)
    geometric.add(tuple(p))
 assert geometric==set(c['perms']) and c['order']==(4,1,3,5,7,2,6,8,0)
 def canon(b):
  alternatives=[]
  for p in c['perms']:
   dest=[0]*9
   for i,x in enumerate(b):dest[p[i]]=x
   alternatives.append(tuple(dest))
  i=alternatives.index(min(alternatives));return alternatives[i],c['perms'][i]
 opening=json.loads((out/'opening015.json').read_text());empty_st=scalar(c,(0,)*9)
 assert opening['approved_zero_based']==list(range(9)) and opening['deterministic_zero_based']==c['order'][0]
 assert opening['logits']==empty_st['logits']
 for k,v in empty_st.items():assert np.array_equal(v,opening['stages'][k]),k
 games=json.loads((out/'games015.json').read_text());saved=np.load(out/'game-stages015.npz');checks=0;scalars=0;rawboards=set();canboards=set();d4=set();sequences=set()
 for g in games:
  b=(0,)*9;seq=[]
  for s in g['steps']:
   assert not win(b) and 0 in b and list(b)==s['raw_board'];cb,p=canon(b);assert list(cb)==s['canonical_board'] and list(p)==s['permutation']
   st=scalar(c,cb)
   for k,v in st.items():
    arr=np.array(v);assert np.array_equal(arr,saved[s['stage_prefix']+'--'+k]),(g['opening'],s['ply'],k);checks+=1;scalars+=arr.size
   members=[i for i in range(9) if b[i]==0 and st['logits'][p[i]]>=0];assert members==s['raw_approved']==optimal(b)==s['raw_optimal_audit']
   ordinary=next(i for i in c['order'] if i in members);assert ordinary==s['ordinary_move']
   selected=g['opening'] if not seq else ordinary;assert selected==s['selected_move'] and selected in members
   seq.append(selected);rawboards.add(b);canboards.add(cb);b=after(b,selected)
  assert 0 not in b and not win(b) and seq==g['sequence'] and list(b)==g['boards'][-1]
  key=min(tuple(p[s] for s in seq) for p in geometric);assert list(key)==g['d4_key'];d4.add(key);sequences.add(tuple(seq))
 # Full reference-domain independent scalar validation, not game policy caching.
 domain=np.load(out/'domain-stages015.npz');seen=set()
 def visit(b):
  if b in seen or win(b) or 0 not in b:return
  seen.add(b)
  for s in range(9):
   if b[s]==0:visit(after(b,s))
 visit((0,)*9);assert len(seen)==4520
 expected=list(map(tuple,domain['boards'].tolist()));assert {canon(b)[0] for b in seen}==set(expected) and len(expected)==627
 for i,b in enumerate(expected):
  st=scalar(c,b)
  for k,v in st.items():assert np.array_equal(v,domain[k][i]),(i,k)
  assert [s for s in range(9) if not b[s] and st['logits'][s]>=0]==optimal(b)
 r=json.loads((out/'results015.json').read_text());assert r['unique_raw_nonterminal_boards']==len(rawboards) and r['unique_canonical_nonterminal_boards']==len(canboards) and r['d4_trajectory_classes']==len(d4) and r['raw_distinct_sequences']==len(sequences)
 from collections import Counter
 observed_routes=Counter(tuple(s['routes']) for g in games for s in g['steps']);domain_routes=Counter(map(tuple,domain['routes'].tolist()));unique_routes=Counter(tuple(domain['routes'][i]) for i,b in enumerate(expected) if b in canboards)
 for rr in r['route_coverage']:
  route=tuple(rr['route']);assert rr['domain_boards']==domain_routes[route] and rr['unique_path_canonical_boards']==unique_routes[route] and rr['game_step_visits']==observed_routes[route]
 assert sum(rr['domain_boards'] for rr in r['route_coverage'])==627
 ply=json.loads((out/'coverage-by-ply015.json').read_text())
 for row in ply:
  p=row['ply'];assert row['domain_canonical']==sum(b.count(0)==9-p for b in expected) and row['path_unique_canonical']==sum(b.count(0)==9-p for b in canboards) and row['path_unique_raw']==sum(b.count(0)==9-p for b in rawboards)
 vals=json.loads((out/'value-coverage015.json').read_text());assert vals==dict(domain_canonical={str(k):v for k,v in Counter(value(b) for b in expected).items()},path_canonical={str(k):v for k,v in Counter(value(b) for b in canboards).items()})
 assert r['lengths']==[len(g['steps']) for g in games] and r['outcomes']=={'draw':9} and r['game_forward_calls']==81
 tr=json.loads((out/'opening-transitions015.json').read_text())['fixed_seed_host_emulation'];state=167;last=4;pairs={};counts={};records=tr['records']
 for idx,rec in enumerate(records):
  assert (last,state) not in pairs;pairs[last,state]=idx
  before=state
  candidates=[i for i in range(9) if i!=last]
  for attempt in range(1,10):
   state=(state//2)^(184 if state%2 else 0)
   if state-1<248:break
  else:raise AssertionError('sampler exhausted')
  move=candidates[(state-1)%8]
  assert rec==dict(previous=last,prng_before=before,opening=move,prng_after=state,attempts=attempt)
  if idx:assert rec['prng_before']==records[idx-1]['prng_after']
  last=move
 assert pairs[last,state]==tr['transient_length'] and len(records)-pairs[last,state]==tr['cycle_length']
 # Exhaust every previous-opening / nonzero PRNG state, using a separate loop.
 census=json.loads((out/'sampler-state-census015.json').read_text());assert len(census)==2295
 support=set()
 for rec in census:
  state=rec['prng_before'];prev=rec['previous'];attempt=0
  while True:
   attempt+=1;lowbit=state&1;state>>=1
   if lowbit:state^=0xb8
   if state<=248:break
   assert attempt<9
  index=(state-1)%8;move=index if index<prev else index+1
  assert rec['opening']==move and rec['prng_after']==state and rec['attempts']==attempt
  support.add((prev,move))
 assert len(support)==72
 # Source call ordering and opening-only guards, bound to frozen sources/listing.
 source=ROOT/'source010/src/app';game=(source/'graphical_game.asm').read_text();sampler=(source/'auto_demo.asm').read_text();wrapper=(source/'wrapper.asm').read_text()
 assert game.index('jsr policy_request')<game.index('jsr auto_resolve_opening')<game.index('stx auto_last_opening')
 assert 'lda $7809' in sampler and 'bne auto_sampler_skip' in sampler and 'cpx auto_last_opening' in sampler
 assert 'jsr full_forward' in wrapper and 'jmp restore_set' in wrapper
 listing=(ROOT/'source010/artifacts/app/010-graphical/app.lst').read_text();assert 'jsr auto_resolve_opening' in listing and 'restore_tie:' in listing
 return dict(passed=True,independent_packet_decoder=True,independent_arbitrary_int_full_forward=True,game_forward_audits=sum(len(g['steps']) for g in games),game_stage_array_checks=checks,game_stage_integer_checks=scalars,domain_full_forward_audits=627,independent_raw_boards=4520,independent_canonical_boards=627,all_sets_optimal=True,geometry_restore_fresh_raw_ties=True,fixed_seed_prng_joint_state_records=len(records),source_flow_bound=True,native_execution=False,packet_sha256=hashlib.sha256(raw).hexdigest())
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('output');a=p.parse_args();print(json.dumps(audit(a.output),sort_keys=True,indent=2))
