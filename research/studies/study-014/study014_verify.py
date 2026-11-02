"""Independent014 audit: packet reader, scalar integer and full weight census.
Imports no014 core, runner, production decoder or arithmetic. Prior013 oracle
provides its independent byte reader/reachability/minimax, not its certificates.
"""
import argparse,hashlib,json,struct
from pathlib import Path
import numpy as np
from study013_verify import decode,score,enumeration,optimal,summary,ORDER
ROOT=Path(__file__).resolve().parent
PACKET='artifacts/flexible-integer/q11-w16-a32-early-interp/model.f9j'
def verify(out):
    out=Path(out);d=np.load(out/'baseline014.npz');f=np.load(out/'forwards014.npz');saved=np.load(out/'joint-bands014.npz');ext=np.load(out/'extrema014.npz')
    boxes=json.loads((out/'boxes014.json').read_text());runs=json.loads((out/'validations014.json').read_text());res=json.loads((out/'results014.json').read_text());cons=json.loads((out/'constraints014.json').read_text())
    packet=(ROOT/PACKET).read_bytes();t,h=decode(packet);w=t['output.weight']['codes'];bias=t['output.bias']['codes'];ee=t['output.weight']['exponents']
    assert h[6]==h[7]==32 and w.shape==(9,8) and bias.shape==(9,)
    b=d['boards'];raw=d['raw_boards'];x=d['merged'];y=d['logits'];ci=d['raw_to_canonical_id'];tr=d['raw_to_canonical_transform']
    assert raw.tolist()==[list(bb) for bb in enumeration()]
    gold=np.array([optimal(tuple(bb)) for bb in b.tolist()]);rgold=np.array([optimal(tuple(bb)) for bb in raw.tolist()])
    assert np.array_equal(gold,d['optimal']) and np.array_equal(rgold,d['raw_optimal'])
    wrapper=packet[struct.calcsize('<4s10BHH'):struct.calcsize('<4s10BHH')+81];perms=[tuple(wrapper[k*9:k*9+9]) for k in range(8)];geometry=set()
    for swap in (False,True):
        for sx in (-1,1):
            for sy in (-1,1):
                pp=[]
                for s in range(9):
                    r,c=divmod(s,3);r-=1;c-=1
                    if swap:r,c=c,r
                    pp.append((sx*r+1)*3+sy*c+1)
                geometry.add(tuple(pp))
    assert set(perms)==geometry and tuple(wrapper[-9:])==ORDER
    lookup={tuple(bb):i for i,bb in enumerate(b.tolist())}
    for i,bb in enumerate(raw.tolist()):
        alternatives=[]
        for p in perms:
            dest=[0]*9
            for s in range(9):dest[p[s]]=bb[s]
            alternatives.append(tuple(dest))
        chosen=min(alternatives);ix=alternatives.index(chosen)
        assert ci[i]==lookup[chosen] and tuple(tr[i])==perms[ix]
    allcodes=np.arange(-32768,32768,dtype=np.int64);assert np.array_equal(allcodes,saved['weight_codes'])
    board_weight_evals=0;valid_pairs=[];intervals=json.loads((ROOT/'results013/certificates013.json').read_text());bounds=[]
    for s in range(9):
        lower=np.full(65536,-32768,dtype=np.int64);upper=np.full(65536,32767,dtype=np.int64);den=2**(-ee[s])
        other=[sum(int(x[i,j])*int(w[s,j]) for j in range(1,8)) for i in range(len(b))]
        obs={v['canonical_id']:v for v in cons[s]['observations']};assert set(obs)==set(np.flatnonzero(b[:,s]==0).tolist())
        # A separate per-BOARD pass over all signed16 weights. No inverse
        # threshold or production vectorized board-batch implementation.
        for i in range(len(b)):
            if b[i,s]!=0:continue
            a=int(x[i,0]);o=other[i];member=bool(y[i,s]>=0)
            assert obs[i]==dict(canonical_id=i,other=o,activation=a,member=member)
            dots=allcodes*a+o
            quotient=np.abs(dots)//den;remainder=np.abs(dots)%den
            quotient=quotient+(2*remainder>=den)
            rounded=np.where(dots<0,-quotient,quotient)
            if member:np.maximum(lower,-rounded,out=lower)
            else:np.minimum(upper,-rounded-1,out=upper)
            board_weight_evals+=len(allcodes)
        assert np.array_equal(lower,saved[f'row{s}-lower']) and np.array_equal(upper,saved[f'row{s}-upper'])
        good=lower<=upper;valid_pairs.append(sum(int(upper[j]-lower[j]+1) for j in np.flatnonzero(good)))
        bc=next(v for v in intervals if v['id']==f'bias-{s}');wc=next(v for v in intervals if v['id']==f'weight-{s}-0')
        index=int(w[s,0])+32768;assert [int(lower[index]),int(upper[index])]==bc['code_interval']
        allowed=np.flatnonzero((lower<=bias[s])&(upper>=bias[s]))-32768
        assert allowed.tolist()==list(range(wc['code_interval'][0],wc['code_interval'][1]+1))
        for grid in boxes['grid']:
            k=grid['numerator'];r=grid['rows'][s];ww=r['weight_interval'];bb=r['bias_interval']
            # Recreate shrinking using exact signed quotient, independent of014.
            for name,cr,old in [('weight_interval',wc,int(w[s,0])),('bias_interval',bc,int(bias[s]))]:
                want=[]
                for end in cr['code_interval']:
                    delta=(abs(end-old)*k)//16
                    want.append(old-delta if end<old else old+delta)
                assert r[name]==want
            start,stop=ww[0]+32768,ww[1]+32768+1
            safe=bb[0]>=int(lower[start:stop].max()) and bb[1]<=int(upper[start:stop].min())
            assert safe==r['safe']
            lows=[];highs=[]
            for i in range(len(b)):
                values=[score(other[i]+int(x[i,0])*wv,ee[s],bv) for wv in ww for bv in bb]
                lows.append(min(values));highs.append(max(values))
            lo=np.array(lows);hi=np.array(highs)
            # No saturation in this panel, permitting exact unclamped comparison.
            assert max(abs(int(v)) for v in lows+highs)<2147483647
            assert np.array_equal(lo,ext[f'k{k}-row{s}-minimum']) and np.array_equal(hi,ext[f'k{k}-row{s}-maximum'])
            pos=(b[:,s]==0)&(y[:,s]>=0);neg=(b[:,s]==0)&(y[:,s]<0)
            assert np.flatnonzero(pos&(lo<0)).tolist()==r['member_failure_ids'] and np.flatnonzero(neg&(hi>=0)).tolist()==r['nonmember_failure_ids']
            assert int(lo[pos].min())==r['member_minimum'] and int(hi[neg].max())==r['nonmember_maximum']
            assert int(lo[r['member_minimum_id']])==r['member_minimum'] and int(hi[r['nonmember_maximum_id']])==r['nonmember_maximum']
        bounds.append(dict(row=s,feasible_signed16_bias_weight_pairs_decimal=str(valid_pairs[-1]),all_weight_codes=65536,source_bias_byte_offset=t['output.bias']['offset']+2*s,source_weight_byte_offset=t['output.weight']['offset']+2*s*8))
    for grid in boxes['grid']:assert grid['safe']==all(v['safe'] for v in grid['rows'])
    accepted=max(g['numerator'] for g in boxes['grid'] if g['safe']);assert accepted==res['accepted_grid_numerator']==boxes['accepted_numerator']
    assert all(not g['safe'] for g in boxes['grid'] if g['numerator']>accepted)
    combinations=1
    for r in boxes['grid'][accepted]['rows']:
        for n in ('weight_interval','bias_interval'):combinations*=r[n][1]-r[n][0]+1
    assert str(combinations)==boxes['accepted_combinations_decimal']==res['accepted_combinations_decimal']
    full_feasible_pairs=1
    for v in valid_pairs:full_feasible_pairs*=v
    scalar_checks=0;byte_checks=[];base=np.array([[score(sum(int(a)*int(c) for a,c in zip(v,row)),ee[k],int(bias[k])) for k,row in enumerate(w)] for v in x]);assert np.array_equal(base,y);scalar_checks+=y.size
    roles={k:0 for k in ('original-row-corner','accepted-row-extremum','accepted-whole-box-pattern')}
    for r in runs:
        roles[r['role']]+=1;ww=w.copy();bb=bias.copy()
        for change in r['changes']:
            s=change['row'];ww[s,0]=change['weight_code'];bb[s]=change['bias_code']
        expected=np.array([[score(sum(int(a)*int(c) for a,c in zip(v,row)),ee[k],int(bb[k])) for k,row in enumerate(ww)] for v in x]);assert np.array_equal(expected,f[r['id']]);scalar_checks+=expected.size
        cm=(expected>=0)&(b==0);rm=np.array([[raw[i,s]==0 and expected[ci[i],tr[i,s]]>=0 for s in range(9)] for i in range(len(raw))])
        assert summary(cm,gold)==r['canonical'] and summary(rm,rgold)==r['raw']
        assert int((((expected>=0)!=(y>=0))&(b!=0)).sum())==r['occupied_sign_crossings']
        for ex in r['examples']:
            i=ex['canonical_id'];s=ex['row'];assert ex['board']==b[i].tolist() and ex['changed_score']==int(expected[i,s]) and ex['baseline_score']==int(y[i,s])
        witness=r['witness']
        if witness:
            i=witness['canonical_id'];s=witness['row'];assert int(expected[i,s])==witness['score']==witness['full_network_score'];assert witness['board']==b[i].tolist()
            key='minimum' if witness['kind']=='member-min' else 'maximum'
            assert int(expected[i,s])==int(ext[f'k{accepted}-row{s}-{key}'][i])
        for ch in r['byte_coordinate_changes']:
            name=ch['tensor'];co=ch['coordinate'];idx=co[0] if len(co)==1 else co[0]*8+co[1];offset=t[name]['offset']+2*idx
            assert struct.unpack_from('<h',packet,offset)[0]==ch['old'];assert struct.unpack('<h',struct.pack('<h',ch['new']))[0]==ch['new']
            byte_checks.append(dict(validation=r['id'],byte_offset=offset,old=ch['old'],new=ch['new']))
    assert roles=={'original-row-corner':36,'accepted-row-extremum':18,'accepted-whole-box-pattern':4} and set(f.files)=={r['id'] for r in runs}
    assert scalar_checks==res['scalar_full_head_checks']
    return dict(pass_all=True,packet_sha256=hashlib.sha256(packet).hexdigest(),independently_verified_weight_codes=9*65536,independent_board_weight_sign_evaluations=board_weight_evals,independent_scalar_full_head_checks=scalar_checks,all17_grid_boxes_independently_certified=True,accepted_box_all_integer_combinations_certified=True,accepted_combinations_decimal=str(combinations),full_joint_feasible_pairs_product_decimal=str(full_feasible_pairs),accepted_grid_numerator=accepted,raw_reachability_minimax_D4_masks_ties=True,independent_raw_boards=len(raw),independent_canonical_boards=len(b),no_shared014_core_decoder_or_production_policy_arithmetic=True,per_row=bounds,byte_checks=byte_checks)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out');print(json.dumps(verify(p.parse_args().out),sort_keys=True,indent=2))
