"""Independent scalar/artifact recount. Does not call study009 quantizer or stats."""
import argparse,hashlib,json,math
from pathlib import Path
from fractions import Fraction
import numpy as np
import torch
from falken9.canonical_integer import CanonicalIntegerPolicy
from falken9.flexible_integer_export import load
from scripts.build_runtime import FOUR_MODEL
ROOT=Path(__file__).resolve().parent
PRIORITY=(4,1,3,5,7,2,6,8,0)


def independent_round(n,d):
    q,r=divmod(abs(int(n)),int(d))
    return (-1 if n<0 else 1)*(q+(2*r>=d))


def canonical_scalar(board):
    choices=[]
    for op in range(8):
        dst=[0]*9;t=[]
        for s in range(9):
            r,c=divmod(s,3)
            rr,cc=((r,c),(c,2-r),(2-r,2-c),(2-c,r),(r,2-c),(2-c,2-r),(2-r,c),(c,r))[op]
            j=rr*3+cc;dst[j]=int(board[s]);t.append(j)
        choices.append((tuple(dst),op,tuple(t)))
    b,_,t=min(choices)
    return b,t


def counts(members,moves,optimal,base_moves):
    n=len(members);correct=np.array([m>=0 and optimal[i,m] for i,m in enumerate(moves)],dtype=bool);empty=~members.any(1)
    return dict(n=n,empty=int(empty.sum()),nonoptimal_nonempty=int((~correct&~empty).sum()),move_errors=int((~correct).sum()),set_changes=int((members!=optimal).any(1).sum()),move_changes=int((moves!=base_moves).sum()),optimal_tie_changes=int(((moves!=base_moves)&correct).sum())),correct


def audit(out):
    out=Path(out);manifest=json.loads((out/'manifest009.json').read_text());rows=json.loads((out/'results009.json').read_text());base=np.load(out/'baseline009.npz');boards=base['boards'];raw=base['raw_boards'];opt=base['optimal'];ropt=base['raw_optimal'];fold=base['fold'];packet=load(FOUR_MODEL)
    assert len(rows)==manifest['override_specifications']==24
    sourcehash=hashlib.sha256(FOUR_MODEL.read_bytes()).hexdigest();assert sourcehash==manifest['source_model_sha256']
    prior=json.loads((ROOT/'preservation-before009.json').read_text())
    for n,h in prior.items():assert hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h,n
    lookup={tuple(b):i for i,b in enumerate(boards)};align=[]
    for j,b in enumerate(raw):
        canon,t=canonical_scalar(b);i=lookup[canon];assert i==base['raw_to_canonical_id'][j] and list(t)==base['raw_to_canonical_transform'][j].tolist();align.append((i,t))
    def decide(y,bs,alignment):
        mm=[];mv=[]
        for b,(i,t) in zip(bs,alignment):
            member=[b[s]==0 and y[i,t[s]]>=0 for s in range(9)];mm.append(member);mv.append(next((s for s in PRIORITY if member[s]),-1))
        return np.array(mm,dtype=bool),np.array(mv,dtype=np.int64)
    identity=[(i,tuple(range(9))) for i in range(627)]
    bcm,bcv=decide(base['logits'],boards,identity);brm,brv=decide(base['logits'],raw,align)
    assert np.array_equal(bcm,opt) and np.array_equal(brm,ropt)
    arrays={};quant_checks=0;norm_checks=0;gate_checks=0;route_checks=0;merged_checks=0;final_checks=0;clipping=0;head=packet['tensors']['output.weight'];bias=packet['tensors']['output.bias']['codes'].tolist();S=1<<packet['frac'];abits=packet['activation_bits'];limit=lambda v,bits:max(-(1<<(bits-1)),min((1<<(bits-1))-1,v))
    scale_rows=[]
    for component in manifest['components']:
        name=component['name'];short=name.split('.')[0];meta=json.loads((out/f'{short}-materialized009.json').read_text());t=packet['tensors'][name]
        assert meta['old_codes']==t['codes'].tolist() and meta['old_exponents']==t['exponents']
        for old,new,e,ee in zip(meta['old_codes'],meta['codes'],meta['old_exponents'],meta['exponents']):
            k=0
            while max(abs(independent_round(v,2**k)) for v in old)>127:k+=1
            assert ee==e+k and [independent_round(v,2**k) for v in old]==new
            assert all(-127<=q<=127 for q in new);quant_checks+=len(old)
        assert meta['old_tensor_payload_bytes']==t['codes'].numel()*2+t['codes'].shape[0]
        assert meta['new_tensor_payload_bytes']==t['codes'].numel()+t['codes'].shape[0]
        assert meta['hypothetical_packet_bytes']==FOUR_MODEL.stat().st_size-t['codes'].numel()
        clipping+=meta['clipped'];scale_rows.append(dict(scope=name,original_row_exponents=meta['old_exponents'],coarse_row_exponents=meta['exponents'],shifts=meta['shifts'],original_payload_bytes=meta['old_tensor_payload_bytes'],coarse_payload_bytes=meta['new_tensor_payload_bytes'],hypothetical_packet_bytes=meta['hypothetical_packet_bytes']))
    # Actual original public wrapper is called again, independent of the runner's behavior helper.
    from falken9.strategy_diagnostics import enumerate_boards
    histories=enumerate_boards();rawcalls=0
    class Replay(CanonicalIntegerPolicy):
        def __init__(self,y):self.y=y
        def __call__(self,bb):return torch.tensor([self.y[lookup[tuple(b)]].tolist() for b in bb.tolist()],dtype=torch.int64)
    for row in rows:
        short=row['scope'].split('.')[0];v=row['variant'];a=np.load(out/f'{short}-{v}009.npz');arrays[(short,v)]=a;y=a['logits']
        cm,cv=decide(y,boards,identity);rm,rv=decide(y,raw,align)
        assert np.array_equal(cm,a['canonical_members']) and np.array_equal(cv,a['canonical_moves'])
        assert np.array_equal(rm,a['raw_members']) and np.array_equal(rv,a['raw_moves'])
        cc,correct=counts(cm,cv,opt,bcv);rc,rawcorrect=counts(rm,rv,ropt,brv)
        for k,n in cc.items():assert row['canonical'][k]==n,(short,v,k,n)
        for k,n in rc.items():assert row['raw'][k]==n,(short,v,k,n)
        for f in range(3):
            mask=fold==f;co,_=counts(cm[mask],cv[mask],opt[mask],bcv[mask])
            for k,n in co.items():assert row['folds'][f][k]==n
        policy=Replay(y)
        for j,b in enumerate(raw):
            try:m=ord(policy.predict_history(histories[tuple(b)]))-97
            except ValueError as e:assert rv[j]==-1 and 'empty learned' in str(e);m=-1
            assert m==rv[j];rawcalls+=1
        for i in range(627):
            z=a['readout_gelu'][i].tolist();mean=independent_round(sum(z),len(z));center=[x-mean for x in z];var=independent_round(sum(x*x for x in center),len(z))+max(1,(S*S+50000)//100000);root=math.isqrt(var)
            norm=[limit(independent_round(independent_round(x*S,root)*int(w),S)+int(b),abits) for x,w,b in zip(center,packet['tensors']['norm2.weight']['codes'],packet['tensors']['norm2.bias']['codes'])]
            assert norm==a['norm2_output'][i].tolist();norm_checks+=len(norm)
            scores=a['router_scores'][i].tolist();route=sorted(range(len(scores)),key=lambda e:(-scores[e],e))[:2];assert route==a['routes'][i].tolist();route_checks+=1
            selected=[scores[e] for e in route];exps=[]
            for sc in selected:
                u=min(512*S,max(0,(max(selected)-sc)*32));idx,remainder=divmod(u,S)
                table=packet['tables']['exp'];ev=independent_round(table[idx]*(S-remainder)+table[min(idx+1,512)]*remainder,S);exps.append(ev)
            gate=[e*32768//sum(exps) for e in exps];gate[selected.index(max(selected))]+=32768-sum(gate)
            assert gate==a['gates'][i].tolist();gate_checks+=len(gate)
            if v!='restore-baseline-merged':
                merged=[]
                for lane in range(8):
                    mix=sum(int(a['expert_outputs'][i,e,lane])*g for e,g in zip(route,gate));merged.append(limit(z[lane]+independent_round(mix,32768),abits))
                assert merged==a['merged'][i].tolist();merged_checks+=len(merged)
            else:assert np.array_equal(a['merged'][i],base['merged'][i])
            result=[]
            for ws,e,b in zip(head['codes'].tolist(),head['exponents'],bias):
                dot=sum(int(x)*w for x,w in zip(a['merged'][i],ws));val=dot*2**e if e>=0 else independent_round(dot,2**(-e));result.append(limit(val+b,packet['output_bits']))
            assert result==y[i].tolist();final_checks+=len(result)
        order=(a['routes']!=base['routes']).any(1);membership=(np.sort(a['routes'],1)!=np.sort(base['routes'],1)).any(1)
        assert int(order.sum())==row['route_order_changes'] and int(membership.sum())==row['route_membership_changes']
        assert int((order&~membership).sum())==row['route_order_only_changes']
        aa=base['logits']>=0;bb=y>=0;legal=boards==0
        assert int((~aa&bb&legal).sum())==row['negative_to_nonnegative']
        assert int((aa&~bb&legal).sum())==row['nonnegative_to_negative']
        assert int(((aa!=bb)&~legal).sum())==row['occupied_sign_flips']
        for k in base.files:
            if k not in a.files:continue
            if v=='clean-code-restoration':assert np.array_equal(a[k],base[k]),(short,k)
            if v in ('self-router-scores-control','self-merged-control'):
                pp=arrays[(short,'plain')];assert np.array_equal(a[k],pp[k]),(short,k)
        if v=='restore-baseline-router-scores':
            assert np.array_equal(a['routes'],base['routes']) and np.array_equal(a['gates'],base['gates'])
        if v=='restore-baseline-merged':assert np.array_equal(y,base['logits'])
    contrasts=[]
    for short in ('query','value','router','readout'):
        plain=arrays[(short,'plain')]
        for v in ('restore-baseline-router-scores','restore-baseline-merged'):
            a=arrays[(short,v)];rec=dict(scope=short,variant=v)
            for domain,optimal in [('canonical',opt),('raw',ropt)]:
                old=plain[domain+'_correct'];new=a[domain+'_correct'];om=plain[domain+'_members'];nm=a[domain+'_members'];goodold=(om==optimal).all(1);goodnew=(nm==optimal).all(1)
                rec[domain]=dict(chosen_rescued=int((~old&new).sum()),chosen_introduced_damage=int((old&~new).sum()),full_sets_restored=int((~goodold&goodnew).sum()),introduced_set_damage=int((goodold&~goodnew).sum()))
            contrasts.append(rec)
    figures=json.loads((out/'figure-layout009.json').read_text())
    from PIL import Image
    for f in figures:
        im=Image.open(out/(f['name']+'.png'));assert im.size==(f['width'],f['height'])
        svg=(out/(f['name']+'.svg')).read_text();assert svg.startswith('<svg') and svg.rstrip().endswith('</svg>')
        for t in f['text_boxes']:
            x1,y1,x2,y2=t['bounds'];assert x1>=0 and y1>=0 and x2<f['width'] and y2<f['height']
    return dict(specifications=len(rows),prior_files_unchanged=len(prior),source_model_sha256=sourcehash,source_model_bytes=FOUR_MODEL.stat().st_size,independent_raw_alignments=len(align),raw_public_wrapper_calls=rawcalls,raw_member_scalar_checks=rawcalls*9,quantization_scalar_checks=quant_checks,norm2_scalar_checks=norm_checks,route_board_checks=route_checks,gate_scalar_checks=gate_checks,merged_scalar_checks=merged_checks,final_affine_scalar_checks=final_checks,clipping=clipping,all_self_controls_exact=True,all_clean_restorations_exact=True,all_merged_restore_logits_exact=True,scales_and_sizes=scale_rows,restoration_contrasts=contrasts,figures_structurally_verified=len(figures),actual_target_execution=False,historical_INT8_reproduction=False)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--result',required=True);a=p.parse_args();report=audit(a.out);Path(a.result).write_text(json.dumps(report,indent=2,sort_keys=True)+'\n');print(json.dumps(report,sort_keys=True))
