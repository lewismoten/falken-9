#!/usr/bin/env python3
"""Bounded host-only frozen-model studies; each run checks frozen manifest."""
import argparse,copy,hashlib,itertools,json,sys
from pathlib import Path
import numpy as np
import torch
from research678_core import mix_exact,all_experts,patch_outputs,mutate_code,sign_census
from study005_run import baseline,geom,stats
from falken9.strategy_diagnostics import DiagnosticPolicy,tactical
from falken9.canonical_integer import CanonicalIntegerPolicy
from falken9.symmetry import canonicalize
from scripts.model_strategy_study import behavior,splits,stored_layout
ROOT=Path(__file__).resolve().parent

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,v):
    def enc(o):
        if isinstance(o,np.ndarray):return o.tolist()
        if isinstance(o,np.generic):return o.item()
        if isinstance(o,torch.Tensor):return o.tolist()
        raise TypeError(type(o).__name__)
    Path(p).write_text(json.dumps(v,default=enc,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n')

def preserved():
    files=json.loads((ROOT/'preservation-before006-008.json').read_text())
    for n,h in files.items():assert sha(ROOT/n)==h,n
    return len(files)

class Data:
    def __init__(self):
        self.b,self.bt,self.c,self.y,self.st,self.raw,self.ci,self.tr,self.opt,self.rawopt,self.cp,self.rp,self.gate,_=baseline()
        self.labels=[tactical(tuple(v)) for v in self.b];self.fold=splits(self.labels)
        self.x=torch.from_numpy(self.st['readout_gelu']);self.z=torch.from_numpy(self.st['norm2_output']);self.route=torch.from_numpy(self.st['routes']);self.gates=torch.from_numpy(self.st['gates']);self.scores=torch.from_numpy(self.st['router_scores'])
        self.e,self.h=all_experts(self.c,self.z);self.q=CanonicalIntegerPolicy(copy.deepcopy(self.c))
        self.ident=np.tile(np.arange(9),(627,1));self.ids=np.arange(627)
        for i in range(627):
            for e in self.route[i]:assert np.array_equal(self.e[i,e].numpy(),self.st['expert_outputs'][i,e])
        assert np.array_equal(self.head(self.e,self.route,self.gates),self.y)
        assert np.array_equal(mix_exact(self.x,self.e,self.route,self.gates).numpy(),self.st['merged'])
    def head(self,e,route,gates,ids=None):
        x=self.x if ids is None else self.x[ids]
        return self.q.linear(mix_exact(x,e,route,gates),'output.weight','output.bias').numpy().copy()
    def pred(self,y):return behavior(y,self.b,self.ids,self.ident,self.opt)
    def summary(self,y):
        p=self.pred(y);rp=behavior(y,self.raw,self.ci,self.tr,self.rawopt)
        return dict(canonical=stats(p,self.cp,np.ones(627,dtype=bool)),raw=stats(rp,self.rp,np.ones(4520,dtype=bool)),folds=[dict(fold=f,**stats(p,self.cp,self.fold==f)) for f in range(3)],tasks={k:stats(p,self.cp,np.array([v[k] for v in self.labels])) for k in ('has_win','must_block','has_fork')},neutral=stats(p,self.cp,np.array([not(v['has_win'] or v['must_block'] or v['has_fork']) for v in self.labels])))
    def snapshot(self,out):
        put(out/'baseline.json',dict(gate=self.gate,boards=self.b,raw_boards=self.raw,raw_to_canonical_id=self.ci,raw_to_canonical_transform=self.tr,fold=self.fold,labels=self.labels,logits=self.y,routes=self.route,gates=self.gates,router_scores=self.scores,readout=self.x,norm2=self.z,expert_outputs_offline=self.e,expert_hidden_offline=self.h,normal_executed_experts=1254,offline_extra_experts=1254,warning='Unselected outputs computed OFFLINE with additional compute; not normal deployed execution.'))

def prepare(stage,out):
    m=json.loads((ROOT/f'experiment-study{stage}.json').read_text())
    for n,h in m['source_sha256'].items():assert sha(ROOT/n)==h,n
    assert m['baseline_sha256']==sha(ROOT/'baseline-study006-008.json')
    preserved();d=Data();out=Path(out);out.mkdir(parents=True,exist_ok=False);put(out/'manifest.json',m);d.snapshot(out)
    return d,out,m

def finish(stage,d,out,summary):
    put(out/'summary.json',summary)
    put(out/'provenance.json',dict(stage=stage,model_sha256=d.gate['model_sha256'],preserved_files=preserved(),imports=d.gate['imports'],no_training=True,no_target_execution=True,arithmetic='F9J2 native integer INT64 host accumulation, half-away rounding and native clamps; wrapper >=0 membership, legal masking, complete-set inverse, fixed raw tie order.',scope='All boards already trained/audited. Folds are probe/selection-heldout only, not novel-domain/model generalization.',manifest_sha256=sha(ROOT/f'experiment-study{stage}.json')))
    from research678_render import render,report
    render(stage,out);report(stage,out)
    print(stage,json.dumps(summary,separators=(',',':')),flush=True)

def run006(out):
    d,out,m=prepare('006',out);n=627;rows=[];vectors=[];preds={};pairs=list(itertools.combinations(range(4),2))
    def evaluate(name,pair,gate,metadata):
        y=d.head(d.e,pair,gate);s=dict(id=name,**metadata,**d.summary(y));rows.append(s);preds[name]=d.pred(y)
        vectors.append(dict(id=name,pairs=pair,gates=gate,logits=y));return y
    yy=evaluate('actual',d.route,d.gates,dict(contract='normal learned pair/gates'))
    assert np.array_equal(yy,d.y)
    yy=evaluate('reverse-pair-and-gates',d.route.flip(1),d.gates.flip(1),dict(contract='order identity control'));assert np.array_equal(yy,d.y)
    evaluate('reverse-pair-only',d.route.flip(1),d.gates,dict(contract='swaps expert gate assignment, not pure order'))
    evaluate('actual-uniform',d.route,torch.full((n,2),16384),dict(contract='gate-only control'))
    pair_results=[]
    for a,b in pairs:
        pair=torch.tensor([[a,b]]).repeat(n,1)
        flip=d.scores[:,a]<d.scores[:,b];pair[flip]=pair[flip].flip(1)
        for mode in ('renormalized','actual-slot','uniform'):
            g=d.q.softmax(d.scores.gather(1,pair)) if mode=='renormalized' else d.gates if mode=='actual-slot' else torch.full((n,2),16384)
            y=evaluate(f'pair-{a}{b}-{mode}',pair,g,dict(pair=[a,b],gate_mode=mode,contract='same-board offline additional experts; recipient outputs fixed'))
            if mode=='renormalized':pair_results.append((a,b,y))
    ranking=[]
    for a,b,y in pair_results:
        p=d.pred(y);mask=d.fold==0;ranking.append(dict(pair=[a,b],training_errors=int((~p['correct']&mask).sum()),training_set_changes=int(((p['members']!=d.opt).any(1)&mask).sum())))
    selected=min(ranking,key=lambda v:(v['training_errors'],v['training_set_changes'],v['pair']))
    # Natural router donors, same fold/ply/side and own/opponent corner-edge-center counts.
    donors=[];coverage=[]
    for kind in ('alternative-pair','same-pair-gate'):
        ids=np.arange(n);matched=np.zeros(n,dtype=bool)
        for i in range(n):
            pool=[j for j in range(n) if j!=i and d.fold[j]==d.fold[i] and d.labels[j]['ply']==d.labels[i]['ply'] and geom(d.b[j])==geom(d.b[i]) and ((set(d.route[j].tolist())!=set(d.route[i].tolist())) if kind=='alternative-pair' else (torch.equal(d.route[j],d.route[i]) and not torch.equal(d.gates[j],d.gates[i])))]
            if pool:ids[i]=min(pool);matched[i]=True
        pair=d.route[ids];donorg=d.gates[ids]
        for mode in ('donor','renormalized','actual-slot'):
            g=donorg if mode=='donor' else d.q.softmax(d.scores.gather(1,pair)) if mode=='renormalized' else d.gates
            y=evaluate(f'natural-{kind}-{mode}',pair,g,dict(contract='natural donor route/gates only; receiver expert outputs held fixed',matched=int(matched.sum()),unmatched_noop=int((~matched).sum())))
            p=d.pred(y)
            coverage.append(dict(kind=kind,mode=mode,matched=stats(p,d.cp,matched),folds=[dict(fold=f,matched=int((matched&(d.fold==f)).sum()),task_support={task:int(sum(bool(matched[i] and d.fold[i]==f and d.labels[i][task]) for i in range(n))) for task in ('has_win','must_block','has_fork')}) for f in range(3)]))
        donors.append(dict(kind=kind,donor_ids=ids,matched=matched))
    # Best/worst are hindsight diagnostics, never a trained alternative policy.
    losses=[]
    for a,b,y in pair_results:
        p=d.pred(y);losses.append((~p['correct']).astype(int)*100+(p['members']!=d.opt).sum(1))
    loss=np.array(losses);actual_set=np.sort(d.route.numpy(),1)
    matched=[]
    selected_name='pair-'+''.join(map(str,selected['pair']))+'-renormalized';p=preds[selected_name]
    for task in ('has_win','must_block','has_fork'):
        for f in range(3):
            positives=[i for i,v in enumerate(d.labels) if d.fold[i]==f and v[task]];matches=[]
            for i in positives:
                pool=[j for j,v in enumerate(d.labels) if d.fold[j]==f and v['ply']==d.labels[i]['ply'] and geom(d.b[j])==geom(d.b[i]) and not(v['has_win'] or v['must_block'] or v['has_fork'])]
                if pool:matches.append((i,min(pool)))
            matched.append(dict(task=task,fold=f,positive_candidates=len(positives),matched_pairs=len(matches),unique_neutral=len(set(j for i,j in matches)),positive_errors=sum(not bool(p['correct'][i]) for i,j in matches),neutral_errors=sum(not bool(p['correct'][j]) for i,j in matches),pairs=matches))
    examples=[]
    for typ,ids in [('actual-needed',np.flatnonzero(loss.max(0)>0)),('robust-all-pairs',np.flatnonzero(loss.max(0)==0))]:
        if len(ids):
            i=int(ids[0]);examples.append(dict(callout=typ,id=i,board=d.b[i],fold=int(d.fold[i]),actual_pair=d.route[i],actual_gates=d.gates[i],actual_logits=d.y[i],actual_set=np.flatnonzero(d.opt[i]),pairs=[dict(pair=[a,b],logits=y[i],set=np.flatnonzero(d.pred(y)['members'][i]),move=int(d.pred(y)['moves'][i])) for a,b,y in pair_results]))
    put(out/'interventions.json',rows);put(out/'vectors.json',vectors);put(out/'donors.json',dict(donors=donors,coverage=coverage));put(out/'selection.json',dict(rankings=ranking,selected=selected,matched_tactical_neutral=matched));put(out/'examples.json',examples)
    summary=dict(interventions=len(rows),pair_memberships=6,normal_expert_evaluations=1254,offline_expert_evaluations=2508,order_and_gate_reversal_exact=True,actual_errors=0,actual_full_set_exact=627,best_pair_zero_loss_boards=int((loss.min(0)==0).sum()),all_pairs_zero_loss_boards=int((loss.max(0)==0).sum()),worst_pair_has_damage_boards=int((loss.max(0)>0).sum()),training_selected_fixed_pair=selected,fixed_pair_confirmation=[r for r in rows if r['id']==selected_name][0],actual_uniform=[r for r in rows if r['id']=='actual-uniform'][0],gate_swap=[r for r in rows if r['id']=='reverse-pair-only'][0],no_strategy_detector_established=True,normal_unselected_experts_unobserved=True)
    finish('006',d,out,summary)

def run007(out):
    d,out,m=prepare('007',out);train=d.fold==0;need=np.array([v['must_block'] for v in d.labels]);neutral=np.array([not(v['has_win'] or v['must_block'] or v['has_fork']) for v in d.labels]);rank=[];lesions={}
    for e in range(4):
        ee=d.e.clone();ee[:,e]=0;y=d.head(ee,d.route,d.gates);p=d.pred(y);active=(d.route.numpy()==e).any(1)
        def rate(mask):
            use=train&active&mask;return float((~p['correct'])[use].mean()) if use.any() else None
        a,b=rate(need),rate(neutral);rank.append(dict(expert=e,train_active=int((train&active).sum()),train_must_block=int((train&active&need).sum()),train_neutral=int((train&active&neutral).sum()),task_error_rate=a,neutral_error_rate=b,contrast=a-b if a is not None and b is not None else None));lesions[e]=y
    candidate=min([r for r in rank if r['contrast'] is not None],key=lambda r:(-r['contrast'],r['expert']))['expert'];control=(candidate+1)%4
    put(out/'selection.json',dict(ranking=rank,selected_expert=candidate,control_expert=control,selection='training-only maximal must-block minus neutral active error-rate contrast; control next cyclic expert ID; post-route full output vector scope'))
    # Reuse exact frozen natural relocation inventory; no wider search if support empty.
    source=ROOT/'artifacts/interpretability/study-005-final/matched-relocations005.json';prior=json.loads(source.read_text());pairs=[];coverage=[]
    for e,role in ((candidate,'candidate'),(control,'control')):
        for contract in ('route-fixed','route-changing'):
            for task in ('win','threat','fork'):
                for f in range(3):
                    rr=[r for r in prior if r['task']==task and r['fold']==f];accepted=[]
                    for r in rr:
                        i,j=r['receiver'],r['donor'];same=torch.equal(d.route[i],d.route[j]);both=bool((d.route[i]==e).any() and (d.route[j]==e).any());gate=int(torch.abs(d.gates[i]-d.gates[j]).max())
                        if same!=(contract=='route-fixed') or not both or gate>4096:continue
                        accepted.append(r)
                    # Frozen cap per role/contract/task/fold; all discarded denominators retained.
                    accepted=accepted[:24];coverage.append(dict(role=role,expert=e,contract=contract,task=task,fold=f,available_prior_pairs=len(rr),accepted=len(accepted),cap=24,matching='same raw candidate, one legal same-mark relocation, same ply/side/geometry/fold; candidate active both; gate Linf<=4096; route contract separate'))
                    for r in accepted:pairs.append(dict(role=role,expert=e,contract=contract,match=r))
    rows=[];examples=[];counts={};identity=0;restoration=0
    for pairid,pair in enumerate(pairs):
        e=pair['expert'];r=pair['match'];i,j=r['receiver'],r['donor']
        for direction,(a,b) in enumerate(((i,j),(j,i))):
            ar=d.route[a:a+1];ag=d.gates[a:a+1];base=d.e[a:a+1];donor=d.e[b:b+1];others=[int(v) for v in ar[0] if int(v)!=e];active=[int(v) for v in ar[0]]
            # Recipient routing/gates and residual fixed; absent donor expert is unavailable, NOT a zero observation.
            shared=[v for v in active if bool((d.route[b]==v).any())]
            allnatural=patch_outputs(base,donor,shared)
            variants={'identity':patch_outputs(base,base,[e]),'candidate-donor':patch_outputs(base,donor,[e]),'noncandidate-natural':patch_outputs(base,donor,[v for v in others if v in shared]),'all-shared-natural':allnatural,'restore-candidate':patch_outputs(allnatural,base,[e]),'zero-noncandidate':base.clone(),'zero-all-selected':base.clone(),'restore-from-zero':base.clone()}
            variants['zero-noncandidate'][:,others]=0;variants['zero-all-selected'][:,active]=0;variants['restore-from-zero'][:,active]=0;variants['restore-from-zero'][:,e]=base[:,e]
            yy={name:d.head(ee,ar,ag,[a])[0] for name,ee in variants.items()}
            assert np.array_equal(yy['identity'],d.y[a]);identity+=1
            assert np.array_equal(yy['restore-candidate'],yy['noncandidate-natural']);assert np.array_equal(yy['restore-from-zero'],yy['zero-noncandidate']);restoration+=2
            outcomes={}
            for name,y in yy.items():
                members=(y>=0)&(d.b[a]==0);moves=[v for v in (4,1,3,5,7,2,6,8,0) if members[v]];move=moves[0] if moves else -1
                rawmask=d.ci==a;full=d.y.copy();full[a]=y
                pp=behavior(full,d.raw[rawmask],d.ci[rawmask],d.tr[rawmask],d.rawopt[rawmask]);bb=behavior(d.y,d.raw[rawmask],d.ci[rawmask],d.tr[rawmask],d.rawopt[rawmask])
                outcomes[name]=dict(logits=y,set=np.flatnonzero(members),move=move,correct=bool(move>=0 and d.opt[a,move]),empty=not bool(members.any()),nonoptimal_nonempty=bool(members.any() and not d.opt[a,move]),set_change=not np.array_equal(members,d.opt[a]),optimal_tie_change=bool(move>=0 and d.opt[a,move] and move!=d.cp['moves'][a]),raw_orbit=stats(pp,bb,np.ones(int(rawmask.sum()),dtype=bool)))
            rec=dict(pair_id=pairid,role=pair['role'],expert=e,contract=pair['contract'],task=r['task'],fold=r['fold'],direction=direction,receiver=a,donor=b,receiver_board=d.b[a],donor_board=d.b[b],receiver_routes=ar[0],donor_routes=d.route[b],receiver_gates=ag[0],donor_gates=d.gates[b],receiver_expert_output=base[0,e],donor_expert_output=donor[0,e],unavailable_nonshared_experts=[v for v in active if v not in shared],raw_alignment=r,scope='post-route, recipient residual/gates fixed; donor latent vector uses own canonical forward; output raw comparison uses declared transform; no query/square axis assumed',outcomes=outcomes,rescue_natural=bool(not outcomes['all-shared-natural']['correct'] and outcomes['restore-candidate']['correct']),new_damage_natural=bool(outcomes['all-shared-natural']['correct'] and not outcomes['restore-candidate']['correct']),rescue_zero=bool(not outcomes['zero-all-selected']['correct'] and outcomes['restore-from-zero']['correct']))
            rows.append(rec)
    for role in ('candidate','control'):
        for contract in ('route-fixed','route-changing'):
            rr=[r for r in rows if r['role']==role and r['contract']==contract]
            counts[f'{role}/{contract}']=dict(directions=len(rr),rescue_natural=sum(r['rescue_natural'] for r in rr),new_damage_natural=sum(r['new_damage_natural'] for r in rr),rescue_zero=sum(r['rescue_zero'] for r in rr),outcomes={name:dict(empty=sum(r['outcomes'][name]['empty'] for r in rr),nonoptimal_nonempty=sum(r['outcomes'][name]['nonoptimal_nonempty'] for r in rr),set_change=sum(r['outcomes'][name]['set_change'] for r in rr),optimal_tie_change=sum(r['outcomes'][name]['optimal_tie_change'] for r in rr)) for name in ('candidate-donor','noncandidate-natural','all-shared-natural','restore-candidate','zero-noncandidate','zero-all-selected','restore-from-zero')})
    for label,predicate in [('local-rescue',lambda r:r['rescue_natural'] or r['rescue_zero']),('insufficient-path',lambda r:not r['outcomes']['zero-noncandidate']['correct']),('robust-preservation',lambda r:r['outcomes']['zero-noncandidate']['correct'] and r['outcomes']['candidate-donor']['correct'])]:
        pool=[r for r in rows if r['role']=='candidate' and predicate(r)]
        if pool:examples.append(dict(callout=label,record=pool[0]))
    put(out/'coverage.json',coverage);put(out/'pairs.json',pairs);put(out/'outcomes.json',rows);put(out/'examples.json',examples)
    put(out/'necessity.json',[dict(expert=e,role='candidate' if e==candidate else 'other',**d.summary(y)) for e,y in lesions.items()])
    summary=dict(selected_expert=candidate,control_expert=control,matched_pairs=len(pairs),bidirectional_trials=len(rows),identity_exact=identity,restoration_equalities_exact=restoration,coverage=coverage,contracts=counts,full_circuit_sufficiency_established=False,natural_mediation_established=False,scope='One complete expert output vector after routing; residual, other paths, gates and final head are retained. Local rescue is not whole-circuit sufficiency. Route-changing contrasts are separate receiver-route-fixed interventions, not upstream router mediation.')
    finish('007',d,out,summary)

def run008(out):
    d,out,m=prepare('008',out);layout=stored_layout(d.c);coords=[]
    for s in range(9):coords.append(('output.bias',(s,),'predeclared-all-output-bias'))
    for e in range(4):coords.append(('router.bias',(e,),'predeclared-all-router-bias'))
    for u in range(16):coords.append(('norm2.weight',(u,),'predeclared-all-small-norm2'))
    # Choose one output weight per output row from training activation magnitude, not confirmation fragility.
    u=int(np.argmax(np.abs(d.st['merged'][d.fold==0]).mean(0)))
    for s in range(9):coords.append(('output.weight',(s,u),'training-max-meanabs-merged'))
    assert len(coords)==38;put(out/'selection.json',dict(coordinates=[dict(tensor=n,coordinate=c,rule=r) for n,c,r in coords],selected_merged_unit=u,training_ids=np.flatnonzero(d.fold==0),layout=layout))
    legal=d.b==0;dist=np.where(d.y>=0,d.y+1,-d.y);mins=np.where(legal,dist,np.iinfo(np.int64).max).min(1)
    census=dict(legal_scores=int(legal.sum()),occupied_scores=int((~legal).sum()),legal_negative=int(((d.y<0)&legal).sum()),legal_zero=int(((d.y==0)&legal).sum()),legal_positive=int(((d.y>0)&legal).sum()),minimum_integer_score_change_to_membership_flip=mins,per_board=[dict(id=i,negative_nearest_zero=int(d.y[i,(d.y[i]<0)&legal[i]].max()) if ((d.y[i]<0)&legal[i]).any() else None,nonnegative_nearest_zero=int(d.y[i,(d.y[i]>=0)&legal[i]].min()),min_change=int(mins[i])) for i in range(627)],boundary='negative -1 -> 0 enters; nonnegative 0 -> -1 leaves; distance y+1 if y>=0 else -y. Not ranking margins/probabilities.')
    put(out/'margin-census.json',census);rows=[];vectors=[];damaged=np.zeros(627,dtype=int);setchanged=np.zeros(627,dtype=int);restored=0;rejected=[]
    for name,coord,rule in coords:
        t=d.c['tensors'][name];old=int(t['codes'][coord]);bits=t['bits'];offset=layout[name]['byte_offset']+np.ravel_multi_index(coord,t['codes'].shape)*bits//8
        for delta in (-1,1):
            ident=f'{name}:{",".join(map(str,coord))}:{delta:+d}'
            try:c=mutate_code(d.c,name,coord,delta)
            except ValueError:rejected.append(dict(id=ident,reason='code boundary',old=old,bits=bits));continue
            # Verify exactly one scalar difference and descriptors/exponents unchanged.
            changed=0
            for nn in d.c['tensors']:
                changed+=int((c['tensors'][nn]['codes']!=d.c['tensors'][nn]['codes']).sum());assert c['tensors'][nn]['exponents']==d.c['tensors'][nn]['exponents']
            assert changed==1
            q=DiagnosticPolicy(c);y=q(d.bt).numpy().copy();p=d.pred(y);damaged+=~p['correct'];setchanged+=(p['members']!=d.opt).any(1)
            restored_c=mutate_code(c,name,coord,-delta);qr=DiagnosticPolicy(restored_c);yr=qr(d.bt).numpy().copy();assert np.array_equal(yr,d.y)
            for k in d.st:assert np.array_equal(qr.stages[k].numpy(),d.st[k]),k
            restored+=1
            s=dict(id=ident,tensor=name,coordinate=coord,rule=rule,old_code=old,new_code=old+delta,bits=bits,byte_offset=int(offset),exponents=t['exponents'],**d.summary(y),**sign_census(d.y,y,legal),route_order_changes=int((q.stages['routes'].numpy()!=d.st['routes']).any(1).sum()),max_abs_logit_delta=int(np.abs(y-d.y).max()))
            rows.append(s);vectors.append(dict(id=ident,logits=y,routes=q.stages['routes'],gates=q.stages['gates']))
    examples=[]
    # Retain maximal fragility and maximal all-intervention robustness, deterministic tie order.
    for label,i in [('fragile',int(np.argmax(setchanged))),('robust',int(max(np.flatnonzero(setchanged==0),key=lambda i:(mins[i],-i))) if (setchanged==0).any() else int(np.argmin(setchanged)))]:
        affected=[v for v in vectors if not np.array_equal((np.array(v['logits'][i])>=0)&legal[i],d.opt[i])];v=affected[0] if affected else vectors[0];spec=next(r for r in rows if r['id']==v['id'])
        examples.append(dict(callout=label,id=i,board=d.b[i],fold=int(d.fold[i]),baseline_logits=d.y[i],baseline_set=np.flatnonzero(d.opt[i]),routes=d.route[i],gates=d.gates[i],minimum_score_change=int(mins[i]),set_change_interventions=int(setchanged[i]),move_failure_interventions=int(damaged[i]),perturbation=spec,perturbed_logits=v['logits'][i],perturbed_set=np.flatnonzero((np.array(v['logits'][i])>=0)&legal[i])))
    put(out/'interventions.json',rows);put(out/'vectors.json',vectors);put(out/'examples.json',examples);put(out/'board-fragility.json',[dict(id=i,board=d.b[i],fold=int(d.fold[i]),set_changes=int(setchanged[i]),move_failures=int(damaged[i]),min_integer_score_change=int(mins[i])) for i in range(627)])
    summary=dict(coordinates=len(coords),attempted_interventions=76,executed_interventions=len(rows),rejected=rejected,all_stage_restorations_exact=restored,legal_score_count=census['legal_scores'],legal_zero_count=census['legal_zero'],boards_any_set_change=int((setchanged>0).sum()),boards_any_move_failure=int((damaged>0).sum()),boards_robust_all_codes=int((setchanged==0).sum()),negative_to_nonnegative=sum(r['negative_to_nonnegative'] for r in rows),nonnegative_to_negative=sum(r['nonnegative_to_negative'] for r in rows),occupied_sign_flips=sum(r['occupied_sign_flips'] for r in rows),worst=sorted(rows,key=lambda r:(-r['canonical']['move_errors'],-r['canonical']['set_changes'],r['id']))[:5],not_precision_conversion=True,no_human_strategy_inference=True)
    finish('008',d,out,summary)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['006','007','008']);p.add_argument('--out',required=True);args=p.parse_args();globals()['run'+args.stage](args.out)
