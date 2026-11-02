"""Study015: actual full integer host inference on bounded self-play paths."""
import argparse,hashlib,io,json,sys,zipfile
from pathlib import Path
from collections import Counter
import numpy as np
import torch
from study015_core import canonical,restore,choose,sample,trajectory_key,PERMS
from falken9.canonical_integer_export import load
from falken9.strategy_diagnostics import DiagnosticPolicy,winner,offline_optimal_set,offline_value
ROOT=Path(__file__).resolve().parent
PACKET=ROOT/'artifacts/flexible-integer/q11-w16-a32-early-interp/model.f9j'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,v):Path(p).write_text(json.dumps(v,sort_keys=True,indent=2,allow_nan=False,default=lambda x:x.tolist() if hasattr(x,'tolist') else int(x))+'\n')
def pack(p,arrays):
 with zipfile.ZipFile(p,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for k,v in sorted(arrays.items()):
   b=io.BytesIO();np.save(b,np.asarray(v),allow_pickle=False);info=zipfile.ZipInfo(k+'.npy',(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16;z.writestr(info,b.getvalue(),compresslevel=9)
def run(out):
 torch.set_num_threads(1);out=Path(out);out.mkdir(exist_ok=False)
 m=json.loads((ROOT/'manifest015.json').read_text())
 for n,h in m['bound_sha256'].items():assert sha(ROOT/n)==h,n
 c=load(PACKET);q=DiagnosticPolicy(c)
 def forward(b):
  cb,p=canonical(b);y=q(torch.tensor([cb],dtype=torch.int64)).numpy()[0].copy()
  st={k:v.numpy()[0].copy() for k,v in q.stages.items()}
  return cb,p,y,st
 # Empty-board membership DISCOVERY uses real whole-network execution.
 cb,p,y,st=forward((0,)*9);openings=restore(y,(0,)*9,p);first=choose(openings)
 put(out/'opening015.json',dict(approved_zero_based=openings,deterministic_zero_based=first,logits=y,stages=st,packet_sha256=sha(PACKET)))
 games=[];allst={};calls=0;raw=set();can=set();allboards=set();terminalboards=set();wrong=0
 for opening in openings:
  b=(0,)*9;seq=[];steps=[];boards=[b]
  while not winner(b) and 0 in b:
   cb,p,y,st=forward(b);calls+=1;members=restore(y,b,p);ordinary=choose(members)
   selected=opening if not seq else ordinary
   assert selected in members and b[selected]==0
   # Oracle labels are consulted after neural selection, never used to choose.
   optimal=sorted(offline_optimal_set(b));wrong+=int(members!=optimal)
   prefix=f'g{opening}-p{len(seq)}'
   for k,v in st.items():allst[prefix+'--'+k]=v
   raw.add(b);can.add(cb);allboards.add(b)
   steps.append(dict(ply=len(seq),side='X' if len(seq)%2==0 else 'O',raw_board=b,canonical_board=cb,permutation=p,canonical_logits=y,raw_approved=members,raw_optimal_audit=optimal,ordinary_move=ordinary,selected_move=selected,routes=st['routes'],gates=st['gates'],stage_prefix=prefix,opening_override=not seq and selected!=ordinary))
   v=list(b);v[selected]=1+len(seq)%2;b=tuple(v);seq.append(selected);boards.append(b)
  allboards.add(b);terminalboards.add(b)
  games.append(dict(opening=opening,is_first_deterministic=opening==first,sequence=seq,d4_key=trajectory_key(seq),length=len(seq),outcome={0:'draw',1:'X win',2:'O win'}[winner(b)],boards=boards,steps=steps))
 # Fresh domain inference is reference coverage, never used to drive games.
 bd=np.load(ROOT/'artifacts/interpretability/study-010-final/baseline010.npz');domain=bd['boards'];q(torch.tensor(domain));domainst={k:v.numpy().copy() for k,v in q.stages.items()}
 for k,v in domainst.items():assert np.array_equal(v,bd[k]),k
 assert len(domain)==627 and wrong==0
 pack(out/'game-stages015.npz',allst);pack(out/'domain-stages015.npz',dict(domainst,boards=domain))
 routes=lambda g:tuple(map(int,g))
 dc=Counter(map(routes,domainst['routes']));pc=Counter(routes(s['routes']) for g in games for s in g['steps'])
 uniqueids=[i for i,b in enumerate(domain.tolist()) if tuple(b) in can];uc=Counter(routes(domainst['routes'][i]) for i in uniqueids)
 coverage=[dict(route=list(r),domain_boards=dc[r],unique_path_canonical_boards=uc[r],game_step_visits=pc[r],domain_gate_sums=[int(domainst['gates'][[i for i,v in enumerate(domainst['routes']) if routes(v)==r],j].sum()) for j in range(2)]) for r in sorted(dc)]
 # Enumerate finite deterministic PRNG joint state, not a random sampling test.
 seen={};last=first;state=0xa7;records=[]
 while (last,state) not in seen:
  assert len(records)<2295
  seen[last,state]=len(records);move,nstate,attempts=sample(openings,last,state)
  records.append(dict(previous=last,prng_before=state,opening=move,prng_after=nstate,attempts=attempts));last,state=move,nstate
 start=seen[last,state];cycle=records[start:]
 allstates=[]
 for prev in openings:
  for seed in range(1,256):
   move,nstate,attempts=sample(openings,prev,seed);allstates.append(dict(previous=prev,prng_before=seed,opening=move,prng_after=nstate,attempts=attempts))
 put(out/'sampler-state-census015.json',allstates)
 transitions=[dict(previous=a,next=b,ideal_conditional='1/8') for a in openings for b in openings if a!=b]
 put(out/'opening-transitions015.json',dict(idealized=dict(states=len(openings),allowed_transitions=transitions,stationary='1/9 per raw opening; not independent; conditional self-transition zero, others1/8',first_game=first),fixed_seed_host_emulation=dict(seed=167,transient_length=start,cycle_length=len(cycle),records=records,cycle_counts=dict(sorted(Counter(r['opening'] for r in cycle).items())),warning='Exact deterministic host LFSR enumeration, NOT measured native sampling or empirical RNG fairness')))
 groups={}
 for g in games:groups.setdefault(str(g['d4_key']),[]).append(g['opening'])
 result=dict(opening_count=len(openings),first_opening_one_based=first+1,complete_games=len(games),game_forward_calls=calls,discovery_forward_calls=1,reference_domain_forward_boards=len(domain),raw_distinct_sequences=len({tuple(g['sequence']) for g in games}),d4_trajectory_classes=len(groups),d4_groups=groups,outcomes=dict(Counter(g['outcome'] for g in games)),lengths=[g['length'] for g in games],unique_raw_nonterminal_boards=len(raw),unique_canonical_nonterminal_boards=len(can),unique_raw_boards_including_terminal=len(allboards),unique_raw_terminal_boards=len(terminalboards),domain_canonical=627,domain_raw=4520,raw_coverage_fraction=f'{len(raw)}/4520',canonical_coverage_fraction=f'{len(can)}/627',minimax_wrong_sets=wrong,route_coverage=coverage,gate_unit='Q15 denominator32768, not move confidence',first_game_sequence_one_based=[s+1 for s in next(g for g in games if g['is_first_deterministic'])['sequence']],packet_sha256=sha(PACKET),manifest_sha256=sha(ROOT/'manifest015.json'),host_only=True,native_replay=False,full_stage_names=sorted(domainst),imports={n:str(Path(mod.__file__).resolve()) for n,mod in sys.modules.items() if n.startswith('falken9') and getattr(mod,'__file__',None)})
 put(out/'coverage-by-ply015.json',[dict(ply=ply,domain_canonical=sum(sum(v!=0 for v in b)==ply for b in domain.tolist()),path_unique_canonical=sum(sum(v!=0 for v in b)==ply for b in can),path_unique_raw=sum(sum(v!=0 for v in b)==ply for b in raw)) for ply in range(9)])
 put(out/'value-coverage015.json',dict(domain_canonical=dict(Counter(offline_value(tuple(b)) for b in domain.tolist())),path_canonical=dict(Counter(offline_value(b) for b in can))))
 put(out/'games015.json',games);put(out/'results015.json',result);return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('output');a=p.parse_args();print(json.dumps(run(a.output),indent=2))
