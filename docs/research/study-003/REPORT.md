# Frozen-model interpretability / study003

## Outcome

**New causal evidence is contextual necessity, donor non-interchangeability, and cancellation—not a strategy neuron or a named expert circuit.** All predeclared negative and unfavorable results are retained. No model was trained, game changed, package built, or release modified.

## Reference and scope

Verified all 69 snapshot evidence hashes and **13167 saved stage vectors across 627 canonical boards** (including logits/routes/gates). Composed host full-set inverse/legal-mask/original-tie outcomes pass on **4520 raw boards**, with zero set/move/tie mismatches. This is comparison to copied actual627 target evidence, not a new 6502 execution.

Packet SHA256 `fe180f8a931f9d92d8aa39da337bc819d0dbe4e6d971edcba00324fbc18a91c1`. Snapshot `027e1c11c6114312fee552cdf894b248fb3e5be0` is a materialized archive, **not a Git working tree**. All imports resolve within the isolated study root. Prior study002 and all 69 copied evidence files remain hash-identical.

The fixed `experiment-manifest.json` was written before any new intervention/held-out evaluation. Selection executed training rows only: all 16 single-zero lesions, then at most 15 contrast candidates excluding E1.h0; 8 upstream lanes; 3 predeclared pairs/groups and 4 donor components. No tuning or expanded search after confirmation. **128 interventions** comprise 80 single-dose, 12 group-dose, 32 donor and 4 upstream/restoration runs; identity control is additional.

Folds group canonical symmetry classes: train372/validation121/test134 (seed1729). These are exploratory selection/confirmation folds only: the frozen model had already fitted/audited this finite domain, and study002 already probed it. Raw copies are not independent observations; no confidence interval or significance claim uses 4520 as independent N. Test-only fork support is six canonical boards; classes overlap. Minimax labels audit outputs offline; it is absent from neural inference.

| Board label | Canonical train / validation / test | Raw whole domain |
|---|---:|---:|
| has_win | 181 / 65 / 75 | 2358 |
| must_block | 91 / 22 / 20 | 976 |
| has_fork | 15 / 5 / 6 | 192 |
| has_fork_prevention | 25 / 14 / 14 | 370 |

Winning/must-block/fork labels describe availability with the stated priority exclusions, not an expert objective. Fork prevention is bounded: no immediate win/threat, opponent fork available, and candidate leaves no fork after each viable one-ply opponent reply. It is not a complete long-horizon prevention theorem.

## Supported: dose-dependent effects, not exclusivity

A=`expert_hidden[1,0]` after GELU; B=`expert_hidden[3,3]`, the training-selected contrast maximizing must-block minus fork move-error rate. Lesions scale only routed observations with the original integer `round_div(h*n,4)`. Unrouted cells are **null/unobserved**, never activation zero. Doses and natural patches are post-routing and changed **zero routes/gates**. Upstream changes are reported separately below.

| Remaining activation | A bad moves raw / canonical | B bad moves raw / canonical |
|---|---:|---:|
| 4/4 | 0/4520 ; 0/627 | 0/4520 ; 0/627 |
| 3/4 | 12/4520 ; 2/627 | 24/4520 ; 3/627 |
| 2/4 | 32/4520 ; 4/627 | 144/4520 ; 20/627 |
| 1/4 | 48/4520 ; 6/627 | 194/4520 ; 28/627 |
| 0/4 | 66/4520 ; 9/627 | 370/4520 ; 55/627 |

“Bad” includes empty legal sets; sets use legal logits >=0, then inverse-map the **complete** set before original-coordinate ties. A canonical chosen-move error need not expand uniformly because tie order is original-coordinate; raw outcomes are re-evaluated, not multiplied by eight.

| Zero lesion | Empty / nonoptimal nonempty / set changes / optimal tie changes (raw) | Same (canonical) |
|---|---:|---:|
| E1.h0 | 26 / 40 / 178 / 24 | 4 / 5 / 25 / 3 |
| E3.h3 | 352 / 18 / 622 / 193 | 52 / 3 / 88 / 28 |

Set/tie categories intentionally overlap: a changed set can retain an optimal chosen move, and a different chosen optimal move is not a failure. `optimal_move_set_changed` in machine results separates set changes retaining optimal behavior.

### Target effects versus covered matched non-target damage

Matching is exact on ply, side, own/opponent corner/edge counts, center ownership and **ordered expert routes**, with max slot-gate difference <=4096/32768. It is not exact squarewise occupancy; that would identify the board and prevent donor contrasts. Rates below are canonical; non-target rates average matched negatives per covered positive, not pooled independent samples. All rows restrict to routed component observations. All-domain comparisons are descriptive, not held-out confirmation.

| Component / target | Target bad / all routed target N | Matched target bad / covered N | Unique matched negatives | Weighted negative error |
|---|---:|---:|---:|---:|
| E1.h0 / has_win | 3/136 | 1/53 | 53 | 6.9% |
| E1.h0 / must_block | 4/58 | 3/30 | 46 | 3.3% |
| E1.h0 / has_fork | 2/16 | 0/7 | 15 | 9.5% |
| E1.h0 / has_fork_prevention | 1/30 | 0/15 | 30 | 6.7% |
| E3.h3 / has_win | 28/177 | 11/60 | 41 | 19.2% |
| E3.h3 / must_block | 21/64 | 14/36 | 41 | 15.3% |
| E3.h3 / has_fork | 0/9 | 0/3 | 9 | 24.4% |
| E3.h3 / has_fork_prevention | 3/22 | 2/10 | 16 | 17.3% |

B shows a descriptive must-block excess versus covered negatives, but most of its whole-domain failures are empty-set damage and it also breaks immediate wins. Confirmation is weak: B must-block validation5/13 routed targets (matched1/2 versus 0% across2 negatives), test1/10 (**no matched test negatives**). B fork validation0/3 and test0/1 are too small to establish selectivity. A fork validation0/1 and test1/4 routed targets, with **no matched target coverage in either fold**, do not establish a fork-specific component. A whole-domain fork matched positives0/7 versus9.5% controls is unfavorable to that interpretation.

Concrete necessity example A: canonical170, board `[0, 0, 0, 0, 0, 2, 2, 1, 1]`, h=25125; zero loses its winning fork. Counterexample canonical259, board `[0, 1, 0, 1, 0, 2, 2, 2, 1]`, has a fork with routed A but remains optimal after zero. B block example canonical268 fails; non-block immediate-win example canonical23 also fails. Full cases and further target-unaffected/non-target-failure examples are in `counterexamples.json`.

## Natural donor patches: limited coverage, no semantic transfer finding

Across all four components/tasks/class directions: 1044 pair records, 113 unique training donors, 116 unique held-out receivers. These totals contain reuse across tasks/components and are **not independent samples**. No relaxation was added when matching failed. Donors minimize canonical occupancy Hamming distance, then gate distance, then canonical index. Gate tolerance does not claim exact gating; receiver gates remain unchanged.

Both boards are fed in their **own canonical input frame**. Patches align the same expert ID and hidden-unit coordinate, not board squares and not route slot numbers. No hidden-unit rotation-equivariance is assumed; raw-to-canonical permutations are saved in `raw-alignment.json`. Donor indexing, receiver indexing and inactive rejection are independently tested.

| Component / donor task | Same-class covered receiver / target / target bad | Cross-class covered receiver / target / target bad |
|---|---:|---:|
| E1.h0 / has_win | 36 / 17 / 0 | 32 / 22 / 0 |
| E1.h0 / must_block | 41 / 3 / 1 | 27 / 7 / 0 |
| E1.h0 / has_fork | 48 / 0 / 0 | 11 / 2 / 0 |
| E1.h0 / has_fork_prevention | 46 / 2 / 0 | 16 / 8 / 0 |
| E1.h1 / has_win | 36 / 17 / 0 | 32 / 22 / 0 |
| E1.h1 / must_block | 41 / 3 / 1 | 27 / 7 / 1 |
| E1.h1 / has_fork | 48 / 0 / 0 | 11 / 2 / 0 |
| E1.h1 / has_fork_prevention | 46 / 2 / 0 | 16 / 8 / 0 |
| E3.h3 / has_win | 47 / 26 / 1 | 28 / 14 / 0 |
| E3.h3 / must_block | 44 / 3 / 2 | 22 / 12 / 3 |
| E3.h3 / has_fork | 60 / 0 / 0 | 2 / 1 / 0 |
| E3.h3 / has_fork_prevention | 57 / 0 / 0 | 5 / 4 / 1 |
| E3.h0 / has_win | 47 / 26 / 3 | 28 / 14 / 3 |
| E3.h0 / must_block | 44 / 3 / 1 | 22 / 12 / 2 |
| E3.h0 / has_fork | 60 / 0 / 0 | 2 / 1 / 1 |
| E3.h0 / has_fork_prevention | 57 / 0 / 0 | 5 / 4 / 1 |

E1.h0 fork same-class has **zero positive receiver coverage**, despite48 covered negative receivers; cross-class covers only2 positive test boards, with0 failures. Do not interpret this as necessity/rescue evidence. For B must-block, same-class causes2/3 positive failures and cross-class3/12; matched E3.h0 causes1/3 and2/12. The donor pools differ, so this is not a balanced class-direction effect. No win/block/fork/prevention feature transplantation is established.

A concrete positive result is **contextual non-interchangeability**: donor320 to receiver268, E3.h3 3483->123, same must-block class, same ply/side/geometry counts/routes, gate delta0, Hamming4, removes the receiver legal set. It is not universal: same-class donor491 to receiver145 changes B -277->579 yet retains an optimal chosen move (gate delta35, Hamming4); cross-class B must-block has9/12 positive receivers remaining optimal. Identity patches preserve **every saved stage/logit/route** on all627. Full donor IDs, activation values, class/fold/coverage and distances are in `donor-pairs.json`; experiment metrics retain matched non-target comparisons, empty sets, set and tie changes.

## Pair interaction and path restoration: retain the negative results

| Pair zero | Single-failure union | Pair failures | New beyond union | Single failures rescued | Max absolute logit nonadditivity |
|---|---:|---:|---:|---:|---:|
| E1.h0 + E1.h1 | 21 | 13 | 0 | 8 | 27 |
| E1.h0 + E3.h3 | 64 | 65 | 1 | 0 | 12 |
| E1.h0 + E3.h0 | 40 | 39 | 0 | 1 | 13 |

These are canonical whole-domain counts. E1+E3 are co-routed on only14/627 canonical boards; most combined damage occurs on disjoint routed populations. Only one new failure beyond the single-failure union appears for A+B: canonical3 (test), a bounded-prevention board. The local A+E1.h1 pair instead **rescues8** union failures and adds none, including test canonical553 where h0 alone retains the optimal canonical chosen move (but changes its complete set) while h1 alone fails; this cancellation is a counterexample to a simple additive necessity story. Small logit nonadditivity (max27) is compatible with downstream integer rounding/clamps; this experiment does not identify its arithmetic source. Sign/tie thresholding can create behavioral interactions without a special nonlinear circuit.

Training activation-only selection chose C=`norm2_output[7]` half. It causes 139/627 canonical and 1041/4520 raw bad moves, **106 ordered-route changes (63 expert-membership changes)** and 530 gate-vector changes. This is an **upstream router-affecting** perturbation, not a pure expert lesion. Restorations retain that altered route/gate state; only baseline/upstream jointly observed experts are patched.

| Restore under C | Covered canonical N | Covered upstream bad | Rescued chosen moves | Newly bad |
|---|---:|---:|---:|---:|
| restore-E1h0 | 235 | 50 | 2 | 2 |
| restore-contrast | 335 | 74 | 2 | 7 |
| restore-both | 14 | 2 | 0 | 0 |

A restores2/50 covered upstream failures but introduces2 new failures: **net zero canonical benefit**. The rescued cases137/414 are both training examples; introduced296 is training and553 is test. Contrast B restores2 but introduces7; joint restoration on14 co-observed cases rescues0/2 upstream failures. This does not identify C->A->fork mediation. M+ board137 demonstrates a real local restoration; M- board553 is its counterexample, newly damaged by restoring A. “Restoration” here is a path intervention, not an identified natural indirect effect; shared upstream damage/rerouting confounds a circuit story.

## Unsupported

- Dedicated fork, win, block or prevention neuron; exclusive expert strategy job titles; board-orientation-equivariant hidden semantics.

- Reliable same-class/cross-class strategy transfer; fork donor coverage was inadequate and matched controls can be equally or more damaging.

- A selective two-unit strategy circuit or a useful mediated rescue from C. Small per-fold classes and empty-set damage narrow the conclusions.

- Model-held-out/OOD generalization, independent symmetry samples, native-target performance changes or gameplay improvements.

## Artifacts and reproduction

Figures: `necessity-context.{png,svg}` and `patch-and-restoration.{png,svg}`. `figure-metadata.json` binds A/B/C/P/M+/M- to exact activation/tensor coordinates and case IDs, source hashes and measured inputs. No metaphorical activations or stored-weight changes are shown. Logit differences are exact whole-model intervention effects, not asserted additive contributions.

Machine evidence: `baseline-gate.json`, fixed `experiment-manifest.json`, `training-selection.json`, `cases.json`, `raw-alignment.json`, `results.json`, `experiment-vectors.json` (full logits/routes/gates/norm2/observed hidden), `effect-table.csv`, `donor-pairs.json`, `pair-interactions.json`, `path-restoration.json`, `identity-controls.json`, `counterexamples.json`, `provenance.json`, `hashes.json`. `results.json` retains all units/doses/groups, class/fold raw+canonical denominators and covered matched-control rates/IDs; table is a flat view, not a second experiment.

Run from `/home/ai/falken9-strategy-study-003`; use a **fresh nonexistent** output directory:

```sh

export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1

export PYTHONPATH=/home/ai/falken9-strategy-study-003

/home/ai/falken-9/.venv/bin/python scripts/model_strategy_study003.py --output artifacts/interpretability/study-003-reproduction-new

/home/ai/falken-9/.venv/bin/python scripts/render_strategy_study003.py --study artifacts/interpretability/study-003-reproduction-new

```

Validation and exact fresh-run comparisons are recorded separately in `verification-study003.json` at the study workspace root. Broader legacy integer tests requiring uncopied FP/training artifacts cannot pass in this bounded evidence snapshot; no packages or external data were fetched to conceal that limitation.
