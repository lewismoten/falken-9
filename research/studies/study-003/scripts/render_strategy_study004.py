#!/usr/bin/env python3
"""Evidence-only study004 report and deterministic annotated figures."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.render_strategy_maps import Canvas,board,heading,INK,MUTED,DYNAMIC,GREEN,RED,EDGE,STATIC,BG,color
from scripts.model_strategy_study import sha
from falken9.strategy_square004 import D,TASKS

def put(p,v):p.write_text(json.dumps(v,separators=(',',':'),allow_nan=False)+'\n')
def fmt(v):return f'{v:+,.2f}'
def sets(v):return '{'+','.join(str(s+1) for s in v)+'}'
def render(study):
    p=Path(study);read=lambda n:json.loads((p/n).read_text())
    cs=read('cases.json');bk=read('exact-paths.json')['records'];su=read('summary.json')
    vs={r['id']:r for r in read('intervention-vectors.json')};rs={r['id']:r for r in read('interventions.json')}
    coords=read('weight-coordinates.json')['scalars'];matches=read('matched-relocations.json')
    def co(n,idx):return next(v for v in coords if v['tensor']==n and v['coordinates']==idx)
    figures=[];callouts={}
    # Two matched strategy-class fork examples, NOT same-ply matched controls.
    c=Canvas(1640,1110)
    heading(c,'Study004 / the same routed unit supports one square and rejects another','Measured per-square score bookkeeping. Scores are full-set membership signals, not probabilities or move preferences.')
    c.paragraph(28,99,'A and B are concrete fork examples, NOT a matched causal pair. All eight output-lane paths are retained; lane5 was training-selected for E2.h2. One path is not the whole expert.',1580,17)
    for row,(tag,i,s,title) in enumerate([('A',49,0,'Fork square loses membership'),('B',170,4,'Fork counterexample retains membership')]):
        y=166+row*347;case=cs[i];b=bk[i];e,h,lane=2,2,5;slot=case['routes'].index(e)
        path=[b['paths'][slot][h][j][s]/D for j in range(8)]
        w=co('expert_w2',[e,h,lane]);v=co('output.weight',[s,lane]);unit=sum(path)
        callouts[tag]=dict(canonical_id=i,square_zero_based=s,expert=e,hidden=h,lane=lane,slot=slot,hidden_value=case['hidden'][e][h],gate=case['gates'][slot],w2=w,head=v,path_numerator=b['paths'][slot][h][lane][s],denominator=D,unit_support=unit)
        c.rect(28,y,1584,324);c.text(44,y+14,f'{tag} / #{i} test / {title}',21,DYNAMIC)
        board(c,48,y+62,case['board'],cell=47,move=s)
        c.text(48,y+219,f'Candidate square {s+1}',17,GREEN)
        c.text(48,y+247,f"Routes {case['routes']}",15,MUTED)
        c.text(48,y+274,f"Gates {case['gates']}",15,MUTED)
        c.line(206,y+132,250,y+132,DYNAMIC,2,True)
        c.text(266,y+63,'DYNAMIC / post-GELU',16,DYNAMIC)
        c.text(266,y+99,f'E2.h2 = {case["hidden"][e][h]}',20)
        c.text(266,y+136,f'gate = {case["gates"][slot]}/32768',17)
        c.paragraph(266,y+178,'This activation and route are observations of this board, not a stored strategy name.',256,15)
        c.line(524,y+132,563,y+132,DYNAMIC,2,True)
        c.text(579,y+63,'STATIC / exact lane5 path',16,STATIC)
        c.text(579,y+98,f'w2[2,2,5] = {w["code"]} x 2^{w["exponent"]}',16)
        c.text(579,y+129,f'head[{s},5] = {v["code"]} x 2^{v["exponent"]}',16)
        c.text(579,y+160,f'RAM {w["runtime_address"]} -> {v["runtime_address"]}',14,MUTED)
        c.text(579,y+195,f'Lane5 pre-round support {fmt(path[5])}',17,GREEN if path[5]>0 else RED)
        c.text(579,y+224,f'All8 unit paths together {fmt(unit)}',17)
        # Eight compact diverging support bars, each own exact value in metadata.
        maxv=max(abs(z) for z in path);base=792
        for j,z in enumerate(path):
            xx=579+j*48;c.rect(xx,y+263,42,27,color(z,maxv),STATIC if j==lane else EDGE,2 if j==lane else 1);c.text(xx+10,y+295,str(j),12,MUTED)
        c.line(984,y+132,1024,y+132,DYNAMIC,2,True)
        c.text(1040,y+63,f'EMPTY square{s+1} / final head',17,GREEN)
        for k,(name,val) in enumerate([('Readout',b['terms']['readout'][s]/D)]+[(f'Executed E{ee}',b['executed_expert_support'][sl][s]/D) for sl,ee in enumerate(b['expert_ids'])]+[('Output bias',b['terms']['output_bias'][s]/D),('Mix + head residual',(b['terms']['mix_round'][s]+b['terms']['head_round'][s])/D)]):
            c.text(1040,y+97+k*25,name,14,MUTED);c.text(1325,y+97+k*25,fmt(val),14)
        basev=case['logits'][s];unitafter=vs['unit-E2h2-0of4']['logits'][i][s];pathafter=vs['path-E2h2-lane5-0of4']['logits'][i][s]
        c.text(1040,y+230,f'Exact logit {basev:+,} >= 0',19,GREEN)
        c.text(1040,y+263,f'Unit zero: {unitafter:+,}; lane5 zero: {pathafter:+,}',15,RED if row==0 else GREEN)
        c.text(1040,y+293,'Lesion effects are NOT additive contributions.',13,MUTED)
    y=882;c.rect(28,y,1584,191)
    c.text(46,y+17,'Why the signs differ',21)
    c.paragraph(46,y+53,'The SAME stored w2[2,2,5] feeds different final-head rows: head[0,5] is negative while head[4,5] is positive. Activity and gating also differ. A: lane5 supports square1 by +47,587.29; B: it rejects square5 by -1,652.04. The latter is outweighed by other computations.',1510,17)
    c.paragraph(46,y+120,'Green board outline marks the candidate, not the chosen preference. Orange/blue lane cells encode positive/negative dynamic support, normalized within each row; purple outlines mark the displayed static path. Exact integer numerators and rounding residuals remain in exact-paths.json.',1510,15)
    figures.append(c.save(p,'square-paths'))
    # Actual same-ply, same-square relocation with full original alignment.
    c=Canvas(1640,1210)
    heading(c,'Study004 / controlled positions, rejection support and zero gates','A legal alternative board is another input, not a causal proof of psychological understanding. No game/model bytes changed.')
    pair=next(r for r in matches if r['task']=='win' and r['fold']==2 and r['receiver']==595)
    c.rect(28,106,1584,475);c.text(46,122,'C / one X relocated: raw square4 -> 8; the EMPTY candidate remains square5',22,DYNAMIC)
    for col,(i,label) in enumerate([(pair['receiver'],'Immediate win'),(pair['donor'],'Required block')]):
        x=46+col*790;case=cs[i];slot=case['routes'].index(1);s=4
        c.text(x,166,f'#{i} / test / {label}',19)
        board(c,x,206,case['board'],cell=54,move=s)
        c.line(x+181,279,x+214,279,DYNAMIC,2,True)
        c.text(x+231,209,f'E1.h0 = {case["hidden"][1][0]}',19)
        c.text(x+231,244,f'Routes {case["routes"]}; gates {case["gates"]}',15,MUTED)
        c.text(x+231,279,f'All8 h0 paths -> square5: {fmt(sum(bk[i]["paths"][slot][0][j][s] for j in range(8))/D)}',16)
        after=vs['unit-E1h0-0of4']['logits'][i][s]
        c.text(x+231,318,f'Logit {case["logits"][s]:+,} -> h0zero {after:+,}',17,GREEN if after>=0 else RED)
        c.text(x+231,353,'Empty legal set after h0zero.' if col==0 else 'Center retained; wrong extra members added.',15,MUTED)
        callouts[f'C{col}']=dict(canonical_id=i,square=4,expert=1,hidden=0,unit_support_numerator=sum(bk[i]['paths'][slot][0][j][s] for j in range(8)),denominator=D)
    c.paragraph(46,405,'Exact controls: same ply4 / X to move, candidate square5 empty, own/opponent corner-edge-center counts, canonical test fold and ordered routes[1,0]. Gate difference245/32768. Here both boards are already canonical (identity permutations).',1516,17)
    c.paragraph(46,479,'This is one matched example, NOT a validated win detector: only2/88 test winning squares and1/20 test blocking squares have any permitted relocation match; zero matched fork test squares. Unit/dose/path outcomes for all fixed controls are retained.',1516,17)
    # Rejection example + executed-zero-gate example.
    for j in range(2):c.rect(28+j*798,608,786,435)
    c.text(46,626,'D / rejecting an ordinary EMPTY square',21,DYNAMIC)
    i,s=91,7;case=cs[i];slot=case['routes'].index(2)
    board(c,46,672,case['board'],cell=49,move=s)
    c.text(216,678,'#91 test / E2.h2',18)
    val=sum(bk[i]['paths'][slot][2][j][s] for j in range(8))/D
    c.text(216,715,f'All8 unit paths to square8: {fmt(val)}',16,RED)
    c.text(216,751,f'Logit {case["logits"][s]:+,} -> unitzero {vs["unit-E2h2-0of4"]["logits"][i][s]:+,}',17)
    c.paragraph(216,788,'Zero adds a nonoptimal square to the set. The canonical chosen move stays optimal; a set error is not automatically a chosen-move error.',565,16)
    c.paragraph(46,914,'Baseline set '+sets(case['optimal_set'])+'; lesion set '+sets([z for z in range(9) if not case['board'][z] and vs['unit-E2h2-0of4']['logits'][i][z]>=0])+'. Neutral means no immediate geometric target label, not strategically irrelevant.',729,16)
    callouts['D']=dict(canonical_id=i,square=s,expert=2,hidden=2,unit_support=val)
    c.text(844,626,'E / executed does NOT mean nonzero gate',21,DYNAMIC)
    case=cs[487];board(c,844,672,case['board'],cell=49,move=5)
    c.text(1014,678,'#487 test / routes [3,2]',18)
    c.text(1014,715,'E2 is EXECUTED; gate = 0/32768',17)
    c.text(1014,751,'E2.h2 = -194 (observed, not missing)',16)
    c.text(1014,788,'Its gated hidden paths contribute exactly 0.',16)
    c.paragraph(844,868,f"Across627 boards: {su['executed_expert_observations']} expert executions; {su['executed_zero_gate_observations']} have zero gates. Another {su['unobserved_expert_board_cells']} expert-board cells are unobserved, not activation zeros.",729,17)
    c.paragraph(844,959,'Occupied square5 has a positive raw score here, but the fixed external legal mask excludes it. That exclusion is not learned occupancy recognition.',729,15)
    callouts['E']=dict(canonical_id=487,executed_expert=2,gate=0,hidden_h2=-194)
    c.paragraph(28,1075,'Membership means legal logit >= 0, followed by the full-set inverse transform and the ORIGINAL-coordinate tie rule. No softmax probabilities, argmax preference, wrapper changes, donor transplantation, rerouting or target reruns are claimed.',1584,18)
    figures.append(c.save(p,'position-contrasts'))
    metadata=dict(figures=figures,callouts=callouts,model_immutable=True,model_sha256=su['model_sha256'],coordinate_convention='zero-based tensors/metadata; one-based displayed squares',plot_convention='Dynamic signed lane support normalized within each row; shared round/clamp residuals never assigned to hidden units',illustrative_example_selection='Deterministic measured positive/counterexamples; no inferential test selection',renderer_sha256=sha(__file__),input_sha256={n:sha(p/n) for n in ('cases.json','exact-paths.json','weight-coordinates.json','matched-relocations.json','interventions.json','intervention-vectors.json','summary.json')})
    put(p/'figure-metadata.json',metadata)
    # Compact report generated from measured evidence only.
    lines=[];a=lines.append
    a('# Frozen per-square study004\n')
    a('**Outcome: exact, distributed, position-sensitive support/rejection paths—not a dedicated strategy component.** E2.h2→lane5 supports one fork square and rejects another through different final-head rows. Strict legal mark-relocation controls provide little confirmation coverage; no strategy-specific interpretation survives as an established finding. No training or game change.\n')
    a('## Gates and scope\n')
    a(f"Before new evaluations the fixed experiment manifest was written. Reproduced **{su['baseline_stage_checks']} saved actual-target stage vectors on627 canonical boards**, routes/gates/logits included, and the composed full-set inverse/legal-mask/original-tie wrapper on4520 legal raw boards with zero errors. Host verification only, **not new C64 execution**. All69 baseline files and all23 study003 artifacts remain hash-identical. Model `{su['model_sha256']}`.\n")
    a('Full-set scores are **not probabilities** or preferences: legal logit>=0 means membership; all members are inverse-transformed before original-coordinate tie selection. No final nonlinear activation exists. Fixed validation, canonicalization, occupied masking, inverse and ties are not learned parameters.\n')
    a(f"All627 boards and **{su['legal_empty_square_observations']} empty-square observations** are descriptive. There are {su['occupied_nonnegative_logits']} occupied/nonnegative-score cells; their exclusion is external, not evidence of learned occupancy recognition. Canonical folds372/121/134 (seed1729) are selection/confirmation folds only: the frozen model had already trained/audited the finite domain. No model-heldout, OOD, significance or independent4520-sample claim.\n")
    a('## Exact arithmetic—not summed lesion deltas\n')
    a('Zero-based e=actual expert ID, r=route slot, h=hidden unit, j=output lane, s=candidate square. Decoded w2 is U[e,h,j] with exponent a[e,j]; final head is W[s,j] with exponent b[s]. Bias codes are directly added in activation units; their stored -11 exponent is Q11 metadata, not another runtime multiplication. R=nearest integer with ties away from zero; C=declared signed32 clamp.\n')
    a('```text\nA[e,j] = Σh hidden[e,h] * U[e,h,j]\nV[e,j] = C(R(A[e,j] * 2^a[e,j]) + expert_b2[e,j])\nM[j] = Σr gate[r] * V[route[r],j]\nmerged[j] = C(readout_GELU[j] + R(M[j]/32768))\nlogit[s] = C(R((Σj merged[j]*W[s,j]) * 2^b[s]) + output_bias[s])\nP[r,h,j,s] = hidden[e,h] * U[e,h,j] * 2^a[e,j]\n               * gate[r]/32768 * W[s,j] * 2^b[s]\n```\n')
    a(f'All final **5643 logits** independently reconstruct exactly. `exact-paths.json` retains all361152 routed hidden→lane→square pre-round numerators over common denominator2^46={D}, plus expert dot products, actual expert outputs, readout vector/lane numerators, weighted-mix numerators, rounded mix, merged, head dots and every final score. Python unbounded integers prevent bookkeeping overflow.\n')
    a('Exact expansion is readout path sum + output bias + ΣP + expert-bias gated/head terms + **unallocated shared** expert-linear rounding/clamp terms + mix-round term + merged-clamp term + head-round/clamp terms. The expert residual is V−(A·2^a+b2), separated into R(A·2^a)−A·2^a and clamp; the mix residual is R(M/32768)−M/32768; the head residual is R(dot·2^b)−dot·2^b. These are propagated through the *linear* downstream weights. No shared remainder is assigned to one hidden unit. Identity is asserted exactly at denominator2^46. This convention is useful bookkeeping, not a unique semantic decomposition.\n')
    a('| Residual term | Max absolute score units | Nonzero cells |\n|---|---:|---:|')
    for k,r in su['rounding'].items():
        if isinstance(r,dict):a(f"| {k} | {r['max_abs']:.6f} | {r['nonzero_cells']} |")
    a(f"\nExpert/merged/head clamps are zero throughout this finite baseline. Combined residual max={su['max_abs_combined_rounding_residual']:.6f}; omitting all named downstream round/clamp residuals changes {su['legal_rounding_sign_changes']} baseline legal membership signs. That is a descriptive finite-domain audit, not permission to replace the integer contract.\n")
    a('| Empty-square term | Mean absolute score units | Max absolute |\n|---|---:|---:|')
    for k,r in su['empty_square_magnitude'].items():a(f"| {k} | {r['mean_abs']:.2f} | {r['max_abs']:.2f} |")
    a('\nPer-executed-expert means include genuinely executed zero gates. Large signed cancellation makes percentages of net score misleading; magnitudes are not causal shares. Readout remains an input-dependent learned residual, not a geometric oracle.\n')
    a(f"Executed expert observations1254; **{su['executed_zero_gate_observations']} have zero gates**, while1254 expert-board cells were not executed and are null/unobserved. Zero gate is not nonexecution. All interventions here are downstream of routing and retain routes/order/membership/gates exactly; this study does not test rerouting (study003 did).\n")
    a('## Square geometry and fixed relocation controls\n')
    a('Independent candidate labels: occupied-own/opponent, legal-empty, immediate win; unique required block only if no own win; fork creation (two distinct next-turn winning squares, no current win/threat); bounded fork prevention via all viable opponent replies; neutral=no target label. Labels may overlap and prevention is not a long-horizon theorem or equivalent to optimal membership. Label code is independently cross-checked against prior geometry and all8 raw/canonical symmetries.\n')
    a('Matching fixes candidate identity in a common raw frame, candidate emptiness, same ply/side, own/opponent corner-edge-center counts, canonical fold, ordered routes, gate tolerance4096/32768. Only legal, reachable, nonterminal alternatives made by relocating one existing mark (Hamming2) qualify. Both inputs are then executed in their own canonical frame; complete raw↔canonical maps are saved. Full occupancy identity would leave no contrast; other upstream states can and do differ. “Donor” in matching files means alternative input, not an activation transplant. Selection uses only training matched support with each board’s mean legal-square support subtracted.\n')
    a('| Label | Train covered / positive squares | Validation | Test |\n|---|---:|---:|---:|')
    for t in TASKS:
        a('| '+t+' | '+' | '.join(f"{su['matching_coverage'][f'{t}:{f}']['covered_positive_squares']}/{su['matching_coverage'][f'{t}:{f}']['positive_squares']}" for f in range(3))+' |')
    a(f"\nThe test fork positives are only{su['candidate_counts']['fork'][2]} candidate squares on{su['test_fork_positive_boards']} canonical boards; low power even before matching.")
    a(f"\nThere are66 fixed pair records (reused boards/overlapping labels are not independent replicates). **Zero validation or test fork matches**: no same-ply matched fork confirmation is available. E3.h1 has no covered held-out blocking contrasts. No matching relaxation or expanded search was added. Neutral squares are descriptive controls; no neutral-positive relocation matching was specified.\n")
    a('## Bounded interventions and unfavorable controls\n')
    a('Training-only screening of16 units across four labels, on predeclared matched centered-support contrasts, selected E2.h2 for win and E3.h1 for block. Appended E1.h0/E3.h3 prior hints and next-unit controls E2.h3/E3.h2. Only22 interventions:12 unit zero/half,2 selected-pair zero/half,8 single-w2-scalar path zero/half. Path lanes selected by training mean absolute target path support: E2.h2 lane5 (control6), E3.h1 lane4 (control5). Adjacent lanes are positional controls, not magnitude-matched; their training strengths are disclosed. No combinatorial search, hyperparameter hunt or donor patches.\n')
    a('| Intervention | Canonical empty / bad nonempty / set change / optimal tie change | Raw same |\n|---|---:|---:|')
    for r in rs.values():
        keys=('empty_set','nonoptimal_nonempty','set_change','equivalent_optimal_tie')
        a('| '+r['id']+' | '+' | '.join(' / '.join(str(r[k][v]) for v in keys) for k in ('canonical','raw'))+' |')
    a('\nBad nonempty means chosen move outside baseline minimax-optimal set. Empty and bad nonempty are disjoint; set and equivalent-optimal-tie columns overlap other categories. A set can be wrong while the selected move remains optimal. Full logits and exact per-class/fold denominators are retained. Integer half-amplitude-only control changes logit magnitudes but preserves every sign/set; demeaning square-support and logit deltas controls generic additive output level, not every amplitude/geometry confound.\n')
    a('| Unit zero / matched task | Train target/control flips / N | Validation | Test |\n|---|---:|---:|---:|')
    for name in ('unit-E2h2-0of4','unit-E3h1-0of4','unit-E1h0-0of4','unit-E3h3-0of4'):
        for t in TASKS:
            rr=[next(v for v in rs[name]['matched'] if v['task']==t and v['fold']==f) for f in range(3)]
            a('| '+name+' / '+t+' | '+' | '.join(f"{v['target_membership_flips']}/{v['control_membership_flips']} / {v['n']}" for v in rr)+' |')
    a('\nSelected-pair effects (not an additive decomposition):')
    for z in read('pair-audit.json'):
        a(f"- Remaining {z['remaining_quarters']}/4: single-failure union{z['single_failure_union']}; pair failures{z['pair_failures']}; rescued{len(z['rescued_union_ids'])}; newly introduced{len(z['new_beyond_union_ids'])}; max absolute logit nonadditivity{z['max_abs_logit_nonadditivity']}.")
    a('\nMatched denominators require the component actually executed in both boards; a zero gate still qualifies as executed. Pair square/matched results require both selected experts observed. Whole-domain chosen-move counts are separate from this coverage. Training effects do not establish held-out class selectivity; some controls flip equally or more. No role survives as a confirmed win/block/fork detector.\n')
    a('## Concrete support, rejection and counterexamples\n')
    for i,s,e,h,lane,label in [(49,0,2,2,5,'fork support'),(170,4,2,2,5,'fork counterexample'),(25,0,3,1,4,'required block'),(150,0,3,1,4,'non-block immediate win'),(91,7,2,2,5,'neutral rejection'),(69,7,2,2,5,'prevention membership dropped'),(69,0,2,2,5,'same-board prevention retained'),(201,5,2,2,5,'neutral equivalent-optimal-tie change')]:
        case=cs[i];slot=case['routes'].index(e);path=bk[i]['paths'][slot][h][lane][s]/D;unit=sum(bk[i]['paths'][slot][h][j][s] for j in range(8))/D
        uu=vs[f'unit-E{e}h{h}-0of4']['logits'][i][s];pp=vs[f'path-E{e}h{h}-lane{lane}-0of4']['logits'][i][s]
        a(f"- **{label}**, canonical{i} test, board`{case['board']}`, human square{s+1}: E{e}.h{h} unit pre-round support{unit:+.2f}, lane{lane} support{path:+.2f}; baseline logit{case['logits'][s]:+d}, unit-zero{uu:+d}, single-lane-weight-zero{pp:+d}.")
    a('\nThe SAME static w2[2,2,5]=-13019·2^-13 at packet byte935/RAM$43a7 reaches head[0,5]=-21104·2^-12 (byte2991/$4baf) but head[4,5]=+13490·2^-12 (byte3055/$4bef). Thus it supports fork square1 on#49 but rejects fork square5 on#170; other paths overpower that rejection. No universal fork-unit story. #25 blocking and #150 own-win damage also refute exclusive E3.h1 blocking semantics. #91 zero adds a nonoptimal neutral square but leaves the chosen canonical move optimal.\n')
    a('The controlled test contrast#595→#588 relocates X raw4→8, center square5 remains empty, ply4/sideX/geometry/routes[1,0]/foldtest fixed, gate delta245. E1.h0=16923→1790; center scores205803→198395; zero h0 makes the win score−84675 but the block score remains167901. The support changes strongly with the board; one matched example does not identify psychological understanding. Alternative controls and alignment permutations are explicit in`matched-relocations.json`.\n')
    a('Figures:`square-paths.{png,svg}` shows boards→observed hidden/gate→actual stored weights→all8 lane paths→candidate score;`position-contrasts.{png,svg}` shows the matched contrast, rejection and actually-executed zero gate. Static parameters never “light up”; colors are measured dynamic support, row-normalized. Exact coordinates/code/exponent packet/RAM addresses are in`weight-coordinates.json` and figure callouts.\n')
    a('## Limits and reproducibility\n')
    a('No unique semantic decomposition, named strategy circuit, probability, preference, learned legal mask, OOD/model-heldout generalization, transplant, mediation or target-speed finding. Discrete set changes and broad empty-set damage do not imply selective strategy roles. Candidate labels are finite geometric conventions; stringent matched positives are scarce. Further broader searches are outside this finite study.\n')
    a('Run commands and immutable hash requirements are in the source bundle README; new modules/scripts/tests only. Exact final acceptance logs, fresh-directory byte reproduction, all69+23 immutability rechecks and artifact SHA256s are bound in`FINAL-STUDY-004.{md,json}` at the research root. The renderer is evidence-only. No GPU initialized, emulator consumed, game/main tree modified, release built/merged or publication performed.\n')
    (p/'REPORT.md').write_text('\n'.join(lines)+'\n')
    from PIL import ImageFont
    fontpath=Path(ImageFont.truetype('DejaVuSans.ttf',16).path)
    put(p/'render-provenance.json',dict(renderer_sha256=sha(__file__),helper_sha256=sha(ROOT/'scripts/render_strategy_maps.py'),pillow=__import__('PIL').__version__,font_path=str(fontpath),font_sha256=sha(fontpath),model_sha256=su['model_sha256']))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--study',required=True);render(ap.parse_args().study)
