"""Preconfirmation descriptor correction for study008; original source preserved."""
import argparse,copy,json
from pathlib import Path
import numpy as np
from research678_run import prepare,put,sha,ROOT,finish
from research678_core import mutate_code,sign_census
from scripts.model_strategy_study import stored_layout
from falken9.strategy_diagnostics import DiagnosticPolicy

def coordinate_panel(c,merged,fold):
    assert c['width']==8,'frozen descriptor width must be8'
    coords=[('output.bias',(s,),'predeclared-all-output-bias') for s in range(9)]
    coords += [('router.bias',(e,),'predeclared-all-router-bias') for e in range(4)]
    coords += [(name,(u,),'amended-predeclared-all-small-norm2-affine') for name in ('norm2.weight','norm2.bias') for u in range(c['width'])]
    u=int(np.argmax(np.abs(merged[fold==0]).mean(0)))
    coords += [('output.weight',(s,u),'training-max-meanabs-merged') for s in range(9)]
    return coords,u

def run(out):
    amendment=ROOT/'amendment-study008-descriptors.json';am=json.loads(amendment.read_text());assert am['source_sha256']['research678_stage008.py']==sha(__file__)
    for n,h in am['source_sha256'].items():assert sha(ROOT/n)==h,n
    d,out,m=prepare('008',out);put(out/'descriptor-amendment.json',am);layout=stored_layout(d.c);coords,u=coordinate_panel(d.c,d.st['merged'],d.fold)
    assert len(coords)==38
    # Validate every axis BEFORE intervention; no invalid coordinate or scope replacement after confirmation.
    for name,coord,rule in coords:
        assert len(coord)==d.c['tensors'][name]['codes'].ndim
        assert all(0<=v<size for v,size in zip(coord,d.c['tensors'][name]['codes'].shape))
    put(out/'selection.json',dict(coordinates=[dict(tensor=n,coordinate=c,rule=r) for n,c,r in coords],selected_merged_unit=u,training_ids=np.flatnonzero(d.fold==0),layout=layout,descriptor_amendment_sha256=sha(amendment)))
    legal=d.b==0;dist=np.where(d.y>=0,d.y+1,-d.y);mins=np.where(legal,dist,np.iinfo(np.int64).max).min(1)
    census=dict(legal_scores=int(legal.sum()),occupied_scores=int((~legal).sum()),legal_negative=int(((d.y<0)&legal).sum()),legal_zero=int(((d.y==0)&legal).sum()),legal_positive=int(((d.y>0)&legal).sum()),minimum_integer_score_change_to_membership_flip=mins,per_board=[dict(id=i,negative_nearest_zero=int(d.y[i,(d.y[i]<0)&legal[i]].max()) if ((d.y[i]<0)&legal[i]).any() else None,nonnegative_nearest_zero=int(d.y[i,(d.y[i]>=0)&legal[i]].min()),min_change=int(mins[i])) for i in range(627)],boundary='negative -1 ->0 enters; nonnegative0 ->-1 leaves; distance y+1 if y>=0 else -y. Not ranking margins/probabilities.')
    put(out/'margin-census.json',census);rows=[];vectors=[];damaged=np.zeros(627,dtype=int);setchanged=np.zeros(627,dtype=int);restored=0;rejected=[]
    for name,coord,rule in coords:
        t=d.c['tensors'][name];old=int(t['codes'][coord]);bits=t['bits'];offset=layout[name]['byte_offset']+np.ravel_multi_index(coord,t['codes'].shape)*bits//8
        for delta in (-1,1):
            ident=f'{name}:{",".join(map(str,coord))}:{delta:+d}'
            try:c=mutate_code(d.c,name,coord,delta)
            except ValueError:rejected.append(dict(id=ident,reason='code boundary',old=old,bits=bits));continue
            changed=0
            for nn in d.c['tensors']:
                changed+=int((c['tensors'][nn]['codes']!=d.c['tensors'][nn]['codes']).sum());assert c['tensors'][nn]['exponents']==d.c['tensors'][nn]['exponents']
            assert changed==1
            q=DiagnosticPolicy(c);y=q(d.bt).numpy().copy();p=d.pred(y);damaged+=~p['correct'];setchanged+=(p['members']!=d.opt).any(1)
            restored_c=mutate_code(c,name,coord,-delta);qr=DiagnosticPolicy(restored_c);yr=qr(d.bt).numpy().copy();assert np.array_equal(yr,d.y)
            for k in d.st:assert np.array_equal(qr.stages[k].numpy(),d.st[k]),k
            restored+=1
            rows.append(dict(id=ident,tensor=name,coordinate=coord,rule=rule,old_code=old,new_code=old+delta,bits=bits,byte_offset=int(offset),exponents=t['exponents'],**d.summary(y),**sign_census(d.y,y,legal),route_order_changes=int((q.stages['routes'].numpy()!=d.st['routes']).any(1).sum()),max_abs_logit_delta=int(np.abs(y-d.y).max())))
            vectors.append(dict(id=ident,logits=y,routes=q.stages['routes'],gates=q.stages['gates']))
    examples=[]
    for label,i in [('fragile',int(np.argmax(setchanged))),('robust',int(max(np.flatnonzero(setchanged==0),key=lambda i:(mins[i],-i))) if (setchanged==0).any() else int(np.argmin(setchanged)))]:
        affected=[v for v in vectors if not np.array_equal((np.array(v['logits'][i])>=0)&legal[i],d.opt[i])];v=affected[0] if affected else vectors[0];spec=next(r for r in rows if r['id']==v['id'])
        examples.append(dict(callout=label,id=i,board=d.b[i],fold=int(d.fold[i]),baseline_logits=d.y[i],baseline_set=np.flatnonzero(d.opt[i]),routes=d.route[i],gates=d.gates[i],minimum_score_change=int(mins[i]),set_change_interventions=int(setchanged[i]),move_failure_interventions=int(damaged[i]),perturbation=spec,perturbed_logits=v['logits'][i],perturbed_set=np.flatnonzero((np.array(v['logits'][i])>=0)&legal[i])))
    put(out/'interventions.json',rows);put(out/'vectors.json',vectors);put(out/'examples.json',examples);put(out/'board-fragility.json',[dict(id=i,board=d.b[i],fold=int(d.fold[i]),set_changes=int(setchanged[i]),move_failures=int(damaged[i]),min_integer_score_change=int(mins[i])) for i in range(627)])
    summary=dict(coordinates=len(coords),attempted_interventions=76,executed_interventions=len(rows),rejected=rejected,all_stage_restorations_exact=restored,legal_score_count=census['legal_scores'],legal_zero_count=census['legal_zero'],boards_any_set_change=int((setchanged>0).sum()),boards_any_move_failure=int((damaged>0).sum()),boards_robust_all_codes=int((setchanged==0).sum()),negative_to_nonnegative=sum(r['negative_to_nonnegative'] for r in rows),nonnegative_to_negative=sum(r['nonnegative_to_negative'] for r in rows),occupied_sign_flips=sum(r['occupied_sign_flips'] for r in rows),worst=sorted(rows,key=lambda r:(-r['canonical']['move_errors'],-r['canonical']['set_changes'],r['id']))[:5],not_precision_conversion=True,no_human_strategy_inference=True,descriptor_amendment_sha256=sha(amendment))
    finish('008',d,out,summary)
    p=out/'REPORT008.md';text=p.read_text().replace('all16 norm2 weights','all8 norm2 weights plus all8 norm2 biases').replace('research678_run.py 008','research678_stage008.py')
    text+='\n## Frozen preconfirmation descriptor correction\nThe initial plan incorrectly assumed16 norm2 weight coordinates; actual packet descriptor has width8 and expert hidden width4. Before ANY study008 intervention, the panel was amended to all8 norm2 weights plus all8 norm2 biases, preserving38 coordinates/76 attempts. `descriptor-amendment.json` binds the corrected source, tests and actual descriptor inventory. Original frozen source/manifests remain byte-for-byte. No outcome-based panel expansion or replacement.\n';p.write_text(text)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['008'],nargs='?',default='008');p.add_argument('--out',required=True);a=p.parse_args();run(a.out)
