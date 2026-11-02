"""Off-contract fixed D4 output aggregation; no neural parameter edits."""
import numpy as np

def aggregate(x):
    x=np.asarray(x,dtype=np.int64)
    return {'mean-exact-sign':x.sum(0)>=0,'intersection':x.min(0)>=0,'union':x.max(0)>=0,'vote-at-least-half':2*(x>=0).sum(0)>=len(x)}

import argparse,datetime,hashlib,json
from pathlib import Path
from study1011_run import put,measure_sets,PRIORITY
from study009_run import pack_arrays
from study1011_draw import text,board,letters,save,BLUE,GREEN
from study009_render import Canvas
from falken9.symmetry import TRANSFORMS,transform_board,inverse
ROOT=Path(__file__).resolve().parent

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def preserve():
    fs=json.loads((ROOT/'preservation-before012.json').read_text())
    for n,h in fs.items():assert sha(ROOT/n)==h,n
    return len(fs)
def run(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False);preserve();m=json.loads((ROOT/'experiment-study012.json').read_text());source=ROOT/m['source_logits_path'];assert sha(source)==m['source_logits_sha256']
    from scripts.build_runtime import FOUR_MODEL
    assert sha(FOUR_MODEL)==m['source_model_sha256']
    a=np.load(source);x=a['aligned_logits'];b=a['canonical_boards'];raw=a['boards'];ci=a['raw_to_canonical_id'];tr=a['raw_to_canonical_transform'];gold=a['canonical_optimal'];rawgold=a['raw_optimal']
    assert x.shape==(8,627,9) and np.array_equal((x[0]>=0)&(b==0),gold)
    agg=aggregate(x);assert list(agg)==m['policies'];records=[];arrays=dict(canonical_boards=b,raw_boards=raw,canonical_optimal=gold,raw_optimal=rawgold,mean_numerator=x.sum(0),minimum_logits=x.min(0),maximum_logits=x.max(0),nonnegative_votes=(x>=0).sum(0));predictions={};canonical={}
    lookup={tuple(row):i for i,row in enumerate(raw)}
    movesgold=measure_sets(rawgold,rawgold)['chosen_moves'];rows=np.arange(4520)[:,None]
    for name,v in agg.items():
        assert np.array_equal(v,aggregate(x[::-1])[name]) and np.array_equal(v,aggregate(np.concatenate((x,x)))[name])
        members=v&(b==0);canonical[name]=members;pred=members[ci[:,None],tr];predictions[name]=pred
        cm=measure_sets(members,gold);cm.pop('chosen_moves');rm=measure_sets(pred,rawgold);moves=np.array(rm.pop('chosen_moves'));not_equiv=0
        for t in TRANSFORMS:
            ids=np.array([lookup[transform_board(row,t)] for row in raw]);assert np.array_equal(pred[ids][:,t],pred),(name,t)
            transformed_moves=np.array([t[s] if s>=0 else -1 for s in moves]);not_equiv+=int((moves[ids]!=transformed_moves).sum())
        fp=int((pred&~rawgold).sum());fn=int((~pred&rawgold).sum())
        if name=='intersection':assert fp==0
        if name=='union':assert fn==0
        record=dict(policy=name,canonical=cm,raw=rm,false_legal_members=fp,missing_optimal_members=fn,full_set_equivariance_observations=36160,full_set_equivariance_failures=0,chosen_not_transform_equivariant_observations=not_equiv,order_identity=True,duplication_identity=True)
        records.append(record);arrays[name+'_canonical_members']=members;arrays[name+'_raw_members']=pred;arrays[name+'_raw_moves']=moves
    meanbad=np.flatnonzero((canonical['mean-exact-sign']!=gold).any(1));example=int(meanbad[0]) if len(meanbad) else 0
    mm=measure_sets(canonical['mean-exact-sign'],gold);nonemptywrong=[]
    for i,s in enumerate(mm['chosen_moves']):
        if s>=0 and not gold[i,s]:nonemptywrong.append(i)
    ids=[example]+([nonemptywrong[0]] if nonemptywrong and nonemptywrong[0]!=example else [])
    examples=[]
    for i in ids:
        examples.append(dict(canonical_id=i,board=b[i].tolist(),legal_mask=(b[i]==0).tolist(),optimal_set=np.flatnonzero(gold[i]).tolist(),aligned_branch_logits=x[:,i].tolist(),mean_numerator=arrays['mean_numerator'][i].tolist(),minimum_logits=arrays['minimum_logits'][i].tolist(),maximum_logits=arrays['maximum_logits'][i].tolist(),nonnegative_votes=arrays['nonnegative_votes'][i].tolist(),policies={name:dict(legal_set=np.flatnonzero(v[i]).tolist(),chosen=measure_sets(v[i:i+1],gold[i:i+1])['chosen_moves'][0]) for name,v in canonical.items()}))
    put(out/'manifest012.json',m);put(out/'results012.json',records);put(out/'examples012.json',examples);pack_arrays(out/'measurements012.npz',arrays)
    put(out/'provenance012.json',dict(source_logits_sha256=sha(source),manifest_sha256=sha(ROOT/'experiment-study012.json'),prior_files_unchanged=preserve(),new_neural_forward_calls=0,independent_board_count=4520,source_orbit_observations=5016,policies=4,scope=m['independence']))
    render(out);report(out)
    print(json.dumps(records,indent=2))

def render(out):
    out=Path(out);rows=json.loads((out/'results012.json').read_text());examples=json.loads((out/'examples012.json').read_text());c=Canvas(1400,920)
    text(c,30,18,['Research012 | Exact symmetry does not guarantee correct moves'],31)
    text(c,30,77,['Fixed external D4 aggregation of the frozen network outputs; OFF-CONTRACT offline compute.'],22)
    text(c,30,145,['A  Every aggregate is perfectly full-set D4 equivariant on 36,160 raw-board/transform observations.'],22)
    text(c,30,203,['B  Complete sets on 4,520 unique raw boards'],26)
    labels={'mean-exact-sign':'Exact group mean','intersection':'Intersection (all8)','union':'Union (any1)','vote-at-least-half':'At least4 /8 votes'}
    for j,r in enumerate(rows):
        y=270+j*104;n=r['raw']['full_set_correct'];text(c,30,y,[labels[r['policy']]],23)
        c.rect(330,y,560*n/4520,33,BLUE,BLUE);text(c,920,y,[f"{n:,} /4,520 exact sets"],22)
        text(c,330,y+46,[f"empty {r['raw']['empty_sets']} | nonoptimal nonempty {r['raw']['nonoptimal_nonempty']} | optimal tie changes {r['raw']['optimal_tie_changes']}"],20)
    text(c,30,736,['C  Frozen canonicalizing wrapper: 4,520 /4,520 correct complete legal sets.',
        'Intersection cannot add false members; union cannot omit optimal members. Neither control proves exactness.',
        'Mean uses exact sum>=0; no rounding of a small negative mean to zero. Scores are NOT probabilities.',
        'These aggregations are fixed postprocessing, not learned symmetry or a deployed replacement.'],21,gap=37)
    m1=save(c,out,'overview012')
    e=examples[0];c=Canvas(1400,1060);text(c,30,18,[f"One actual counterexample | Canonical ID{e['canonical_id']} | Whole sets, fresh raw ties"],28)
    text(c,30,76,['Blue fill = correct member; red fill = false member; green border = complete optimal set.'],21)
    for j,r in enumerate(rows):
        name=r['policy'];x=25+j*346;text(c,x,130,[labels[name]],23)
        rec=e['policies'][name];board(c,x+35,180,e['board'],rec['legal_set'],e['optimal_set'],cell=75)
        text(c,x,430,[f"set {{{letters(rec['legal_set'])}}}",f"chosen {letters([rec['chosen']]) if rec['chosen']>=0 else 'EMPTY'}",f"truth {{{letters(e['optimal_set'])}}}"],21,gap=34)
    text(c,30,576,['D  Exact aligned aggregate evidence (mean displayed as numerator /8)'],25)
    text(c,30,626,['square       mean numerator      min score      max score      nonnegative votes /8'],20,mono=True)
    for s in range(9):
        text(c,30,670+s*31,[f"  {chr(97+s)}           {e['mean_numerator'][s]:>10}       {e['minimum_logits'][s]:>9}      {e['maximum_logits'][s]:>9}                 {e['nonnegative_votes'][s]}"],20,mono=True)
    text(c,30,986,['Source contains all eight branch logits and actual masks. Canonicalization still chooses the verified correct branch.'],20)
    m2=save(c,out,'case012');put(out/'figure-metadata012.json',dict(figures=[m1,m2],canonical_id=e['canonical_id'],callouts=list('ABCD'),exact_sum_sign=True,off_contract=True))

def report(out):
    out=Path(out);rows=json.loads((out/'results012.json').read_text());ex=json.loads((out/'examples012.json').read_text());m=json.loads((out/'manifest012.json').read_text())
    t=['# Research012 — an equivariant external policy can still be wrong\n\n','**New bounded follow-up after verified010/011:** test whether imposing exact D4 output symmetry by group aggregation replaces the correctness supplied by canonicalization. It does not. This is four frozen offline postprocessing policies, not training, a deployed replacement, or learned network equivariance.\n\n','[![Aggregate summary](overview012.png)](overview012.svg)\n\n','## Predeclared algorithms and source\n\n`manifest012.json` / root `experiment-study012.json` fixes all four policies before aggregate outcomes. All8 D4 elements are equally weighted, including stabilizer repetitions. The source is the immutable010 trace SHA-256 `'+m['source_logits_sha256']+'`. This reuses4,520 measured direct network inputs expanded to5,016 canonical-orbit observations; there are **zero new neural forwards**. All boards were already trained/audited.\n\n','* Mean: exact sum of eight aligned integer logits is nonnegative. This tests the exact rational mean sign **without rounding**; no tiny negative mean can become a zero member.\n* Intersection: all8 signs are nonnegative.\n* Union: at least1 sign is nonnegative.\n* Vote-at-least-half: at least4/8 signs are nonnegative; ties are included by preregistration.\n\nThe actual external legal mask and original raw-coordinate priority `ebdfhcgia` still apply. Nonnegative logits encode membership, not calibrated probabilities. Mean aggregation is a declared diagnostic algorithm, not a confidence average. It uses exact int64 host sums; no deployable accumulator/RAM/speed claim is made.\n\n','## Exact unique-raw outcomes\n\n|Policy|Exact full sets /4520|Empty sets|Nonoptimal nonempty|Chosen optimal|Different optimal ties|False legal members|Missing optimal members|\n|---|---:|---:|---:|---:|---:|---:|---:|\n']
    for r in rows:
        v=r['raw'];t.append(f"|{r['policy']}|{v['full_set_correct']}|{v['empty_sets']}|{v['nonoptimal_nonempty']}|{v['chosen_optimal']}|{v['optimal_tie_changes']}|{r['false_legal_members']}|{r['missing_optimal_members']}|\n")
    t.append('\nThe fixed canonicalizing wrapper remains4,520/4,520 exact sets and correct raw ties. Every aggregate above is **exactly full-set equivariant**, exhaustively checked on36,160 raw-board/transform observations per policy. Symmetry is therefore insufficient for the complete tactical-policy contract. Equivariance is enforced by external averaging/logic; it was not learned by the network.\n\n## Canonical counts are separate, not multiplied by8\n\n|Policy|Exact sets /627|Empty sets|Nonoptimal nonempty choices|Chosen optimal /627|\n|---|---:|---:|---:|---:|\n')
    for r in rows:
        v=r['canonical'];t.append(f"|{r['policy']}|{v['full_set_correct']}|{v['empty_sets']}|{v['nonoptimal_nonempty']}|{v['chosen_optimal']}|\n")
    t.append('\n## Exact constraints and controls\n\nThe eight branches include a canonicalized orientation with the correct full set. Consequently **intersection has no false legal members**, but can remove every valid member; **union omits no optimal members**, but can add nonoptimal members that the raw-coordinate tie later selects. Both theoretical constraints pass.\n\nOrder reversal and duplicating all8 branches to16 leave every policy unchanged (votes threshold scales to8/16). The single canonical branch recovers the baseline627 full sets. Independent audit recomputes each policy from all8 measured branches for **every4,520 raw input** instead of trusting canonical expansion, independently checks minimax/metrics and allD4 set equalities.\n\nChosen moves are freshly tied in actual raw coordinates. Transforming an old chosen move is not used as a substitute. The selected-move map itself need not be equivariant because fixed priority is coordinate dependent.\n\n|Policy|Non-equivariant chosen-move observations /36160 (not a full-set symmetry failure)|\n|---|---:|\n')
    for r in rows:t.append(f"|{r['policy']}|{r['chosen_not_transform_equivariant_observations']}|\n")
    t.append('\n## Actual predeclared example\n\n[![Measured board and scalar aggregates](case012.png)](case012.svg)\n\nFirst canonical ID with a mean full-set disagreement: **'+str(ex[0]['canonical_id'])+'**. All branch logits, legal masks, exact sum/min/max/vote values and four full sets are retained in `examples012.json`; the figure is not a synthetic illustration. The separately declared first nonoptimal nonempty mean-choice example is retained if it exists; no panel is expanded to hunt for failures.\n\n## Limits and stopping decision\n\nNo model bytes, stages, routes, gates or expert computations are changed. Original frozen source SHA-256 remains `fe180f8a931f9d92d8aa39da337bc819d0dbe4e6d971edcba00324fbc18a91c1`. Normally inactive expert observations remain unobserved in010/011; this study only consumes final measured logits. Neural stage restoration is not applicable because no neural parameter/stage is edited.\n\nThe result neither proves that every possible ensemble fails nor licenses a broader post-hoc ensemble search. It evaluates exactly the four declared policies on an already trained/audited domain. Their perfect imposed symmetry does not establish hidden-layer invariance, strategic component identities or new-domain generalization. It makes no target speed/RAM claim and does not run on or alter the accepted game.\n\nThis is the **one optional follow-up**. Stop here: no study013, larger aggregation panel, relaxed matching or retraining. See `FINAL-STUDY-012.json`, root verification/source bundle and `README-REPRODUCTION012.md`. Research010/011, all older evidence and accepted application010 remain untouched.\n')
    (out/'REPORT012.md').write_text(''.join(t))
    earlier=(ROOT/'artifacts/interpretability/study-010-011-walkthrough/ILLUSTRATED-SYNTHESIS1011.md').read_text()
    earlier=earlier.replace('(forward-attention1011.', '(../study-010-011-walkthrough/forward-attention1011.').replace('(forward-experts1011.', '(../study-010-011-walkthrough/forward-experts1011.')
    appended=['\n## 4. Does enforcing symmetry externally repair correctness?\n\n','[![Exact equivariance versus correctness](overview012.png)](overview012.svg)\n\n','Research012 is the one predeclared optional follow-up after010/011 verified. All four group aggregates are perfectly full-set D4 equivariant, but none satisfies the complete-set contract. Exactness is a property of what the set contains, not merely how it rotates.\n\n','|Fixed offline aggregation|Exact sets /4520|Empty|Nonoptimal nonempty|\n|---|---:|---:|---:|\n']
    for r in rows:appended.append(f"|{r['policy']}|{r['raw']['full_set_correct']}|{r['raw']['empty_sets']}|{r['raw']['nonoptimal_nonempty']}|\n")
    appended+=['\n[![Real group-aggregation counterexample](case012.png)](case012.svg)\n\n','A canonical branch is exactly correct, yet averaging in off-contract branches can change the full set. Intersection introduces no false members but can return nothing; union omits no optimal members but can add a nonoptimal square selected by raw tie priority. The first predeclared mean-error board is shown above; all eight branch logits are retained. These are fixed external algorithms, not trained strategies, calibrated-confidence averages or shipping changes. [Full012 report](REPORT012.md).\n\n','### Integration and stopping boundary\n\nThe two requested studies plus one justified bounded follow-up are complete. Original010/011 synthesis and all earlier files remain unchanged; this combined reader edition is new. No013 or post-hoc algorithm sweep follows. All eight new figure pairs are measured and use native clickable SVG; model/game remain frozen. See root handoff/verification/source bundles for independent checks and byte-identical reproductions.\n']
    (out/'SYNTHESIS010-012.md').write_text(earlier+''.join(appended))
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--out',required=True);args=a.parse_args();run(args.out)
