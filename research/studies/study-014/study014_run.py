"""Bounded study014. Real full integer forwards plus exact joint proof."""
import argparse,copy,hashlib,io,json,sys,zipfile
from pathlib import Path
import numpy as np
import torch
from study014_core import extrema,bias_bands,shrink
from falken9.canonical_integer_export import load
from falken9.canonical_integer import CanonicalIntegerPolicy
from falken9.strategy_diagnostics import DiagnosticPolicy,enumerate_boards
from falken9.symmetry import restore_moves
ROOT=Path(__file__).resolve().parent
PACKET='artifacts/flexible-integer/q11-w16-a32-early-interp/model.f9j'
BASE='artifacts/interpretability/study-010-final/baseline010.npz'
RAW='artifacts/interpretability/study-010-final/measurements010.npz'
ORDER=(4,1,3,5,7,2,6,8,0)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,v):
    Path(p).write_text(json.dumps(v,sort_keys=True,indent=2,allow_nan=False,default=lambda x:x.tolist() if hasattr(x,'tolist') else int(x))+'\n')
def pack(p,arrays):
    with zipfile.ZipFile(p,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for k,v in sorted(arrays.items()):
            b=io.BytesIO();np.save(b,np.asarray(v),allow_pickle=False)
            info=zipfile.ZipInfo(k+'.npy',(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16
            z.writestr(info,b.getvalue(),compresslevel=9)
def verify_inputs():
    m=json.loads((ROOT/'manifest014.json').read_text())
    for n,h in m['bound_sha256'].items():assert sha(ROOT/n)==h,n
    p=json.loads((ROOT/'preservation014.json').read_text())
    for label,v in p.items():
        base=Path(v['root'])
        for n,h in v['sha256'].items():assert sha(base/n)==h,(label,n)
        if label!='main-protected':assert {str(q.relative_to(base)) for q in base.rglob('*') if q.is_file()}==set(v['sha256']),label
    return m

def metrics(m,g):
    moves=np.array([next((s for s in ORDER if row[s]),-1) for row in m]);old=np.array([next(s for s in ORDER if row[s]) for row in g])
    good=np.array([s>=0 and g[i,s] for i,s in enumerate(moves)])
    return dict(n=len(g),set_changes=int((m!=g).any(1).sum()),empty=int((moves<0).sum()),nonoptimal_nonempty=int(((moves>=0)&~good).sum()),optimal_tie_changes=int((good&(moves!=old)).sum()),move_changes=int((moves!=old).sum()))

def scalar(merged,c):
    def rnd(a,d):return (1 if a>=0 else -1)*((abs(a)+d//2)//d)
    w=c['tensors']['output.weight'];bias=c['tensors']['output.bias']['codes'].tolist()
    return np.array([[max(-2147483648,min(2147483647,rnd(sum(int(a)*int(q) for a,q in zip(x,row)),1<<-w['exponents'][s])+bias[s])) for s,row in enumerate(w['codes'].tolist())] for x in merged.tolist()],dtype=np.int64)

def run(out):
    torch.set_num_threads(1);manifest=verify_inputs();out=Path(out);out.mkdir(parents=True,exist_ok=False)
    (out/'manifest014.json').write_bytes((ROOT/'manifest014.json').read_bytes())
    bd=np.load(ROOT/BASE);rd=np.load(ROOT/RAW)
    b=bd['boards'];raw=rd['boards'];gold=bd['optimal'];rgold=rd['raw_optimal'];ci=rd['raw_to_canonical_id'];tr=rd['raw_to_canonical_transform']
    assert len(b)==627 and len(raw)==4520
    c=load(ROOT/PACKET);q=DiagnosticPolicy(copy.deepcopy(c));bt=torch.from_numpy(b);y=q(bt).numpy().copy();stages={k:v.numpy().copy() for k,v in q.stages.items()};merged=stages['merged']
    for k,v in stages.items():assert np.array_equal(v,bd[k]),k
    assert np.array_equal(y,scalar(merged,c));assert np.array_equal((y>=0)&(b==0),gold)
    assert np.array_equal((y[ci[:,None],tr]>=0)&(raw==0),rgold)
    histories=enumerate_boards();assert sorted(histories)==[tuple(bb) for bb in raw.tolist()]
    lookup={tuple(bb):i for i,bb in enumerate(b.tolist())};active=y;public_calls=0
    class Fixture(CanonicalIntegerPolicy):
        # TEST ONLY composed wrapper; never installed in application.
        def __call__(self,boards,return_routes=False):
            return torch.tensor(np.array([active[lookup[tuple(bb)]] for bb in boards.tolist()]),dtype=torch.int64)
    fixture=Fixture(c)
    def evaluate(yy):
        nonlocal active,public_calls
        active=yy;cm=(yy>=0)&(b==0);rm=(yy[ci[:,None],tr]>=0)&(raw==0)
        for i,bb in enumerate(raw.tolist()):
            expected=next((s for s in ORDER if rm[i,s]),-1)
            if expected<0:
                try:fixture.predict_history(histories[tuple(bb)])
                except ValueError as e:assert 'empty learned optimal set' in str(e)
                else:raise AssertionError('empty set not rejected')
            else:assert fixture.predict_history(histories[tuple(bb)])==chr(97+expected)
            restored=restore_moves([chr(97+s) for s in range(9) if cm[ci[i],s]],tr[i])
            assert sorted(ord(v)-97 for v in restored)==np.flatnonzero(rm[i]).tolist()
            public_calls+=1
        return dict(canonical=metrics(cm,gold),raw=metrics(rm,rgold),occupied_sign_crossings=int((((yy>=0)!=(y>=0))&(b!=0)).sum()),legal_negative_to_nonnegative=int(((y<0)&(yy>=0)&(b==0)).sum()),legal_nonnegative_to_negative=int(((y>=0)&(yy<0)&(b==0)).sum()))
    baseline_metrics=evaluate(y)
    certs=json.loads((ROOT/'results013/certificates013.json').read_text());rowdata=[];constraints=[];bands={};codes=np.arange(-32768,32768,dtype=np.int64)
    for s in range(9):
        bc=next(v for v in certs if v['id']==f'bias-{s}');wc=next(v for v in certs if v['id']==f'weight-{s}-0')
        w=c['tensors']['output.weight']['codes'][s].numpy();oldb=int(c['tensors']['output.bias']['codes'][s]);oldw=int(w[0]);den=1<<-c['tensors']['output.weight']['exponents'][s]
        assert oldb==bc['old_code'] and oldw==wc['old_code']
        other=merged[:,1:]@w[1:];a=merged[:,0];legal=b[:,s]==0;member=y[:,s]>=0
        low,high=bias_bands(other[legal],a[legal],den,member[legal],codes)
        bands[f'row{s}-lower']=low;bands[f'row{s}-upper']=high
        rowdata.append(dict(row=s,old_bias=oldb,old_weight=oldw,bias_interval=bc['code_interval'],weight_interval=wc['code_interval'],denominator=den,other=other,activation=a,legal=legal,member=member))
        constraints.append(dict(row=s,denominator=den,observations=[dict(canonical_id=int(i),other=int(other[i]),activation=int(a[i]),member=bool(member[i])) for i in np.flatnonzero(legal)],formula='R(other+activation*w)+b >= 0 for member; <0 otherwise; signed16 b,w; R half-away; exact equivalent piecewise half-planes in REPORT014.md'))
    grid=[];extreme_arrays={}
    for k in manifest['dyadic_grid_numerators']:
        rows=[]
        for r in rowdata:
            s=r['row'];ww=shrink(r['weight_interval'],r['old_weight'],k);bb=shrink(r['bias_interval'],r['old_bias'],k)
            lo,hi=extrema(r['other'],r['activation'],r['denominator'],ww,bb)
            pos=r['legal']&r['member'];neg=r['legal']&~r['member'];badp=np.flatnonzero(pos&(lo<0));badn=np.flatnonzero(neg&(hi>=0))
            ip=int(np.flatnonzero(pos)[np.argmin(lo[pos])]);inn=int(np.flatnonzero(neg)[np.argmax(hi[neg])])
            rows.append(dict(row=s,weight_interval=ww,bias_interval=bb,member_minimum=int(lo[ip]),member_minimum_id=ip,nonmember_maximum=int(hi[inn]),nonmember_maximum_id=inn,member_failure_ids=badp,nonmember_failure_ids=badn,safe=not(len(badp) or len(badn))))
            extreme_arrays[f'k{k}-row{s}-minimum']=lo;extreme_arrays[f'k{k}-row{s}-maximum']=hi
        grid.append(dict(numerator=k,denominator=16,safe=all(v['safe'] for v in rows),rows=rows))
    accepted=max(v['numerator'] for v in grid if v['safe']);assert all(v['safe']==(v['numerator']<=accepted) for v in grid)
    selected=grid[accepted];original=grid[16]
    # Number of distinct integer parameter combinations, exact Python integers.
    combination_count=1
    for r in selected['rows']:
        for name in ('weight_interval','bias_interval'):
            lo,hi=r[name];combination_count*=hi-lo+1
    put(out/'constraints014.json',constraints);pack(out/'joint-bands014.npz',dict(bands,weight_codes=codes));pack(out/'extrema014.npz',extreme_arrays)
    put(out/'boxes014.json',dict(grid=grid,accepted_numerator=accepted,accepted_combinations_decimal=str(combination_count),original_box_safe=original['safe'],grid_maximal_not_continuous_optimal=True))
    records=[];vectors={};restorations=0
    def execute(ident,changes,role,witness=None):
        nonlocal restorations
        cc=copy.deepcopy(c)
        for s,bb,ww in changes:
            assert -32768<=bb<=32767 and -32768<=ww<=32767
            cc['tensors']['output.bias']['codes'][s]=bb;cc['tensors']['output.weight']['codes'][s,0]=ww
        allowed={('output.bias',(s,)) for s,bb,ww in changes}|{('output.weight',(s,0)) for s,bb,ww in changes}
        actual=[]
        for name,t in c['tensors'].items():
            assert t['exponents']==cc['tensors'][name]['exponents'] and t['bits']==cc['tensors'][name]['bits']
            for co in (t['codes']!=cc['tensors'][name]['codes']).nonzero().tolist():
                assert (name,tuple(co)) in allowed;actual.append(dict(tensor=name,coordinate=co,old=int(t['codes'][tuple(co)]),new=int(cc['tensors'][name]['codes'][tuple(co)])))
        qq=DiagnosticPolicy(cc);yy=qq(bt).numpy().copy()
        for k,v in stages.items():
            if k!='logits':assert np.array_equal(qq.stages[k].numpy(),v),(ident,k)
        assert np.array_equal(yy,scalar(merged,cc)),ident
        measured=evaluate(yy)
        if role!='original-row-corner':assert measured['canonical']['set_changes']==measured['raw']['set_changes']==0,ident
        examples=[]
        flips=np.argwhere(((yy>=0)!=(y>=0))&(b==0))
        if len(flips):
            i,s=map(int,flips[0]);examples.append(dict(canonical_id=i,row=s,board=b[i],baseline_score=int(y[i,s]),changed_score=int(yy[i,s]),baseline_set=np.flatnonzero(gold[i]),changed_set=np.flatnonzero((yy[i]>=0)&(b[i]==0)),merged_lane0=int(merged[i,0])))
        if witness:
            i=witness['canonical_id'];s=witness['row'];assert int(yy[i,s])==witness['score'];witness.update(board=b[i],baseline_score=int(y[i,s]),full_network_score=int(yy[i,s]))
        # Restore every selected scalar on this exact candidate and recompute.
        restored=copy.deepcopy(cc)
        for s,bb,ww in changes:
            restored['tensors']['output.bias']['codes'][s]=c['tensors']['output.bias']['codes'][s]
            restored['tensors']['output.weight']['codes'][s,0]=c['tensors']['output.weight']['codes'][s,0]
        qr=DiagnosticPolicy(restored);yr=qr(bt).numpy().copy()
        for k,v in stages.items():assert np.array_equal(qr.stages[k].numpy(),v),(ident,k)
        assert evaluate(yr)==baseline_metrics;restorations+=1
        rec=dict(id=ident,role=role,changes=[dict(row=s,bias_code=bb,weight_code=ww) for s,bb,ww in changes],changed_scalar_count=len(actual),byte_coordinate_changes=actual,examples=examples,witness=witness,restored_all_stages_sets_raw_ties=True,**measured)
        records.append(rec);vectors[ident]=yy
        print(ident,'canonical sets',measured['canonical']['set_changes'],'raw',measured['raw'],flush=True)
    # Frozen 9*4 panel, no selection by damage.
    for r in rowdata:
        s=r['row']
        for ib in (0,1):
            for iw in (0,1):execute(f'original-row{s}-b{ib}-w{iw}',[(s,r['bias_interval'][ib],r['weight_interval'][iw])],'original-row-corner')
    # Exact worst legal positive and negative observations for each accepted row.
    for r,box in zip(rowdata,selected['rows']):
        s=r['row'];ww=box['weight_interval'];bb=box['bias_interval']
        for label,key,maximum in [('member-min','member_minimum',False),('nonmember-max','nonmember_maximum',True)]:
            i=box[key+'_id'];a=int(r['activation'][i]);wi=(1 if a>=0 else 0) if maximum else (0 if a>=0 else 1);bi=int(maximum)
            execute(f'accepted-row{s}-{label}',[(s,bb[bi],ww[wi])],'accepted-row-extremum',dict(canonical_id=i,row=s,score=box[key],kind=label,activation=a,bias_endpoint_index=bi,weight_endpoint_index=wi))
    for ib,iw in manifest['whole_box_patterns']:
        changes=[(r['row'],r['bias_interval'][ib],r['weight_interval'][iw]) for r in selected['rows']]
        execute(f'accepted-all-b{ib}-w{iw}',changes,'accepted-whole-box-pattern')
    assert len(records)==58 and restorations==58
    put(out/'validations014.json',records);pack(out/'forwards014.npz',vectors)
    pack(out/'baseline014.npz',dict(stages,boards=b,optimal=gold,raw_boards=raw,raw_optimal=rgold,raw_to_canonical_id=ci,raw_to_canonical_transform=tr))
    imports={n:str(Path(mod.__file__).resolve()) for n,mod in sys.modules.items() if (n=='falken9' or n.startswith('falken9.') or n.startswith('study014') or n.startswith('study013')) and getattr(mod,'__file__',None)}
    assert all(Path(p).is_relative_to(ROOT) for p in imports.values()),imports
    result=dict(study='014',model_sha256=sha(ROOT/PACKET),manifest_sha256=sha(ROOT/'manifest014.json'),domain=dict(canonical=627,raw=4520,previously_trained_and_audited=True),original_row_corner_batches=36,accepted_row_extremum_batches=18,extra_whole_box_batches=4,candidate_batches=len(records),restoration_batches=restorations,baseline_batches=1,total_full_network_batches=117,full_network_board_executions=117*627,baseline_stage_count=len(stages),scalar_full_head_checks=59*int(y.size),composed_public_wrapper_calls=public_calls,original_box_safe=original['safe'],original_failing_corner_batches=sum(v['role']=='original-row-corner' and v['canonical']['set_changes']>0 for v in records),accepted_grid_numerator=accepted,grid_denominator=16,grid_maximal_not_continuous_optimal=True,accepted_box_all_combinations_certified=selected['safe'],accepted_combinations_decimal=str(combination_count),all_stages_restored=True,baseline=baseline_metrics,imports=imports,no_further_study=True)
    put(out/'results014.json',result)
    from study014_verify import verify
    put(out/'independent-audit014.json',verify(out))
    from study014_render import render
    render(out)
    verify_inputs();print(json.dumps(result,sort_keys=True,indent=2))
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--out',required=True);run(parser.parse_args().out)
