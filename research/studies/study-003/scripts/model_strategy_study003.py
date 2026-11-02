#!/usr/bin/env python3
"""Bounded frozen-model study003. See fixed experiment-study003.json."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import torch
from falken9.strategy_diagnostics import DiagnosticPolicy,tactical,enumerate_boards,offline_optimal_set
from falken9.strategy_patching import PatchPolicy,donor_values
from falken9.flexible_integer_export import load
from falken9.symmetry import canonicalize
from scripts.model_strategy_study import splits,behavior,sha,dump
from scripts.verify_app import fixture_records
from scripts.build_runtime import FOUR_MODEL
ROOT=Path(__file__).resolve().parents[1]
TASKS=('has_win','must_block','has_fork','has_fork_prevention')
KEYS=('ply','side','own_corners','opponent_corners','own_edges','opponent_edges','center_own','center_opponent')


def compact(path,obj):
    Path(path).write_text(json.dumps(obj,separators=(',',':'),allow_nan=False)+'\n')


def cname(c):return f'E{c[0]}.h{c[1]}'


def key(label,route):return tuple(int(label[k]) for k in KEYS)+tuple(map(int,route))


def run(output):
    torch.set_num_threads(1)
    out=Path(output);out.mkdir(parents=True,exist_ok=False)
    # All imports must bind this isolated snapshot, never editable main.
    import falken9.strategy_diagnostics as sd, scripts.model_strategy_study as ss
    assert Path(sd.__file__).is_relative_to(ROOT) and Path(ss.__file__).is_relative_to(ROOT)
    snapshot=json.loads((ROOT/'RESEARCH-SNAPSHOT.json').read_text())
    for name,h in snapshot['source_evidence_sha256'].items():assert sha(ROOT/name)==h,name
    records,fixture_hashes=fixture_records();rows=sorted(records.values(),key=lambda r:r['canonical_index'])
    boards=np.array([r['board'] for r in rows],dtype=np.int64);bt=torch.from_numpy(boards)
    c=load(FOUR_MODEL);policy=DiagnosticPolicy(c);logits=policy(bt).numpy().copy()
    stages={k:v.numpy().copy() for k,v in policy.stages.items()};checks=0
    for i,row in enumerate(rows):
        for name,gold in row['stages'].items():
            got=stages[name][i]
            if name in ('expert_hidden_pre','expert_hidden','expert_outputs'):got=got[stages['routes'][i]]
            assert got.tolist()==gold,(i,name)
            checks+=1
    labels=[tactical(tuple(b)) for b in boards];fold=splits(labels)
    raw_list=sorted(enumerate_boards());raw=np.array(raw_list,dtype=np.int64)
    lookup={tuple(b):i for i,b in enumerate(boards)}
    pairs=[canonicalize(b) for b in raw_list]
    ci=np.array([lookup[b] for b,t in pairs]);transforms=np.array([t for b,t in pairs])
    optimal=np.zeros((len(raw),9),dtype=bool)
    for i,b in enumerate(raw_list):optimal[i,list(offline_optimal_set(b))]=True
    assert (len(boards),len(raw))==(627,4520)
    base=behavior(logits,raw,ci,transforms,optimal)
    assert base['correct'].all() and np.array_equal(base['members'],optimal)
    canopt=np.array([[j in offline_optimal_set(tuple(b)) for j in range(9)] for b in boards])
    ident=np.tile(np.arange(9),(len(boards),1));cibase=np.arange(len(boards))
    canbase=behavior(logits,boards,cibase,ident,canopt)
    # Verify original-coordinate priority using independent explicit set inversion.
    priority=list(c['wrapper'][-9:]);assert priority==[4,1,3,5,7,2,6,8,0]
    for i,(b,t) in enumerate(pairs):
        members={j for j in range(9) if raw[i,j]==0 and logits[lookup[b],t[j]]>=0}
        assert members==set(np.flatnonzero(base['members'][i]))
        assert next(j for j in priority if j in members)==base['moves'][i]
    dump(out/'baseline-gate.json',dict(canonical=627,raw=4520,all_stage_vectors_checked=checks,evidence_hashes_verified=len(snapshot['source_evidence_sha256']),fixture_sha256=fixture_hashes,model_sha256=sha(FOUR_MODEL),legal_set_errors=0,nonoptimal_moves=0,tie_mismatches=0,wrapper_scope='Python composed full-set inverse/legal-mask/original-tie wrapper against saved actual627 vectors; no new 6502 execution'))
    # Copy precommitted fixed plan after passing baseline, before any new evaluation.
    (out/'experiment-manifest.json').write_bytes((ROOT/'experiment-study003.json').read_bytes())
    routes=stages['routes'];gates=stages['gates'];bank=stages['expert_hidden']
    active=np.zeros((627,4),dtype=bool)
    for e in range(4):active[:,e]=(routes==e).any(1)
    ys={t:np.array([v[t] for v in labels],dtype=bool) for t in TASKS}
    geometry=[key(v,r) for v,r in zip(labels,routes)]
    raw_fold=fold[ci]
    # Save full alignment and observed masks. Null means NOT evaluated expert.
    cases=[]
    for i,b in enumerate(boards):
        hidden=[[int(x) for x in bank[i,e]] if active[i,e] else None for e in range(4)]
        cases.append(dict(id=i,board=b.tolist(),fold=['train','validation','test'][fold[i]],labels=labels[i],routes=routes[i].tolist(),gates=gates[i].tolist(),hidden=hidden,logits=logits[i].tolist(),optimal_set=np.flatnonzero(canopt[i]).tolist(),raw_multiplicity=int((ci==i).sum())))
    compact(out/'cases.json',cases)
    compact(out/'raw-alignment.json',[dict(board=list(b),canonical_index=int(ci[i]),original_to_canonical=list(map(int,transforms[i])),baseline_move=int(base['moves'][i]),optimal_set=np.flatnonzero(optimal[i]).tolist()) for i,b in enumerate(raw_list)])
    results=[];experiments=[];cache={}

    def stats(pred,ref,mask):
        valid=pred['members'].any(1);empty=~valid;bad=~pred['correct'];setdiff=(pred['members']!=ref['members']).any(1)
        tie=(pred['moves']!=ref['moves'])&pred['correct']
        n=int(mask.sum())
        return dict(n=n,empty_set=int((empty&mask).sum()),nonoptimal_nonempty=int((bad&~empty&mask).sum()),nonoptimal_including_empty=int((bad&mask).sum()),complete_set_change=int((setdiff&mask).sum()),equivalent_optimal_tie_change=int((tie&mask).sum()),optimal_move_set_changed=int((setdiff&pred['correct']&mask).sum()))

    def evaluate(name,q,coverage=None,meta=None):
        y=q(bt).numpy().copy();s={k:v.numpy().copy() for k,v in q.stages.items()}
        pred=behavior(y,raw,ci,transforms,optimal);cp=behavior(y,boards,cibase,ident,canopt)
        cover=np.ones(627,dtype=bool) if coverage is None else coverage
        rc=cover[ci]
        routechange=(s['routes']!=routes).any(1);gatechange=(s['gates']!=gates).any(1)
        record=dict(id=name,metadata=meta or {},raw=stats(pred,base,np.ones(4520,dtype=bool)),canonical=stats(cp,canbase,np.ones(627,dtype=bool)),covered_raw=stats(pred,base,rc),covered_canonical=stats(cp,canbase,cover),coverage_canonical_ids=np.flatnonzero(cover).tolist(),route_changes=int(routechange.sum()),gate_changes=int(gatechange.sum()),classes={})
        error=~cp['correct'];rawerror=~pred['correct']
        for task in TASKS:
            strata={}
            for f,fn in [(None,'all'),(0,'train'),(1,'validation'),(2,'test')]:
                fmask=np.ones(627,dtype=bool) if f is None else fold==f
                mask=cover&fmask&ys[task]
                # Exact geometry + ordered routes + gate tolerance matching, only covered negatives.
                covered_target=[];weighted=0.0;neg_ids=set()
                for i in np.flatnonzero(mask):
                    negatives=[j for j in np.flatnonzero(cover&fmask&~ys[task]) if geometry[j]==geometry[i] and np.abs(gates[j]-gates[i]).max()<=4096]
                    if negatives:
                        covered_target.append(int(i));weighted+=float(error[negatives].mean());neg_ids.update(negatives)
                ids=np.array(covered_target,dtype=int)
                strata[fn]=dict(canonical=stats(cp,canbase,mask),raw=stats(pred,base,mask[ci]),matched_target_n=len(ids),matched_negative_unique_n=len(neg_ids),matched_target_errors=int(error[ids].sum()),matched_negative_weighted_errors=weighted,matched_target_error_rate=float(error[ids].mean()) if len(ids) else None,matched_negative_error_rate=weighted/len(ids) if len(ids) else None,matched_target_ids=covered_target,matched_negative_ids=sorted(map(int,neg_ids)))
            record['classes'][task]=strata
        # Full logits/routes/gates support independent outcome recounts; inactive hidden cells explicit null in baseline cases.
        record['route_membership_changes']=int((np.sort(s['routes'],axis=1)!=np.sort(routes,axis=1)).any(1).sum())
        experiments.append(dict(id=name,logits=y.tolist(),routes=s['routes'].tolist(),gates=s['gates'].tolist(),norm2_output=s['norm2_output'].tolist(),hidden=[[s['expert_hidden'][i,e].tolist() if e in s['routes'][i] else None for e in range(4)] for i in range(627)]))
        record['changed_canonical_ids']=np.flatnonzero((cp['members']!=canbase['members']).any(1)).tolist()
        record['nonoptimal_canonical_ids']=np.flatnonzero(error).tolist()
        record['empty_canonical_ids']=np.flatnonzero(~cp['members'].any(1)).tolist()
        results.append(record);cache[name]=(y,cp,s)
        return record

    units=[(e,u) for e in range(4) for u in range(4)]
    # Selection phase: only TRAINING rows are executed for the 16 single lesions.
    train_ids=np.flatnonzero(fold==0);training=[]
    for component in units:
        q=PatchPolicy(c,doses=[(*component,0)]);y=q(bt[train_ids]).numpy()
        pred=behavior(y,boards[train_ids],np.arange(len(train_ids)),ident[train_ids],canopt[train_ids]);error=~pred['correct']
        rates={t:float(error[ys[t][train_ids]].mean()) if ys[t][train_ids].any() else 0.0 for t in TASKS}
        training.append(dict(component=list(component),rates=rates,score=rates['must_block']-rates['has_fork']))
    ranked=sorted((v for v in training if v['component']!=[1,0]),key=lambda v:(-v['score'],v['component']))
    contrast=tuple(ranked[0]['component']);control=(contrast[0],(contrast[1]+1)%4)
    # Select one upstream lane via TRAINING activation differences only.
    upstream=[]
    for u in range(8):
        q=PatchPolicy(c,interventions=[dict(stage='norm2_output',unit=u,mode='half')]);q(bt[train_ids])
        rt=q.stages['routes'].numpy();mask=active[train_ids,1]&(rt==1).any(1)
        delta=np.abs(q.stages['expert_hidden'].numpy()[:,1,0]-bank[train_ids,1,0])
        upstream.append(dict(unit=u,n=int(mask.sum()),mean_abs_E1h0_change=float(delta[mask].mean()) if mask.any() else 0.0))
    up=sorted(upstream,key=lambda v:(-v['mean_abs_E1h0_change'],v['unit']))[0]['unit']
    selection=dict(contrast=list(contrast),control=list(control),single_training=training,upstream_training=upstream,upstream_unit=up,train_ids=train_ids.tolist())
    dump(out/'training-selection.json',selection)
    print('Baseline passed; fixed training selection',contrast,'upstream',up,flush=True)
    # Only now confirm selected hypotheses / all predeclared units on held-out folds.
    for component in units:
        for n in range(5):
            e,u=component;name=f'dose-{cname(component)}-{n}of4'
            r=evaluate(name,PatchPolicy(c,doses=[(e,u,n)]),active[:,e],dict(kind='dose',component=list(component),remaining_quarters=n))
            assert r['route_changes']==r['gate_changes']==0
    groups=[((1,0),(1,1)),((1,0),contrast),((1,0),control)]
    interactions=[]
    for gi,group in enumerate(groups):
        for n in range(4):
            name=f'group{gi}-{n}of4';cover=np.logical_and.reduce([active[:,e] for e,u in group])
            evaluate(name,PatchPolicy(c,doses=[(e,u,n) for e,u in group]),cover,dict(kind='group',components=[list(v) for v in group],remaining_quarters=n))
        a,b=[f'dose-{cname(v)}-0of4' for v in group];ab=f'group{gi}-0of4'
        ea=~cache[a][1]['correct'];eb=~cache[b][1]['correct'];eab=~cache[ab][1]['correct']
        residual=cache[ab][0]-cache[a][0]-cache[b][0]+logits
        interactions.append(dict(id=gi,components=[list(v) for v in group],union_single_failure_ids=np.flatnonzero(ea|eb).tolist(),pair_failure_ids=np.flatnonzero(eab).tolist(),new_beyond_union_ids=np.flatnonzero(eab&~(ea|eb)).tolist(),rescued_union_ids=np.flatnonzero(~eab&(ea|eb)).tolist(),logit_nonadditivity_abs_max=int(np.abs(residual).max()),logit_nonadditivity_nonzero_cells=int((residual!=0).sum()),per_canonical_logit_residual=residual.tolist()))
    dump(out/'pair-interactions.json',interactions)
    # All identity controls, including each selected and matched component.
    components=list(dict.fromkeys([(1,0),(1,1),contrast,control]))
    identity=[]
    for e,u in components:
        vals=[int(bank[i,e,u]) if active[i,e] else None for i in range(627)]
        identity.append(dict(expert=e,unit=u,values=vals))
    iq=PatchPolicy(c,patches=identity);assert np.array_equal(iq(bt).numpy(),logits)
    for k in stages:assert np.array_equal(iq.stages[k].numpy(),stages[k]),k
    dump(out/'identity-controls.json',dict(all627_all_stages_equal=True,components=[list(v) for v in components]))
    # Natural scalar patches. Selection uses labels and board geometry only, no outcomes.
    donor_rows=[]
    for component in components:
        e,u=component
        for task in TASKS:
            for cross in (False,True):
                donor_ids=np.full(627,-1,dtype=int)
                for i in np.flatnonzero((fold!=0)&active[:,e]):
                    pool=[j for j in train_ids if active[j,e] and geometry[i]==geometry[j] and (bool(ys[task][j])!=bool(ys[task][i]))==cross and np.abs(gates[j]-gates[i]).max()<=4096]
                    if not pool:continue
                    j=min(pool,key=lambda j:(int((boards[i]!=boards[j]).sum()),int(np.abs(gates[i]-gates[j]).max()),int(j)))
                    donor_ids[i]=j
                    donor_rows.append(dict(id=f'{cname(component)}-{task}-'+('cross' if cross else 'same')+f'-R{i}-D{j}',component=list(component),task=task,cross_class=cross,receiver=int(i),donor=int(j),hamming=int((boards[i]!=boards[j]).sum()),gate_delta=int(np.abs(gates[i]-gates[j]).max()),receiver_class=bool(ys[task][i]),donor_class=bool(ys[task][j]),receiver_activation=int(bank[i,e,u]),donor_activation=int(bank[j,e,u]),receiver_fold=int(fold[i]),canonical_alignment='same expert ID and hidden unit; independent canonical input frames'))
                vals=donor_values(bank,routes,donor_ids,e,u);name=f'patch-{cname(component)}-{task}-'+('cross' if cross else 'same')
                r=evaluate(name,PatchPolicy(c,patches=[dict(expert=e,unit=u,values=vals)]),donor_ids>=0,dict(kind='natural_patch',component=list(component),task=task,cross_class=cross,unique_donors=len(set(map(int,donor_ids[donor_ids>=0])))))
                assert r['route_changes']==r['gate_changes']==0
    compact(out/'donor-pairs.json',donor_rows)
    print('Dose and donor experiments done',len(results),flush=True)
    # Path restoration under one independently selected upstream perturbation.
    intervention=[dict(stage='norm2_output',unit=up,mode='half')]
    upstream_id=f'upstream-norm2-{up}-half'
    evaluate(upstream_id,PatchPolicy(c,interventions=intervention),meta=dict(kind='upstream',unit=up))
    uroutes=cache[upstream_id][2]['routes'];up_pred=cache[upstream_id][1]
    mediation=[]
    for label,comps in [('E1h0',[(1,0)]),('contrast',[contrast]),('both',[(1,0),contrast])]:
        patches=[];coverage=np.ones(627,dtype=bool)
        for e,u in comps:
            mask=active[:,e]&(uroutes==e).any(1);coverage&=mask
            patches.append(dict(expert=e,unit=u,values=[int(bank[i,e,u]) if mask[i] else None for i in range(627)]))
        name='restore-'+label
        evaluate(name,PatchPolicy(c,patches=patches,interventions=intervention),coverage,dict(kind='path_restore',components=[list(v) for v in comps],upstream_unit=up))
        pred=cache[name][1];badup=~up_pred['correct'];bad=~pred['correct']
        mediation.append(dict(id=name,coverage_ids=np.flatnonzero(coverage).tolist(),covered_upstream_failures=int((badup&coverage).sum()),rescued_ids=np.flatnonzero(badup&~bad&coverage).tolist(),introduced_ids=np.flatnonzero(~badup&bad&coverage).tolist(),all_set_restored_ids=np.flatnonzero((pred['members']==canbase['members']).all(1)&(up_pred['members']!=canbase['members']).any(1)&coverage).tolist(),upstream_routes_retained=bool(np.array_equal(cache[name][2]['routes'],uroutes)),upstream_gates_retained=bool(np.array_equal(cache[name][2]['gates'],cache[upstream_id][2]['gates']))))
    dump(out/'path-restoration.json',mediation)
    compact(out/'results.json',results);compact(out/'experiment-vectors.json',experiments)
    # Counterexamples: successful target necessity and target unaffected; non-target failures.
    examples=[]
    for component in [(1,0),contrast]:
        name=f'dose-{cname(component)}-0of4';error=~cache[name][1]['correct'];cover=active[:,component[0]]
        for task in TASKS:
            for condition,mask in [('target_failure',cover&ys[task]&error),('target_unaffected',cover&ys[task]&~error),('nontarget_failure',cover&~ys[task]&error)]:
                ids=np.flatnonzero(mask)
                if len(ids):
                    i=int(ids[0]);examples.append(dict(id=f'EX-{cname(component)}-{task}-{condition}',condition=condition,component=list(component),task=task,canonical_id=i,board=boards[i].tolist(),activation=int(bank[i,component[0],component[1]]),baseline_set=np.flatnonzero(canbase['members'][i]).tolist(),lesion_set=np.flatnonzero(cache[name][1]['members'][i]).tolist(),baseline_move=int(canbase['moves'][i]),lesion_move=int(cache[name][1]['moves'][i]),baseline_logits=logits[i].tolist(),lesion_logits=cache[name][0][i].tolist(),fold=int(fold[i])))
    compact(out/'counterexamples.json',examples)
    for name,h in snapshot['source_evidence_sha256'].items():assert sha(ROOT/name)==h
    assert np.array_equal(DiagnosticPolicy(c)(bt).numpy(),logits)
    summary=dict(raw_boards=4520,canonical_boards=627,fold_counts={n:int((fold==i).sum()) for i,n in enumerate(['train','validation','test'])},class_counts={t:{n:int((ys[t]&(fold==i)).sum()) for i,n in enumerate(['train','validation','test'])} for t in TASKS},raw_class_counts={t:int(ys[t][ci].sum()) for t in TASKS},experiments=len(results),donor_pairs=len(donor_rows),unique_donors=len({v['donor'] for v in donor_rows}),unique_receivers=len({v['receiver'] for v in donor_rows}),contrast=list(contrast),upstream_unit=up,source_evidence_unchanged=True,model_immutable=True)
    dump(out/'summary.json',summary)
    provenance=dict(snapshot=snapshot,source_sha256={p:sha(ROOT/p) for p in ['experiment-study003.json','falken9/strategy_patching.py','scripts/model_strategy_study003.py','falken9/strategy_diagnostics.py','scripts/model_strategy_study.py','tests/test_strategy_study003.py']},interpreter='/home/ai/falken-9/.venv/bin/python',dependencies=dict(torch=torch.__version__,numpy=np.__version__),import_root=str(ROOT),command=f'OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONPATH={ROOT} /home/ai/falken-9/.venv/bin/python scripts/model_strategy_study003.py --output <FRESH_OUTPUT>',scope='Host CPU exact integer interventions; no training, no native target rerun, no main checkout modifications')
    dump(out/'provenance.json',provenance)
    dump(out/'hashes.json',{p.name:sha(p) for p in sorted(out.iterdir()) if p.is_file()})
    print(json.dumps(summary,indent=2),flush=True)
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True)
    run(parser.parse_args().output)
