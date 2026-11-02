"""Deterministic evidence figures; Pillow+SVG, no matplotlib/install."""
from pathlib import Path
import json,hashlib
from scripts.render_strategy_maps import Canvas,INK,MUTED,DYNAMIC,GREEN,RED,EDGE,BG

def read(out,n):return json.loads((Path(out)/n).read_text())
def board(c,x,y,b,selected=()):
    for k,v in enumerate(b):
        xx=x+(k%3)*48;yy=y+(k//3)*48;c.rect(xx,yy,48,48,BG,GREEN if k in selected else EDGE,3 if k in selected else 1);c.text(xx+15,yy+8,'.XO'[v],25)
    c.text(x,y+153,'0..8 row-major; X=1 O=2',13,MUTED)
def lines(c,x,y,ss,width=1100,size=18):
    for text in ss:y=c.paragraph(x,y,text,width,size)+12
    return y

def render(stage,out):
    out=Path(out);s=read(out,'summary.json');examples=read(out,'examples.json');b=read(out,'baseline.json');figs=[]
    c=Canvas(1580,1000);c.text(28,22,f'Study{stage} / frozen-model measured evidence',28)
    c.text(28,65,'627 canonical /4520 raw boards; host integer counterfactuals, not new target benchmarks or model-heldout tests.',17,MUTED)
    if stage=='006':
        rows=read(out,'interventions.json');c.text(30,113,'A / same-board pair membership and gating',22,DYNAMIC)
        c.text(30,151,'Bars = canonical wrong or empty chosen moves /627. Complete sets counted separately in JSON/report.',17,MUTED)
        rr=[r for r in rows if r['id'].endswith('renormalized') and r['id'].startswith('pair-')]+[r for r in rows if r['id'] in ('actual','actual-uniform','reverse-pair-only')]
        for j,r in enumerate(rr):
            y=202+j*55;n=r['canonical']['move_errors'];c.text(30,y,r['id'],17);c.rect(370,y,850*n/627,23,RED,RED);c.text(390+850*n/627,y,str(n),17)
        lines(c,30,735,[f"B / All six renormalized pairs preserve full sets on {s['all_pairs_zero_loss_boards']}/627 boards; at least one pair does so on {s['best_pair_zero_loss_boards']}/627.",f"Training-only fixed pair: {s['training_selected_fixed_pair']['pair']}. Offline all-expert evaluation:2508 outputs vs1254 normally executed; additional1254 are not deployed compute.",'Pair+gate reversal is exact; reversing only the pair changes expert-to-gate assignment. Alternative pairs are not proposed trained policies.'],1500,18)
    elif stage=='007':
        c.text(30,113,f"A / post-route output-vector scope: candidate expert{s['selected_expert']}, control expert{s['control_expert']}",22,DYNAMIC)
        lines(c,30,160,['Recipient readout residual + recipient router/gates + selected expert outputs -> rounded mixture -> frozen output head. Only declared expert output vectors are transplanted/zeroed. Other learned computation remains.','Natural contrasts: one legal mark relocation, same raw candidate/ply/geometry/fold; candidate active both; gate difference <=4096/32768. Route-fixed and naturally route-changing contrasts are separate.'],1500,19)
        y=345
        for name,v in s['contracts'].items():
            c.rect(28,y,1520,112);c.text(46,y+12,name+f" / {v['directions']} directed trials",21,DYNAMIC)
            c.text(46,y+48,f"Natural restoration rescues {v['rescue_natural']}; new damage {v['new_damage_natural']}; zero-background rescues {v['rescue_zero']}",18)
            c.text(46,y+78,f"Candidate preserved, other selected path zeroed: {v['outcomes']['zero-noncandidate']['empty']} empty / {v['outcomes']['zero-noncandidate']['nonoptimal_nonempty']} nonoptimal nonempty",17)
            y+=125
        lines(c,30,865,[f"B / {s['matched_pairs']} matched pairs; {s['identity_exact']} exact identity controls; {s['restoration_equalities_exact']} exact restoration equalities.",'Local rescue/preservation does not establish whole-circuit sufficiency or natural mediation. Shared donor paths only; absent donor experts stay unavailable, not measured zero.'],1500,17)
    else:
        c.text(30,113,'A / exact membership boundary, not a categorical score margin',22,DYNAMIC)
        lines(c,30,160,[f"Legal scores: {s['legal_score_count']}; exact zeros: {s['legal_zero_count']}. Negative -1 ->0 enters; nonnegative0 ->-1 leaves. Occupied-square sign changes are removed by fixed legal masking.",f"{s['executed_interventions']}/{s['attempted_interventions']} valid +/-1 stored-code interventions, one coordinate at a time. {s['all_stage_restorations_exact']} original-code restorations reproduce every baseline stage.",f"Boards with any complete-set change {s['boards_any_set_change']}/627; chosen-move failure {s['boards_any_move_failure']}/627; robust to every tested code {s['boards_robust_all_codes']}/627."],1500,20)
        c.text(30,430,'B / failure-prone coordinates (bounded predeclared38-coordinate panel)',22,DYNAMIC)
        for j,r in enumerate(s['worst']):
            y=485+j*67;c.text(30,y,r['id'],17);n=r['canonical']['move_errors'];c.rect(530,y,800*n/627,24,RED,RED);c.text(550+800*n/627,y,str(n)+'/627 wrong/empty',16)
        lines(c,30,865,['These are local stored-code perturbations, not a reduced-precision packet conversion. No claim that the most fragile parameter represents a human strategy. Descriptors, exponents and original model bytes unchanged.'],1500,18)
    figs.append(c.save(out,f'overview{stage}'))
    # Actual boards and numeric path/gate/code evidence with stable callouts.
    c=Canvas(1580,1130);c.text(28,22,f'Study{stage} / actual cases, controls and counterexamples',27)
    c.text(28,65,'A-C callouts refer to exact evidence records; green outline = baseline full optimal set, not score ranking.',17,MUTED)
    show=examples[:3] if stage=='007' else examples[:2]
    panelh=290 if len(show)==3 else 420
    for j,ex in enumerate(show):
        y=110+j*(panelh+22);c.rect(25,y,1530,panelh);c.text(44,y+14,f"{chr(65+j)} / {ex['callout']}",22,DYNAMIC)
        if stage=='006':
            i=ex['id'];board(c,48,y+65,ex['board'],ex['actual_set']);ss=[f"Canonical ID{i}; fold{ex['fold']}; actual pair{ex['actual_pair']}, Q15 gates{ex['actual_gates']}",f"Actual >=0 legal set {ex['actual_set']}; actual logits{ex['actual_logits']}"]+[f"Alternative pair{p['pair']}: full set{p['set']}; chosen move{p['move']}" for p in ex['pairs']]
            lines(c,240,y+65,ss,1270,17)
        elif stage=='007':
            r=ex['record'];board(c,48,y+65,r['receiver_board']);board(c,230,y+65,r['donor_board']);ss=[f"IDs {r['receiver']} <- {r['donor']}; {r['task']} fold{r['fold']} / {r['contract']}",f"Routes {r['receiver_routes']} / {r['donor_routes']}; gates {r['receiver_gates']} / {r['donor_gates']}",f"Expert{r['expert']} actual output prefix {r['receiver_expert_output'][:5]} -> donor {r['donor_expert_output'][:5]}",f"Natural all-shared set {r['outcomes']['all-shared-natural']['set']}; restore set {r['outcomes']['restore-candidate']['set']}",f"Zero-all set {r['outcomes']['zero-all-selected']['set']}; candidate restored {r['outcomes']['restore-from-zero']['set']}",f"Raw donor->canonical transform {r['raw_alignment']['donor_raw_to_canonical']}; unavailable {r['unavailable_nonshared_experts']}"]
            lines(c,425,y+58,ss,1090,16)
        else:
            i=ex['id'];r=ex['perturbation'];board(c,48,y+65,ex['board'],ex['baseline_set']);ss=[f"Canonical ID{i}; fold{ex['fold']}; route{ex['routes']}; Q15 gates{ex['gates']}",f"Baseline set {ex['baseline_set']}; min integer score change to boundary {ex['minimum_score_change']}",f"Across76 tested codes: {ex['set_change_interventions']} set changes, {ex['move_failure_interventions']} chosen-move failures",f"Coordinate {r['tensor']}{r['coordinate']}; stored code{r['old_code']} ->{r['new_code']} ({r['bits']} bits), byte offset{r['byte_offset']}",f"Baseline logits {ex['baseline_logits']}",f"Perturbed logits {ex['perturbed_logits']}; legal set{ex['perturbed_set']}",'Robust case is robust only to this finite panel, not all possible parameter changes.']
            lines(c,240,y+65,ss,1270,18)
    c.text(28,1084,'All output sets are full nonnegative legal membership. Raw inverse transforms and fixed ties are non-neural; no strategy names inferred.',16,MUTED)
    figs.append(c.save(out,f'cases{stage}'))
    (out/'figure-metadata.json').write_text(json.dumps(dict(figures=figs,callouts=[dict(letter=chr(65+j),evidence=ex) for j,ex in enumerate(show)],renderer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),sort_keys=True,separators=(',',':'))+'\n')

def report(stage,out):
    out=Path(out);s=read(out,'summary.json');title={'006':'Router usefulness: membership, order and gates','007':'Bounded pathway preservation and local rescue','008':'Exact integer decision-fragility'}[stage]
    text=f'# Study{stage} — {title}\n\nFrozen5195-byte packet SHA-256 `fe180f8a931f9d92d8aa39da337bc819d0dbe4e6d971edcba00324fbc18a91c1`. Host-only analysis. No deployed model/game changes.\n\n## Gates and interpretation\nExact replay:627 actual-target fixtures,13167 complete stage vectors,5643 logit scalars. Composed complete-set/legal/tie outcomes exact on4520 raw boards. This reuses saved target evidence, not new target execution/performance. Additional unselected experts evaluated offline only; baseline observation placeholders are not measured zero activity. Selected zero gate remains a real executed expert.\n\nScores encode >=0 optimal-set membership, not categorical preferences or probabilities. Wrapper canonicalization, legal masking, full-set inverse and raw tie order are fixed non-neural. All finite boards were previously trained/audited;372/121/134 folds are probe/selection confirmation, not novel-domain generalization. Interventions are OOD and preserve native integer rounding, clamps and accumulation. No strategy labels inferred from damage.\n\n![Measured overview](overview'+stage+'.png)\n\n![Actual cases and counterexamples](cases'+stage+'.png)\n\n'
    if stage=='006':
        text+='## Pair controls and findings\nSame-board expert outputs remain fixed for all six declared pair memberships. Each pair is ordered by receiver router score (low-ID ties), then receives native selected-score renormalization, receiver actual slot gates or uniform gates. Reversing pair and gates jointly is a pure-order control; reversing only pair is a gate-assignment intervention. Natural donors match fold, ply/side and own/opponent corner-edge-center counts; unmatched receivers remain no-op and coverage is separately reported in donors.json. Gate donors with same ordered route separate gating from pair choice.\n\n'
        text+=f"Actual gates:0/627 errors. Uniform actual pair:{s['actual_uniform']['canonical']['move_errors']}/627; pair-only reversal:{s['gate_swap']['canonical']['move_errors']}/627. All six renormalized pairs exactly preserve full sets on{s['all_pairs_zero_loss_boards']}/627 boards; at least one pair on{s['best_pair_zero_loss_boards']}/627. Best/worst are hindsight outcome bounds, not alternative trained policy choices. Training-selected fixed pair{s['training_selected_fixed_pair']['pair']}, confirmation metrics below.\n\n"
        text+='| Intervention | Empty | Nonoptimal nonempty | Full-set changes | Optimal tie changes | Raw chosen errors /4520 |\n|---|---:|---:|---:|---:|---:|\n'
        for r in read(out,'interventions.json'):
            q=r['canonical'];text+=f"|{r['id']}|{q['empty']}|{q['nonoptimal_nonempty']}|{q['set_changes']}|{q['optimal_tie_changes']}|{r['raw']['move_errors']}|\n"
        text+='\n### Matched tactical versus neutral confirmation (training-selected fixed pair)\nRepeated donors/neutral boards are not independent. Zero matched support remains unavailable; matching is not relaxed.\n\n|Task|Fold|Positive candidates|Matched pairs|Unique neutral|Positive errors|Neutral errors|\n|---|---:|---:|---:|---:|---:|---:|\n'
        for r in read(out,'selection.json')['matched_tactical_neutral']:text+='|'+ '|'.join(str(r[k]) for k in ('task','fold','positive_candidates','matched_pairs','unique_neutral','positive_errors','neutral_errors'))+'|\n'
        text+='\nThe matched contrasts quantify selective task effects relative to broad damage, but do not establish a named detector or causal strategy circuit. Offline all-expert computation2508 vs1254 normal outputs is additional work.\n'
    elif stage=='007':
        text+=f"## Declared circuit boundary\nCandidate expert{s['selected_expert']} selected on training-only necessity contrast (must-block minus matched-neutral active error rates); control expert{s['control_expert']} is the predeclared next cyclic ID, not post-hoc best control. Scope is a whole expert output vector after routing, with receiver residual/gates/head retained. It is NOT a full network circuit. Natural matches reuse study005's frozen legal one-mark relocations; preserve raw candidate identity/ply/side/geometry/fold, candidate active in both; gate Linf<=4096/32768. Route-fixed and naturally route-changing contrasts are reported separately. Both patch directions executed. Donor latent vectors are computed in their own canonical frames; no square-axis latent alignment is invented. Raw orbit outcomes use exact declared transforms. Unavailable donor experts are never substituted as observed zeros.\n\n"
        text+='Candidate-only patch, shared-noncandidate natural corruption, all-shared patch and candidate restoration are compared with zero-noncandidate/zero-all/restoration controls. Identity and restoration algebra are exact. Rescue reports newly introduced failures too. Natural pathway transplantation is off-distribution; retaining one output path while zeroing another is a local preservation test only, not natural mediation or full-circuit sufficiency.\n\n'
        text+='|Role/contract|Directed trials|Natural rescues|New damage|Zero rescues|Candidate preserved: empty|Candidate preserved: nonoptimal nonempty|\n|---|---:|---:|---:|---:|---:|---:|\n'
        for name,v in s['contracts'].items():text+=f"|{name}|{v['directions']}|{v['rescue_natural']}|{v['new_damage_natural']}|{v['rescue_zero']}|{v['outcomes']['zero-noncandidate']['empty']}|{v['outcomes']['zero-noncandidate']['nonoptimal_nonempty']}|\n"
        text+='\n### Matching coverage (no post-hoc relaxation; cap24/stratum)\n|Role|Contract|Task|Fold|Prior eligible relocation inventory|Accepted pairs|\n|---|---|---|---:|---:|---:|\n'
        for r in s['coverage']:text+='|'+ '|'.join(str(r[k]) for k in ('role','contract','task','fold','available_prior_pairs','accepted'))+'|\n'
        text+='\nFull per-direction empty/nonoptimal/tie/full-set and raw-orbit outcomes, exact expert output vectors and restoration records are in outcomes.json. Counterexamples are retained in figure cases007 A-C; lack of support is unavailable evidence, not a null circuit effect.\n'
    else:
        text+=f"## Exact sign fragility\n{s['legal_score_count']} legal scores, {s['legal_zero_count']} exact zeros. Membership-flip distance is y+1 for y>=0 and -y for y<0; this is not a ranking margin. Negative-to-nonnegative legal flips:{s['negative_to_nonnegative']}; nonnegative-to-negative legal flips:{s['nonnegative_to_negative']}; occupied flips ignored by legal mask:{s['occupied_sign_flips']}. Counts sum board-square-intervention observations, not unique boards.\n\n"
        text+=f"Predeclared all9 output biases, all4 router biases, all16 norm2 weights; plus one output weight per row at the merged unit with maximal mean absolute TRAINING activation.38 coordinates,76 +/-1-code attempts;{s['executed_interventions']} executed,{len(s['rejected'])} boundary rejects. Each copy differs in exactly one stored code; all descriptors/exponents unchanged; original packet never rewritten. Full network recomputed and each original code restored with all-stage parity:{s['all_stage_restorations_exact']}.\n\n"
        text+=f"Any full-set change:{s['boards_any_set_change']}/627; any chosen-move failure:{s['boards_any_move_failure']}/627; robust to ALL tested interventions:{s['boards_robust_all_codes']}/627. Raw-coordinate complete-set/tie outcomes evaluated separately, not canonical errors multiplied by8. Fragility is local to this finite panel; no implication of universal robustness, optimal bit width, or actual reduced-precision conversion.\n\n"
        text+='|Coordinate/delta|Old -> new|Empty|Nonoptimal nonempty|Set changes|Optimal tie changes|Raw errors /4520|\n|---|---|---:|---:|---:|---:|---:|\n'
        for r in read(out,'interventions.json'):
            q=r['canonical'];text+=f"|{r['id']}|{r['old_code']} -> {r['new_code']}|{q['empty']}|{q['nonoptimal_nonempty']}|{q['set_changes']}|{q['optimal_tie_changes']}|{r['raw']['move_errors']}|\n"
    text+='\n## Reproduction and evidence\nRun `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/ai/falken9-strategy-study-003 /home/ai/falken-9/.venv/bin/python research678_run.py '+stage+' --out <fresh-directory>`. This historical interpreter path supplies dependencies only. Local falken9/scripts imports must resolve inside the isolated snapshot. verification-study'+stage+'.json records fresh-directory byte equality and preservation. Bundles exclude model binaries, ROMs, secrets, environments and caches; a hash-matching original packet and target fixtures are prerequisites. No external writes or notifications.\n'
    (out/f'REPORT{stage}.md').write_text(text)
