#!/usr/bin/env python3
"""Finite per-square exact path study. Only fresh study004 outputs are writable."""
import argparse,copy,hashlib,json,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
import torch
from falken9.strategy_square004 import D,TASKS,rnd,square_labels,bookkeep
from falken9.strategy_diagnostics import DiagnosticPolicy,tactical,enumerate_boards,offline_optimal_set,parameter_copy
from falken9.strategy_patching import PatchPolicy
from falken9.flexible_integer_export import load
from falken9.symmetry import canonicalize
from scripts.model_strategy_study import splits,behavior,sha,stored_layout
from scripts.verify_app import fixture_records
from scripts.build_runtime import FOUR_MODEL

def put(p,v):
    p.write_text(json.dumps(v,separators=(',',':'),allow_nan=False)+'\n')

def prior():
    a=json.loads((ROOT/'RESEARCH-SNAPSHOT.json').read_text())['source_evidence_sha256']
    b=json.loads((ROOT/'verification-study003.json').read_text())['sha256']
    assert len(a)==69 and len(b)==23
    for n,h in a.items():assert sha(ROOT/n)==h,n
    for n,h in b.items():assert sha(ROOT/'artifacts/interpretability/study-003-final'/n)==h,n
    return len(a),len(b)

def geom(b):
    side=1+sum(v!=0 for v in b)%2
    return tuple(sum(b[s]==m for s in squares) for m in (side,3-side) for squares in ((0,2,6,8),(1,3,5,7),(4,)))

def outcome(y,b,opt):
    members=(y>=0)&(b==0);order=[4,1,3,5,7,2,6,8,0]
    moves=np.array([next((s for s in order if row[s]),-1) for row in members])
    correct=np.array([s>=0 and opt[i,s] for i,s in enumerate(moves)])
    return members,moves,correct

def run(output):
    torch.set_num_threads(1)
    out=Path(output);out.mkdir(parents=True,exist_ok=False)
    import falken9.strategy_square004 as sm,scripts.model_strategy_study as ss
    assert Path(sm.__file__).is_relative_to(ROOT) and Path(ss.__file__).is_relative_to(ROOT)
    importmap={n:str(Path(m.__file__).resolve()) for n,m in sorted(sys.modules.items()) if (n=='falken9' or n.startswith('falken9.') or n.startswith('scripts.')) and getattr(m,'__file__',None)}
    assert all(Path(v).is_relative_to(ROOT) for v in importmap.values()),importmap
    n69,n23=prior()
    records,fh=fixture_records();rows=sorted(records.values(),key=lambda r:r['canonical_index'])
    boards=np.array([r['board'] for r in rows],dtype=np.int64);bt=torch.from_numpy(boards)
    c=load(FOUR_MODEL);q=DiagnosticPolicy(c);y=q(bt).numpy().copy()
    st={k:v.numpy().copy() for k,v in q.stages.items()};checks=0
    for i,r in enumerate(rows):
        for k,gold in r['stages'].items():
            got=st[k][i]
            if k in ('expert_hidden_pre','expert_hidden','expert_outputs'):got=got[st['routes'][i]]
            assert got.tolist()==gold,(i,k)
            checks+=1
    rawlist=sorted(enumerate_boards());raw=np.array(rawlist,dtype=np.int64)
    lookup={tuple(b):i for i,b in enumerate(boards)}
    aligned=[canonicalize(b) for b in rawlist]
    ci=np.array([lookup[b] for b,t in aligned]);trans=np.array([t for b,t in aligned])
    rawopt=np.array([[s in offline_optimal_set(b) for s in range(9)] for b in rawlist])
    base=behavior(y,raw,ci,trans,rawopt)
    assert len(raw)==4520 and len(boards)==627 and base['correct'].all() and np.array_equal(base['members'],rawopt)
    opt=np.array([[s in offline_optimal_set(tuple(b)) for s in range(9)] for b in boards])
    cm,move,correct=outcome(y,boards,opt);assert correct.all() and np.array_equal(cm,opt)
    priority=list(c['wrapper'][-9:]);assert priority==[4,1,3,5,7,2,6,8,0]
    for i,(b,t) in enumerate(aligned):
        mem={s for s in range(9) if raw[i,s]==0 and y[lookup[b],t[s]]>=0}
        assert mem==set(np.flatnonzero(base['members'][i]))
        assert next(s for s in priority if s in mem)==base['moves'][i]
    put(out/'baseline-gate.json',dict(canonical=627,raw=4520,stage_vectors=checks,fixture_sha256=fh,model_sha256=sha(FOUR_MODEL),wrapper_set_errors=0,wrapper_move_errors=0,scope='Host reproduction of saved actual target evidence; no new C64 execution',prior69=n69,prior23=n23))
    (out/'experiment-manifest.json').write_bytes((ROOT/'experiment-study004.json').read_bytes())
    print('004 baseline627/4520 and69+23 immutable hashes PASS',flush=True)
    labels=[square_labels(tuple(map(int,b))) for b in boards];old=[tactical(tuple(b)) for b in boards];fold=splits(old)
    for i,l in enumerate(labels):
        for task,oldkey in [('win','wins'),('block','block_squares'),('fork','forks'),('prevention','fork_prevention_squares')]:
            gold=old[i][oldkey] if task!='fork' or old[i]['has_fork'] else []
            assert [s for s in range(9) if l[s][task]]==gold,(i,task)
    books=[bookkeep(c,{k:v[i].tolist() for k,v in st.items()}) for i in range(627)]
    put(out/'exact-paths.json',dict(denominator=D,axes='board,route-slot,hidden-unit,expert-output-lane,candidate-square; expert IDs explicit; absent experts unobserved',records=books))
    layout=stored_layout(c)
    rawpacket=FOUR_MODEL.read_bytes();pos=struct.calcsize('<4s10BHH')+81;scale_offsets={}
    for name in layout:
        bits,rank,n=struct.unpack_from('<BBH',rawpacket,pos)
        scale_offsets[name]=pos+4+rank;pos+=4+rank+n
    # Every hidden->lane and lane->square scalar, packet offset, RAM address.
    coords=[]
    for name in ('expert_w2','expert_b2','output.weight','output.bias'):
        t=c['tensors'][name]
        for idx in np.ndindex(tuple(t['codes'].shape)):
            flat=int(np.ravel_multi_index(idx,t['codes'].shape));offset=layout[name]['byte_offset']+flat*t['bits']//8
            exp=t['exponents'][idx[0]*8+idx[-1]] if name=='expert_w2' else t['exponents'][idx[0]] if name=='output.weight' else t['exponents'][0]
            ei=idx[0]*8+idx[-1] if name=='expert_w2' else idx[0] if name=='output.weight' else 0
            scaleoffset=scale_offsets[name]+ei
            assert struct.unpack_from('<b',rawpacket,scaleoffset)[0]==exp
            coords.append(dict(tensor=name,coordinates=list(idx),flat_index=flat,packet_byte_offset=offset,runtime_address=hex(0x4000+offset),bits=t['bits'],code=int(t['codes'][idx]),exponent=exp,exponent_byte_offset=scaleoffset,exponent_runtime_address=hex(0x4000+scaleoffset)))
    put(out/'weight-coordinates.json',dict(indexing='zero based; RAM base$4000 from saved runtime model residency; little-endian W16 scalars',layout=layout,scalars=coords))
    put(out/'raw-alignment.json',[dict(board=list(b),canonical_id=int(ci[i]),raw_to_canonical=list(map(int,trans[i])),fold=int(fold[ci[i]]),optimal_set=np.flatnonzero(rawopt[i]).tolist(),selected_move=int(base['moves'][i])) for i,b in enumerate(rawlist)])
    cases=[]
    for i,b in enumerate(boards):
        cases.append(dict(id=i,board=b.tolist(),ply=int((b!=0).sum()),side=1+int((b!=0).sum())%2,fold=int(fold[i]),labels=labels[i],routes=st['routes'][i].tolist(),gates=st['gates'][i].tolist(),hidden=[st['expert_hidden'][i,e].tolist() if e in st['routes'][i] else None for e in range(4)],logits=y[i].tolist(),optimal_set=np.flatnonzero(opt[i]).tolist()))
    put(out/'cases.json',cases)
    # Canonical receiver is kept in its own raw frame. Legal mark relocation
    # changes exactly two squares; donor is then fed in ITS canonical frame.
    rawset=set(rawlist);matches=[];coverage={}
    for task in TASKS:
        for f in range(3):coverage[f'{task}:{f}']=dict(positive_squares=0,covered_positive_squares=0,unique_donors=0)
        for i,barr in enumerate(boards):
            b=tuple(map(int,barr));f=int(fold[i])
            for s in range(9):
                if not labels[i][s][task]:continue
                coverage[f'{task}:{f}']['positive_squares']+=1
                pool=[]
                for src,v in enumerate(b):
                    if not v:continue
                    for dest,w in enumerate(b):
                        if w or dest==s:continue
                        alt=list(b);alt[src]=0;alt[dest]=v;alt=tuple(alt)
                        if alt not in rawset or geom(alt)!=geom(b):continue
                        cb,tr=canonicalize(alt);j=lookup[cb];ss=int(tr[s])
                        if j==i or fold[j]!=f or labels[j][ss][task]:continue
                        if not np.array_equal(st['routes'][i],st['routes'][j]):continue
                        gd=int(np.abs(st['gates'][i]-st['gates'][j]).max())
                        if gd>4096:continue
                        pool.append((src,dest,j,ss,gd,alt,tuple(map(int,tr))))
                if pool:
                    src,dest,j,ss,gd,alt,tr=min(pool)
                    matches.append(dict(task=task,fold=f,receiver=i,receiver_square=s,donor=j,donor_square=ss,receiver_raw=list(b),donor_raw=list(alt),receiver_raw_to_canonical=list(range(9)),donor_raw_to_canonical=list(tr),relocated_mark=b[src],from_square=src,to_square=dest,hamming_raw=2,gate_delta=gd,geometry=list(geom(b))))
                    coverage[f'{task}:{f}']['covered_positive_squares']+=1
    for task in TASKS:
        for f in range(3):coverage[f'{task}:{f}']['unique_donors']=len({r['donor'] for r in matches if r['task']==task and r['fold']==f})
    put(out/'matched-relocations.json',matches);put(out/'matching-coverage.json',coverage)
    # Descriptive path patterns with actually executed units only. No zeros
    # are substituted for absent expert observations.
    support=np.full((627,4,4,9),np.nan)
    lanes=np.full((627,4,4,8,9),np.nan)
    for i,bk in enumerate(books):
        for slot,e in enumerate(bk['expert_ids']):
            p=np.array(bk['paths'][slot],dtype=np.float64)/D
            lanes[i,e]=p;support[i,e]=p.sum(1)
    centered=support.copy()
    # Explicit axes avoid NumPy advanced-index axis reordering.
    for i,b in enumerate(boards):
        for e in st['routes'][i]:
            centered[i,e]=support[i,e]-support[i,e][:,b==0].mean(1)[:,None]
    rankings=[]
    for task in TASKS:
        for e in range(4):
            for h in range(4):
                rr=[r for r in matches if r['task']==task and r['fold']==0 and e in st['routes'][r['receiver']]]
                vals=[float(centered[r['receiver'],e,h,r['receiver_square']]-centered[r['donor'],e,h,r['donor_square']]) for r in rr]
                rankings.append(dict(task=task,component=[e,h],train_matched_n=len(vals),mean_centered_support_contrast=float(np.mean(vals)) if vals else None))
    chosen=[];selected_tasks={}
    for task in TASKS:
        rank=sorted([r for r in rankings if r['task']==task and r['train_matched_n']],key=lambda r:(-r['mean_centered_support_contrast'],r['component']))
        if rank and tuple(rank[0]['component']) not in chosen and len(chosen)<2:
            comp=tuple(rank[0]['component']);chosen.append(comp);selected_tasks[str(comp)]=task
    components=list(dict.fromkeys(chosen+[(1,0),(3,3)]+[(e,(h+1)%4) for e,h in chosen]))
    assert len(components)<=6
    selection=dict(rankings=rankings,selected=[list(v) for v in chosen],components=[list(v) for v in components],selected_tasks=selected_tasks)
    put(out/'training-selection.json',selection)
    # Per-square activity patterns: all domain is descriptive, folds reported.
    patterns=[]
    for task in TASKS+('neutral',):
        for f in range(3):
            for e in range(4):
                for h in range(4):
                    entries=[(i,s) for i in range(627) if fold[i]==f and e in st['routes'][i] for s in range(9) if labels[i][s][task]]
                    vals=[support[i,e,h,s] for i,s in entries]
                    patterns.append(dict(task=task,fold=f,expert=e,hidden=h,n=len(vals),positive_support=int(sum(v>0 for v in vals)),negative_support=int(sum(v<0 for v in vals)),mean_support=float(np.mean(vals)) if vals else None,mean_centered_support=float(np.mean([centered[i,e,h,s] for i,s in entries])) if vals else None))
    put(out/'square-patterns.json',patterns)
    lane_patterns=[]
    for task in TASKS+('neutral',):
        for s in range(9):
            for e in range(4):
                ids=[i for i in range(627) if e in st['routes'][i] and labels[i][s][task]]
                for h in range(4):
                    for j in range(8):
                        vals=[lanes[i,e,h,j,s] for i in ids]
                        lane_patterns.append(dict(task=task,square=s,expert=e,hidden=h,lane=j,n=len(vals),positive=int(sum(v>0 for v in vals)),negative=int(sum(v<0 for v in vals)),mean=float(np.mean(vals)) if vals else None))
    put(out/'lane-square-patterns.json',lane_patterns)
    # Identity patches verify same expert ID, not slot and not fabricated zeros.
    identity=[dict(expert=e,unit=h,values=[int(st['expert_hidden'][i,e,h]) if e in st['routes'][i] else None for i in range(627)]) for e,h in components]
    iq=PatchPolicy(c,patches=identity);assert np.array_equal(iq(bt).numpy(),y)
    assert all(np.array_equal(iq.stages[k].numpy(),v) for k,v in st.items())
    results=[];vectors=[]
    def evalrun(name,pol,meta):
        yy=pol(bt).numpy().copy()
        assert np.array_equal(pol.stages['routes'].numpy(),st['routes']) and np.array_equal(pol.stages['gates'].numpy(),st['gates'])
        mm,mv,ok=outcome(yy,boards,opt);rawp=behavior(yy,raw,ci,trans,rawopt)
        def stats(members,moves,good,basem,bmoves):
            empty=~members.any(1)
            return dict(n=len(members),empty_set=int(empty.sum()),nonoptimal_nonempty=int((~good&~empty).sum()),nonoptimal_including_empty=int((~good).sum()),set_change=int((members!=basem).any(1).sum()),equivalent_optimal_tie=int(((moves!=bmoves)&good).sum()))
        square=[];matched=[]
        relevant=[meta['expert']] if 'expert' in meta else [p[0] for p in meta.get('components',[])]
        covered=np.array([all(e in st['routes'][i] for e in relevant) for i in range(627)])
        for task in TASKS+('neutral',):
            for f in range(3):
                mask=np.array([[covered[i] and fold[i]==f and labels[i][s][task] for s in range(9)] for i in range(627)])
                square.append(dict(task=task,fold=f,n=int(mask.sum()),dropped_baseline_member=int((mask&cm&~mm).sum()),added_baseline_reject=int((mask&~cm&mm).sum()),membership_change=int((mask&(cm!=mm)).sum()),mean_logit_delta=float((yy-y)[mask].mean()) if mask.any() else None))
                rr=[r for r in matches if r['task']==task and r['fold']==f and covered[r['receiver']] and covered[r['donor']]]
                dd=yy-y
                vals=[];targetflips=0;controlflips=0
                for r in rr:
                    i,s,j,t=r['receiver'],r['receiver_square'],r['donor'],r['donor_square']
                    vals.append(float(dd[i,s]-dd[i,boards[i]==0].mean()-dd[j,t]+dd[j,boards[j]==0].mean()))
                    targetflips+=int(mm[i,s]!=cm[i,s]);controlflips+=int(mm[j,t]!=cm[j,t])
                matched.append(dict(task=task,fold=f,n=len(rr),target_membership_flips=targetflips,control_membership_flips=controlflips,mean_demeaned_logit_delta_contrast=float(np.mean(vals)) if vals else None))
        rec=dict(id=name,metadata=meta,canonical=stats(mm,mv,ok,cm,move),raw=stats(rawp['members'],rawp['moves'],rawp['correct'],base['members'],base['moves']),square=square,matched=matched,route_order_changes=0,route_membership_changes=0,gate_changes=0,changed_canonical_ids=np.flatnonzero((mm!=cm).any(1)).tolist())
        results.append(rec);vectors.append(dict(id=name,logits=yy.tolist(),routes=pol.stages['routes'].tolist(),gates=pol.stages['gates'].tolist()))
        return yy
    cache={}
    for e,h in components:
        for n in (0,2):
            name=f'unit-E{e}h{h}-{n}of4';cache[name]=evalrun(name,PatchPolicy(c,doses=[(e,h,n)]),dict(kind='unit_dose',expert=e,hidden=h,remaining_quarters=n))
    if len(chosen)==2:
        for n in (0,2):
            name=f'pair-{n}of4';cache[name]=evalrun(name,PatchPolicy(c,doses=[(e,h,n) for e,h in chosen]),dict(kind='pair_dose',components=[list(v) for v in chosen],remaining_quarters=n))
    path_selection=[]
    for e,h in chosen:
        task=selected_tasks[str((e,h))]
        entries=[(i,s) for i in range(627) if fold[i]==0 and e in st['routes'][i] for s in range(9) if labels[i][s][task]]
        strengths=[float(np.mean([abs(lanes[i,e,h,j,s]) for i,s in entries])) if entries else 0.0 for j in range(8)]
        lane=max(range(8),key=lambda j:(strengths[j],-j));path_selection.append(dict(expert=e,hidden=h,task=task,selected_lane=lane,control_lane=(lane+1)%8,training_mean_abs_path=strengths,training_n=len(entries)))
        for j,kind in [(lane,'selected'),((lane+1)%8,'adjacent_control')]:
            for n in (0,2):
                code=int(c['tensors']['expert_w2']['codes'][e,h,j]);value=rnd(code*n,4)
                cc=parameter_copy(c,'expert_w2',(e,h,j),value)
                name=f'path-E{e}h{h}-lane{j}-{n}of4';cache[name]=evalrun(name,DiagnosticPolicy(cc),dict(kind='single_weight_path',expert=e,hidden=h,lane=j,lane_kind=kind,remaining_quarters=n,original_code=code,replacement_code=value))
    pair_audit=[]
    if len(chosen)==2:
        for n in (0,2):
            aa,bb=[cache[f'unit-E{e}h{h}-{n}of4'] for e,h in chosen]
            ab=cache[f'pair-{n}of4']
            ea=~outcome(aa,boards,opt)[2];eb=~outcome(bb,boards,opt)[2];eab=~outcome(ab,boards,opt)[2]
            nonadd=ab-aa-bb+y
            pair_audit.append(dict(remaining_quarters=n,single_failure_union=int((ea|eb).sum()),pair_failures=int(eab.sum()),rescued_union_ids=np.flatnonzero((ea|eb)&~eab).tolist(),new_beyond_union_ids=np.flatnonzero(~(ea|eb)&eab).tolist(),max_abs_logit_nonadditivity=int(np.abs(nonadd).max()),logit_nonadditivity=nonadd.tolist(),interpretation='finite lesion interaction; NOT additive contribution or semantic circuit evidence'))
    put(out/'pair-audit.json',pair_audit)
    put(out/'path-selection.json',path_selection)
    # Amplitude-only integer control; maintain signs including exact zero.
    amplitude=np.sign(y)*((np.abs(y)+1)//2)
    am,_,_=outcome(amplitude,boards,opt);assert np.array_equal(am,cm)
    put(out/'amplitude-identity-controls.json',dict(amplitude_half_sign_preserved=True,amplitude_changed_logit_cells=int((amplitude!=y).sum()),identity_all627_all_stages=True,route_slot_distinct_from_expert_id=True,postrouting_all_interventions_route_gate_changes=0))
    put(out/'interventions.json',results);put(out/'intervention-vectors.json',vectors)
    examples=[]
    for e,h in components:
        yy=cache[f'unit-E{e}h{h}-0of4'];mm,mv,ok=outcome(yy,boards,opt)
        for task in TASKS+('neutral',):
            for condition in ('positive_dropped','positive_retained','nonmember_added'):
                pool=[(i,s) for i in range(627) if e in st['routes'][i] for s in range(9) if labels[i][s][task] and ((cm[i,s] and not mm[i,s]) if condition=='positive_dropped' else (cm[i,s] and mm[i,s]) if condition=='positive_retained' else (not cm[i,s] and mm[i,s]))]
                if not pool:continue
                # Confirmatory examples preferred, deterministic lexicographic.
                i,s=min(pool,key=lambda x:(fold[x[0]]!=2,x))
                examples.append(dict(id=f'E{e}h{h}-{task}-{condition}',component=[e,h],task=task,condition=condition,canonical_id=i,square=s,board=boards[i].tolist(),fold=int(fold[i]),baseline_logit=int(y[i,s]),lesion_logit=int(yy[i,s]),pre_round_unit_support=float(support[i,e,h,s]),centered_support=float(centered[i,e,h,s]),baseline_set=np.flatnonzero(cm[i]).tolist(),lesion_set=np.flatnonzero(mm[i]).tolist(),empty_set=bool(not mm[i].any()),nonoptimal_nonempty=bool(mm[i].any() and not ok[i]),equivalent_optimal_tie=bool(ok[i] and mv[i]!=move[i])))
    put(out/'examples.json',examples)
    # Exact residual ranges and descriptive top-down magnitude, not percentages
    # of psychological cause. Cancellation makes ratios ill conditioned.
    residual_keys=('mix_round','merge_clamp','head_round','head_clamp')
    residual_summary={k:dict(max_abs=float(max(abs(v) for b in books for v in b['terms'][k])/D),nonzero_cells=sum(v!=0 for b in books for v in b['terms'][k])) for k in residual_keys}
    residual_summary['expert_round']=dict(max_abs=float(max(abs(v) for b in books for k,values in b['terms'].items() if k.endswith('_round') and k.startswith('E') for v in values)/D),nonzero_cells=sum(v!=0 for b in books for k,values in b['terms'].items() if k.endswith('_round') and k.startswith('E') for v in values))
    residual_summary['expert_clamp_nonzero']=sum(v!=0 for b in books for k,values in b['terms'].items() if k.endswith('_clamp') and k.startswith('E') for v in values)
    magnitude={}
    for k in ('readout','output_bias'):
        vals=[abs(b['terms'][k][s])/D for i,b in enumerate(books) for s in range(9) if boards[i,s]==0]
        magnitude[k]=dict(mean_abs=float(np.mean(vals)),max_abs=float(max(vals)))
    vals=[abs(values[s])/D for i,b in enumerate(books) for values in b['executed_expert_support'] for s in range(9) if boards[i,s]==0]
    magnitude['per_executed_expert']=dict(mean_abs=float(np.mean(vals)),max_abs=float(max(vals)))
    rounding_sign_changes=[]
    total_rounding_max=0
    for i,b in enumerate(books):
        for s in range(9):
            pre=sum(v[s] for k,v in b['terms'].items() if not k.endswith('_round') and k not in ('mix_round','head_round') and not k.endswith('_clamp'))
            total_rounding_max=max(total_rounding_max,abs(int(y[i,s])*D-pre))
            if boards[i,s]==0 and ((pre>=0)!=(y[i,s]>=0)):rounding_sign_changes.append([i,s])
    put(out/'rounding-threshold-audit.json',dict(pre_round_convention='readout + output bias + all routed unit paths + expert biases; all named rounding/clamp residuals omitted ONLY for this descriptive comparison',legal_sign_change_coordinates=rounding_sign_changes,max_abs_combined_residual=float(total_rounding_max/D),not_a_new_inference_contract=True))
    n69,n23=prior();assert np.array_equal(DiagnosticPolicy(c)(bt).numpy(),y)
    summary=dict(canonical=627,raw=4520,baseline_stage_checks=checks,prior69_verified=n69,prior23_verified=n23,exact_logits=627*9,bookkeeping_max_error=0,denominator=D,identity_all_stages=True,interventions=len(results),selected=[list(v) for v in chosen],confirmed_components=[list(v) for v in components],matched_pairs=len(matches),matching_coverage=coverage,fold_counts=[int((fold==f).sum()) for f in range(3)],candidate_counts={t:[sum(labels[i][s][t] for i in range(627) if fold[i]==f for s in range(9)) for f in range(3)] for t in TASKS+('neutral',)},executed_expert_observations=1254,executed_zero_gate_observations=int((st['gates']==0).sum()),unobserved_expert_board_cells=1254,rounding=residual_summary,empty_square_magnitude=magnitude,model_sha256=sha(FOUR_MODEL),game_changed=False)
    summary['test_fork_positive_boards']=sum(any(labels[i][s]['fork'] for s in range(9)) for i in range(627) if fold[i]==2)
    summary['legal_empty_square_observations']=int((boards==0).sum())
    summary['occupied_nonnegative_logits']=int(((boards!=0)&(y>=0)).sum())
    summary['legal_rounding_sign_changes']=len(rounding_sign_changes)
    summary['max_abs_combined_rounding_residual']=float(total_rounding_max/D)
    put(out/'summary.json',summary)
    put(out/'provenance.json',dict(snapshot='027e1c11c6114312fee552cdf894b248fb3e5be0',model_sha256=sha(FOUR_MODEL),import_root=str(ROOT),all_imported_project_modules_verified_inside_root=True,interpreter='/home/ai/falken-9/.venv/bin/python',torch=torch.__version__,numpy=np.__version__,source_sha256={n:sha(ROOT/n) for n in ('experiment-study004.json','falken9/strategy_square004.py','scripts/model_strategy_study004.py','tests/test_strategy_study004.py')},execution='CPU1thread; actual-target saved evidence reproduced on host; no new C64 execution; no game/main changes'))
    put(out/'hashes.json',{p.name:sha(p) for p in sorted(out.iterdir()) if p.is_file()})
    print(json.dumps(summary,indent=2),flush=True)
    return summary

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);run(ap.parse_args().output)
