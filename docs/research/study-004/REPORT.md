# Frozen per-square study004

**Outcome: exact, distributed, position-sensitive support/rejection paths—not a dedicated strategy component.** E2.h2→lane5 supports one fork square and rejects another through different final-head rows. Strict legal mark-relocation controls provide little confirmation coverage; no strategy-specific interpretation survives as an established finding. No training or game change.

## Gates and scope

Before new evaluations the fixed experiment manifest was written. Reproduced **13167 saved actual-target stage vectors on627 canonical boards**, routes/gates/logits included, and the composed full-set inverse/legal-mask/original-tie wrapper on4520 legal raw boards with zero errors. Host verification only, **not new C64 execution**. All69 baseline files and all23 study003 artifacts remain hash-identical. Model `fe180f8a931f9d92d8aa39da337bc819d0dbe4e6d971edcba00324fbc18a91c1`.

Full-set scores are **not probabilities** or preferences: legal logit>=0 means membership; all members are inverse-transformed before original-coordinate tie selection. No final nonlinear activation exists. Fixed validation, canonicalization, occupied masking, inverse and ties are not learned parameters.

All627 boards and **2270 empty-square observations** are descriptive. There are 1832 occupied/nonnegative-score cells; their exclusion is external, not evidence of learned occupancy recognition. Canonical folds372/121/134 (seed1729) are selection/confirmation folds only: the frozen model had already trained/audited the finite domain. No model-heldout, OOD, significance or independent4520-sample claim.

## Exact arithmetic—not summed lesion deltas

Zero-based e=actual expert ID, r=route slot, h=hidden unit, j=output lane, s=candidate square. Decoded w2 is U[e,h,j] with exponent a[e,j]; final head is W[s,j] with exponent b[s]. Bias codes are directly added in activation units; their stored -11 exponent is Q11 metadata, not another runtime multiplication. R=nearest integer with ties away from zero; C=declared signed32 clamp.

```text
A[e,j] = Σh hidden[e,h] * U[e,h,j]
V[e,j] = C(R(A[e,j] * 2^a[e,j]) + expert_b2[e,j])
M[j] = Σr gate[r] * V[route[r],j]
merged[j] = C(readout_GELU[j] + R(M[j]/32768))
logit[s] = C(R((Σj merged[j]*W[s,j]) * 2^b[s]) + output_bias[s])
P[r,h,j,s] = hidden[e,h] * U[e,h,j] * 2^a[e,j]
               * gate[r]/32768 * W[s,j] * 2^b[s]
```

All final **5643 logits** independently reconstruct exactly. `exact-paths.json` retains all361152 routed hidden→lane→square pre-round numerators over common denominator2^46=70368744177664, plus expert dot products, actual expert outputs, readout vector/lane numerators, weighted-mix numerators, rounded mix, merged, head dots and every final score. Python unbounded integers prevent bookkeeping overflow.

Exact expansion is readout path sum + output bias + ΣP + expert-bias gated/head terms + **unallocated shared** expert-linear rounding/clamp terms + mix-round term + merged-clamp term + head-round/clamp terms. The expert residual is V−(A·2^a+b2), separated into R(A·2^a)−A·2^a and clamp; the mix residual is R(M/32768)−M/32768; the head residual is R(dot·2^b)−dot·2^b. These are propagated through the *linear* downstream weights. No shared remainder is assigned to one hidden unit. Identity is asserted exactly at denominator2^46. This convention is useful bookkeeping, not a unique semantic decomposition.

| Residual term | Max absolute score units | Nonzero cells |
|---|---:|---:|
| mix_round | 7.893023 | 4671 |
| merge_clamp | 0.000000 | 0 |
| head_round | 0.500000 | 5643 |
| head_clamp | 0.000000 | 0 |
| expert_round | 8.837550 | 10233 |

Expert/merged/head clamps are zero throughout this finite baseline. Combined residual max=11.964528; omitting all named downstream round/clamp residuals changes 0 baseline legal membership signs. That is a descriptive finite-domain audit, not permission to replace the integer contract.

| Empty-square term | Mean absolute score units | Max absolute |
|---|---:|---:|
| readout | 17228.41 | 120240.93 |
| output_bias | 3629.31 | 9588.00 |
| per_executed_expert | 55250.08 | 1131595.12 |

Per-executed-expert means include genuinely executed zero gates. Large signed cancellation makes percentages of net score misleading; magnitudes are not causal shares. Readout remains an input-dependent learned residual, not a geometric oracle.

Executed expert observations1254; **108 have zero gates**, while1254 expert-board cells were not executed and are null/unobserved. Zero gate is not nonexecution. All interventions here are downstream of routing and retain routes/order/membership/gates exactly; this study does not test rerouting (study003 did).

## Square geometry and fixed relocation controls

Independent candidate labels: occupied-own/opponent, legal-empty, immediate win; unique required block only if no own win; fork creation (two distinct next-turn winning squares, no current win/threat); bounded fork prevention via all viable opponent replies; neutral=no target label. Labels may overlap and prevention is not a long-horizon theorem or equivalent to optimal membership. Label code is independently cross-checked against prior geometry and all8 raw/canonical symmetries.

Matching fixes candidate identity in a common raw frame, candidate emptiness, same ply/side, own/opponent corner-edge-center counts, canonical fold, ordered routes, gate tolerance4096/32768. Only legal, reachable, nonterminal alternatives made by relocating one existing mark (Hamming2) qualify. Both inputs are then executed in their own canonical frame; complete raw↔canonical maps are saved. Full occupancy identity would leave no contrast; other upstream states can and do differ. “Donor” in matching files means alternative input, not an activation transplant. Selection uses only training matched support with each board’s mean legal-square support subtracted.

| Label | Train covered / positive squares | Validation | Test |
|---|---:|---:|---:|
| win | 18/213 | 3/80 | 2/88 |
| block | 19/91 | 0/22 | 1/20 |
| fork | 5/20 | 0/8 | 0/7 |
| prevention | 17/72 | 0/34 | 1/39 |

The test fork positives are only7 candidate squares on6 canonical boards; low power even before matching.

There are66 fixed pair records (reused boards/overlapping labels are not independent replicates). **Zero validation or test fork matches**: no same-ply matched fork confirmation is available. E3.h1 has no covered held-out blocking contrasts. No matching relaxation or expanded search was added. Neutral squares are descriptive controls; no neutral-positive relocation matching was specified.

## Bounded interventions and unfavorable controls

Training-only screening of16 units across four labels, on predeclared matched centered-support contrasts, selected E2.h2 for win and E3.h1 for block. Appended E1.h0/E3.h3 prior hints and next-unit controls E2.h3/E3.h2. Only22 interventions:12 unit zero/half,2 selected-pair zero/half,8 single-w2-scalar path zero/half. Path lanes selected by training mean absolute target path support: E2.h2 lane5 (control6), E3.h1 lane4 (control5). Adjacent lanes are positional controls, not magnitude-matched; their training strengths are disclosed. No combinatorial search, hyperparameter hunt or donor patches.

| Intervention | Canonical empty / bad nonempty / set change / optimal tie change | Raw same |
|---|---:|---:|
| unit-E2h2-0of4 | 63 / 14 / 122 / 5 | 488 / 86 / 914 / 53 |
| unit-E2h2-2of4 | 52 / 8 / 96 / 2 | 400 / 46 / 710 / 28 |
| unit-E3h1-0of4 | 3 / 20 / 71 / 1 | 24 / 187 / 512 / 8 |
| unit-E3h1-2of4 | 1 / 10 / 33 / 1 | 8 / 85 / 226 / 8 |
| unit-E1h0-0of4 | 4 / 5 / 25 / 3 | 26 / 40 / 178 / 24 |
| unit-E1h0-2of4 | 2 / 2 / 17 / 2 | 16 / 16 / 128 / 16 |
| unit-E3h3-0of4 | 52 / 3 / 88 / 28 | 352 / 18 / 622 / 193 |
| unit-E3h3-2of4 | 20 / 0 / 37 / 6 | 144 / 0 / 250 / 26 |
| unit-E2h3-0of4 | 0 / 61 / 106 / 5 | 0 / 460 / 808 / 40 |
| unit-E2h3-2of4 | 0 / 51 / 86 / 4 | 0 / 400 / 656 / 28 |
| unit-E3h2-0of4 | 1 / 24 / 50 / 1 | 8 / 181 / 382 / 4 |
| unit-E3h2-2of4 | 1 / 17 / 34 / 0 | 8 / 131 / 258 / 0 |
| pair-0of4 | 64 / 34 / 189 / 6 | 500 / 273 / 1402 / 61 |
| pair-2of4 | 54 / 18 / 133 / 3 | 416 / 131 / 964 / 36 |
| path-E2h2-lane5-0of4 | 35 / 22 / 89 / 2 | 268 / 168 / 680 / 28 |
| path-E2h2-lane5-2of4 | 27 / 15 / 69 / 1 | 208 / 112 / 528 / 30 |
| path-E2h2-lane6-0of4 | 0 / 3 / 18 / 6 | 0 / 11 / 132 / 48 |
| path-E2h2-lane6-2of4 | 0 / 1 / 9 / 6 | 0 / 2 / 68 / 48 |
| path-E3h1-lane4-0of4 | 1 / 17 / 37 / 1 | 8 / 134 / 272 / 8 |
| path-E3h1-lane4-2of4 | 0 / 12 / 24 / 1 | 0 / 90 / 176 / 8 |
| path-E3h1-lane5-0of4 | 2 / 15 / 30 / 1 | 12 / 106 / 216 / 8 |
| path-E3h1-lane5-2of4 | 2 / 5 / 23 / 1 | 12 / 44 / 168 / 8 |

Bad nonempty means chosen move outside baseline minimax-optimal set. Empty and bad nonempty are disjoint; set and equivalent-optimal-tie columns overlap other categories. A set can be wrong while the selected move remains optimal. Full logits and exact per-class/fold denominators are retained. Integer half-amplitude-only control changes logit magnitudes but preserves every sign/set; demeaning square-support and logit deltas controls generic additive output level, not every amplitude/geometry confound.

| Unit zero / matched task | Train target/control flips / N | Validation | Test |
|---|---:|---:|---:|
| unit-E2h2-0of4 / win | 2/2 / 11 | 0/0 / 3 | 0/0 / 1 |
| unit-E2h2-0of4 / block | 1/1 / 13 | 0/0 / 0 | 0/0 / 0 |
| unit-E2h2-0of4 / fork | 1/0 / 4 | 0/0 / 0 | 0/0 / 0 |
| unit-E2h2-0of4 / prevention | 3/0 / 10 | 0/0 / 0 | 0/1 / 1 |
| unit-E3h1-0of4 / win | 0/0 / 6 | 0/0 / 3 | 0/0 / 1 |
| unit-E3h1-0of4 / block | 1/1 / 10 | 0/0 / 0 | 0/0 / 0 |
| unit-E3h1-0of4 / fork | 0/0 / 2 | 0/0 / 0 | 0/0 / 0 |
| unit-E3h1-0of4 / prevention | 0/0 / 7 | 0/0 / 0 | 0/0 / 0 |
| unit-E1h0-0of4 / win | 0/0 / 12 | 0/0 / 0 | 1/0 / 1 |
| unit-E1h0-0of4 / block | 0/0 / 9 | 0/0 / 0 | 0/1 / 1 |
| unit-E1h0-0of4 / fork | 0/0 / 3 | 0/0 / 0 | 0/0 / 0 |
| unit-E1h0-0of4 / prevention | 1/0 / 10 | 0/0 / 0 | 0/0 / 1 |
| unit-E3h3-0of4 / win | 3/3 / 6 | 2/2 / 3 | 0/0 / 1 |
| unit-E3h3-0of4 / block | 3/3 / 10 | 0/0 / 0 | 0/0 / 0 |
| unit-E3h3-0of4 / fork | 1/0 / 2 | 0/0 / 0 | 0/0 / 0 |
| unit-E3h3-0of4 / prevention | 1/0 / 7 | 0/0 / 0 | 0/0 / 0 |

Selected-pair effects (not an additive decomposition):
- Remaining 0/4: single-failure union100; pair failures98; rescued2; newly introduced0; max absolute logit nonadditivity15.
- Remaining 2/4: single-failure union71; pair failures72; rescued0; newly introduced1; max absolute logit nonadditivity19.

Matched denominators require the component actually executed in both boards; a zero gate still qualifies as executed. Pair square/matched results require both selected experts observed. Whole-domain chosen-move counts are separate from this coverage. Training effects do not establish held-out class selectivity; some controls flip equally or more. No role survives as a confirmed win/block/fork detector.

## Concrete support, rejection and counterexamples

- **fork support**, canonical49 test, board`[0, 0, 1, 1, 0, 2, 2, 2, 1]`, human square1: E2.h2 unit pre-round support+87192.08, lane5 support+47587.29; baseline logit+19082, unit-zero-68111, single-lane-weight-zero-28505.
- **fork counterexample**, canonical170 test, board`[0, 0, 0, 0, 0, 2, 2, 1, 1]`, human square5: E2.h2 unit pre-round support-37.25, lane5 support-1652.04; baseline logit+33078, unit-zero+33112, single-lane-weight-zero+34728.
- **required block**, canonical25 test, board`[0, 1, 0, 1, 2, 2, 1, 2, 1]`, human square1: E3.h1 unit pre-round support+13286.94, lane4 support+5201.32; baseline logit+12842, unit-zero-451, single-lane-weight-zero+7641.
- **non-block immediate win**, canonical150 test, board`[0, 0, 1, 2, 2, 1, 1, 1, 2]`, human square1: E3.h1 unit pre-round support+15434.33, lane4 support+6041.94; baseline logit+9060, unit-zero-6374, single-lane-weight-zero+3021.
- **neutral rejection**, canonical91 test, board`[1, 0, 1, 2, 0, 2, 1, 0, 2]`, human square8: E2.h2 unit pre-round support-8998.22, lane5 support-2700.55; baseline logit-7619, unit-zero+1375, single-lane-weight-zero-4924.
- **prevention membership dropped**, canonical69 test, board`[0, 0, 1, 1, 2, 2, 0, 0, 1]`, human square8: E2.h2 unit pre-round support+31976.52, lane5 support+9596.80; baseline logit+12808, unit-zero-19165, single-lane-weight-zero+3214.
- **same-board prevention retained**, canonical69 test, board`[0, 0, 1, 1, 2, 2, 0, 0, 1]`, human square1: E2.h2 unit pre-round support+15599.80, lane5 support+8513.99; baseline logit+169833, unit-zero+154231, single-lane-weight-zero+161321.
- **neutral equivalent-optimal-tie change**, canonical201 test, board`[0, 1, 2, 1, 1, 0, 2, 2, 1]`, human square6: E2.h2 unit pre-round support+5826.17, lane5 support+4673.96; baseline logit+5434, unit-zero-387, single-lane-weight-zero+759.

The SAME static w2[2,2,5]=-13019·2^-13 at packet byte935/RAM$43a7 reaches head[0,5]=-21104·2^-12 (byte2991/$4baf) but head[4,5]=+13490·2^-12 (byte3055/$4bef). Thus it supports fork square1 on#49 but rejects fork square5 on#170; other paths overpower that rejection. No universal fork-unit story. #25 blocking and #150 own-win damage also refute exclusive E3.h1 blocking semantics. #91 zero adds a nonoptimal neutral square but leaves the chosen canonical move optimal.

The controlled test contrast#595→#588 relocates X raw4→8, center square5 remains empty, ply4/sideX/geometry/routes[1,0]/foldtest fixed, gate delta245. E1.h0=16923→1790; center scores205803→198395; zero h0 makes the win score−84675 but the block score remains167901. The support changes strongly with the board; one matched example does not identify psychological understanding. Alternative controls and alignment permutations are explicit in`matched-relocations.json`.

Figures:`square-paths.{png,svg}` shows boards→observed hidden/gate→actual stored weights→all8 lane paths→candidate score;`position-contrasts.{png,svg}` shows the matched contrast, rejection and actually-executed zero gate. Static parameters never “light up”; colors are measured dynamic support, row-normalized. Exact coordinates/code/exponent packet/RAM addresses are in`weight-coordinates.json` and figure callouts.

## Limits and reproducibility

No unique semantic decomposition, named strategy circuit, probability, preference, learned legal mask, OOD/model-heldout generalization, transplant, mediation or target-speed finding. Discrete set changes and broad empty-set damage do not imply selective strategy roles. Candidate labels are finite geometric conventions; stringent matched positives are scarce. Further broader searches are outside this finite study.

Run commands and immutable hash requirements are in the source bundle README; new modules/scripts/tests only. Exact final acceptance logs, fresh-directory byte reproduction, all69+23 immutability rechecks and artifact SHA256s are bound in`FINAL-STUDY-004.{md,json}` at the research root. The renderer is evidence-only. No GPU initialized, emulator consumed, game/main tree modified, release built/merged or publication performed.

