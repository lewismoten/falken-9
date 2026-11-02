"""Study013: finite one-coordinate certificates, then actual full forwards."""
import argparse,copy,hashlib,io,json,sys,zipfile
from pathlib import Path
import numpy as np
import torch
from study013_core import certificate,rounded
from falken9.canonical_integer_export import load
from falken9.canonical_integer import CanonicalIntegerPolicy
from falken9.strategy_diagnostics import DiagnosticPolicy,enumerate_boards,parameter_copy
from falken9.symmetry import restore_moves
ROOT=Path(__file__).resolve().parent
PACKET='artifacts/flexible-integer/q11-w16-a32-early-interp/model.f9j'
BASE='artifacts/interpretability/study-010-final/baseline010.npz'
RAW='artifacts/interpretability/study-010-final/measurements010.npz'
PRIORITY=[4,1,3,5,7,2,6,8,0]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,v):
    Path(p).write_text(json.dumps(v,sort_keys=True,indent=2,allow_nan=False,default=lambda o:o.tolist() if hasattr(o,'tolist') else int(o))+'\n')
def pack(p,arrays):
    with zipfile.ZipFile(p,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for k,v in sorted(arrays.items()):
            b=io.BytesIO();np.save(b,np.asarray(v),allow_pickle=False)
            info=zipfile.ZipInfo(k+'.npy',(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16
            z.writestr(info,b.getvalue(),compresslevel=9)
def verify_inputs():
    m=json.loads((ROOT/'manifest013.json').read_text())
    for n,h in m['source_sha256'].items():assert sha(ROOT/n)==h,n
    for n,h in m['input_sha256'].items():assert sha(ROOT/n)==h,n
    for label,source in [('prior','/home/ai/falken9-strategy-study-003'),('main-protected','/home/ai/falken-9')]:
        for n,h in json.loads((ROOT/f'preservation-{label}.json').read_text()).items():assert sha(Path(source)/n)==h,(label,n)
    return m

def metrics(members,gold):
    moves=np.array([next((s for s in PRIORITY if row[s]),-1) for row in members])
    base=np.array([next(s for s in PRIORITY if row[s]) for row in gold])
    correct=np.array([s>=0 and gold[i,s] for i,s in enumerate(moves)])
    return dict(n=len(gold),set_changes=int((members!=gold).any(1).sum()),empty=int((moves<0).sum()),nonoptimal_nonempty=int(((moves>=0)&~correct).sum()),optimal_tie_changes=int((correct&(moves!=base)).sum()),move_changes=int((moves!=base).sum()))

def scalar_head(merged,c):
    w=c['tensors']['output.weight'];bias=c['tensors']['output.bias']['codes'].tolist();out=[]
    for x in merged.tolist():
        row=[]
        for s,ww in enumerate(w['codes'].tolist()):
            a=sum(int(v)*int(q) for v,q in zip(x,ww));e=w['exponents'][s]
            y=(a*(1<<e) if e>=0 else rounded(a,1<<-e))+bias[s]
            row.append(max(-(1<<31),min((1<<31)-1,y)))
        out.append(row)
    return np.array(out,dtype=np.int64)

def run(out):
    torch.set_num_threads(1);m=verify_inputs();out=Path(out);out.mkdir(exist_ok=False,parents=True)
    (out/'manifest013.json').write_bytes((ROOT/'manifest013.json').read_bytes())
    bdata=np.load(ROOT/BASE);rdata=np.load(ROOT/RAW)
    b=bdata['boards'];raw=rdata['boards'];ci=rdata['raw_to_canonical_id'];tr=rdata['raw_to_canonical_transform'];gold=bdata['optimal'];rgold=rdata['raw_optimal']
    c=load(ROOT/PACKET);q=DiagnosticPolicy(copy.deepcopy(c));bt=torch.from_numpy(b);y=q(bt).numpy().copy();merged=q.stages['merged'].numpy().copy()
    stages={k:v.numpy().copy() for k,v in q.stages.items()}
    for k,v in stages.items():assert np.array_equal(v,bdata[k]),k
    assert np.array_equal(y,scalar_head(merged,c));assert np.array_equal((y>=0)&(b==0),gold)
    assert np.array_equal((y[ci[:,None],tr]>=0)&(raw==0),rgold)
    assert len(b)==627 and len(raw)==4520
    imports={n:str(Path(mod.__file__).resolve()) for n,mod in sys.modules.items() if (n=='falken9' or n.startswith('falken9.') or n.startswith('study013')) and getattr(mod,'__file__',None)}
    assert all(Path(p).is_relative_to(ROOT) for p in imports.values())
    histories=enumerate_boards();assert sorted(histories)==[tuple(row) for row in raw.tolist()]
    lookup={tuple(row):i for i,row in enumerate(b.tolist())}
    class Fixture(CanonicalIntegerPolicy):
        # TEST ONLY composed public wrapper, not deployment or a neural forward.
        def __call__(self,boards,return_routes=False):
            return torch.tensor(np.array([active[lookup[tuple(row)]] for row in boards.tolist()]),dtype=torch.int64)
    fixture=Fixture(c);public_calls=0
    def evaluate(yy):
        nonlocal active,public_calls
        cm=(yy>=0)&(b==0);rm=(yy[ci[:,None],tr]>=0)&(raw==0)
        for j,board in enumerate(raw.tolist()):
            expected=next((s for s in PRIORITY if rm[j,s]),-1)
            if expected<0:
                try:fixture.predict_history(histories[tuple(board)])
                except ValueError as exc:assert 'empty learned optimal set' in str(exc)
                else:raise AssertionError('empty wrapper should reject')
            else:assert fixture.predict_history(histories[tuple(board)])==chr(97+expected)
            restored=restore_moves([chr(97+s) for s in range(9) if cm[ci[j],s]],tr[j])
            assert sorted(ord(v)-97 for v in restored)==np.flatnonzero(rm[j]).tolist()
            public_calls+=1
        return dict(canonical=metrics(cm,gold),raw=metrics(rm,rgold),legal_negative_to_nonnegative=int(((y<0)&(yy>=0)&(b==0)).sum()),legal_nonnegative_to_negative=int(((y>=0)&(yy<0)&(b==0)).sum()),occupied_sign_crossings=int((((y>=0)!=(yy>=0))&(b!=0)).sum()))
    active=y;baseline_metrics=evaluate(y)
    certs=[];runs=[];vectors={};all_constraints=[];restorations=0
    for spec in m['coordinates']:
        kind=spec['kind'];s=spec['row'];j=spec.get('column',0);name='output.'+('bias' if kind=='bias' else 'weight');coord=(s,) if kind=='bias' else (s,j)
        t=c['tensors'][name];old=int(t['codes'][coord]);bits=t['bits'];lo=-(1<<(bits-1));hi=(1<<(bits-1))-1
        w=c['tensors']['output.weight']['codes'][s].tolist();bias=int(c['tensors']['output.bias']['codes'][s]);e=c['tensors']['output.weight']['exponents'][s];assert e<0;d=1<<-e
        ids=np.flatnonzero(b[:,s]==0).tolist();rows=[dict(dot=sum(int(x)*int(ww) for x,ww in zip(merged[i],w)),activation=int(merged[i,j]),bias=bias,member=bool(y[i,s]>=0)) for i in ids]
        cr=certificate(rows,kind,old,d,lo,hi);constraints=cr.pop('constraints')
        for v in constraints:v['canonical_id']=ids[v.pop('row')]
        for side in ('lower','upper'):cr[side+'_limiting_ids']=[ids[k] for k in cr.pop(side+'_limit_rows')]
        cr.update(spec,old_code=old,source_bits=bits,source_code_bounds=[lo,hi],stored_exponent=t['exponents'][0 if kind=='bias' else s],head_row_exponent=e,denominator=d,legal_population=len(ids),source_coordinate=list(coord),tensor=name)
        cr['effective_parameter_delta_unit']=f'2^{cr["stored_exponent"]}'
        certs.append(cr);all_constraints.append(dict(id=spec['id'],constraints=constraints))
        for side,endpoint,direction in [('lower',cr['code_interval'][0],-1),('upper',cr['code_interval'][1],1)]:
            for role,new in [('endpoint',endpoint),('nearest-failure',endpoint+direction)]:
                ident=spec['id']+'-'+side+'-'+role
                if not lo<=new<=hi:
                    runs.append(dict(id=ident,coordinate_id=spec['id'],side=side,role=role,status='censored-no-in-range-code',proposed_code=new,source_code_bounds=[lo,hi]));continue
                cc=parameter_copy(c,name,coord,new)
                assert sum(int((cc['tensors'][n]['codes']!=v['codes']).sum()) for n,v in c['tensors'].items())==int(new!=old)
                for n,v in c['tensors'].items():assert v['exponents']==cc['tensors'][n]['exponents']
                qq=DiagnosticPolicy(cc);yy=qq(bt).numpy().copy()
                for k,v in stages.items():
                    if k!='logits':assert np.array_equal(qq.stages[k].numpy(),v),(ident,k)
                assert np.array_equal(yy,scalar_head(merged,cc)),ident
                active=yy;measure=evaluate(yy)
                assert (measure['canonical']['set_changes']==0)==(role=='endpoint'),ident
                # Restore original code, recompute FULL network, every stage and raw tie.
                restored=parameter_copy(cc,name,coord,old);qr=DiagnosticPolicy(restored);yr=qr(bt).numpy().copy()
                for k,v in stages.items():assert np.array_equal(qr.stages[k].numpy(),v),(ident,k)
                active=yr;restoremetrics=evaluate(yr);assert restoremetrics==baseline_metrics;restorations+=1
                flip=np.flatnonzero(((y[:,s]>=0)!=(yy[:,s]>=0))&(b[:,s]==0)).tolist()
                occupied=np.flatnonzero(((y[:,s]>=0)!=(yy[:,s]>=0))&(b[:,s]!=0)).tolist()
                examples=[]
                for typ,pool in [('legal-limiter',flip),('occupied-only',occupied)]:
                    if pool:
                        i=pool[0];examples.append(dict(kind=typ,canonical_id=i,board=b[i],baseline_logits=y[i],changed_logits=yy[i],merged=merged[i],baseline_set=np.flatnonzero(gold[i]),changed_set=np.flatnonzero((yy[i]>=0)&(b[i]==0)),changed_square=s,baseline_score=int(y[i,s]),changed_score=int(yy[i,s]),score_distance_to_flip=int(y[i,s]+1 if y[i,s]>=0 else -y[i,s])))
                record=dict(id=ident,coordinate_id=spec['id'],side=side,role=role,status='executed',old_code=old,new_code=new,delta_code=new-old,legal_crossing_ids=flip,occupied_crossing_ids=occupied,examples=examples,restored_all_stages=True,restored_canonical_and_raw=restoremetrics,**measure)
                runs.append(record);vectors[ident]=yy
                print(ident,new,'sets',measure['canonical']['set_changes'],'raw errors',measure['raw']['empty']+measure['raw']['nonoptimal_nonempty'],flush=True)
    put(out/'certificates013.json',certs);put(out/'constraints013.json',all_constraints);put(out/'validations013.json',runs)
    pack(out/'forwards013.npz',vectors);pack(out/'baseline013.npz',dict(stages,boards=b,optimal=gold,raw_boards=raw,raw_optimal=rgold,raw_to_canonical_id=ci,raw_to_canonical_transform=tr))
    result=dict(coordinates=len(certs),executed_full_forward_validations=len(vectors),restored_full_forward_validations=restorations,censored_sides=sum(int(v[k]) for v in certs for k in ('lower_censored','upper_censored')),baseline_stage_vectors=627*len(stages),baseline_logit_scalars=int(y.size),full_forward_scalar_head_checks=(len(vectors)+1)*int(y.size),composed_public_wrapper_calls=public_calls,domain=dict(canonical=627,raw=4520),all_endpoint_sets_exact=True,all_in_range_nearest_codes_fail=True,all_restored_stages_sets_raw_ties_exact=True,baseline=baseline_metrics,model_sha256=sha(ROOT/PACKET),manifest_sha256=sha(ROOT/'manifest013.json'),imports=imports)
    put(out/'results013.json',result)
    from study013_verify import verify
    put(out/'independent-audit013.json',verify(out))
    from study013_render import render
    render(out)
    verify_inputs();print(json.dumps(result,indent=2))
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--out',required=True);args=a.parse_args();run(args.out)
