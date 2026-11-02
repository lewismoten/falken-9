"""Exact scalar threshold/half-space intersection; no floating inference."""
def rounded(a,d):
    assert d>0
    return (1 if a>0 else -1 if a<0 else 0)*((abs(a)+d//2)//d)

def threshold(target,d):
    """Smallest integer a with half-away round(a/d)>=target."""
    assert d>0
    return target*d-(d//2 if target>0 else (d-1)//2)

def constrain(lo,hi,a,c,positive):
    """Intersect integer [lo,hi] with a*x>=c or its strict complement."""
    if not positive:
        a,c=-a,1-c
    if a>0:lo=max(lo,-((-c)//a))
    elif a<0:hi=min(hi,c//a)
    elif c>0:return None
    return (lo,hi) if lo<=hi else None

def certificate(rows,kind,old,d,code_lo,code_hi):
    # Unbounded symbolic limits use None. The 2**100 working sentinel is
    # proved beyond this packet's finite input/code threshold envelope.
    sentinel=1<<100
    lo,hi=-sentinel,sentinel
    constraints=[]
    for i,r in enumerate(rows):
        if kind=='bias':a=1;c=-rounded(r['dot'],d)
        else:a=r['activation'];c=threshold(-r['bias'],d)-r['dot']+old*a
        interval=constrain(-sentinel,sentinel,a,c,r['member'])
        assert interval is not None
        ll,hh=interval;lo=max(lo,ll);hi=min(hi,hh)
        constraints.append(dict(row=i,a=a,c=c,positive=r['member'],lower=None if ll==-sentinel else ll,upper=None if hh==sentinel else hh))
    assert lo<=old<=hi
    clipped=[max(lo,code_lo),min(hi,code_hi)]
    return dict(code_interval=clipped,delta_interval=[clipped[0]-old,clipped[1]-old],mathematical_interval=[None if lo==-sentinel else lo,None if hi==sentinel else hi],lower_censored=lo<=code_lo,upper_censored=hi>=code_hi,lower_limit_rows=[v['row'] for v in constraints if v['lower']==lo],upper_limit_rows=[v['row'] for v in constraints if v['upper']==hi],constraints=constraints)
