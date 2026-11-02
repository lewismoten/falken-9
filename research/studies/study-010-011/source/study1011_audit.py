"""Independent board/tuple census and symmetry auditing (no measurement helpers)."""
import argparse,json,hashlib
from pathlib import Path
from functools import lru_cache
from collections import defaultdict
import numpy as np
ROOT=Path(__file__).resolve().parent
LINES=((0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6))
TASKS=('has_win','must_block','has_fork','has_opponent_fork','has_fork_prevention')
PRIORITY=(4,1,3,5,7,2,6,8,0)
def put(p,v):Path(p).write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')
def independent_transforms():
    # Matrix rotation differs from production's coordinate recurrence.
    grid=np.arange(9).reshape(3,3);out=[]
    for reflected in (False,True):
        base=np.fliplr(grid) if reflected else grid
        for rotations in range(4):
            a=np.rot90(base,-rotations);out.append(tuple(int(np.flatnonzero(a.ravel()==s)[0]) for s in range(9)))
    return tuple(out)
def moved(b,t):
    out=[0]*9
    for s,d in enumerate(t):out[d]=int(b[s])
    return tuple(out)
def win(b):
    return any(b[a] and b[a]==b[c]==b[d] for a,c,d in LINES)
def placed(b,s,mark):return tuple(mark if i==s else x for i,x in enumerate(b))
@lru_cache(None)
def value(b):
    if win(b):return -1
    if all(b):return 0
    mark=1+sum(x!=0 for x in b)%2
    return max(-value(placed(b,s,mark)) for s,x in enumerate(b) if not x)
def oracle(b):
    b=tuple(map(int,b));mark=1+sum(x!=0 for x in b)%2
    d={s:-value(placed(b,s,mark)) for s,x in enumerate(b) if not x};v=max(d.values())
    return tuple(s for s,x in d.items() if x==v)
def immediate(b,p):return [s for s,x in enumerate(b) if not x and win(placed(b,s,p))]
def forks(b,p):return [s for s,x in enumerate(b) if not x and not win(placed(b,s,p)) and len(immediate(placed(b,s,p),p))>=2]
def label_board(b):
    b=tuple(map(int,b));p=1+sum(x!=0 for x in b)%2;o=3-p;w=immediate(b,p);t=immediate(b,o);f=forks(b,p);of=forks(b,o);prevent=[]
    if not w and not t and of:
        for s,x in enumerate(b):
            if x:continue
            a=placed(b,s,p)
            if win(a) or immediate(a,o):continue
            replies=[placed(a,z,o) for z,y in enumerate(a) if not y]
            viable=[r for r in replies if not immediate(r,p)]
            if viable and all(len(immediate(r,o))<2 for r in viable):prevent.append(s)
    return dict(has_win=bool(w),must_block=not w and len(t)==1,has_fork=not w and not t and bool(f),has_opponent_fork=not w and not t and bool(of),has_fork_prevention=bool(prevent))
def reachable():
    seen=set()
    def visit(b):
        if win(b) or all(b) or b in seen:return
        seen.add(b);p=1+sum(x!=0 for x in b)%2
        for s,x in enumerate(b):
            if not x:visit(placed(b,s,p))
    visit((0,)*9);return seen

def metrics(sets,gold):
    n=len(sets);empty=wrong=changed=tie=chosen_changed=exact=correct=0
    for a,b in zip(sets,gold):
        a=set(a);b=set(b);m=next((s for s in PRIORITY if s in a),None);base=next(s for s in PRIORITY if s in b)
        empty+=not a;wrong+=bool(a) and m not in b;changed+=a!=b;exact+=a==b;correct+=m in b;tie+=m in b and m!=base;chosen_changed+=m!=base
    return dict(n=n,full_set_correct=exact,full_set_changes=changed,empty_sets=empty,nonoptimal_nonempty=wrong,chosen_optimal=correct,chosen_errors=empty+wrong,chosen_changes=chosen_changed,optimal_tie_changes=tie)

def audit010(directory):
    d=Path(directory);a=np.load(d/'measurements010.npz');r=json.loads((d/'results010.json').read_text());raw=a['boards'];b=a['canonical_boards'];y=a['logits'];ts=independent_transforms();lookup={tuple(row):i for i,row in enumerate(raw)}
    assert set(lookup)==reachable() and len(lookup)==4520
    assert {min(moved(x,t) for t in ts) for x in raw}=={tuple(x) for x in b}
    gold=[oracle(row) for row in raw];sets=[tuple(s for s in range(9) if row[s]==0 and yy[s]>=0) for row,yy in zip(raw,y)]
    assert metrics(sets,gold)==r['unique_direct']
    exact=changes=0;all8=np.ones(627,bool);alllog=np.ones(627,bool);stagechecks=0
    base=np.load(d/'baseline010.npz')
    for ti,t in enumerate(ts):
        ids=np.array([lookup[moved(x,t)] for x in b]);assert np.array_equal(ids,a['orbit_to_raw'][ti])
        assert np.array_equal(y[ids][:,t],a['aligned_logits'][ti])
        gg=[oracle(raw[j]) for j in ids];ss=[sets[j] for j in ids]
        rr={k:v for k,v in r['per_transform'][ti].items() if k in metrics(ss,gg)}
        assert metrics(ss,gg)==rr
        eq=[]
        for i,j in enumerate(ids):
            aligned=set(s for s in range(9) if t[s] in sets[j]);expected=set(oracle(b[i]));eq.append(aligned==expected)
            assert set(np.flatnonzero(a['aligned_legal_sets'][ti,i]))==aligned
        all8&=eq;exact+=sum(eq);changes+=627-sum(eq);alllog&=(a['aligned_logits'][ti]==a['canonical_logits']).all(1)
        # Independent axis-aligned exact stage count, expert masks explicit.
        sq={'board_embedding','board_normalized','board_query','board_key','board_value','attended','projected','attention_residual'}
        both={'attention_scores','attention_probs'}
        for k,expected in r['stage_alignment'][ti]['equal_boards'].items():
            count=0
            for i,j in enumerate(ids):
                v=a[k][j]
                if k in sq:v=np.take(v,t,axis=0)
                elif k in both:v=np.take(np.take(v,t,axis=0),t,axis=1)
                elif k=='logits':v=np.take(v,t)
                if k.startswith('expert_'):
                    left={int(e):tuple(base[k][i,e]) for e in base['routes'][i]};right={int(e):tuple(v[e]) for e in a['routes'][j]};count+=left==right
                else:count+=np.array_equal(base[k][i],v)
            assert count==expected,(ti,k,count,expected);stagechecks+=1
    assert int(all8.sum())==r['all8_full_set_equivariant_canonical_boards'] and int(alllog.sum())==r['all8_exact_aligned_logits_canonical_boards']
    assert exact==r['orbit_full_set_correct'] and changes==r['orbit_full_set_changes']
    # Independently reconstruct fixed wrapper: min canonical board, full set inverse, raw priority.
    bl={tuple(x):i for i,x in enumerate(b)}
    for row in raw:
        canon,ti=min((moved(row,t),i) for i,t in enumerate(ts));t=ts[ti];i=bl[canon]
        members={s for s in range(9) if not row[s] and a['canonical_logits'][i,t[s]]>=0}
        assert members==set(oracle(row));assert next(s for s in PRIORITY if s in members) in members
    ex=json.loads((d/'examples010.json').read_text());bad=[i for i in range(627) if not all8[i]]
    assert ex[0]['canonical_id']==bad[0]
    for e in ex:
        j=e['raw_id'];assert e['board']==raw[j].tolist() and e['direct_logits']==y[j].tolist()
        assert e['direct_legal_set']==list(sets[j]) and e['wrapper_legal_set']==list(gold[j])
        for key in ('expert_hidden','expert_outputs'):
            for x in e[key]:assert x['executed']==(x['expert_id'] in e['routes']) and ((x['value'] is None)==(not x['executed']))
    out=dict(passed=True,independent_reachable_boards=4520,independent_minimax_raw_sets=4520,orbit_observations=5016,aligned_stage_counts_checked=stagechecks,independent_wrapper_reconstructions=4520,unique_metrics=metrics(sets,gold),no_new_target_execution=True)
    put(d/'independent-audit010.json',out);return out

def control(b):
    ply=sum(x!=0 for x in b);p=1+ply%2
    return (ply,ply%2,*[sum(b[s]==mark for s in cells) for mark in (p,3-p) for cells in ((0,2,6,8),(1,3,5,7),(4,))])
def keyvalue(v):
    a=np.asarray(v);return (a.shape,tuple(int(x) for x in a.ravel()))
def stage_values(a,name):
    if name=='unordered_routes':return np.sort(a['routes'],1)
    if name=='pair_and_gates':return np.c_[a['routes'],a['gates']]
    if name=='unmasked_signs':return a['logits']>=0
    if name=='legal_sign_set':return (a['logits']>=0)&(a['boards']==0)
    if name.startswith('executed_'):
        stage=name[len('executed_'):];vals=[]
        for i in range(627):
            vec=[]
            for e in range(a[stage].shape[1]):
                active=e in a['routes'][i];vec.extend((e,int(active)))
                if active:vec.extend(map(int,a[stage][i,e]))
            vals.append(np.array(vec))
        return vals
    return a[name]

def independent_summary(groups,labels,opt,controls,boards):
    def summarize(gs):
        du=[g for g in gs if len(g)>1];mt=[g for g in du if len({labels[i] for i in g})>1];mo=[g for g in du if len({opt[i] for i in g})>1]
        def first(gs,lab):
            pairs=[(x,y) for g in gs for x in g for y in g if tuple(boards[x])<tuple(boards[y]) and lab[x]!=lab[y]]
            return list(min(pairs,key=lambda pair:(tuple(boards[pair[0]]),tuple(boards[pair[1]])))) if pairs else None
        return dict(population=sum(map(len,gs)),distinct_classes=len(gs),duplicate_classes=len(du),duplicate_boards=sum(map(len,du)),redundant_boards=sum(len(g)-1 for g in du),colliding_pairs=sum(len(g)*(len(g)-1)//2 for g in du),mixed_tactic_classes=len(mt),mixed_optimal_classes=len(mo),max_class_size=max(map(len,gs),default=0),first_tactic_pair=first(mt,labels),first_optimal_pair=first(mo,opt),mixed_classes_per_tactic={task:sum(len({labels[i][j] for i in g})>1 for g in gs) for j,task in enumerate(TASKS)})
    cond=[]
    for g in groups:
        by=defaultdict(list)
        for i in g:by[controls[i]].append(i)
        cond.extend(by.values())
    result=summarize(groups);result['conditioned']=summarize(cond);return result

def audit011(directory):
    d=Path(directory);a=np.load(d/'baseline011.npz');b=a['boards'];records=json.loads((d/'boards011.json').read_text());rows=json.loads((d/'results011.json').read_text());classes=json.loads((d/'classes011.json').read_text());ex=json.loads((d/'examples011.json').read_text())
    labs=[label_board(row) for row in b];labels=[tuple(x[k] for k in TASKS) for x in labs];opts=[oracle(row) for row in b];controls=[control(row) for row in b];checked=0
    for i,r in enumerate(records):
        assert r['board']==b[i].tolist() and r['optimal_set']==list(opts[i]) and r['control']==list(controls[i])
        assert all(r['labels'][k]==labs[i][k] for k in TASKS)
        for key in ('expert_hidden','expert_outputs'):
            for ob in r[key]:
                e=ob['expert_id'];active=e in a['routes'][i]
                assert ob['executed']==active and (ob['value']==a[key][i,e].tolist() if active else ob['value'] is None)
    for row in rows:
        name=row['stage'];vals=stage_values(a,name);groups=defaultdict(list)
        for i,v in enumerate(vals):groups[keyvalue(v)].append(i)
        gs=list(groups.values());expected=independent_summary(gs,labels,opts,controls,b)
        assert {k:v for k,v in row.items() if k!='stage'}==expected,name
        assert {tuple(sorted(g)) for g in gs}=={tuple(sorted(g['ids'])) for g in classes[name]},name
        # Validate digest with independent documented wire format and collision equality.
        for g in classes[name]:
            i=g['ids'][0];v=np.asarray(vals[i],dtype='<i8',order='C');wire=json.dumps(list(v.shape),separators=(',',':')).encode()+b'\0'+v.tobytes()
            assert hashlib.sha256(wire).hexdigest()==g['sha256']
            assert all(keyvalue(vals[j])==keyvalue(vals[i]) for j in g['ids'])
        checked+=len(gs)
    per=json.loads((d/'expert-census011.json').read_text());executed=0
    for r in per:
        e=r['expert_id'];ids=np.flatnonzero((a['routes']==e).any(1));assert ids.tolist()==r['canonical_ids']
        groups=defaultdict(list)
        for i in ids:groups[keyvalue(a[r['stage']][i,e])].append(int(i))
        summary=independent_summary(list(groups.values()),labels,opts,controls,b)
        # Population census's chosen examples follow canonical ID order for per-expert scope.
        for field in ('population','distinct_classes','duplicate_classes','duplicate_boards','redundant_boards','colliding_pairs','mixed_tactic_classes','mixed_optimal_classes','max_class_size'):
            assert r[field]==summary[field] and r['conditioned'][field]==summary['conditioned'][field]
        assert r['inactive_observations'] is None
        zg=sum(a['gates'][i,np.flatnonzero(a['routes'][i]==e)[0]]==0 for i in ids);assert int(zg)==r['executed_zero_gate_boards']
        if r['stage']=='expert_hidden':executed+=len(ids)
    assert executed==1254
    for x in ex:
        ids=x['canonical_ids'];vals=stage_values(a,x['stage']);assert keyvalue(vals[ids[0]])==keyvalue(vals[ids[1]])
        assert x['stage_values']==[vals[i].tolist() for i in ids]
    out=dict(passed=True,independent_board_labels=627,independent_minimax_sets=627,tuple_stage_scopes=len(rows),exact_classes_checked=checked,per_expert_scopes=len(per),executed_expert_observations=executed,inactive_values_null=True,examples_checked=len(ex),hash_alone_never_establishes_equality=True)
    put(d/'independent-audit011.json',out);return out
def audit_walkthrough(directory,baseline_path):
    from falken9.flexible_integer_export import load
    from scripts.build_runtime import FOUR_MODEL
    d=Path(directory);t=json.loads((d/'walkthrough1011.json').read_text());a=np.load(baseline_path);c=load(FOUR_MODEL);i=t['canonical_id'];q=t['query_square'];s=t['head_square'];b=a['boards'][i]
    def rd(n,d):return (1 if n>=0 else -1)*((abs(int(n))+d//2)//d)
    assert t['board']==b.tolist() and t['side_embedding_index']==int((b!=0).sum()%2)
    pars=t['static_parameter_snippets'];tables=c['tensors']
    assert pars['occupancy_code']==tables['occupancy.weight']['codes'][int(b[q])].tolist()
    assert pars['position_code']==tables['position']['codes'][q].tolist()
    assert pars['side_code']==tables['side.weight']['codes'][t['side_embedding_index']].tolist()
    assert t['embedding']==[sum(v) for v in zip(pars['occupancy_code'],pars['position_code'],pars['side_code'])]==a['board_embedding'][i,q].tolist()
    assert t['query_vector']==a['board_query'][i,q].tolist() and t['key0_vector']==a['board_key'][i,0].tolist()
    assert sum(x*y for x,y in zip(t['query_vector'],t['key0_vector']))==t['query_key0_dot']
    assert t['attention_q15']==a['attention_probs'][i,q].tolist() and sum(t['attention_q15'])==32768
    w=[sum(int(a['attention_probs'][i,q,k])*int(a['board_value'][i,k,l]) for k in range(9)) for l in range(8)]
    assert w==t['weighted_value_numerator'] and [rd(v,32768) for v in w]==t['attended']
    routes=a['routes'][i].tolist();assert routes==t['routes'] and a['gates'][i].tolist()==t['gates']
    assert t['expert_hidden']==[a['expert_hidden'][i,e].tolist() for e in routes]
    assert t['expert_outputs']==[a['expert_outputs'][i,e].tolist() for e in routes]
    numerator=[sum(t['expert_outputs'][slot][lane]*t['gates'][slot] for slot in range(2)) for lane in range(8)]
    assert numerator==t['weighted_expert_numerator'] and t['merged']==[v+rd(n,32768) for v,n in zip(t['readout_gelu'],numerator)]
    head=tables['output.weight'];bias=tables['output.bias']['codes'].tolist();ys=[]
    for row,exp,bi in zip(head['codes'].tolist(),head['exponents'],bias):
        dot=sum(w*v for w,v in zip(row,t['merged']));ys.append((dot*(1<<exp) if exp>=0 else rd(dot,1<<-exp))+bi)
    assert ys==t['logits']==a['logits'][i].tolist()
    assert pars['output_row']==head['codes'][s].tolist() and pars['output_bias']==bias[s] and pars['output_exponent']==head['exponents'][s]
    assert t['head_products']==[v*w for v,w in zip(t['merged'],pars['output_row'])] and sum(t['head_products'])==t['head_dot']
    assert t['head_scaled']+pars['output_bias']==ys[s]
    assert t['legal_mask']==(b==0).tolist();members=[sq for sq in range(9) if not b[sq] and ys[sq]>=0]
    assert t['legal_set']==members==list(oracle(b)) and t['chosen']==next(sq for sq in PRIORITY if sq in members)
    out=dict(passed=True,canonical_id=i,head_scalars=9,embedding_scalars=8,weighted_value_scalars=8,merge_scalars=8,static_and_dynamic_separated=True,full_set_and_priority_checked=True)
    put(d/'independent-audit-walkthrough1011.json',out);return out

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('study',choices=['010','011']);a.add_argument('directory');args=a.parse_args();print(json.dumps(globals()['audit'+args.study](args.directory),indent=2))
