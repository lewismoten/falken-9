"""Frozen-model study010/011 deterministic evidence helpers."""
import hashlib,json
import numpy as np
SQUARE_ROWS={'board_embedding','board_normalized','board_query','board_key','board_value','attended','projected','attention_residual'}
SQUARE_BOTH={'attention_scores','attention_probs'}
def align_stage(name,value,transform):
    t=np.asarray(transform)
    if name in SQUARE_ROWS:return value[t]
    if name in SQUARE_BOTH:return value[np.ix_(t,t)]
    if name=='logits':return value[t]
    return value

def serialize(value):
    a=np.asarray(value,dtype='<i8',order='C')
    return json.dumps(list(a.shape),separators=(',',':')).encode()+b'\0'+a.tobytes(order='C')

def expert_record(routes,values):
    active=set(map(int,routes))
    return [dict(expert_id=e,executed=e in active,value=values[e].tolist() if e in active else None) for e in range(len(values))]

def executed_vector(routes,values):
    record=expert_record(routes,values);out=[]
    for r in record:
        out.extend([r['expert_id'],int(r['executed'])])
        if r['executed']:out.extend(r['value'])
    return np.array(out,dtype=np.int64)

def collision_census(values,labels,optimal,controls,hash_fn=lambda b:hashlib.sha256(b).hexdigest()):
    # A digest only selects a bucket; bytes, including exact shape, establish equality.
    buckets={};groups=[];keys=[]
    for i,value in enumerate(values):
        data=serialize(value);digest=hash_fn(data);found=None
        for key,g in buckets.get(digest,[]):
            if key==data:found=g;break
        if found is None:
            found=[];buckets.setdefault(digest,[]).append((data,found));groups.append(found);keys.append(digest)
        found.append(i)
    def summarize(gs):
        du=[g for g in gs if len(g)>1]
        mixed_t=[g for g in du if len({labels[i] for i in g})>1]
        mixed_o=[g for g in du if len({optimal[i] for i in g})>1]
        def first(gs,lab):
            candidates=[]
            for g in gs:
                for a in g:
                    for b in g:
                        if a<b and lab[a]!=lab[b]:candidates.append((a,b));break
                    if candidates and candidates[-1][0]==a:break
            return list(min(candidates)) if candidates else None
        return dict(population=sum(map(len,gs)),distinct_classes=len(gs),duplicate_classes=len(du),duplicate_boards=sum(map(len,du)),redundant_boards=sum(len(g)-1 for g in du),colliding_pairs=sum(len(g)*(len(g)-1)//2 for g in du),mixed_tactic_classes=len(mixed_t),mixed_optimal_classes=len(mixed_o),first_tactic_pair=first(mixed_t,labels),first_optimal_pair=first(mixed_o,optimal),max_class_size=max(map(len,gs),default=0))
    cond=[]
    for g in groups:
        d={}
        for i in g:d.setdefault(controls[i],[]).append(i)
        cond.extend(d.values())
    result=summarize(groups);result['conditioned']=summarize(cond)
    return result,[dict(ids=g,sha256=k) for g,k in zip(groups,keys)]
