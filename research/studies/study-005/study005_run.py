#!/usr/bin/env python3
"""Bounded study005; baseline command must precede frozen manifest and run."""
import argparse,hashlib,json,sys,platform,copy
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import numpy as np
import torch
from study005_core import Attention005,apportion,masks,LINES,candidate_labels,Q15
from falken9.strategy_diagnostics import DiagnosticPolicy,tactical,enumerate_boards,offline_optimal_set,ridge_scores,binary_metrics
from falken9.flexible_integer_export import load
from falken9.symmetry import canonicalize
from scripts.model_strategy_study import behavior,splits
from scripts.verify_app import fixture_records
from scripts.build_runtime import FOUR_MODEL

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,v):Path(p).write_text(json.dumps(v,separators=(',',':'),allow_nan=False)+'\n')
def prior():
    specs=[('RESEARCH-SNAPSHOT.json','source_evidence_sha256',ROOT,69),('verification-study003.json','sha256',ROOT/'artifacts/interpretability/study-003-final',23),('verification-study004.json','sha256',ROOT/'artifacts/interpretability/study-004-final',28)]
    checked={}
    for fn,key,base,n in specs:
        vals=json.loads((ROOT/fn).read_text())[key];assert len(vals)==n
        for name,h in vals.items():
            p=base/name;assert sha(p)==h,str(p);checked[str(p.relative_to(ROOT))]=h
    return checked

def baseline():
    torch.set_num_threads(1);pres=prior()
    import falken9.strategy_diagnostics as sd
    records,fh=fixture_records();rows=sorted(records.values(),key=lambda r:r['canonical_index'])
    b=np.array([r['board'] for r in rows],dtype=np.int64);bt=torch.from_numpy(b)
    c=load(FOUR_MODEL);q=DiagnosticPolicy(c);y=q(bt).numpy().copy();st={k:v.numpy().copy() for k,v in q.stages.items()};checks=0
    for i,r in enumerate(rows):
        for k,gold in r['stages'].items():
            v=st[k][i]
            if k in ('expert_hidden_pre','expert_hidden','expert_outputs'):v=v[st['routes'][i]]
            assert v.tolist()==gold,(i,k);checks+=1
    rawlist=sorted(enumerate_boards());raw=np.array(rawlist,dtype=np.int64);lookup={tuple(v):i for i,v in enumerate(b)}
    aligned=[canonicalize(v) for v in rawlist];ci=np.array([lookup[v] for v,t in aligned]);tr=np.array([t for v,t in aligned])
    opt=np.array([[s in offline_optimal_set(tuple(v)) for s in range(9)] for v in b]);rawopt=np.array([[s in offline_optimal_set(v) for s in range(9)] for v in rawlist])
    cp=behavior(y,b,np.arange(len(b)),np.tile(np.arange(9),(len(b),1)),opt);rp=behavior(y,raw,ci,tr,rawopt)
    assert len(b)==627 and len(raw)==4520 and np.array_equal(cp['members'],opt) and np.array_equal(rp['members'],rawopt) and rp['correct'].all()
    priority=list(c['wrapper'][-9:]);assert priority==[4,1,3,5,7,2,6,8,0]
    for j,(can,t) in enumerate(aligned):
        members={s for s in range(9) if raw[j,s]==0 and y[lookup[can],t[s]]>=0}
        assert members==set(np.flatnonzero(rp['members'][j]));assert next(s for s in priority if s in members)==rp['moves'][j]
    im={n:str(Path(m.__file__).resolve()) for n,m in sorted(sys.modules.items()) if (n=='falken9' or n.startswith('falken9.') or n.startswith('scripts.') or n=='study005_core') and getattr(m,'__file__',None)}
    assert all(Path(v).is_relative_to(ROOT) for v in im.values()),im
    gate=dict(canonical=627,raw=4520,stage_vectors=checks,logit_scalars=int(y.size),fixture_sha256=fh,model_sha256=sha(FOUR_MODEL),model_bytes=FOUR_MODEL.stat().st_size,wrapper_set_errors=0,wrapper_move_errors=0,wrapper_tie_errors=0,imports=im,preservation_counts=[69,23,28],scope='Exact host replay of saved actual-target627 stages and composed full-set wrapper4520; no emulator/new target execution')
    return b,bt,c,y,st,raw,ci,tr,opt,rawopt,cp,rp,gate,pres

def geom(b):
    side=1+sum(v!=0 for v in b)%2
    return tuple(sum(b[s]==mark for s in squares) for mark in (side,3-side) for squares in ((0,2,6,8),(1,3,5,7),(4,)))
def stats(p,base,mask):
    empty=~p['members'].any(1);bad=~p['correct'];mask=np.asarray(mask)
    return dict(n=int(mask.sum()),empty=int((empty&mask).sum()),nonoptimal_nonempty=int((bad&~empty&mask).sum()),move_errors=int((bad&mask).sum()),set_changes=int(((p['members']!=base['members']).any(1)&mask).sum()),move_changes=int(((p['moves']!=base['moves'])&mask).sum()),optimal_tie_changes=int(((p['moves']!=base['moves'])&p['correct']&mask).sum()),mean_margin=float(p['margin'][mask].mean()) if mask.any() else None,mean_margin_delta=float((p['margin']-base['margin'])[mask].mean()) if mask.any() else None)
def correlation(x,y):
    x=np.array(x,dtype=float);y=np.array(y,dtype=float);x-=x.mean();y-=y.mean();d=np.sqrt((x*x).sum()*(y*y).sum());return float(x@y/d) if d else None

def run(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    manifest=ROOT/'experiment-study005.json';m=json.loads(manifest.read_text());assert m['intervention_count']==19
    b,bt,c,y,st,raw,ci,tr,opt,rawopt,cp,rp,gate,pres=baseline()
    assert m['baseline_gate_sha256']==sha(ROOT/'baseline-study005.json')
    assert json.loads((ROOT/'baseline-study005.json').read_text())==gate
    for n,h in m['source_sha256'].items():assert sha(ROOT/n)==h,n
    (out/'experiment-manifest005.json').write_bytes(manifest.read_bytes());put(out/'baseline-gate005.json',gate)
    labels=[candidate_labels(tuple(v)) for v in b];fold=splits([tactical(tuple(v)) for v in b]);assert np.bincount(fold).tolist()==[372,121,134]
    put(out/'raw-alignment005.json',[dict(raw_board=v.tolist(),canonical_id=int(ci[i]),raw_to_canonical=tr[i].tolist(),fold=int(fold[ci[i]]),optimal=np.flatnonzero(rawopt[i]).tolist(),move=int(rp['moves'][i])) for i,v in enumerate(raw)])
    put(out/'baseline-vectors005.json',dict(boards=b.tolist(),fold=fold.tolist(),candidate_labels=labels,stages={k:v.tolist() for k,v in st.items()}))
    p=st['attention_probs'];v=st['board_value'];proj=st['projected'];train=fold==0
    meanp=np.array([apportion(row,Q15) for row in p[train].sum(0)]);meanv=np.array([[int(round(float(x))) for x in row] for row in v[train].mean(0)]);meanproj=np.array([[int(round(float(x))) for x in row] for row in proj[train].mean(0)])
    put(out/'training-means005.json',dict(train_ids=np.flatnonzero(train).tolist(),attention_q15=meanp.tolist(),value_integer=meanv.tolist(),projection_integer=meanproj.tolist(),rounding='P: floor largest-remainder low-key ties; V/projection: nearest ties-even mean, offline override only'))
    # Descriptive entropy/sparsity, and within-stratum occupancy controls.
    prob=p/Q15;entropy=-(np.where(prob>0,prob*np.log2(np.maximum(prob,1e-300)),0)).sum(-1)
    def variance(array,keys):
        arr=np.asarray(array,dtype=float);groups={}
        for i,k in enumerate(keys):groups.setdefault(tuple(k),[]).append(i)
        total=0.;count=0
        for ids in groups.values():
            if len(ids)<2:continue
            vv=arr[ids];total+=float(((vv-vv.mean(0))**2).sum());count+=len(ids)*int(np.prod(arr.shape[1:]))
        return dict(groups=len(groups),nonsingleton_groups=sum(len(ids)>1 for ids in groups.values()),scalar_observations=count,within_mse=total/count if count else None)
    edgevals=[];edgekeys=[];qkvvals=[];qkvkeys=[]
    for i,board in enumerate(b):
        side=1+int((board!=0).sum())%2;ply=int((board!=0).sum())
        for q in range(9):
            occ=lambda s:0 if not board[s] else 1 if board[s]==side else 2
            qkvkeys.append((ply,q,occ(q)));qkvvals.append(np.r_[st['board_query'][i,q],st['board_key'][i,q],v[i,q]])
            for k in range(9):edgekeys.append((ply,q,k,occ(q),occ(k)));edgevals.append([p[i,q,k]])
    desc=dict(row_entropy_bits=dict(min=float(entropy.min()),mean=float(entropy.mean()),max=float(entropy.max()),uniform_max=float(np.log2(9))),zero_fraction=float((p==0).mean()),row_max_probability=dict(min=float(prob.max(-1).min()),mean=float(prob.max(-1).mean()),max=float(prob.max(-1).max())),effective_keys_mean=float((2**entropy).mean()),position_mean_attention_mse=float(((p-meanp)**2).mean()),position_mean_value_mse=float(((v-meanv)**2).mean()),position_mean_projection_mse=float(((proj-meanproj)**2).mean()),edge_variation_controlled_ply_q_k_own_opponent=variance(edgevals,edgekeys),local_qkv_variation_controlled_ply_square_occupancy=variance(qkvvals,qkvkeys),attention_axes='B,query-row,key-column; single full9x9 head, canonical zero-based squares; row NOT chosen output square',scope='Descriptive finite domain; softmax over keys is not candidate preference; occupied legal mask external')
    put(out/'descriptive005.json',desc)
    # Same-ply legal relocation, same counts per corner/edge/center, candidate remains empty.
    rawset={tuple(x) for x in raw};lookup={tuple(x):i for i,x in enumerate(b)};pairs=[];coverage=[]
    for task in ('win','threat','fork'):
        for f in range(3):
            positive=0;covered=0
            for i,board in enumerate(b):
                if fold[i]!=f:continue
                for s in range(9):
                    if not labels[i][s][task]:continue
                    positive+=1;pool=[]
                    for src,mark in enumerate(board):
                        if not mark:continue
                        for dest in range(9):
                            if board[dest] or dest==s:continue
                            alt=board.copy();alt[src]=0;alt[dest]=mark;alt=tuple(map(int,alt))
                            if alt not in rawset or geom(alt)!=geom(board):continue
                            cb,t=canonicalize(alt);j=lookup[cb];ss=int(t[s])
                            if j==i or fold[j]!=f or labels[j][ss][task]:continue
                            pool.append((src,dest,j,ss,alt,tuple(map(int,t))))
                    if not pool:continue
                    src,dest,j,ss,alt,t=min(pool);t=np.array(t);covered+=1
                    dp=p[i]-p[j][np.ix_(t,t)];dv=v[i]-v[j,t];dproj=proj[i]-proj[j,t]
                    # Distinguish probability changes from exact actual P*V weighted numerator.
                    weighted_i=p[i].astype(np.int64)[:,:,None]*v[i][None,:,:]
                    pj=p[j][np.ix_(t,t)];vj=v[j,t];weighted_j=pj[:,:,None]*vj[None,:,:]
                    rec=dict(task=task,fold=f,receiver=i,candidate=s,donor=j,donor_candidate=ss,receiver_raw=board.tolist(),donor_raw=list(alt),receiver_raw_to_canonical=list(range(9)),donor_raw_to_canonical=t.tolist(),from_square=src,to_square=dest,mark=int(board[src]),geometry=list(geom(board)),route_changed=bool((st['routes'][i]!=st['routes'][j]).any()),gate_linf=int(np.abs(st['gates'][i]-st['gates'][j]).max()),aligned_attention_l1=int(np.abs(dp).sum()),candidate_row_p_l1=int(np.abs(dp[s]).sum()),candidate_col_p_l1=int(np.abs(dp[:,s]).sum()),aligned_value_l1=int(np.abs(dv).sum()),actual_weighted_pv_numerator_l1=int(np.abs(weighted_i-weighted_j).sum()),aligned_projection_l1=int(np.abs(dproj).sum()),candidate_projection_l1=int(np.abs(dproj[s]).sum()),candidate_logit_delta=int(y[i,s]-y[j,ss]),centered_candidate_logit_contrast=float(y[i,s]-y[i,board==0].mean()-y[j,ss]+y[j,b[j]==0].mean()))
                    pairs.append(rec)
            coverage.append(dict(task=task,fold=f,positive_candidates=positive,matched_positive_candidates=covered,unmatched=positive-covered))
    put(out/'matched-relocations005.json',pairs);put(out/'matching-coverage005.json',coverage)
    # Eight geometry groups ranked ON TRAIN ONLY. No lesion selection or outcome tuning.
    rankings=[]
    for li,line in enumerate(LINES):
        target,ctrl=masks((line,));rr=[r for r in pairs if r['fold']==0 and r['task'] in ('win','threat') and r['candidate'] in line]
        vals=[]
        for r in rr:
            i,j,t=r['receiver'],r['donor'],np.array(r['donor_raw_to_canonical']);s=r['candidate']
            vals.append(float((p[i,s,target[s]].sum()-p[j][np.ix_(t,t)][s,target[s]].sum())/Q15))
        rankings.append(dict(line_id=li,line=list(line),train_matched_n=len(vals),mean_candidate_line_mass_contrast=float(np.mean(vals)) if vals else None))
    selected=sorted([r for r in rankings if r['train_matched_n']],key=lambda r:(-abs(r['mean_candidate_line_mass_contrast']),r['line_id']))[0]
    put(out/'training-selection005.json',dict(rule=m['selection_rule'],rankings=rankings,selected=selected,confirmation_not_model_heldout=True))
    # Finite candidate probes: controls vs P row+column vs projected vector, ridge10.
    xs=[];atts=[];projs=[];ys={t:[] for t in ('win','threat','fork')};ids=[]
    for i,board in enumerate(b):
        ply=int((board!=0).sum());g=list(geom(board))
        for s in range(9):
            if board[s]:continue
            xs.append([int(ply==z) for z in range(9)]+[int(s==z) for z in range(9)]+g)
            atts.append(np.r_[p[i,s],p[i,:,s]]/Q15);projs.append(np.r_[proj[i,s],proj[i].mean(0)]/2048);ids.append(i)
            for task in ys:ys[task].append(labels[i][s][task])
    xs=np.array(xs);atts=np.array(atts);projs=np.array(projs);ids=np.array(ids);probe=[]
    for task in ys:
        lab=np.array(ys[task],dtype=int)
        for feat,x in [('controls',xs),('controls_plus_attention_rowcol',np.c_[xs,atts]),('controls_plus_projected_candidate_globalmean',np.c_[xs,projs])]:
            for f in (1,2):
                tm=fold[ids]==0;em=fold[ids]==f;scores=ridge_scores(x[tm],lab[tm],x[em],10.)
                probe.append(dict(task=task,feature=feat,fold=f,**binary_metrics(lab[em],scores)))
    put(out/'candidate-probes005.json',dict(target='Independent geometric candidate classification, NOT softmax preference; ridge10 fixed, threshold0.5',records=probe))
    interventions=[('noop',dict(mode='noop')),('uniform',dict(mode='uniform')),('identity-attention',dict(mode='identity')),('position-mean',dict(mode='positionmean')),('half-position-mean',dict(mode='halfpositionmean'))]
    groups=[('horizontal',masks(LINES[:3])),('diagonals',masks(LINES[6:])),('training-line',masks((tuple(selected['line']),)))]
    for name,group in groups:
        for which in ('target','control'):
            for dose in (1,2):interventions.append((f'{name}-{which}-{dose}of2',dict(mode='edges',group=group,which=which,dose=dose)))
    interventions += [('value-position-mean',dict(mode='valuemean')),('projection-position-mean',dict(mode='projectionmean'))]
    assert len(interventions)==19
    results=[];vectors=[];allpred={};allst={};budgets={}
    for name,kwargs in interventions:
        q=Attention005(c,meanp=meanp,meanv=meanv,meanproj=meanproj,**kwargs);yy=q(bt).numpy().copy();ss={k:vv.numpy().copy() for k,vv in q.stages.items()}
        assert np.array_equal(q.actual_probs,p);assert np.all(q.effective_probs.sum(-1)==Q15)
        # Native query/key/value unchanged except explicitly named value intervention.
        assert np.array_equal(ss['board_query'],st['board_query']) and np.array_equal(ss['board_key'],st['board_key'])
        if kwargs['mode']!='valuemean':assert np.array_equal(ss['board_value'],v)
        if name=='noop':
            assert np.array_equal(yy,y)
            for k in st:assert np.array_equal(st[k],ss[k]),k
        pred=behavior(yy,b,np.arange(627),np.tile(np.arange(9),(627,1)),opt);rawpred=behavior(yy,raw,ci,tr,rawopt)
        rc=(ss['routes']!=st['routes']).any(1);gc=(ss['gates']!=st['gates']).any(1)
        rms=(np.sort(ss['routes'],1)!=np.sort(st['routes'],1)).any(1)
        meta={k:vv for k,vv in kwargs.items() if k!='group'}
        if 'group' in kwargs:meta.update(target_mask=kwargs['group'][0].tolist(),control_mask=kwargs['group'][1].tolist())
        row=dict(id=name,metadata=meta,canonical=stats(pred,cp,np.ones(627,dtype=bool)),raw=stats(rawpred,rp,np.ones(4520,dtype=bool)),route_order_changes=int(rc.sum()),route_membership_changes=int(rms.sum()),gate_changes=int(gc.sum()),route_unchanged=stats(pred,cp,~rc),route_changed=stats(pred,cp,rc),mean_abs_probability_delta=float(np.abs(q.effective_probs-p).mean()/Q15),mean_abs_projected_delta=float(np.abs(ss['projected']-proj).mean()),mean_abs_logit_delta=float(np.abs(yy-y).mean()),matched=[],folds=[])
        for f in range(3):row['folds'].append(dict(fold=f,**stats(pred,cp,fold==f)))
        for cov in coverage:
            task,f=cov['task'],cov['fold'];rr=[r for r in pairs if r['task']==task and r['fold']==f];delta=yy-y;posflip=[];negflip=[];contrasts=[]
            for r in rr:
                i,s,j,t=r['receiver'],r['candidate'],r['donor'],r['donor_candidate'];posflip.append(bool(pred['members'][i,s]!=cp['members'][i,s]));negflip.append(bool(pred['members'][j,t]!=cp['members'][j,t]));contrasts.append(float(delta[i,s]-delta[i,b[i]==0].mean()-delta[j,t]+delta[j,b[j]==0].mean()))
            row['matched'].append(dict(task=task,fold=f,n=len(rr),positive_flips=sum(posflip),negative_flips=sum(negflip),mean_centered_delta_contrast=float(np.mean(contrasts)) if contrasts else None,receiver_route_changes=sum(bool(rc[r['receiver']]) for r in rr),donor_route_changes=sum(bool(rc[r['donor']]) for r in rr)))
        results.append(row);allpred[name]=pred;allst[name]=ss
        if q.moved is not None:budgets[name]=q.moved;row['moved_mass_total']=int(q.moved.sum());row['active_rows']=int((q.moved>0).sum())
        vectors.append(dict(id=name,logits=yy.tolist(),routes=ss['routes'].tolist(),gates=ss['gates'].tolist(),effective_attention_probs=q.effective_probs.tolist(),projected=ss['projected'].tolist(),attended=ss['attended'].tolist()))
        print(name,row['canonical']['move_errors'],'errors',int(rc.sum()),'route changes',flush=True)
    for name,_ in groups:
        for dose in (1,2):assert np.array_equal(budgets[f'{name}-target-{dose}of2'],budgets[f'{name}-control-{dose}of2'])
    put(out/'interventions005.json',results);put(out/'intervention-vectors005.json',vectors)
    # Actual same-ply contrast examples, including unfavorable control damage and small-P/large-V contrast.
    examples=[]
    for selector,rr in [('matched_threat',[r for r in pairs if r['task']=='threat' and r['fold']==2]),('small_attention_large_value',pairs)]:
        if not rr:continue
        r=max(rr,key=lambda r:r['actual_weighted_pv_numerator_l1']/(1+r['aligned_attention_l1'])) if selector=='small_attention_large_value' else rr[0]
        i,j=r['receiver'],r['donor'];s,t=r['candidate'],r['donor_candidate'];lesion='training-line-target-2of2';control='training-line-control-2of2'
        examples.append(dict(callout=selector,match=r,baseline_receiver_move=int(cp['moves'][i]),baseline_donor_move=int(cp['moves'][j]),receiver_logit=int(y[i,s]),donor_logit=int(y[j,t]),receiver_actual_p=p[i].tolist(),donor_actual_p_aligned=p[j][np.ix_(r['donor_raw_to_canonical'],r['donor_raw_to_canonical'])].tolist(),receiver_value=v[i].tolist(),receiver_projection=proj[i].tolist(),target_lesion_move=int(allpred[lesion]['moves'][i]),control_lesion_move=int(allpred[control]['moves'][i]),target_lesion_set=np.flatnonzero(allpred[lesion]['members'][i]).tolist(),control_lesion_set=np.flatnonzero(allpred[control]['members'][i]).tolist()))
    # Explicit control counterexample chosen without hiding failure.
    controls=[r for r in results if '-control-' in r['id']];worst=max(controls,key=lambda r:r['canonical']['move_errors']);pp=allpred[worst['id']];bad=np.flatnonzero(~pp['correct'])
    counter=None
    if len(bad):
        i=int(bad[0]);counter=dict(id=i,board=b[i].tolist(),fold=int(fold[i]),intervention=worst['id'],baseline_set=np.flatnonzero(cp['members'][i]).tolist(),perturbed_set=np.flatnonzero(pp['members'][i]).tolist(),baseline_move=int(cp['moves'][i]),perturbed_move=int(pp['moves'][i]),route_before=st['routes'][i].tolist(),route_after=allst[worst['id']]['routes'][i].tolist())
    put(out/'examples005.json',dict(examples=examples,unfavorable_control=counter))
    pairs_summary=[]
    for cov in coverage:
        rr=[r for r in pairs if r['task']==cov['task'] and r['fold']==cov['fold']]
        pairs_summary.append(dict(**cov,mean_attention_l1=float(np.mean([r['aligned_attention_l1'] for r in rr])) if rr else None,mean_value_l1=float(np.mean([r['aligned_value_l1'] for r in rr])) if rr else None,mean_projection_l1=float(np.mean([r['aligned_projection_l1'] for r in rr])) if rr else None,route_changed=sum(r['route_changed'] for r in rr)))
    put(out/'matched-summary005.json',pairs_summary)
    provenance=dict(python=platform.python_version(),torch=torch.__version__,numpy=np.__version__,cpu_threads=torch.get_num_threads(),environment_contract='OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1; borrowed dependency interpreter only; imports isolated',source_sha256=m['source_sha256'],manifest_sha256=sha(manifest),preserved_sha256=prior(),model_sha256=sha(FOUR_MODEL))
    put(out/'provenance005.json',provenance)
    render(out);report(out)

def render(out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    matplotlib.rcParams.update({'svg.hashsalt':'study005','font.size':10,'font.family':'DejaVu Sans'})
    examples=json.loads((out/'examples005.json').read_text());d=json.loads((out/'descriptive005.json').read_text());rs=json.loads((out/'interventions005.json').read_text())
    fig=plt.figure(figsize=(14,9),layout='constrained');gs=fig.add_gridspec(2,3,width_ratios=[1,1,1.35])
    for row,ex in enumerate(examples['examples'][:2]):
        r=ex['match'];b=r['receiver_raw'];a=r['donor_raw'];ax=fig.add_subplot(gs[row,0]);ax.axis('off')
        lines=['ABC'[s%3]+str(s//3+1) for s in range(9)]
        boardstr=lambda bb:'\n'.join('   '.join(('.','X','O')[bb[3*y+x]] for x in range(3)) for y in range(3))
        ax.text(.02,.97,f"{chr(65+row)}  {ex['callout']}\n{r['task']}; fold {r['fold']}; candidate raw {lines[r['candidate']]}\nReceiver raw = canonical #{r['receiver']}\n{boardstr(b)}\nDonor raw (relocation {r['from_square']}→{r['to_square']})\n{boardstr(a)}\nRaw→donor canonical: {r['donor_raw_to_canonical']}\nCandidate canonical: {r['candidate']} → {r['donor_candidate']}\nActual logits: {ex['receiver_logit']} vs {ex['donor_logit']}\nActual aligned P L1: {r['aligned_attention_l1']}/32768\nActual aligned V L1: {r['aligned_value_l1']}\nActual aligned projection L1: {r['aligned_projection_l1']}\nTarget/control lesion sets: {ex['target_lesion_set']} / {ex['control_lesion_set']}",va='top',family='DejaVu Sans Mono',fontsize=9)
        ax=fig.add_subplot(gs[row,1]);im=ax.imshow(np.array(ex['receiver_actual_p'])/Q15,vmin=0,vmax=max(.15,float(np.max(np.array(ex['receiver_actual_p'])/Q15))),cmap='viridis');ax.set_title(f"Actual receiver P — #{r['receiver']}");ax.set_xlabel('Key k (canonical zero-based)');ax.set_ylabel('Query q (canonical zero-based)');ax.set_xticks(range(9));ax.set_yticks(range(9));fig.colorbar(im,ax=ax,shrink=.7,label='Actual Q15 probability /32768')
    ax=fig.add_subplot(gs[:,2]);names=[r['id'] for r in rs];ys=np.arange(len(rs));ax.barh(ys,[r['canonical']['move_errors'] for r in rs],label='Nonoptimal / empty moves',color='#b25d4b');ax.scatter([r['route_order_changes'] for r in rs],ys,color='#285a80',s=18,label='Route order changed');ax.set_yticks(ys,names,fontsize=8);ax.invert_yaxis();ax.set_xlabel('Canonical boards /627');ax.set_title('C  Measured upstream perturbations\nOOD interventions, not actual model behavior');ax.legend(loc='lower right',fontsize=8)
    fig.suptitle(f"Frozen Falken-9 study005 — entropy {d['row_entropy_bits']['mean']:.3f} / {np.log2(9):.3f} bits; all rows feed global flattened readout\nX/O are absolute marks; A–C columns, 1–3 rows; candidate labels independent; no strategy detector established",fontsize=12)
    fig.savefig(out/'attention-evidence005.png',dpi=130,metadata={'Software':'study005'});fig.savefig(out/'attention-evidence005.svg',metadata={'Date':None,'Creator':'study005'});plt.close(fig)
    put(out/'figure-metadata005.json',dict(source_files=['examples005.json','descriptive005.json','interventions005.json'],source_sha256={n:sha(out/n) for n in ['examples005.json','descriptive005.json','interventions005.json']},coordinate_convention='Raw zero-based row-major0..8; A-C columns/1-3 rows; receiver canonical frame identity, donor raw-to-canonical explicitly listed; P[q,k] actual unperturbed; no removed edges displayed as actual',callouts=['A matched test threat','B smallest-P/large-value ratio example','C actual measured lesion outcomes'],model_sha256=sha(FOUR_MODEL)))

def report(out):
    d=json.loads((out/'descriptive005.json').read_text());rs=json.loads((out/'interventions005.json').read_text());cov=json.loads((out/'matching-coverage005.json').read_text());sel=json.loads((out/'training-selection005.json').read_text());probe=json.loads((out/'candidate-probes005.json').read_text())['records'];gate=json.loads((out/'baseline-gate005.json').read_text())
    lines=['# Study005: bounded attention and board geometry','',f"Baseline: {gate['stage_vectors']} exact saved-target stage vectors, 5643 logits, 627 canonical boards; complete legal sets/moves/ties reproduced over4520 raw boards. Frozen model5195 bytes. Host composed proof only; no new emulator execution.",'','## Outcomes',f"Actual attention is broad: mean row entropy {d['row_entropy_bits']['mean']:.6f} bits (max log2(9)); effective keys {d['effective_keys_mean']:.4f}; zero fraction {d['zero_fraction']:.6g}; mean row maximum {d['row_max_probability']['mean']:.6f}.",f"Position-mean P MSE (Q15 units squared): {d['position_mean_attention_mse']:.6f}. Within ply/query/key/own-opponent occupancy MSE: {d['edge_variation_controlled_ply_q_k_own_opponent']['within_mse']:.6f}. Local QKV within ply/square/occupancy MSE: {d['local_qkv_variation_controlled_ply_square_occupancy']['within_mse']:.6f}. Local QKV is token-local, not itself a whole-board detector; attention normalization and weighted values vary with the board.",f"Training-only line selection: {sel['selected']}. Eight fixed geometric groups ranked by natural training pair probability contrast, not lesion outcomes; one selected group confirmed alongside horizontal/diagonal and matched controls.",'','## Finite interventions (19, all retained)','|Intervention|Canonical errors/627|Set changes|Raw errors/4520|Route-order changes|Gate changes|','|---|---:|---:|---:|---:|---:|']
    for r in rs:lines.append(f"|{r['id']}|{r['canonical']['move_errors']}|{r['canonical']['set_changes']}|{r['raw']['move_errors']}|{r['route_order_changes']}|{r['gate_changes']}|")
    lines+=['','All probability overrides have exact nonnegative Q15 row sums32768. Target/control masks have identical per-row cardinality, disjoint edges, and exactly equal moved mass min(target mass,control mass) × dose/2 floored. This caps removal, so full dose does NOT necessarily remove every target edge. Original masked mass is proportionally removed; transferred mass is apportioned to complement keys. Floors then largest remainders, low-key ties. Zero-weight redistribution uses uniform eligible keys; inactive rows are identity. Group controls avoid the selected group but can lie on other winning lines; they are not guaranteed semantically neutral. All19 are upstream: route-changing and route-unchanged outcomes reported separately in machine evidence; no post-routing attribution.','', '## Matched geometry and probe confirmation','Same-ply single mark relocation across legal nonterminal raw boards; fixed candidate stays empty; same per-mark corner/edge/center counts; same fold; label-positive receiver versus label-negative donor. Canonical donor is independently canonicalized and both attention axes plus value/projection rows realigned to receiver raw frame. No route matching is imposed; changed routes/gates explicitly retained. One lexicographic donor per positive candidate; donors may be reused.','|Task|Fold (0 train,1 val,2 test)|Positive candidates|Matched|','|---|---:|---:|---:|']
    for r in cov:lines.append(f"|{r['task']}|{r['fold']}|{r['positive_candidates']}|{r['matched_positive_candidates']}|")
    lines+=['','|Task|Fold|Feature|Positives / N|AUC|Balanced accuracy|','|---|---:|---|---:|---:|---:|']
    for r in probe:lines.append(f"|{r['task']}|{r['fold']}|{r['feature']}|{r['positives']}/{r['n']}|{r['auc']}|{r['balanced_accuracy']}|")
    lines+=['','Fixed ridge10 and threshold0.5; controls include ply and candidate identity one-hots plus own/opponent corner/edge/center counts. No tuning or added feature search. These are independent candidate labels, not output softmax choices. AUC/probe increments are descriptive correlates, not causal strategy circuits; no multiplicity significance claimed.','','## Interpretation and limits','Attention, values and projected vectors respond to legal board relocations beyond aggregate occupancy counts. This is not evidence of a dedicated line/threat detector: local embedding/QKV are deterministic occupancy+position+side functions; probabilities are broad; probability changes and actual P*V contributions must not be conflated. Actual Q/K/V and weighted-numerator differences are in matched-relocations005.json, while modified probabilities and downstream projections/logits are in intervention-vectors005.json. Query row never means chosen output square: all nine rows flow through residual, flatten/readout, GELU/norm, learned route/gate and output head.','Small probability changes can coexist with substantial value/projection differences. Position-mean attention preserving behavior would only show finite-domain robustness at that override; catastrophic identity/group lesions are OOD damage, not selective tactical mediation. Unfavorable matched controls and explicit counterexample remain in examples005.json. Zero positives/zero matched cases are absence of evidence, not zero-error proof.','Selection split372/121/134 seed1729 is symmetry-grouped for probes/selection only. All627 were already model-trained/audited; no OOD/model-heldout claim; sparse fork support. Independent geometric fork candidates here include boards excluded by earlier has_fork tactical gating and are NOT the earlier six-positive-board test label. Donor availability restricts conclusions, not repaired through relaxed matching. No training, weight/game change, GPU, install, main checkout execution, merge, upload, services or publication.','', '## Artifacts and reproduction','Frozen experiment-manifest005.json precedes all new evaluation. Baseline-only command precedes root manifest. Reproduce with the recorded single-thread environment and dependency interpreter: `python study005_run.py run --output <fresh005-directory>` (full exact command in FINAL-STUDY-005.md). PNG/SVG rendered from measured JSON only; actual attention panels are unperturbed. Source hashes and preserved69+23+28 artifacts recorded in provenance005.json. Final verification binds independent tests and fresh deterministic bytes.']
    (out/'REPORT005.md').write_text('\n'.join(lines)+'\n')

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('command',choices=['baseline','run']);a.add_argument('--output');args=a.parse_args()
    if args.command=='baseline':
        *_,gate,pres=baseline();put(ROOT/'baseline-study005.json',gate);put(ROOT/'preservation-before005.json',pres);print(json.dumps(gate,indent=2))
    else:run(args.output)
