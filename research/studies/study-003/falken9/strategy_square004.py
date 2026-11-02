"""Offline study004 independent arithmetic; never imported by the game."""
def rnd(n,d):
    assert d>0
    q,r=divmod(abs(int(n)),int(d))
    return (-1 if n<0 else 1)*(q+int(2*r>=d))

def scaled(n,e):
    return int(n)*(1<<e) if e>=0 else rnd(int(n),1<<(-e))

TASKS=('win','block','fork','prevention')
LINES=tuple(tuple(3*r+c for c in range(3)) for r in range(3))+tuple(tuple(3*r+c for r in range(3)) for c in range(3))+((0,4,8),(2,4,6))

def won(b,m):
    return any(all(b[s]==m for s in line) for line in LINES)

def played(b,s,m):
    assert b[s]==0
    return tuple(m if j==s else v for j,v in enumerate(b))

def wins(b,m):
    return {s for s,v in enumerate(b) if not v and won(played(b,s,m),m)}

def forks(b,m):
    return {s for s,v in enumerate(b) if not v and not won(played(b,s,m),m) and len(wins(played(b,s,m),m))>=2}

def square_labels(b):
    side=1+sum(v!=0 for v in b)%2;opp=3-side
    w=wins(b,side);th=wins(b,opp);f=forks(b,side);of=forks(b,opp)
    prevent=set()
    if not w and not th and of:
        for s,v in enumerate(b):
            if v:continue
            after=played(b,s,side)
            if won(after,side) or wins(after,opp):continue
            viable=[played(after,j,opp) for j,v in enumerate(after) if not v and not wins(played(after,j,opp),side)]
            if viable and all(len(wins(r,opp))<2 for r in viable):prevent.add(s)
    out=[]
    for s,v in enumerate(b):
        d=dict(legal=v==0,occupied_own=v==side,occupied_opponent=v==opp,win=s in w,block=not w and len(th)==1 and s in th,fork=not w and not th and s in f,prevention=s in prevent)
        d['neutral']=d['legal'] and not any(d[t] for t in TASKS)
        out.append(d)
    return out

# Packet-specific common denominator, validated against decoded exponents.
D=1<<46

def clamp(n,bits):
    return max(-(1<<(bits-1)),min((1<<(bits-1))-1,int(n)))

def bookkeep(c,st):
    t=c['tensors'];W=t['output.weight']['codes'].tolist();oe=t['output.weight']['exponents']
    U=t['expert_w2']['codes'].tolist();ee=t['expert_w2']['exponents'];B=t['expert_b2']['codes'].tolist()
    ob=t['output.bias']['codes'].tolist();x=st['readout_gelu'];rt=st['routes'];g=st['gates']
    assert all(-18<=e<=0 for e in ee) and all(-13<=e<=0 for e in oe)
    paths=[];unit=[];bias=[];eround=[];eclamp=[];full=[];expert_a=[]
    mix=[0]*8
    for slot,e in enumerate(rt):
        h=st['expert_hidden'][e]
        a=[sum(h[u]*U[e][u][j] for u in range(4)) for j in range(8)]
        pre=[scaled(a[j],ee[e*8+j])+B[e][j] for j in range(8)]
        y=[clamp(v,c['activation_bits']) for v in pre]
        assert y==st['expert_outputs'][e]
        expert_a.append(a)
        for j in range(8):mix[j]+=g[slot]*y[j]
        p=[[[h[u]*U[e][u][j]*(1<<(18+ee[e*8+j]))*g[slot]*W[s][j]*(1<<(13+oe[s])) for s in range(9)] for j in range(8)] for u in range(4)]
        paths.append(p)
        unit.append([sum(p[u][j][s] for u in range(4) for j in range(8)) for s in range(9)])
        bias.append([sum(B[e][j]*g[slot]*W[s][j]*(1<<(31+oe[s])) for j in range(8)) for s in range(9)])
        er=[(scaled(a[j],ee[e*8+j])*(1<<18)-a[j]*(1<<(18+ee[e*8+j]))) for j in range(8)]
        eround.append([sum(er[j]*g[slot]*W[s][j]*(1<<(13+oe[s])) for j in range(8)) for s in range(9)])
        eclamp.append([sum((y[j]-pre[j])*g[slot]*W[s][j]*(1<<(31+oe[s])) for j in range(8)) for s in range(9)])
        full.append([sum(y[j]*g[slot]*W[s][j]*(1<<(31+oe[s])) for j in range(8)) for s in range(9)])
    rm=[rnd(v,32768) for v in mix];premerge=[x[j]+rm[j] for j in range(8)]
    merged=[clamp(v,c['activation_bits']) for v in premerge]
    assert merged==st['merged']
    acc=[sum(merged[j]*W[s][j] for j in range(8)) for s in range(9)]
    roundhead=[scaled(acc[s],oe[s]) for s in range(9)]
    prehead=[roundhead[s]+ob[s] for s in range(9)]
    logits=[clamp(v,c['output_bits']) for v in prehead]
    assert logits==st['logits']
    terms=dict(readout=[sum(x[j]*W[s][j]*(1<<(46+oe[s])) for j in range(8)) for s in range(9)],output_bias=[v*D for v in ob],mix_round=[sum((rm[j]*32768-mix[j])*W[s][j]*(1<<(31+oe[s])) for j in range(8)) for s in range(9)],merge_clamp=[sum((merged[j]-premerge[j])*W[s][j]*(1<<(46+oe[s])) for j in range(8)) for s in range(9)],head_round=[roundhead[s]*D-acc[s]*(1<<(46+oe[s])) for s in range(9)],head_clamp=[(logits[s]-prehead[s])*D for s in range(9)])
    for slot,e in enumerate(rt):
        terms[f'E{e}_units']=unit[slot];terms[f'E{e}_bias']=bias[slot]
        terms[f'E{e}_round']=eround[slot];terms[f'E{e}_clamp']=eclamp[slot]
    assert all(sum(v[s] for v in terms.values())==logits[s]*D for s in range(9))
    return dict(expert_ids=rt,gates=g,paths=paths,terms=terms,executed_expert_support=full,expert_pre_round_dot=expert_a,expert_actual_outputs=[st['expert_outputs'][e] for e in rt],readout_vector=x,readout_lane_numerators=[[x[j]*W[s][j]*(1<<(46+oe[s])) for s in range(9)] for j in range(8)],mix_numerator=mix,rounded_mix=rm,merged=merged,head_dot=acc,reconstructed_logits=logits)
