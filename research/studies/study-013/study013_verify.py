"""Independent packet reader, full signed-code census, scalar and raw oracle.
Does NOT import study013_core, runner, production decoder, or policy arithmetic.
"""
import argparse,hashlib,json,struct
from functools import lru_cache
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parent
NAMES=('position','expert_w1','expert_b1','expert_w2','expert_b2','occupancy.weight','side.weight','norm1.weight','norm1.bias','query.weight','key.weight','value.weight','projection.weight','readout.weight','readout.bias','norm2.weight','norm2.bias','router.weight','router.bias','output.weight','output.bias')
ORDER=(4,1,3,5,7,2,6,8,0)
def decode(raw):
    header=struct.unpack_from('<4s10BHH',raw);assert header[0]==b'F9J2'
    p=struct.calcsize('<4s10BHH')+81;desc=[]
    for n in NAMES:
        bits,rank,k=struct.unpack_from('<BBH',raw,p);p+=4
        shape=tuple(raw[p:p+rank]);p+=rank
        e=struct.unpack_from('<'+'b'*k,raw,p);p+=k;desc.append((n,bits,shape,e))
    out={}
    for n,bits,shape,e in desc:
        count=int(np.prod(shape));offset=p
        values=struct.unpack_from('<'+('h' if bits==16 else 'b')*count,raw,p);p+=count*bits//8
        out[n]=dict(codes=np.array(values,dtype=np.int64).reshape(shape),exponents=e,bits=bits,offset=offset)
    assert len(raw)==p+2052
    return out,header

def divide(a,d):
    if a<0:return -((-a+d//2)//d)
    return (a+d//2)//d

def score(dot,e,bias):
    val=(dot*(2**e) if e>=0 else divide(dot,2**(-e)))+bias
    return min(2147483647,max(-2147483648,val))

LINES=((0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6))
def won(b):return any(b[a]!=0 and b[a]==b[c]==b[d] for a,c,d in LINES)
def after(b,s):
    bb=list(b);bb[s]=1+(9-b.count(0))%2;return tuple(bb)
@lru_cache(None)
def value(b):
    if won(b):return -1
    if 0 not in b:return 0
    return max(-value(after(b,s)) for s in range(9) if b[s]==0)
def optimal(b):
    vals={s:-value(after(b,s)) for s in range(9) if b[s]==0};best=max(vals.values())
    return np.array([vals.get(s,-2)==best for s in range(9)])
def enumeration():
    seen=set()
    def visit(b):
        if b in seen or won(b) or 0 not in b:return
        seen.add(b)
        for s in range(9):
            if b[s]==0:visit(after(b,s))
    visit((0,)*9);return sorted(seen)
def summary(m,g):
    moves=[next((s for s in ORDER if r[s]),-1) for r in m];base=[next(s for s in ORDER if r[s]) for r in g]
    good=[v>=0 and bool(g[i,v]) for i,v in enumerate(moves)]
    return dict(n=len(g),set_changes=sum(not np.array_equal(a,b) for a,b in zip(m,g)),empty=moves.count(-1),nonoptimal_nonempty=sum(v>=0 and not good[i] for i,v in enumerate(moves)),optimal_tie_changes=sum(good[i] and v!=base[i] for i,v in enumerate(moves)),move_changes=sum(a!=b for a,b in zip(moves,base)))

def verify(out):
    out=Path(out);d=np.load(out/'baseline013.npz');yy=np.load(out/'forwards013.npz');certs=json.loads((out/'certificates013.json').read_text());runs=json.loads((out/'validations013.json').read_text())
    rawbytes=(ROOT/'artifacts/flexible-integer/q11-w16-a32-early-interp/model.f9j').read_bytes();t,h=decode(rawbytes)
    assert h[6]==32 and h[7]==32 # activation and output bit widths
    w=t['output.weight']['codes'];bias=t['output.bias']['codes'];exps=t['output.weight']['exponents'];merged=d['merged'];b=d['boards'];y=d['logits'];raw=d['raw_boards'];ci=d['raw_to_canonical_id'];tr=d['raw_to_canonical_transform']
    assert np.array_equal(raw,np.array(enumeration()))
    gold=np.array([optimal(tuple(bb)) for bb in b.tolist()]);rgold=np.array([optimal(tuple(bb)) for bb in raw.tolist()])
    assert np.array_equal(gold,d['optimal']) and np.array_equal(rgold,d['raw_optimal'])
    # Build D4 independently using coordinate matrices and choose lexicographic
    # board, then first original transform index in the frozen packet wrapper.
    wrapper=rawbytes[struct.calcsize('<4s10BHH'):struct.calcsize('<4s10BHH')+81]
    perms=[tuple(wrapper[k*9:k*9+9]) for k in range(8)]
    geometric=set()
    for swap in (False,True):
        for sx in (-1,1):
            for sy in (-1,1):
                p=[]
                for s in range(9):
                    r,c=divmod(s,3);r-=1;c-=1
                    if swap:r,c=c,r
                    p.append((sx*r+1)*3+sy*c+1)
                geometric.add(tuple(p))
    assert set(perms)==geometric;assert tuple(wrapper[-9:])==ORDER
    lookup={tuple(bb):i for i,bb in enumerate(b.tolist())}
    for k,bb in enumerate(raw.tolist()):
        alternatives=[]
        for p in perms:
            dest=[0]*9
            for s in range(9):dest[p[s]]=bb[s]
            alternatives.append(tuple(dest))
        smallest=min(alternatives);idx=alternatives.index(smallest)
        assert ci[k]==lookup[smallest] and tuple(tr[k])==perms[idx]
    code_evaluations=0;scalar_checks=0;code_bytes=[]
    for cr in certs:
        s=cr['row'];j=cr.get('column',0);kind=cr['kind'];old=cr['old_code'];lo,hi=cr['source_code_bounds'];legal=b[:,s]==0
        dots=merged[legal]@w[s];activ=merged[legal,j];members=y[legal,s]>=0;den=1<<-exps[s]
        assert [lo,hi]==[-32768,32767] and cr['source_bits']==16
        assert old==int(bias[s] if kind=='bias' else w[s,j])
        allgood=[]
        for start in range(lo,hi+1,1024):
            codes=np.arange(start,min(start+1024,hi+1),dtype=np.int64)
            dot=dots[None,:] if kind=='bias' else dots[None,:]+(codes[:,None]-old)*activ[None,:]
            scaled=np.where(dot>=0,(np.abs(dot)+den//2)//den,-((np.abs(dot)+den//2)//den))
            values=scaled+codes[:,None] if kind=='bias' else scaled+bias[s]
            good=((values>=0)==members[None,:]).all(1)
            allgood.extend(codes[good].tolist());code_evaluations+=len(codes)*len(dots)
        assert allgood and allgood==list(range(allgood[0],allgood[-1]+1))
        assert [allgood[0],allgood[-1]]==cr['code_interval']
        for side,bound,neighbor in [('lower',allgood[0],allgood[0]-1),('upper',allgood[-1],allgood[-1]+1)]:
            r=next(r for r in runs if r['coordinate_id']==cr['id'] and r['side']==side and r['role']=='nearest-failure')
            if lo<=neighbor<=hi:
                assert r['status']=='executed' and r['new_code']==neighbor
                changed=np.flatnonzero(((yy[r['id']][:,s]>=0)!=(y[:,s]>=0))&legal).tolist()
                assert changed and changed==r['legal_crossing_ids']
                assert set(cr[side+'_limiting_ids']).issubset(changed)
            else:assert r['status']=='censored-no-in-range-code'
        for r in [v for v in runs if v['coordinate_id']==cr['id'] and v['status']=='executed']:
            cc=w.copy();bb=bias.copy();new=r['new_code']
            if kind=='bias':bb[s]=new
            else:cc[s,j]=new
            # Verify actual byte offset and signed16 code representation without
            # producing or saving any perturbed model packet.
            coord_index=s if kind=='bias' else s*w.shape[1]+j
            offset=t[cr['tensor']]['offset']+coord_index*2
            assert struct.unpack_from('<h',rawbytes,offset)[0]==old
            assert struct.unpack('<h',struct.pack('<h',new))[0]==new
            code_bytes.append(dict(validation=r['id'],source_byte_offset=offset,old_code=old,new_code=new,old_signed16_hex=struct.pack('<h',old).hex(),new_signed16_hex=struct.pack('<h',new).hex()))
            expected=[]
            for x in merged.tolist():
                expected.append([score(sum(a*int(c) for a,c in zip(x,row)),exps[k],int(bb[k])) for k,row in enumerate(cc)])
            expected=np.array(expected,dtype=np.int64);assert np.array_equal(expected,yy[r['id']]);scalar_checks+=expected.size
            cm=(expected>=0)&(b==0);rm=np.array([[raw[i,s]==0 and expected[ci[i],tr[i,s]]>=0 for s in range(9)] for i in range(len(raw))])
            assert summary(cm,gold)==r['canonical'] and summary(rm,rgold)==r['raw']
            assert int((((expected>=0)!=(y>=0))&(b!=0)).sum())==r['occupied_sign_crossings']
            for ex in r['examples']:
                i=ex['canonical_id'];assert ex['board']==b[i].tolist() and ex['baseline_logits']==y[i].tolist() and ex['changed_logits']==expected[i].tolist()
    # Independent baseline scalar arithmetic as well.
    baseline=np.array([[score(sum(int(a)*int(c) for a,c in zip(x,row)),exps[k],int(bias[k])) for k,row in enumerate(w)] for x in merged]);assert np.array_equal(baseline,y);scalar_checks+=y.size
    return dict(pass_all=True,packet_sha256=hashlib.sha256(rawbytes).hexdigest(),independent_signed16_code_board_sign_evaluations=code_evaluations,independent_scalar_full_head_checks=scalar_checks,certificates_verified=len(certs),independent_raw_boards=len(raw),independent_canonical_boards=len(b),all_representable_codes_enumerated=True,independent_reachability_minimax_D4_masks_ties=True,code_byte_evidence=code_bytes,no_shared_threshold_or_decoder_or_policy_arithmetic=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out');a=p.parse_args();print(json.dumps(verify(a.out),sort_keys=True,indent=2))
