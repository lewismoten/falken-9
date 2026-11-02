"""Bounded immutable study009; all full forwards host integer, raw wrapper composed."""
import argparse,copy,hashlib,io,json,time,zipfile
from fractions import Fraction
from pathlib import Path
import numpy as np
import torch
from study005_run import baseline,stats
from study009_core import approximate,CutPolicy
from research678_run import put,sha
from research678_core import sign_census
from falken9.canonical_integer import CanonicalIntegerPolicy
from falken9.strategy_diagnostics import enumerate_boards,tactical
from falken9.symmetry import canonicalize,restore_moves
from scripts.model_strategy_study import behavior,splits
ROOT=Path(__file__).resolve().parent


def pack_arrays(path,arrays):
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,a in sorted(arrays.items()):
            b=io.BytesIO();np.save(b,np.asarray(a),allow_pickle=False)
            item=zipfile.ZipInfo(name+'.npy',(1980,1,1,0,0,0));item.compress_type=zipfile.ZIP_DEFLATED;item.external_attr=0o644<<16
            z.writestr(item,b.getvalue(),compresslevel=9)


def round_scalar(n,d):
    assert d>0
    return (1 if n>=0 else -1)*((abs(n)+d//2)//d)


def linear_scalar(x,t,bias,bits):
    out=[]
    for row,e,b in zip(t['codes'].tolist(),t['exponents'],bias):
        dot=sum(int(a)*int(w) for a,w in zip(x,row))
        val=dot*(1<<e) if e>=0 else round_scalar(dot,1<<(-e))
        out.append(max(-(1<<(bits-1)),min((1<<(bits-1))-1,val+int(b))))
    return out


def scalar_audit(packet,low,meta,st,stlow):
    name=meta['name'];t=packet['tensors'][name];u=low['tensors'][name]
    errors=[];round_checks=0
    for row,(old,new,e,ee,k) in enumerate(zip(t['codes'].tolist(),u['codes'].tolist(),t['exponents'],u['exponents'],meta['shifts'])):
        assert ee==e+k
        for a,b in zip(old,new):
            # Independent Fraction nearest, with exact half-away decision.
            f=Fraction(a,1<<k);n=abs(f.numerator);d=f.denominator
            expected=(1 if f>=0 else -1)*((2*n+d)//(2*d))
            assert b==expected and -127<=b<=127
            errors.append(abs(Fraction(a)*Fraction(2)**e-Fraction(b)*Fraction(2)**ee));round_checks+=1
        if k:
            assert any(abs(round_scalar(a,1<<(k-1)))>127 for a in old)
    x={'query.weight':st['board_normalized'],'value.weight':st['board_normalized'],'router.weight':st['norm2_output'],'readout.weight':st['attention_residual'].reshape(627,72)}[name]
    target={'query.weight':'board_query','value.weight':'board_value','router.weight':'router_scores','readout.weight':'readout_pre'}[name]
    biasname={'router.weight':'router.bias','readout.weight':'readout.bias'}.get(name)
    bias=packet['tensors'][biasname]['codes'].tolist() if biasname else [0]*len(u['exponents'])
    xx=x.reshape(-1,x.shape[-1]);gold=stlow[target].reshape(-1,len(bias));checks=0
    for v,g in zip(xx,gold):
        assert linear_scalar(v.tolist(),u,bias,packet['activation_bits'])==g.tolist();checks+=len(g)
    return dict(code_rounding_scalars=round_checks,linear_output_scalars=checks,clipping=meta['clipped'],max_effective_abs_error=str(max(errors)),mean_effective_abs_error=str(sum(errors)/len(errors)),effective_changed_scalars=sum(v!=0 for v in errors),minimal_shift_all_rows=True)


def raw_wrapper(y,b,raw,ci,tr,rawopt):
    lookup={tuple(row):i for i,row in enumerate(b)}
    class Replay(CanonicalIntegerPolicy):
        def __init__(self):pass
        def __call__(self,boards):
            return torch.tensor(np.array([y[lookup[tuple(v)]] for v in boards.tolist()]),dtype=torch.int64)
    policy=Replay();histories=enumerate_boards();members=[];moves=[]
    for board in raw:
        board=tuple(map(int,board));canonical,transform=canonicalize(board)
        idx=lookup[canonical]
        ms=[chr(97+s) for s in range(9) if canonical[s]==0 and y[idx,s]>=0]
        restored=restore_moves(ms,transform)
        members.append([chr(97+s) in restored for s in range(9)])
        try:move=ord(policy.predict_history(histories[board]))-97
        except ValueError as e:
            assert not restored and 'empty learned optimal set' in str(e);move=-1
        assert move==(ord(restored[0])-97 if restored else -1)
        moves.append(move)
    predicted=behavior(y,raw,ci,tr,rawopt)
    assert np.array_equal(members,predicted['members']) and np.array_equal(moves,predicted['moves'])
    return predicted,dict(public_predict_history_calls=len(raw),empty_exceptions=int((np.array(moves)<0).sum()),boundary='Actual public history/canonicalization/inverse/tie wrapper with TEST-ONLY already verified canonical forward logits; composed proof, not 4520 repeated scalar neural forwards.')


def run(out):
    started=time.monotonic();out=Path(out);out.mkdir(parents=True,exist_ok=False)
    manifest=json.loads((ROOT/'experiment-study009.json').read_text())
    frozen=json.loads((ROOT/'preservation-before009.json').read_text())
    for n,h in frozen.items():assert sha(ROOT/n)==h,n
    b,bt,c,y,st,raw,ci,tr,opt,rawopt,cp,rp,gate,_=baseline()
    assert gate==json.loads((ROOT/'baseline-study009.json').read_text())
    assert gate['model_sha256']==manifest['source_model_sha256']
    labels=[tactical(tuple(v)) for v in b];fold=splits(labels);ident=np.tile(np.arange(9),(627,1));ids=np.arange(627)
    put(out/'manifest009.json',manifest);put(out/'baseline-gate009.json',gate)
    pack_arrays(out/'baseline009.npz',dict(st,boards=b,raw_boards=raw,raw_to_canonical_id=ci,raw_to_canonical_transform=tr,fold=fold,optimal=opt,raw_optimal=rawopt))
    put(out/'labels009.json',labels)
    rows=[];selections=[];scalar=[];baseraw,rawgate=raw_wrapper(y,b,raw,ci,tr,rawopt)
    for scope in manifest['components']:
        name=scope['name'];short=name.split('.')[0];low,meta=approximate(c,name)
        assert meta['shape']==scope['shape'];put(out/f'{short}-materialized009.json',meta)
        p=CutPolicy(copy.deepcopy(low));yp=p(bt).numpy().copy();pst={k:v.numpy().copy() for k,v in p.stages.items()}
        scalar.append(dict(scope=name,**scalar_audit(c,low,meta,st,pst)))
        plainpred=behavior(yp,b,ids,ident,opt)
        variants=[('plain',None,None),('restore-baseline-router-scores','router_scores',st['router_scores']),('self-router-scores-control','router_scores',pst['router_scores']),('restore-baseline-merged','merged',st['merged']),('self-merged-control','merged',pst['merged']),('clean-code-restoration',None,None)]
        scoped={}
        for variant,cut,value in variants:
            if variant=='plain':q=p;yy=yp;ss=pst
            else:
                q=CutPolicy(copy.deepcopy(c if variant=='clean-code-restoration' else low),cut,torch.tensor(value) if value is not None else None)
                yy=q(bt).numpy().copy();ss={k:v.numpy().copy() for k,v in q.stages.items()}
            if variant in ('self-router-scores-control','self-merged-control','clean-code-restoration'):
                expected=st if variant=='clean-code-restoration' else pst
                assert all(np.array_equal(ss[k],expected[k]) for k in expected)
            if variant=='restore-baseline-router-scores':
                assert np.array_equal(ss['routes'],st['routes']) and np.array_equal(ss['gates'],st['gates'])
            if variant=='restore-baseline-merged':assert np.array_equal(yy,y)
            pred=behavior(yy,b,ids,ident,opt);rawpred,rg=raw_wrapper(yy,b,raw,ci,tr,rawopt)
            route_order=(ss['routes']!=st['routes']).any(1)
            route_membership=(np.sort(ss['routes'],1)!=np.sort(st['routes'],1)).any(1)
            # Check final affine independently, including bias in native units and output clamp.
            for i in range(627):
                assert linear_scalar(ss['merged'][i].tolist(),c['tensors']['output.weight'],c['tensors']['output.bias']['codes'].tolist(),c['output_bits'])==yy[i].tolist()
            row=dict(scope=name,variant=variant,canonical=stats(pred,cp,np.ones(627,dtype=bool)),raw=stats(rawpred,rp,np.ones(4520,dtype=bool)),folds=[dict(fold=f,**stats(pred,cp,fold==f)) for f in range(3)],tasks={task:stats(pred,cp,np.array([v[task] for v in labels])) for task in ('has_win','must_block','has_fork')},**sign_census(y,yy,b==0),route_order_changes=int(route_order.sum()),route_membership_changes=int(route_membership.sum()),route_order_only_changes=int((route_order&~route_membership).sum()),gate_boards_changed=int((ss['gates']!=st['gates']).any(1).sum()),max_abs_logit_delta=int(np.abs(yy-y).max()),stage_changes={k:dict(boards=int((ss[k]!=st[k]).reshape(627,-1).any(1).sum()),scalars=int((ss[k]!=st[k]).sum()),max_abs_delta=int(np.abs(ss[k]-st[k]).max())) for k in st if not k.startswith('expert_')},executed_expert_observations=int(ss['routes'].size),unselected_expert_slots='Unobserved; zeros in saved dense diagnostic arrays are placeholders, not execution.',restored_chosen_failures=int((~plainpred['correct']&pred['correct']).sum()),introduced_chosen_failures=int((plainpred['correct']&~pred['correct']).sum()),restored_full_sets=int(((plainpred['members']!=opt).any(1)&(pred['members']==opt).all(1)).sum()),introduced_set_damage=int(((plainpred['members']==opt).all(1)&(pred['members']!=opt).any(1)).sum()),saturation_by_stage=q.stats['saturation_by_stage'],raw_wrapper=rg,final_head_scalar_checks=5643)
            rows.append(row);scoped[variant]=(yy,ss,pred)
            pack_arrays(out/f'{short}-{variant}009.npz',dict(ss,canonical_members=pred['members'],canonical_moves=pred['moves'],canonical_correct=pred['correct'],raw_members=rawpred['members'],raw_moves=rawpred['moves'],raw_correct=rawpred['correct']))
        for f in range(3):
            categories={'chosen-move-failure':~plainpred['correct'],'set-change-optimal-move':(plainpred['members']!=opt).any(1)&plainpred['correct'],'robust-changed-stage':(plainpred['members']==opt).all(1)&(pst['merged']!=st['merged']).any(1)}
            for category,mask in categories.items():
                pool=np.flatnonzero(mask&(fold==f));selections.append(dict(scope=name,category=category,fold=f,available=len(pool),canonical_id=int(pool[0]) if len(pool) else None))
        rr=scoped['restore-baseline-router-scores'][2]
        for category,mask in [('route-restoration-rescue',~plainpred['correct']&rr['correct']),('route-restoration-introduced-damage',plainpred['correct']&~rr['correct'])]:
            pool=np.flatnonzero(mask);selections.append(dict(scope=name,category=category,available=len(pool),canonical_id=int(pool[0]) if len(pool) else None))
        print(short,json.dumps({r['variant']:{'canonical':r['canonical'],'routes':r['route_order_changes'],'membership':r['route_membership_changes'],'rescue':r['restored_chosen_failures'],'newdamage':r['introduced_chosen_failures']} for r in rows if r['scope']==name},separators=(',',':')),flush=True)
        assert time.monotonic()-started<manifest['maximum_seconds']
    put(out/'results009.json',rows);put(out/'selection009.json',selections);put(out/'scalar-audit009.json',scalar)
    for n,h in frozen.items():assert sha(ROOT/n)==h,n
    put(out/'provenance009.json',dict(source_model_sha256=gate['model_sha256'],manifest_sha256=sha(ROOT/'experiment-study009.json'),preservation_manifest_sha256=sha(ROOT/'preservation-before009.json'),prior_files_unchanged=len(frozen),baseline_raw_wrapper=rawgate,override_specifications=len(rows),full_canonical_integer_forwards=len(rows)*627,final_head_scalar_checks=len(rows)*5643,self_control_all_stage_equalities=8*21,clean_all_stage_equalities=4*21,limits=manifest['limits'],scope_warning='All627 boards previously trained/audited; folds are probe/selection confirmation only. Logit>=0 means set membership, never categorical confidence.',imports=gate['imports']))
    print('COMPLETE',len(rows),len(frozen),flush=True)

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--out',required=True);args=a.parse_args();run(args.out)
