#!/usr/bin/env python3
"""Finite CPU-only study of frozen F9J2. Never modifies/shares release tensors."""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import math
import struct
import sys
import platform
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import torch
from falken9.strategy_diagnostics import (DiagnosticPolicy, tactical, enumerate_boards,
    offline_optimal_set, ridge_scores, binary_metrics, parameter_copy)
from falken9.flexible_integer_export import load
from falken9.symmetry import TRANSFORMS, canonicalize, transform_board, inverse
from falken9.canonical_integer_export import HEADER
from falken9.integer_export import NAMES
from scripts.verify_app import fixture_records
from scripts.build_runtime import FOUR_MODEL, ROOT

TASKS=('has_win','has_opponent_win','must_block','opponent_double_threat','has_fork',
       'has_opponent_fork','has_fork_prevention','center_own','center_opponent','center_empty')
STRATEGIES=('has_win','must_block','has_fork')
STAGES=('board_embedding','board_normalized','attention_probs','attended','readout_gelu','norm2_output','router_scores','expert_hidden','merged')
SEED=1729


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def dump(path,value):Path(path).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')

def dump_rows(path,rows):
    """Compact valid JSON, one complete evidence record per line."""
    Path(path).write_text('[\n'+',\n'.join(json.dumps(row,separators=(',',':'),allow_nan=False) for row in rows)+'\n]\n')

def csv_write(path,rows):
    if not rows:return
    with Path(path).open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def splits(labels):
    rng=np.random.default_rng(SEED);fold=np.zeros(len(labels),dtype=int)
    for ply in range(9):
        indices=np.array([i for i,v in enumerate(labels) if v['ply']==ply]);rng.shuffle(indices)
        n=len(indices);train=max(1,int(.6*n));validation=int(.2*n)
        fold[indices[train:train+validation]]=1;fold[indices[train+validation:]]=2
    return fold


def controls(labels):
    return np.array([[int(v['ply']==p) for p in range(9)]+[v[k] for k in ('own_corners','opponent_corners','own_edges','opponent_edges','center_own','center_opponent')] for v in labels],dtype=float)


def unit_features(stages):
    rows=[]
    for stage in STAGES:
        values=stages[stage];shape=values.shape[1:]
        for coord in np.ndindex(shape):
            active=np.ones(len(values),dtype=bool)
            if stage=='expert_hidden':active=(stages['routes']==coord[0]).any(1)
            rows.append(dict(stage=stage,coordinates=coord,values=values[(slice(None),)+coord],active=active))
    return rows


def residual_correlation(x,y,ply):
    x=np.asarray(x,dtype=float).copy();y=np.asarray(y,dtype=float).copy()
    for p in np.unique(ply):
        mask=ply==p;x[mask]-=x[mask].mean();y[mask]-=y[mask].mean()
    den=np.sqrt((x*x).sum()*(y*y).sum())
    return float(x@y/den) if den else 0.0


def stored_layout(candidate):
    raw=FOUR_MODEL.read_bytes();pos=struct.calcsize(HEADER)+81
    for name in NAMES:
        bits,rank,n=struct.unpack_from('<BBH',raw,pos);pos+=4+rank+n
    result={};global_index=0
    for name in NAMES:
        t=candidate['tensors'][name];size=t['codes'].numel()*t['bits']//8
        result[name]=dict(byte_offset=pos,global_parameter_start=global_index,shape=list(t['codes'].shape),bits=t['bits'],exponents=t['exponents']);pos+=size
        global_index+=t['codes'].numel()
    assert pos+2052==len(raw)
    return result


def parameter_for_unit(unit,task,labels,stages,candidate,train):
    stage=unit['stage'];coord=tuple(unit['coordinates']);ys=np.array([v[task] for v in labels])
    active=np.ones(len(labels),dtype=bool)
    if stage=='expert_hidden':
        e,u=coord;name='expert_w1';weights=candidate['tensors'][name]['codes'][e,:,u].numpy()
        inputs=stages['norm2_output'];active=(stages['routes']==e).any(1)
        make=lambda k:(e,int(k),u)
    elif stage=='readout_gelu':
        u=coord[0];name='readout.weight';weights=candidate['tensors'][name]['codes'][u].numpy()
        inputs=stages['attention_residual'].reshape(len(labels),-1);make=lambda k:(u,int(k))
    else:
        name='norm2.weight';u=coord[0]
        weights=candidate['tensors'][name]['codes'].numpy()
        distance=np.abs(np.abs(weights)-abs(weights[u])).astype(float);distance[u]=np.inf
        return name,(u,),(int(np.argmin(distance)),)
    positive=train&active&ys;negative=train&active&~ys
    contrast=inputs[positive].mean(0)-inputs[negative].mean(0) if positive.any() and negative.any() else inputs[train&active].mean(0)
    k=int(np.argmax(np.abs(weights*contrast)))
    # Same output row/scale and closest absolute stored magnitude, not a random
    # different-sized weight. This control may itself matter; measure it too.
    distances=np.abs(np.abs(weights)-abs(weights[k])).astype(float);distances[k]=np.inf
    control=int(np.argmin(distances))
    return name,make(k),make(control)


def behavior(logits,raw_boards,canonical_indices,transforms,optimal):
    mapped=logits[canonical_indices[:,None],transforms]
    members=(mapped>=0)&(raw_boards==0)
    order=np.array([4,1,3,5,7,2,6,8,0]);valid=members.any(1)
    moves=np.where(valid,order[members[:,order].argmax(1)],-1)
    correct=valid&optimal[np.arange(len(moves)),moves.clip(0)]
    # Signed margin to the correct complete-set classification boundary0.
    support=np.where(optimal,mapped,np.inf).min(1)
    reject=np.where((~optimal)&(raw_boards==0),-mapped,np.inf).min(1)
    margin=np.minimum(support,reject)
    return dict(members=members,moves=moves,correct=correct,margin=margin,mapped=mapped)


def matched_control_error(error,task,raw_labels):
    groups={}
    for i,v in enumerate(raw_labels):
        key=tuple(v[k] for k in ('ply','own_corners','opponent_corners','center_own','center_opponent'))
        groups.setdefault(key,[[],[]])[int(bool(v[task]))].append(i)
    target_count=covered=0;total=0.0;target_errors=0
    for negative,positive in groups.values():
        target_count+=len(positive)
        if positive and negative:
            covered+=len(positive);total+=len(positive)*float(error[negative].mean())
            target_errors+=int(error[positive].sum())
    return (total/covered if covered else None),(target_errors/covered if covered else None),covered,target_count


def run(output):
    torch.set_num_threads(1);out=Path(output);out.mkdir(parents=True,exist_ok=True)
    release_root=ROOT/'distribution/huggingface/upload'
    frozen={str(p.relative_to(ROOT)):sha(p) for p in release_root.rglob('*') if p.is_file()}
    frozen[str(FOUR_MODEL.relative_to(ROOT))]=sha(FOUR_MODEL)
    records,fixture_hashes=fixture_records();rows=sorted(records.values(),key=lambda r:r['canonical_index'])
    boards=np.array([r['board'] for r in rows],dtype=np.int64);candidate=load(FOUR_MODEL)
    policy=DiagnosticPolicy(candidate);logits=policy(torch.from_numpy(boards)).numpy()
    assert logits.tolist()==[r['stages']['logits'] for r in rows]
    stages={k:v.numpy().copy() for k,v in policy.stages.items()}
    # Every saved intermediate (not just logits), accounting for expert-slot vs
    # expert-ID bank layout in this diagnostic trace.
    stage_checks=0
    for i,row in enumerate(rows):
        for name,gold in row['stages'].items():
            got=stages[name][i]
            if name in ('expert_hidden_pre','expert_hidden','expert_outputs'):got=got[stages['routes'][i]]
            assert got.tolist()==gold,(i,name)
            stage_checks+=1
    labels=[tactical(tuple(b)) for b in boards];fold=splits(labels);train=fold==0;validation=fold==1;test=fold==2
    ctrl=controls(labels);features=unit_features(stages)
    raw_histories=enumerate_boards();raw_list=sorted(raw_histories);raw=np.array(raw_list,dtype=np.int64)
    canonical_lookup={tuple(b):i for i,b in enumerate(boards)}
    pairs=[canonicalize(b) for b in raw_list]
    ci=np.array([canonical_lookup[b] for b,t in pairs]);transforms=np.array([t for b,t in pairs])
    assert len(raw)==4520 and len(boards)==627 and set(ci)==set(range(627))
    optimal=np.zeros((len(raw),9),dtype=bool)
    for i,b in enumerate(raw_list):optimal[i,list(offline_optimal_set(b))]=True
    baseline=behavior(logits,raw,ci,transforms,optimal)
    assert baseline['correct'].all() and np.array_equal(baseline['members'],optimal)
    raw_labels=[tactical(b) for b in raw_list]
    # Symmetry proof includes complete optimal sets; chosen original-coordinate
    # tie-breaking is deliberately NOT required to be geometrically equivariant.
    roundtrips=tie_counterexamples=0;tie_example=None
    raw_lookup={b:i for i,b in enumerate(raw_list)}
    for i,b in enumerate(raw_list):
        for t in TRANSFORMS:
            moved=transform_board(b,t);j=raw_lookup[moved]
            assert transform_board(moved,inverse(t))==b
            assert set(np.flatnonzero(optimal[j]))=={t[k] for k in np.flatnonzero(optimal[i])}
            roundtrips+=1
            if baseline['moves'][j]!=t[baseline['moves'][i]]:
                tie_counterexamples+=1
                if tie_example is None:tie_example=dict(board=list(b),transformed=list(moved),permutation=list(t),move=int(baseline['moves'][i]),mapped_move=int(t[baseline['moves'][i]]),actual_move=int(baseline['moves'][j]))
    dump(out/'symmetry.json',dict(board_transform_set_roundtrips=roundtrips,learned_transform_weights=False,tie_choice_nonequivariant_examples=tie_counterexamples,first_tie_counterexample=tie_example))
    probe_rows=[];rankings=[];expert_rows=[];selections=[]
    families={'controls':ctrl,'raw_occupancy':np.eye(3)[boards].reshape(len(boards),-1)}
    families.update({name:stages[name].reshape(len(boards),-1) for name in STAGES})
    route_gate=np.zeros((len(boards),4))
    for slot in range(2):route_gate[np.arange(len(boards)),stages['routes'][:,slot]]=stages['gates'][:,slot]/32768
    families['route_gate']=np.column_stack((route_gate,route_gate>0))
    families['expert_hidden']=np.column_stack((families['expert_hidden'],np.stack([(stages['routes']==e).any(1) for e in range(4)],axis=1)))
    for task_index,task in enumerate(TASKS):
        y=np.array([v[task] for v in labels],dtype=int)
        shuffled=y.copy();rng=np.random.default_rng(SEED+task_index)
        for p in range(9):
            ix=np.flatnonzero(np.array([v['ply'] for v in labels])==p);shuffled[ix]=rng.permutation(y[ix])
        for family,x in families.items():
            design=x if family=='controls' else np.column_stack((ctrl,x))
            for name,target in [('actual',y),('within_ply_shuffled',shuffled)]:
                for split,mask in [('validation',validation),('test',test)]:
                    metrics=binary_metrics(target[mask],ridge_scores(design[train],target[train],design[mask]))
                    probe_rows.append(dict(task=task,family=family,labels=name,split=split,features=design.shape[1],**metrics))
        task_ranks=[]
        for unit in features:
            mask=train&unit['active'];values=unit['values'];target=y[mask]
            if len(target)<20 or target.min()==target.max():continue
            ply=np.array([v['ply'] for v in labels])[mask]
            correlation=residual_correlation(values[mask],target,ply)
            row=dict(task=task,stage=unit['stage'],coordinates=','.join(map(str,unit['coordinates'])),n=int(mask.sum()),positives=int(target.sum()),residual_ply_correlation=correlation,positive_mean=float(values[mask&y.astype(bool)].mean()),negative_mean=float(values[mask&~y.astype(bool)].mean()))
            rankings.append(row);task_ranks.append((abs(correlation),unit,row))
        if task in STRATEGIES:
            usable=[v for v in task_ranks if v[1]['stage'] in ('readout_gelu','norm2_output','expert_hidden')]
            _,unit,rank=max(usable,key=lambda v:v[0]);coord=unit['coordinates']
            choice:dict=dict(callout='ABC'[len(selections)],task=task,stage=unit['stage'],coordinates=list(coord),training_association=rank,
                        baseline_value=int(np.median(unit['values'][train&unit['active']])))
            # A single-unit held-out probe is reported, not only its training rank.
            x=np.column_stack((ctrl,unit['values'],unit['active'].astype(int)))
            choice['heldout_unit_probe']=binary_metrics(y[test],ridge_scores(x[train],y[train],x[test]))
            route_design=np.column_stack((ctrl,unit['active'].astype(int)))
            choice['heldout_route_control_probe']=binary_metrics(y[test],ridge_scores(route_design[train],y[train],route_design[test]))
            active_train=train&unit['active'];active_test=test&unit['active']
            if active_test.any():
                choice['heldout_active_only_probe']=binary_metrics(y[active_test],ridge_scores(x[active_train],y[active_train],x[active_test]))
            selections.append(choice)
        for e in range(4):
            active=(stages['routes']==e).any(1);gate=np.zeros(len(boards))
            for slot in range(2):gate+=np.where(stages['routes'][:,slot]==e,stages['gates'][:,slot]/32768,0)
            for positive in [False,True]:
                mask=train&(y==int(positive));expert_rows.append(dict(task=task,expert=e,label=int(positive),n=int(mask.sum()),routed=int(active[mask].sum()),routing_rate=float(active[mask].mean()) if mask.any() else None,mean_gate=float(gate[mask].mean()) if mask.any() else None))
    csv_write(out/'probes.csv',probe_rows);csv_write(out/'units.csv',sorted(rankings,key=lambda r:(r['task'],-abs(r['residual_ply_correlation']))));csv_write(out/'experts.csv',expert_rows)
    layout=stored_layout(candidate);experiments=[]
    position_ranks=[r for r in rankings if r['task']=='center_own' and r['stage']=='board_embedding' and r['coordinates'].startswith('4,')]
    position_rank=max(position_ranks,key=lambda r:abs(r['residual_ply_correlation']))
    position_coord=tuple(map(int,position_rank['coordinates'].split(',')))
    pv=int(candidate['tensors']['position']['codes'][position_coord]);pl=layout['position']
    pf=int(np.ravel_multi_index(position_coord,pl['shape']))
    spatial=dict(callout='P1',tensor='position',coordinates=list(position_coord),flat_index=pf,global_parameter_index=pl['global_parameter_start']+pf,packet_byte_offset=pl['byte_offset']+pf*2,stored_value=pv,bits=16,scale='Q11 constant embedding offset; NOT a rotation parameter',training_association=position_rank,
        attention_association=max((r for r in rankings if r['task']=='has_win' and r['stage']=='attention_probs'),key=lambda r:abs(r['residual_ply_correlation'])),position_values=candidate['tensors']['position']['codes'].tolist())
    for mode in ('zero','half'):
        replacement=0 if mode=='zero' else (1 if pv>=0 else -1)*((abs(pv)+1)//2)
        experiments.append(dict(id='P1-'+mode,kind='stored_position_parameter',parameter=dict(name='position',coordinates=list(position_coord),value=replacement)))
    peers=candidate['tensors']['position']['codes'][4].numpy();distance=np.abs(np.abs(peers)-abs(pv)).astype(float);distance[position_coord[1]]=np.inf
    control=int(np.argmin(distance));spatial['control_coordinates']=[4,control]
    experiments.append(dict(id='P1-control-zero',kind='matched_position_parameter_control',parameter=dict(name='position',coordinates=[4,control],value=0)))
    for stage in ('readout_gelu','norm2_output'):
        for u in range(8):experiments.append(dict(id=f'{stage}-{u}-zero',kind='activation',items=[dict(stage=stage,unit=u,mode='zero')]))
    for e in range(4):
        for u in range(4):experiments.append(dict(id=f'expert-{e}-hidden-{u}-zero',kind='activation',items=[dict(stage='expert_hidden',expert=e,unit=u,mode='zero')]))
        experiments.append(dict(id=f'expert-{e}-output-zero',kind='expert_output',items=[dict(stage='expert_outputs',expert=e,mode='zero')]))
    for selection in selections:
        coord=selection['coordinates'];item=dict(stage=selection['stage'],unit=coord[-1])
        if selection['stage']=='expert_hidden':item['expert']=coord[0]
        selection['zero_intervention']=next(v['id'] for v in experiments if v.get('items')==[{**item,'mode':'zero'}])
        for mode in ('half','baseline'):
            intervention={**item,'mode':mode}
            if mode=='baseline':intervention['value']=selection['baseline_value']
            experiments.append(dict(id=selection['callout']+'-'+mode,kind='activation_dose',items=[intervention]))
        name,coordinates,control_coordinates=parameter_for_unit(selection,selection['task'],labels,stages,candidate,train)
        value=int(candidate['tensors'][name]['codes'][coordinates]);tensor_layout=layout[name]
        flat=int(np.ravel_multi_index(coordinates,tensor_layout['shape']))
        selection['parameter']=dict(callout=selection['callout']+'1',tensor=name,coordinates=list(coordinates),flat_index=flat,global_parameter_index=tensor_layout['global_parameter_start']+flat,packet_byte_offset=tensor_layout['byte_offset']+flat*tensor_layout['bits']//8,stored_value=value,bits=tensor_layout['bits'],exponents=tensor_layout['exponents'],control_coordinates=list(control_coordinates))
        for mode in ('zero','half'):
            replacement=0 if mode=='zero' else (1 if value>=0 else -1)*((abs(value)+1)//2)
            experiments.append(dict(id=selection['callout']+'1-'+mode,kind='stored_parameter',parameter=dict(name=name,coordinates=list(coordinates),value=replacement)))
        experiments.append(dict(id=selection['callout']+'1-control-zero',kind='matched_parameter_control',parameter=dict(name=name,coordinates=list(control_coordinates),value=0)))
    unique=[]
    for selection in selections:
        coord=selection['coordinates'];item=dict(stage=selection['stage'],unit=coord[-1],mode='zero')
        if selection['stage']=='expert_hidden':item['expert']=coord[0]
        if item not in unique:unique.append(item)
    if len(unique)>=2:experiments.append(dict(id='top-pair-zero',kind='bounded_pair',items=unique[:2]))
    effect_rows=[];detail=[];counterexamples=[];intervention_logits={}
    for experiment in experiments:
        c=candidate
        if 'parameter' in experiment:
            p=experiment['parameter'];c=parameter_copy(candidate,p['name'],p['coordinates'],p['value'])
        model=DiagnosticPolicy(c,experiment.get('items',[]));changed=model(torch.from_numpy(boards)).numpy()
        action=behavior(changed,raw,ci,transforms,optimal);error=~action['correct'];moves_changed=action['moves']!=baseline['moves'];set_error=(action['members']!=optimal).any(1)
        rerouted=(model.stages['routes'].numpy()!=stages['routes']).any(1)[ci]
        intervention_logits[experiment['id']]=changed
        effects={}
        for task in ('all',)+STRATEGIES:
            mask=np.ones(len(raw),dtype=bool) if task=='all' else np.array([v[task] for v in raw_labels],dtype=bool)
            control,target_rate,covered,total=(None,None,0,0) if task=='all' else matched_control_error(error,task,raw_labels)
            row=dict(id=experiment['id'],kind=experiment['kind'],subset=task,n=int(mask.sum()),nonoptimal_or_empty=int(error[mask].sum()),empty_set=int((action['moves'][mask]<0).sum()),move_changes=int(moves_changed[mask].sum()),set_errors=int(set_error[mask].sum()),route_changes=int(rerouted[mask].sum()),mean_margin_delta=float((action['margin']-baseline['margin'])[mask].mean()),matched_nontarget_error_rate=control,matched_target_error_rate=target_rate,matched_target_covered=covered,matched_target_total=total)
            effect_rows.append(row);effects[task]=row
        examples=[]
        for task in STRATEGIES:
            indices=np.flatnonzero(error&np.array([v[task] for v in raw_labels]))
            for i in indices[:1]:examples.append(dict(task=task,board=raw[i].tolist(),history=raw_histories[tuple(raw[i])],canonical_index=int(ci[i]),before_move=int(baseline['moves'][i]),after_move=int(action['moves'][i]),before_set=np.flatnonzero(baseline['members'][i]).tolist(),after_set=np.flatnonzero(action['members'][i]).tolist(),before_logits=baseline['mapped'][i].tolist(),after_logits=action['mapped'][i].tolist(),before_routes=stages['routes'][ci[i]].tolist(),after_routes=model.stages['routes'][ci[i]].tolist()))
        neutral=np.flatnonzero(error&~np.array([v['has_win'] or v['must_block'] or v['has_fork'] for v in raw_labels]))
        if len(neutral):
            i=int(neutral[0]);examples.append(dict(task='non-target counterexample',board=raw[i].tolist(),history=raw_histories[tuple(raw[i])],before_move=int(baseline['moves'][i]),after_move=int(action['moves'][i])))
        counterexamples.append(dict(id=experiment['id'],examples=examples))
        detail.append({**experiment,'effects':effects,'canonical_logit_changed_boards':int((changed!=logits).any(1).sum()),'canonical_logits_sha256':hashlib.sha256(changed.astype('<i8').tobytes()).hexdigest(),'saturations':model.stats['saturations']})
    csv_write(out/'interventions.csv',effect_rows);dump_rows(out/'interventions.json',detail);dump_rows(out/'counterexamples.json',counterexamples)
    cases=[]
    canonical_behavior=behavior(logits,boards,np.arange(len(boards)),np.tile(np.arange(9),(len(boards),1)),np.stack([np.array([i in offline_optimal_set(tuple(b)) for i in range(9)]) for b in boards]))
    for choice in selections:
        task=choice['task'];coord=tuple(choice['coordinates']);values=stages[choice['stage']][(slice(None),)+coord]
        active=np.ones(len(boards),dtype=bool) if choice['stage']!='expert_hidden' else (stages['routes']==coord[0]).any(1)
        square_key={'has_win':'wins','must_block':'block_squares','has_fork':'forks'}[task]
        eligible=[i for i,v in enumerate(labels) if test[i] and active[i] and v[task] and int(canonical_behavior['moves'][i]) in v[square_key]]
        if not eligible:eligible=[i for i,v in enumerate(labels) if active[i] and v[task] and int(canonical_behavior['moves'][i]) in v[square_key]]
        positive=max(eligible,key=lambda i:abs(values[i]))
        neutral=[i for i,v in enumerate(labels) if active[i] and v['ply']==labels[positive]['ply'] and not (v['has_win'] or v['has_opponent_win'] or v['has_fork'] or v['has_opponent_fork'])]
        if not neutral:neutral=[i for i,v in enumerate(labels) if active[i] and v['ply']==labels[positive]['ply'] and not v[task]]
        # Closest occupancy controls; choose a strongly active non-target when
        # tied to expose a counterexample rather than flattering the callout.
        negative=min(neutral,key=lambda i:(sum(abs(float(a)-float(b)) for a,b in zip(ctrl[i],ctrl[positive])),-abs(values[i])))
        matching_distance=float(np.abs(ctrl[negative]-ctrl[positive]).sum())
        treatment=choice['zero_intervention'];newlogits=intervention_logits[treatment]
        for kind,i in [('tactical',positive),('matched-nontarget',negative)]:
            before=int(canonical_behavior['moves'][i]);members=[j for j in range(9) if boards[i,j]==0 and newlogits[i,j]>=0]
            after=next((j for j in [4,1,3,5,7,2,6,8,0] if j in members),-1)
            cases.append(dict(callout=choice['callout'],task=task,kind=kind,canonical_index=i,probe_split=['train','validation','test'][fold[i]],board=boards[i].tolist(),labels=labels[i],same_ply_match=True,occupancy_control_L1_distance=matching_distance,move=before,after_zero_move=after,after_zero_optimal=after in offline_optimal_set(tuple(boards[i])),unit_value=int(values[i]),routes=stages['routes'][i].tolist(),gates_q15=stages['gates'][i].tolist(),expert_hidden=stages['expert_hidden'][i].tolist(),readout_gelu=stages['readout_gelu'][i].tolist(),norm2_output=stages['norm2_output'][i].tolist(),logits=logits[i].tolist(),zero_logits=newlogits[i].tolist(),selected_logit_delta=int(newlogits[i,before]-logits[i,before]),attention_probs_q15=stages['attention_probs'][i].tolist()))
    dump(out/'callouts.json',selections);dump(out/'cases.json',cases)
    dump(out/'spatial.json',spatial)
    dump_rows(out/'canonical-labels.json',[dict(canonical_index=i,board=boards[i].tolist(),fold=int(fold[i]),**v) for i,v in enumerate(labels)])
    np.savez_compressed(out/'baseline-stages.npz',boards=boards,**stages)
    for name,digest in frozen.items():assert sha(ROOT/name)==digest,name
    dump(out/'frozen-release-hashes.json',frozen)
    source_paths=['falken9/strategy_diagnostics.py','scripts/model_strategy_study.py','falken9/flexible_integer.py','falken9/flexible_integer_export.py','falken9/canonical_integer.py','falken9/canonical_integer_export.py','falken9/integer_model.py','falken9/integer_export.py','falken9/policy.py','falken9/symmetry.py','src/app/wrapper.asm']
    summary=dict(status='passed',model_sha256=sha(FOUR_MODEL),model_bytes=FOUR_MODEL.stat().st_size,core_sha256='838aa62a854aa58bd603c7525b52dc67c4c4b01ea0f50f58982475959ec61961',seed=SEED,canonical_boards=len(boards),raw_boards=len(raw),fold_counts={name:int((fold==i).sum()) for i,name in enumerate(['train','validation','test'])},baseline_cached_logit_mismatches=0,baseline_stage_vectors_checked=stage_checks,baseline_optimal_set_errors=0,symmetry_roundtrips=roundtrips,interventions=len(experiments),probe_metric_rows=len(probe_rows),exploratory_unit_associations=len(rankings),multiplicity='Exploratory training ranks, no significance/p-value claims or multiplicity-corrected discoveries; fixed held-out probe families reported in full.',generalization='Probe-held-out canonical boards; NOT model-held-out states: deployed model was fitted/audited on this finite domain.',intervention_scope='Copies only;627 exact integer forward reruns per treatment, composed into4520 original-coordinate wrappers. Fixed rounding/clamp/router/tie contract. Minimax offline diagnostic only.',release_files_unchanged=len(frozen),source_sha256={p:sha(ROOT/p) for p in source_paths},fixture_sha256=fixture_hashes,versions=dict(python=platform.python_version(),numpy=np.__version__,torch=torch.__version__),label_prevalence={task:dict(canonical_positive=sum(bool(v[task]) for v in labels),canonical_n=len(labels),raw_positive=sum(bool(v[task]) for v in raw_labels),raw_n=len(raw_labels)) for task in TASKS})
    summary['unique_intervention_specifications']=len({json.dumps({k:v for k,v in d.items() if k in ('items','parameter')},sort_keys=True) for d in detail})
    summary['unique_intervention_logit_outcomes']=len({d['canonical_logits_sha256'] for d in detail})
    summary['inference_device']='cpu'
    summary['cuda_context_initialized']=torch.cuda.is_initialized()
    dump(out/'summary.json',summary)
    print(json.dumps({k:summary[k] for k in ['status','canonical_boards','raw_boards','fold_counts','interventions','exploratory_unit_associations','release_files_unchanged']},indent=2))
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();run(args.output)
