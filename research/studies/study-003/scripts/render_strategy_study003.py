#!/usr/bin/env python3
"""Study003 evidence-only reader report and deterministic PNG/SVG figures."""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from scripts.render_strategy_maps import Canvas,board,heading,INK,MUTED,DYNAMIC,GREEN,RED,EDGE
from scripts.model_strategy_study import sha,dump
ROOT=Path(__file__).resolve().parents[1]
TASKS=('has_win','must_block','has_fork','has_fork_prevention')


def cellset(values):return '{'+','.join(str(i+1) for i in values)+'}'


def members(logits,b):return [i for i in range(9) if not b[i] and logits[i]>=0]


def move(logits,b):
    return next((i for i in (4,1,3,5,7,2,6,8,0) if not b[i] and logits[i]>=0),-1)


def fmt(rate):return 'uncovered' if rate is None else f'{100*rate:.1f}%'


def render(study):
    root=Path(study);read=lambda f:json.loads((root/f).read_text())
    cs=read('cases.json');rs={r['id']:r for r in read('results.json')};vs={r['id']:r for r in read('experiment-vectors.json')}
    summary=read('summary.json');gate=read('baseline-gate.json');pairs=read('donor-pairs.json');interactions=read('pair-interactions.json');med=read('path-restoration.json');selection=read('training-selection.json')
    base=np.array([v['logits'] for v in cs]);contrast=summary['contrast'];assert contrast==[3,3], 'Renderer coordinate contract changed; update explicit callouts, not findings'
    # All example choices are deterministic selections from measured records.
    fork_id=next(v['id'] for v in cs if v['board']==[0,0,0,0,0,2,2,1,1])
    unaffected=next(v['id'] for v in cs if v['labels']['has_fork'] and v['hidden'][1] is not None and v['hidden'][1][0]!=0 and v['id'] not in rs['dose-E1.h0-0of4']['nonoptimal_canonical_ids'] and v['id']!=fork_id)
    block_id=next(v['receiver'] for v in pairs if v['id']=='E3.h3-must_block-same-R268-D320')
    win_damage=next(i for i in rs['dose-E3.h3-0of4']['nonoptimal_canonical_ids'] if cs[i]['labels']['has_win'])
    callouts={
        'A':dict(activation_coordinate=['expert_hidden',1,0],incoming_tensor_slice='expert_w1[1,:,0]',outgoing_tensor_slice='expert_w2[1,0,:]',examples=[fork_id,unaffected],intervention='dose-E1.h0-0of4'),
        'B':dict(activation_coordinate=['expert_hidden',3,3],incoming_tensor_slice='expert_w1[3,:,3]',outgoing_tensor_slice='expert_w2[3,3,:]',examples=[block_id,win_damage],intervention='dose-E3.h3-0of4'),
        'C':dict(activation_coordinate=['norm2_output',summary['upstream_unit']],intervention=f"upstream-norm2-{summary['upstream_unit']}-half"),
        'P':dict(activation_coordinate=['expert_hidden',3,3],pair_id='E3.h3-must_block-same-R268-D320',intervention='patch-E3.h3-must_block-same'),
        'M+':dict(activation_coordinate=['expert_hidden',1,0],canonical_id=med[0]['rescued_ids'][0],intervention='restore-E1h0'),
        'M-':dict(activation_coordinate=['expert_hidden',1,0],canonical_id=next(i for i in med[0]['introduced_ids'] if cs[i]['fold']=='test'),intervention='restore-E1h0')}
    figures=[]
    c=Canvas(1480,1050)
    heading(c,'Study003 / necessity is contextual, not an expert job title','Frozen integer activations after GELU. A = E1.h0; B = E3.h3 (training-selected contrast). All indices zero-based in metadata.')
    c.rect(28,102,720,355);c.text(46,120,'Dose response / whole finite domain',22)
    c.text(46,155,'Remaining hidden activation',16,MUTED);c.text(350,155,'A bad moves',16,DYNAMIC);c.text(535,155,'B bad moves',16,DYNAMIC)
    for row,n in enumerate([4,3,2,1,0]):
        y=192+row*40;c.text(46,y,f'{n}/4 after integer rounding',17)
        for component,x in [('E1.h0',350),('E3.h3',535)]:
            r=rs[f'dose-{component}-{n}of4'];c.text(x,y,f"{r['raw']['nonoptimal_including_empty']}/4520 raw",17)
            c.text(x,y+21,f"{r['canonical']['nonoptimal_including_empty']}/627 canonical",12,MUTED)
    c.paragraph(46,411,'Bad = empty legal set OR selected move outside the offline optimal set. Raw symmetry copies are descriptive expansion, not independent evidence.',678,14)
    c.rect(772,102,680,355);c.text(790,120,'Selectivity check / exact geometry + route strata',21)
    y=163
    for component,task in [('E1.h0','has_fork'),('E3.h3','must_block')]:
        z=rs[f'dose-{component}-0of4']['classes'][task]['all']
        c.text(790,y,f"{component} / {task}",18,DYNAMIC)
        c.text(790,y+30,f"Matched target {z['matched_target_errors']}/{z['matched_target_n']} vs non-target {fmt(z['matched_negative_error_rate'])}",17)
        c.text(790,y+58,f"Unique non-targets {z['matched_negative_unique_n']}; target-weighted control rate",14,MUTED)
        y+=100
    c.paragraph(790,367,'B is more damaging overall, with mostly empty sets. Its test must-block comparison has NO matched non-target coverage. Neither observation identifies a dedicated strategy component.',626,15)
    examples=[('A+',fork_id,'E1.h0','Fork example / fails'),('A-',unaffected,'E1.h0','Fork counterexample / survives'),('B+',block_id,'E3.h3','Must-block example / fails'),('B-',win_damage,'E3.h3','Non-block counterexample / win fails')]
    for j,(label,i,component,title) in enumerate(examples):
        x=28+j*362;c.rect(x,481,338,468);c.paragraph(x+15,497,label+'  '+title,306,16,DYNAMIC)
        case=cs[i];exp=vs[f'dose-{component}-0of4'];after=exp['logits'][i];bm=move(base[i],case['board']);am=move(after,case['board'])
        board(c,x+88,548,case['board'],cell=51,move=bm,after=am)
        e,u=map(int,[component[1],component[-1]])
        c.text(x+15,714,f"Canonical {i} / {case['fold']}",16)
        c.text(x+15,744,f"h={case['hidden'][e][u]} -> 0; gates {case['gates']}",14,MUTED)
        c.text(x+15,774,'Base set '+cellset(members(base[i],case['board'])),16,GREEN)
        c.text(x+15,805,'Zero set '+cellset(members(after,case['board'])),16,RED if am not in case['optimal_set'] else GREEN)
        delta=int(after[bm])-int(base[i,bm]);c.text(x+15,839,f'Baseline-move logit change {delta:+d}',14)
        c.paragraph(x+15,873,'Logit difference is the whole-model lesion effect, NOT an additive unit contribution.',306,13)
    c.paragraph(28,976,'Board squares are human-facing 1..9. Green outline = baseline choice; red outline = changed choice if present. Empty set has no red move. Activations/gates are computed; stored weights never change.',1410,15)
    figures.append(c.save(root,'necessity-context'))
    # Donor patch and path restoration, with counterexamples adjacent.
    c=Canvas(1480,1100)
    heading(c,'Study003 / natural patches and bounded path restoration','Measured scalar replacements in canonical input frames; receiver gates retained. Same-class donors are not automatically safe.')
    pair=next(p for p in pairs if p['id']==callouts['P']['pair_id']);donor=cs[pair['donor']];receiver=cs[pair['receiver']]
    c.rect(28,105,1424,415);c.text(46,124,'P / E3.h3 natural same-class patch',23,DYNAMIC)
    for case,x,title in [(donor,62,'Training donor'),(receiver,307,'Test receiver')]:
        c.text(x,166,title+f" #{case['id']}",17);board(c,x+15,205,case['board'],cell=51)
        c.text(x,373,f"E3.h3 = {case['hidden'][3][3]}",17)
        c.text(x,402,f"must_block = {case['labels']['must_block']}",14,MUTED)
    c.line(247,278,310,278,DYNAMIC,2,True)
    x=580;c.text(x,169,f"Same geometry counts, side, ply and ordered routes {receiver['routes']}",17)
    c.text(x,202,f"Hamming distance {pair['hamming']}; gate delta {pair['gate_delta']}/32768",17,MUTED)
    patched=vs['patch-E3.h3-must_block-same']['logits'][receiver['id']]
    c.text(x,237,'Receiver base set '+cellset(members(receiver['logits'],receiver['board']))+' -> patched '+cellset(members(patched,receiver['board'])),19,RED)
    c.text(x,279,'Same-class target failures 2/3; cross-class 3/12',19)
    c.text(x,313,'Matched unit E3.h0: same 1/3; cross 2/12',17,MUTED)
    c.paragraph(x,350,'These donor pools are small and differ. No semantic-transfer effect is established: same-class donors also harm, cross-class donors often do not. Activation magnitude/context, not task membership alone, matters.',823,17)
    c.paragraph(46,461,'E1.h0 fork patches: NO positive same-class receivers; cross-class reaches only 2 fork-positive test boards and causes 0 bad moves. That is a coverage failure, not evidence for/against a fork circuit.',1378,16)
    upstream=vs[callouts['C']['intervention']]
    for j,label in enumerate(['M+','M-']):
        i=callouts[label]['canonical_id'];case=cs[i];x=28+j*720;c.rect(x,546,704,360)
        c.text(x+16,564,f"{label} / restore A under C / board {i} ({case['fold']})",21,DYNAMIC)
        ub=upstream['logits'][i];rest=vs['restore-E1h0']['logits'][i]
        board(c,x+24,611,case['board'],cell=49,move=move(ub,case['board']),after=move(rest,case['board']))
        c.text(x+194,613,'Upstream set '+cellset(members(ub,case['board'])),17)
        c.text(x+194,645,'Restore set '+cellset(members(rest,case['board'])),17,GREEN if label=='M+' else RED)
        c.text(x+194,677,'Optimal set '+cellset(case['optimal_set']),17,MUTED)
        uph=upstream['hidden'][i][1][0];c.text(x+194,711,f"E1.h0: {uph} -> {case['hidden'][1][0]}",17)
        c.paragraph(x+194,748,'Restoration retains the upstream-lesioned route/gates; this is not a natural indirect-effect estimate.',480,15)
        c.paragraph(x+16,830,'Green outline = upstream choice; red = restored choice. Empty-set choices have no outline.',666,13)
    c.paragraph(28,934,f"C = norm2_output[{summary['upstream_unit']}] half: {rs[callouts['C']['intervention']]['route_changes']} ordered-route changes and {rs[callouts['C']['intervention']]['gate_changes']} gate-vector changes /627. A restoration rescues 2/50 covered upstream failures but creates 2 new failures; net 0 canonical benefit.",1410,18)
    c.paragraph(28,1010,'M+ is a training example, M- a test counterexample. Local E1.h0+E1.h1 joint zero rescues 8 single-lesion failures: non-monotone damage/cancellation, not a dedicated two-unit strategy circuit.',1410,17)
    figures.append(c.save(root,'patch-and-restoration'))
    metadata=dict(model_sha256=gate['model_sha256'],weights_are_unchanged=True,coordinate_convention='zero-based expert/unit/tensor; human board squares one-based',callouts=callouts,figures=figures,renderer_sha256=sha(__file__),input_sha256={name:sha(root/name) for name in ['cases.json','results.json','experiment-vectors.json','donor-pairs.json','path-restoration.json','pair-interactions.json']})
    dump(root/'figure-metadata.json',metadata)
    # Compact machine-readable table: all units/doses, all classes/folds, exact denominators.
    table=[]
    for r in rs.values():
        for task in TASKS:
            for fold,z in r['classes'][task].items():
                table.append(dict(experiment=r['id'],task=task,fold=fold,**{'canonical_'+k:v for k,v in z['canonical'].items()},**{'raw_'+k:v for k,v in z['raw'].items()},**{k:v for k,v in z.items() if k.startswith('matched_') and not k.endswith('_ids')}))
    with (root/'effect-table.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(table[0]));w.writeheader();w.writerows(table)
    report=[]
    def line(s=''):report.append(s)
    line('# Frozen-model interpretability / study003')
    line('## Outcome')
    line('**New causal evidence is contextual necessity, donor non-interchangeability, and cancellation—not a strategy neuron or a named expert circuit.** All predeclared negative and unfavorable results are retained. No model was trained, game changed, package built, or release modified.')
    line('## Reference and scope')
    line(f"Verified all {gate['evidence_hashes_verified']} snapshot evidence hashes and **{gate['all_stage_vectors_checked']} saved stage vectors across 627 canonical boards** (including logits/routes/gates). Composed host full-set inverse/legal-mask/original-tie outcomes pass on **4520 raw boards**, with zero set/move/tie mismatches. This is comparison to copied actual627 target evidence, not a new 6502 execution.")
    line(f"Packet SHA256 `{gate['model_sha256']}`. Snapshot `{read('provenance.json')['snapshot']['snapshot_commit']}` is a materialized archive, **not a Git working tree**. All imports resolve within the isolated study root. Prior study002 and all 69 copied evidence files remain hash-identical.")
    line('The fixed `experiment-manifest.json` was written before any new intervention/held-out evaluation. Selection executed training rows only: all 16 single-zero lesions, then at most 15 contrast candidates excluding E1.h0; 8 upstream lanes; 3 predeclared pairs/groups and 4 donor components. No tuning or expanded search after confirmation. **128 interventions** comprise 80 single-dose, 12 group-dose, 32 donor and 4 upstream/restoration runs; identity control is additional.')
    line('Folds group canonical symmetry classes: train372/validation121/test134 (seed1729). These are exploratory selection/confirmation folds only: the frozen model had already fitted/audited this finite domain, and study002 already probed it. Raw copies are not independent observations; no confidence interval or significance claim uses 4520 as independent N. Test-only fork support is six canonical boards; classes overlap. Minimax labels audit outputs offline; it is absent from neural inference.')
    line('| Board label | Canonical train / validation / test | Raw whole domain |')
    line('|---|---:|---:|')
    for task in TASKS:line(f"| {task} | {' / '.join(str(summary['class_counts'][task][f]) for f in ('train','validation','test'))} | {summary['raw_class_counts'][task]} |")
    line('Winning/must-block/fork labels describe availability with the stated priority exclusions, not an expert objective. Fork prevention is bounded: no immediate win/threat, opponent fork available, and candidate leaves no fork after each viable one-ply opponent reply. It is not a complete long-horizon prevention theorem.')
    line('## Supported: dose-dependent effects, not exclusivity')
    line('A=`expert_hidden[1,0]` after GELU; B=`expert_hidden[3,3]`, the training-selected contrast maximizing must-block minus fork move-error rate. Lesions scale only routed observations with the original integer `round_div(h*n,4)`. Unrouted cells are **null/unobserved**, never activation zero. Doses and natural patches are post-routing and changed **zero routes/gates**. Upstream changes are reported separately below.')
    line('| Remaining activation | A bad moves raw / canonical | B bad moves raw / canonical |')
    line('|---|---:|---:|')
    for n in (4,3,2,1,0):
        vals=[rs[f'dose-{comp}-{n}of4'] for comp in ('E1.h0','E3.h3')]
        line(f"| {n}/4 | "+' | '.join(f"{r['raw']['nonoptimal_including_empty']}/4520 ; {r['canonical']['nonoptimal_including_empty']}/627" for r in vals)+' |')
    line('“Bad” includes empty legal sets; sets use legal logits >=0, then inverse-map the **complete** set before original-coordinate ties. A canonical chosen-move error need not expand uniformly because tie order is original-coordinate; raw outcomes are re-evaluated, not multiplied by eight.')
    line('| Zero lesion | Empty / nonoptimal nonempty / set changes / optimal tie changes (raw) | Same (canonical) |')
    line('|---|---:|---:|')
    for comp in ('E1.h0','E3.h3'):
        r=rs[f'dose-{comp}-0of4'];keys=('empty_set','nonoptimal_nonempty','complete_set_change','equivalent_optimal_tie_change')
        line(f'| {comp} | '+ ' | '.join(' / '.join(str(r[k][v]) for v in keys) for k in ('raw','canonical'))+' |')
    line('Set/tie categories intentionally overlap: a changed set can retain an optimal chosen move, and a different chosen optimal move is not a failure. `optimal_move_set_changed` in machine results separates set changes retaining optimal behavior.')
    line('### Target effects versus covered matched non-target damage')
    line('Matching is exact on ply, side, own/opponent corner/edge counts, center ownership and **ordered expert routes**, with max slot-gate difference <=4096/32768. It is not exact squarewise occupancy; that would identify the board and prevent donor contrasts. Rates below are canonical; non-target rates average matched negatives per covered positive, not pooled independent samples. All rows restrict to routed component observations. All-domain comparisons are descriptive, not held-out confirmation.')
    line('| Component / target | Target bad / all routed target N | Matched target bad / covered N | Unique matched negatives | Weighted negative error |')
    line('|---|---:|---:|---:|---:|')
    for comp in ('E1.h0','E3.h3'):
        for task in TASKS:
            z=rs[f'dose-{comp}-0of4']['classes'][task]['all'];v=z['canonical']
            line(f"| {comp} / {task} | {v['nonoptimal_including_empty']}/{v['n']} | {z['matched_target_errors']}/{z['matched_target_n']} | {z['matched_negative_unique_n']} | {fmt(z['matched_negative_error_rate'])} |")
    line('B shows a descriptive must-block excess versus covered negatives, but most of its whole-domain failures are empty-set damage and it also breaks immediate wins. Confirmation is weak: B must-block validation5/13 routed targets (matched1/2 versus 0% across2 negatives), test1/10 (**no matched test negatives**). B fork validation0/3 and test0/1 are too small to establish selectivity. A fork validation0/1 and test1/4 routed targets, with **no matched target coverage in either fold**, do not establish a fork-specific component. A whole-domain fork matched positives0/7 versus9.5% controls is unfavorable to that interpretation.')
    line(f"Concrete necessity example A: canonical{fork_id}, board `{cs[fork_id]['board']}`, h=25125; zero loses its winning fork. Counterexample canonical{unaffected}, board `{cs[unaffected]['board']}`, has a fork with routed A but remains optimal after zero. B block example canonical{block_id} fails; non-block immediate-win example canonical{win_damage} also fails. Full cases and further target-unaffected/non-target-failure examples are in `counterexamples.json`.")
    line('## Natural donor patches: limited coverage, no semantic transfer finding')
    line(f"Across all four components/tasks/class directions: {summary['donor_pairs']} pair records, {summary['unique_donors']} unique training donors, {summary['unique_receivers']} unique held-out receivers. These totals contain reuse across tasks/components and are **not independent samples**. No relaxation was added when matching failed. Donors minimize canonical occupancy Hamming distance, then gate distance, then canonical index. Gate tolerance does not claim exact gating; receiver gates remain unchanged.")
    line('Both boards are fed in their **own canonical input frame**. Patches align the same expert ID and hidden-unit coordinate, not board squares and not route slot numbers. No hidden-unit rotation-equivariance is assumed; raw-to-canonical permutations are saved in `raw-alignment.json`. Donor indexing, receiver indexing and inactive rejection are independently tested.')
    line('| Component / donor task | Same-class covered receiver / target / target bad | Cross-class covered receiver / target / target bad |')
    line('|---|---:|---:|')
    for comp in ('E1.h0','E1.h1','E3.h3','E3.h0'):
        for task in TASKS:
            vals=[]
            for direction in ('same','cross'):
                r=rs[f'patch-{comp}-{task}-{direction}'];v=r['classes'][task]['all']['canonical'];vals.append(f"{r['covered_canonical']['n']} / {v['n']} / {v['nonoptimal_including_empty']}")
            line(f'| {comp} / {task} | '+' | '.join(vals)+' |')
    line('E1.h0 fork same-class has **zero positive receiver coverage**, despite48 covered negative receivers; cross-class covers only2 positive test boards, with0 failures. Do not interpret this as necessity/rescue evidence. For B must-block, same-class causes2/3 positive failures and cross-class3/12; matched E3.h0 causes1/3 and2/12. The donor pools differ, so this is not a balanced class-direction effect. No win/block/fork/prevention feature transplantation is established.')
    line('A concrete positive result is **contextual non-interchangeability**: donor320 to receiver268, E3.h3 3483->123, same must-block class, same ply/side/geometry counts/routes, gate delta0, Hamming4, removes the receiver legal set. It is not universal: same-class donor491 to receiver145 changes B -277->579 yet retains an optimal chosen move (gate delta35, Hamming4); cross-class B must-block has9/12 positive receivers remaining optimal. Identity patches preserve **every saved stage/logit/route** on all627. Full donor IDs, activation values, class/fold/coverage and distances are in `donor-pairs.json`; experiment metrics retain matched non-target comparisons, empty sets, set and tie changes.')
    line('## Pair interaction and path restoration: retain the negative results')
    line('| Pair zero | Single-failure union | Pair failures | New beyond union | Single failures rescued | Max absolute logit nonadditivity |')
    line('|---|---:|---:|---:|---:|---:|')
    for r in interactions:
        line('| '+' + '.join(f'E{e}.h{u}' for e,u in r['components'])+f" | {len(r['union_single_failure_ids'])} | {len(r['pair_failure_ids'])} | {len(r['new_beyond_union_ids'])} | {len(r['rescued_union_ids'])} | {r['logit_nonadditivity_abs_max']} |")
    line('These are canonical whole-domain counts. E1+E3 are co-routed on only14/627 canonical boards; most combined damage occurs on disjoint routed populations. Only one new failure beyond the single-failure union appears for A+B: canonical3 (test), a bounded-prevention board. The local A+E1.h1 pair instead **rescues8** union failures and adds none, including test canonical553 where h0 alone retains the optimal canonical chosen move (but changes its complete set) while h1 alone fails; this cancellation is a counterexample to a simple additive necessity story. Small logit nonadditivity (max27) is compatible with downstream integer rounding/clamps; this experiment does not identify its arithmetic source. Sign/tie thresholding can create behavioral interactions without a special nonlinear circuit.')
    up_id=callouts['C']['intervention'];ur=rs[up_id]
    line(f"Training activation-only selection chose C=`norm2_output[{summary['upstream_unit']}]` half. It causes {ur['canonical']['nonoptimal_including_empty']}/627 canonical and {ur['raw']['nonoptimal_including_empty']}/4520 raw bad moves, **{ur['route_changes']} ordered-route changes ({ur['route_membership_changes']} expert-membership changes)** and {ur['gate_changes']} gate-vector changes. This is an **upstream router-affecting** perturbation, not a pure expert lesion. Restorations retain that altered route/gate state; only baseline/upstream jointly observed experts are patched.")
    line('| Restore under C | Covered canonical N | Covered upstream bad | Rescued chosen moves | Newly bad |')
    line('|---|---:|---:|---:|---:|')
    for r in med:line(f"| {r['id']} | {len(r['coverage_ids'])} | {r['covered_upstream_failures']} | {len(r['rescued_ids'])} | {len(r['introduced_ids'])} |")
    line('A restores2/50 covered upstream failures but introduces2 new failures: **net zero canonical benefit**. The rescued cases137/414 are both training examples; introduced296 is training and553 is test. Contrast B restores2 but introduces7; joint restoration on14 co-observed cases rescues0/2 upstream failures. This does not identify C->A->fork mediation. M+ board137 demonstrates a real local restoration; M- board553 is its counterexample, newly damaged by restoring A. “Restoration” here is a path intervention, not an identified natural indirect effect; shared upstream damage/rerouting confounds a circuit story.')
    line('## Unsupported')
    line('- Dedicated fork, win, block or prevention neuron; exclusive expert strategy job titles; board-orientation-equivariant hidden semantics.')
    line('- Reliable same-class/cross-class strategy transfer; fork donor coverage was inadequate and matched controls can be equally or more damaging.')
    line('- A selective two-unit strategy circuit or a useful mediated rescue from C. Small per-fold classes and empty-set damage narrow the conclusions.')
    line('- Model-held-out/OOD generalization, independent symmetry samples, native-target performance changes or gameplay improvements.')
    line('## Artifacts and reproduction')
    line('Figures: `necessity-context.{png,svg}` and `patch-and-restoration.{png,svg}`. `figure-metadata.json` binds A/B/C/P/M+/M- to exact activation/tensor coordinates and case IDs, source hashes and measured inputs. No metaphorical activations or stored-weight changes are shown. Logit differences are exact whole-model intervention effects, not asserted additive contributions.')
    line('Machine evidence: `baseline-gate.json`, fixed `experiment-manifest.json`, `training-selection.json`, `cases.json`, `raw-alignment.json`, `results.json`, `experiment-vectors.json` (full logits/routes/gates/norm2/observed hidden), `effect-table.csv`, `donor-pairs.json`, `pair-interactions.json`, `path-restoration.json`, `identity-controls.json`, `counterexamples.json`, `provenance.json`, `hashes.json`. `results.json` retains all units/doses/groups, class/fold raw+canonical denominators and covered matched-control rates/IDs; table is a flat view, not a second experiment.')
    line('Run from `/home/ai/falken9-strategy-study-003`; use a **fresh nonexistent** output directory:')
    line('```sh')
    line('export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1')
    line('export PYTHONPATH=/home/ai/falken9-strategy-study-003')
    line('/home/ai/falken-9/.venv/bin/python scripts/model_strategy_study003.py --output artifacts/interpretability/study-003-reproduction-new')
    line('/home/ai/falken-9/.venv/bin/python scripts/render_strategy_study003.py --study artifacts/interpretability/study-003-reproduction-new')
    line('```')
    line('Validation and exact fresh-run comparisons are recorded separately in `verification-study003.json` at the study workspace root. Broader legacy integer tests requiring uncopied FP/training artifacts cannot pass in this bounded evidence snapshot; no packages or external data were fetched to conceal that limitation.')
    (root/'REPORT.md').write_text('\n\n'.join(report).replace('|\n\n|','|\n|')+'\n')
    # Renderer/test hashes are part of independent reproducible metadata.
    dump(root/'render-provenance.json',dict(renderer_sha256=sha(__file__),canvas_sha256=sha(ROOT/'scripts/render_strategy_maps.py'),artifact_tests_sha256=sha(ROOT/'tests/test_strategy_study003_artifacts.py')))
    dump(root/'hashes.json',{p.name:sha(p) for p in sorted(root.iterdir()) if p.is_file() and p.name!='hashes.json'})
    return metadata


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--study',required=True)
    render(parser.parse_args().study)
