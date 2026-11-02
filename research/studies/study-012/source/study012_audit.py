"""Independent full-raw-orbit aggregation audit, without study012 helpers."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from study1011_audit import independent_transforms,moved,oracle,metrics,PRIORITY
ROOT=Path(__file__).resolve().parent

def audit(directory):
    d=Path(directory);m=json.loads((d/'manifest012.json').read_text());p=ROOT/m['source_logits_path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==m['source_logits_sha256']
    src=np.load(p);a=np.load(d/'measurements012.npz');rows=json.loads((d/'results012.json').read_text());raw=src['boards'];b=src['canonical_boards'];lookup={tuple(row):i for i,row in enumerate(raw)};ts=independent_transforms();ys=src['logits'];gold=[oracle(row) for row in raw]
    # All4520 raw inputs ×all8 branches, no canonical-output expansion.
    branches=np.array([[ys[lookup[moved(board,t)],list(t)] for t in ts] for board in raw])
    definitions={
        'mean-exact-sign':lambda v:sum(map(int,v))>=0,
        'intersection':lambda v:all(int(x)>=0 for x in v),
        'union':lambda v:any(int(x)>=0 for x in v),
        'vote-at-least-half':lambda v:sum(int(x)>=0 for x in v)>=4}
    equiv=0
    for row in rows:
        name=row['policy'];fn=definitions[name];members=np.array([[not raw[i,s] and fn(branches[i,:,s]) for s in range(9)] for i in range(4520)])
        assert np.array_equal(members,a[name+'_raw_members'])
        sets=[tuple(np.flatnonzero(x)) for x in members];assert metrics(sets,gold)==row['raw']
        assert int((members&~src['raw_optimal']).sum())==row['false_legal_members']
        assert int((~members&src['raw_optimal']).sum())==row['missing_optimal_members']
        chosen=np.array([next((s for s in PRIORITY if s in x),-1) for x in sets]);assert np.array_equal(chosen,a[name+'_raw_moves'])
        noneq=0
        for t in ts:
            transformed=np.array([lookup[moved(board,t)] for board in raw])
            assert np.array_equal(members[transformed][:,t],members);equiv+=4520
            movedchosen=np.array([t[s] if s>=0 else -1 for s in chosen]);noneq+=int((movedchosen!=chosen[transformed]).sum())
        assert noneq==row['chosen_not_transform_equivariant_observations'] and row['full_set_equivariance_failures']==0
        # No-op order / duplication controls independently use exact Python definitions.
        assert all(fn(branches[i,:,s])==fn(branches[i,::-1,s]) for i in range(4520) for s in range(9))
    ex=json.loads((d/'examples012.json').read_text());bl={tuple(board):i for i,board in enumerate(raw)}
    can_gold=[oracle(board) for board in b]
    for row in rows:
        name=row['policy'];pred=a[name+'_canonical_members'];assert metrics([tuple(np.flatnonzero(x)) for x in pred],can_gold)==row['canonical']
    bad=np.flatnonzero((a['mean-exact-sign_canonical_members']!=src['canonical_optimal']).any(1));assert ex[0]['canonical_id']==int(bad[0])
    wrong=[]
    for i,pred in enumerate(a['mean-exact-sign_canonical_members']):
        chosen=next((s for s in PRIORITY if pred[s]),-1)
        if chosen>=0 and chosen not in can_gold[i]:wrong.append(i)
    expected=[int(bad[0])]+([wrong[0]] if wrong and wrong[0]!=int(bad[0]) else [])
    assert [e['canonical_id'] for e in ex]==expected
    for e in ex:
        i=e['canonical_id'];j=bl[tuple(b[i])];v=branches[j]
        assert e['aligned_branch_logits']==v.tolist() and e['optimal_set']==list(can_gold[i])
        assert e['mean_numerator']==[sum(map(int,v[:,s])) for s in range(9)]
        assert e['minimum_logits']==[min(map(int,v[:,s])) for s in range(9)] and e['maximum_logits']==[max(map(int,v[:,s])) for s in range(9)]
        assert e['nonnegative_votes']==[sum(int(x)>=0 for x in v[:,s]) for s in range(9)]
        for name,fn in definitions.items():
            members=[s for s in range(9) if not b[i,s] and fn(v[:,s])];chosen=next((s for s in PRIORITY if s in members),-1)
            assert e['policies'][name]==dict(legal_set=members,chosen=chosen)
    result=dict(passed=True,independent_raw_boards=4520,raw_branch_observations=36160,policies=4,full_set_equivariance_board_transform_checks=equiv,independent_membership_scalars=4*4520*9,new_neural_calls=0,exact_unrounded_mean_sign=True,predeclared_examples=expected,source_logits_sha256=m['source_logits_sha256'])
    (d/'independent-audit012.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n');return result
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('directory');args=a.parse_args();print(json.dumps(audit(args.directory),indent=2))
