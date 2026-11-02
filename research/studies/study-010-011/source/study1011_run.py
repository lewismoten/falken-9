"""Predeclared symmetry and exact representation census. CPU/offline only."""
import argparse,copy,hashlib,json,time
from pathlib import Path
import numpy as np
import torch
from study005_run import baseline,geom
from study009_run import pack_arrays,raw_wrapper
from study1011_core import align_stage,collision_census,executed_vector,expert_record
from falken9.strategy_diagnostics import DiagnosticPolicy,tactical
from falken9.canonical_integer import CanonicalIntegerPolicy
from falken9.symmetry import TRANSFORMS,transform_board,inverse
ROOT=Path(__file__).resolve().parent
TACTICS=('has_win','must_block','has_fork','has_opponent_fork','has_fork_prevention')
PRIORITY=[4,1,3,5,7,2,6,8,0]
def put(p,v):Path(p).write_text(json.dumps(v,sort_keys=True,indent=2,allow_nan=False,default=lambda x:x.item() if isinstance(x,np.generic) else x.tolist())+'\n')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def preserve():
    vals=json.loads((ROOT/'preservation-010-011-initial.json').read_text())
    for n,h in vals.items():assert sha(ROOT/n)==h,n
    return len(vals)
def measure_sets(pred,gold,priority=PRIORITY):
    pred=np.asarray(pred,bool);gold=np.asarray(gold,bool)
    moves=np.array([next((s for s in priority if row[s]),-1) for row in pred])
    base=np.array([next((s for s in priority if row[s]),-1) for row in gold])
    empty=moves<0;correct=np.array([m>=0 and gold[i,m] for i,m in enumerate(moves)])
    return dict(n=len(pred),full_set_correct=int((pred==gold).all(1).sum()),full_set_changes=int((pred!=gold).any(1).sum()),empty_sets=int(empty.sum()),nonoptimal_nonempty=int((~correct&~empty).sum()),chosen_optimal=int(correct.sum()),chosen_errors=int((~correct).sum()),chosen_changes=int((moves!=base).sum()),optimal_tie_changes=int((correct&(moves!=base)).sum()),chosen_moves=moves.tolist())
def prepared(sid,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False);count=preserve()
    m=json.loads((ROOT/f'experiment-study{sid}.json').read_text());data=baseline()
    assert data[-2]==json.loads((ROOT/'baseline-study010-011.json').read_text())
    assert sha(ROOT/'baseline-study010-011.json')==m['baseline_sha256']
    put(out/f'manifest{sid}.json',m);put(out/f'baseline-gate{sid}.json',data[-2])
    return out,m,data,count

def run010(out):
    start=time.monotonic();out,m,data,count=prepared('010',out)
    b,bt,c,y,st,raw,ci,tr,opt,rawopt,cp,rp,gate,_=data
    lookup={tuple(v):i for i,v in enumerate(raw)}
    orbit=np.array([[lookup[transform_board(v,t)] for v in b] for t in TRANSFORMS])
    assert orbit.shape==(8,627) and len(set(orbit.ravel()))==4520
    q=DiagnosticPolicy(copy.deepcopy(c));direct=q(torch.tensor(raw,dtype=torch.int64)).numpy().copy();ds={k:v.numpy().copy() for k,v in q.stages.items()}
    # Independent production forward, without diagnostic hooks, on all unique boards.
    plain=CanonicalIntegerPolicy(copy.deepcopy(c))(torch.tensor(raw,dtype=torch.int64)).numpy()
    assert np.array_equal(plain,direct)
    assert all(np.array_equal(ds[k][orbit[0]],v) for k,v in st.items())
    aligned=np.array([[direct[j,list(t)] for j in orbit[ti]] for ti,t in enumerate(TRANSFORMS)])
    member=aligned>=0;member&=(b==0)[None,:,:]
    rawmembers=(direct>=0)&(raw==0)
    rows=[];stage_rows=[]
    for ti,t in enumerate(TRANSFORMS):
        # All 627 transform observations are re-executed to validate dedup indexing.
        transformed=np.array([transform_board(v,t) for v in b],dtype=np.int64)
        assert np.array_equal(transformed,raw[orbit[ti]])
        qq=DiagnosticPolicy(copy.deepcopy(c));yy=qq(torch.from_numpy(transformed)).numpy()
        assert np.array_equal(yy,direct[orbit[ti]])
        for k,v in qq.stages.items():assert np.array_equal(v.numpy(),ds[k][orbit[ti]]),(ti,k)
        rawgold=opt[:,list(inverse(t))]
        predraw=rawmembers[orbit[ti]]
        r=measure_sets(predraw,rawgold);r.pop('chosen_moves')
        assert r['full_set_changes']==int((member[ti]!=opt).any(1).sum())
        rows.append(dict(transform_id=ti,source_to_destination=list(t),**r,exact_aligned_logit_boards=int((aligned[ti]==y).all(1).sum()),route_order_equal=int((ds['routes'][orbit[ti]]==st['routes']).all(1).sum()),route_membership_equal=int((np.sort(ds['routes'][orbit[ti]],1)==np.sort(st['routes'],1)).all(1).sum()),gate_equal=int((ds['gates'][orbit[ti]]==st['gates']).all(1).sum())))
        eq={}
        for k,v in st.items():
            if k.startswith('expert_'):
                eq[k]=sum(np.array_equal(executed_vector(st['routes'][i],v[i]),executed_vector(ds['routes'][j],ds[k][j])) for i,j in enumerate(orbit[ti]))
            else:eq[k]=sum(np.array_equal(v[i],align_stage(k,ds[k][j],t)) for i,j in enumerate(orbit[ti]))
        stage_rows.append(dict(transform_id=ti,equal_boards=eq))
    unique=measure_sets(rawmembers,rawopt);unique.pop('chosen_moves')
    # Orbit selected moves use actual transformed-coordinate priority, NOT transformed old chosen move.
    wrapper,wrappergate=raw_wrapper(y,b,raw,ci,tr,rawopt)
    assert wrapper['correct'].all() and np.array_equal(wrapper['members'],rawopt)
    changes=(member!=opt[None,:,:]).any(2)
    ids=np.flatnonzero(changes[1:].any(0))
    if not len(ids):ids=np.flatnonzero((aligned[1:]!=y).any(2).any(0))
    eid=int(ids[0]) if len(ids) else 0
    examples=[]
    for ti,t in enumerate(TRANSFORMS):
        j=int(orbit[ti,eid]);canmembers=opt[eid,list(inverse(t))];r=measure_sets(rawmembers[j:j+1],canmembers[None,:])
        examples.append(dict(callout=chr(65+ti),canonical_id=eid,transform_id=ti,raw_id=j,board=raw[j].tolist(),source_to_destination=list(t),canonical_board=b[eid].tolist(),direct_logits=direct[j].tolist(),aligned_logits=aligned[ti,eid].tolist(),direct_legal_set=np.flatnonzero(rawmembers[j]).tolist(),wrapper_legal_set=np.flatnonzero(canmembers).tolist(),direct_chosen=r['chosen_moves'][0],wrapper_chosen=next(s for s in PRIORITY if canmembers[s]),routes=ds['routes'][j].tolist(),gates=ds['gates'][j].tolist(),expert_hidden=expert_record(ds['routes'][j],ds['expert_hidden'][j]),expert_outputs=expert_record(ds['routes'][j],ds['expert_outputs'][j])))
    stabilizers=np.array([len(set(orbit[:,i])) for i in range(627)])
    result=dict(unique_direct=unique,orbit_observations=5016,unique_direct_inputs=4520,canonical_inputs=627,per_transform=rows,orbit_full_set_changes=int(changes.sum()),orbit_full_set_correct=int((~changes).sum()),all8_full_set_equivariant_canonical_boards=int((~changes).all(0).sum()),all8_exact_aligned_logits_canonical_boards=int((aligned==y[None,:,:]).all(2).all(0).sum()),orbit_size_distribution={str(k):int((stabilizers==k).sum()) for k in sorted(set(stabilizers.tolist()))},wrapper=dict(full_sets_correct=4520,chosen_optimal=4520,original_coordinate_ties_correct=4520,**wrappergate),stage_alignment=stage_rows,selected_example_canonical_id=eid,example_selection='first canonical ID with any nonidentity full-set disagreement, else logit disagreement, else0',inactive_experts='Null/unobserved in JSON. Dense NPZ expert zeros are storage placeholders only. Executed zero gates remain executed.')
    put(out/'results010.json',result);put(out/'examples010.json',examples)
    pack_arrays(out/'measurements010.npz',dict(ds,boards=raw,canonical_boards=b,canonical_logits=y,canonical_optimal=opt,raw_optimal=rawopt,raw_to_canonical_id=ci,raw_to_canonical_transform=tr,orbit_to_raw=orbit,aligned_logits=aligned,aligned_legal_sets=member,direct_legal_sets=rawmembers))
    pack_arrays(out/'baseline010.npz',dict(st,boards=b,optimal=opt))
    put(out/'provenance010.json',dict(prior_files_unchanged=preserve(),manifest_sha256=sha(ROOT/'experiment-study010.json'),source_model_sha256=gate['model_sha256'],identity_stage_equalities=len(st),production_direct_logit_scalar_checks=int(direct.size),dedup_crosschecks=5016,dedup_stage_equalities=8*len(st),imports=gate['imports'],scope=m['warning']))
    assert time.monotonic()-start<m['maximum_seconds'];print(json.dumps({k:v for k,v in result.items() if k not in ('stage_alignment','per_transform')},indent=2))

def values011(st,opt):
    n=len(opt);v={k:list(a) for k,a in st.items() if not k.startswith('expert_')}
    v['unordered_routes']=list(np.sort(st['routes'],axis=1));v['pair_and_gates']=list(np.concatenate((st['routes'],st['gates']),axis=1))
    for k in ('expert_hidden_pre','expert_hidden','expert_outputs'):v['executed_'+k]=[executed_vector(st['routes'][i],st[k][i]) for i in range(n)]
    v['unmasked_signs']=list(st['logits']>=0);v['legal_sign_set']=list(opt)
    return v

def run011(out):
    start=time.monotonic();out,m,data,count=prepared('011',out)
    b,bt,c,y,st,raw,ci,tr,opt,rawopt,cp,rp,gate,_=data
    labs=[tactical(tuple(v)) for v in b];labels=[tuple(bool(x[k]) for k in TACTICS) for x in labs]
    optimal=[tuple(map(int,np.flatnonzero(v))) for v in opt]
    controls=[(int((v!=0).sum()),int((v!=0).sum()%2),*geom(v)) for v in b]
    vals=values011(st,opt);assert set(vals)==set(m['stages'])
    order=sorted(range(627),key=lambda i:tuple(b[i]));rows=[];classes={};examples=[]
    for name in m['stages']:
        r,g=collision_census([vals[name][i] for i in order],[labels[i] for i in order],[optimal[i] for i in order],[controls[i] for i in order])
        for rr in (r,r['conditioned']):
            for field in ('first_tactic_pair','first_optimal_pair'):
                if rr[field] is not None:rr[field]=[order[i] for i in rr[field]]
        for group in g:group['ids']=[order[i] for i in group['ids']]
        for controlled,keys in [(False,labels),(True,labels)]:
            relevant=[]
            for group in g:
                sub={}
                for i in group['ids']:sub.setdefault(controls[i] if controlled else (),[]).append(i)
                relevant.extend(sub.values())
            mixes={task:sum(len({labs[i][task] for i in ids})>1 for ids in relevant) for task in TACTICS}
            (r['conditioned'] if controlled else r)['mixed_classes_per_tactic']=mixes
        rows.append(dict(stage=name,**r));classes[name]=g
        for reason,ids in [('different-tactic-tuple',r['first_tactic_pair']),('different-optimal-set',r['first_optimal_pair']),('controlled-different-tactic',r['conditioned']['first_tactic_pair']),('controlled-different-optimal-set',r['conditioned']['first_optimal_pair'])]:
            if ids is None:continue
            examples.append(dict(stage=name,reason=reason,canonical_ids=ids,boards=[b[i].tolist() for i in ids],labels=[labs[i] for i in ids],optimal_sets=[list(optimal[i]) for i in ids],legal_masks=[(b[i]==0).tolist() for i in ids],routes=[st['routes'][i].tolist() for i in ids],gates=[st['gates'][i].tolist() for i in ids],stage_values=[vals[name][i].tolist() for i in ids],logits=[y[i].tolist() for i in ids]))
    per=[]
    for e in range(c['experts']):
        ids=np.flatnonzero((st['routes']==e).any(1))
        for stage in ('expert_hidden_pre','expert_hidden','expert_outputs'):
            r,g=collision_census(list(st[stage][ids,e]),[labels[i] for i in ids],[optimal[i] for i in ids],[controls[i] for i in ids])
            per.append(dict(expert_id=e,stage=stage,canonical_ids=ids.tolist(),executed_observations=len(ids),executed_zero_gate_boards=sum(int(st['gates'][i,np.flatnonzero(st['routes'][i]==e)[0]])==0 for i in ids),inactive_observations=None,**r))
    records=[dict(canonical_id=i,board=b[i].tolist(),labels=labs[i],control=list(controls[i]),optimal_set=list(optimal[i]),routes=st['routes'][i].tolist(),gates=st['gates'][i].tolist(),expert_hidden=expert_record(st['routes'][i],st['expert_hidden'][i]),expert_outputs=expert_record(st['routes'][i],st['expert_outputs'][i])) for i in range(627)]
    put(out/'results011.json',rows);put(out/'classes011.json',classes);put(out/'examples011.json',examples);put(out/'expert-census011.json',per);put(out/'boards011.json',records)
    pack_arrays(out/'baseline011.npz',dict(st,boards=b,optimal=opt))
    put(out/'provenance011.json',dict(prior_files_unchanged=preserve(),manifest_sha256=sha(ROOT/'experiment-study011.json'),source_model_sha256=gate['model_sha256'],canonical_board_observations=627,stage_scopes=len(rows),per_expert_scopes=len(per),executed_expert_observations=1254,imports=gate['imports'],warning=m['warning']))
    assert time.monotonic()-start<m['maximum_seconds'];print('\n'.join(f"{r['stage']}: {r['distinct_classes']} classes; mixed tactics {r['mixed_tactic_classes']}; mixed optimal {r['mixed_optimal_classes']}; controlled {r['conditioned']['mixed_tactic_classes']}/{r['conditioned']['mixed_optimal_classes']}" for r in rows))
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('study',choices=['010','011']);a.add_argument('--out',required=True);args=a.parse_args();globals()['run'+args.study](args.out)
