# Falken-9 model research report

[Project overview](README.md) · [C64 game](docs/C64_GAME.md) ·
[Initial detailed study](docs/MODEL_INTERPRETABILITY.md)

## The answer so far

The frozen model has **causally relevant, distributed and position-sensitive
components**, but the studies have not established a dedicated win, block,
fork or fork-prevention neuron/expert. Stored weights do not change with a
board; activations, attention probabilities, routing/gates and their downstream
contributions do. A failed search for a clean detector is not proof that the
network contains no strategic information.

The same 5,195-byte F9J2 model was used throughout:
`fe180f8a931f9d92d8aa39da337bc819d0dbe4e6d971edcba00324fbc18a91c1`.
The studies run host-side exact-integer interventions and observational audits, comparing their baselines
to saved actual-target evidence. They are not new C64 performance benchmarks,
training runs or gameplay changes.

## Suggested reading routes

- **See the computation:** start with [one actual forward pass](#a-worked-forward-pass-from-stored-codes-to-one-actual-move), then return to the intervention studies.
- **Understand the guarantees:** compare [wrapper symmetry](#learned-symmetry-is-different-from-wrapper-provided-symmetry), [individual parameter intervals](#exact-parameter-intervals-beyond-a-handful-of-harmless-perturbations) and [joint safety](#individually-safe-changes-can-fail-togetherbut-a-smaller-joint-region-is-certified).
- **Understand the game:** follow [self-play coverage and its sampler qualification](#self-play-variety-is-not-exhaustive-model-coverage), then [random-opponent versus worst-case outcomes](#worst-case-safety-and-random-opponent-wins-are-different-objectives).

## Reading the figures

- **Squares:** research arrays generally use zero-based `0 1 2 / 3 4 5 / 6 7 8`;
  the C64 shows human labels `1 2 3 / 4 5 6 / 7 8 9`. Check each figure's legend
  before comparing coordinates. A raw board and its canonical orientation can
  assign different numbers to the same physical mark.
- **Experts and units:** E0–E3 are actual expert IDs, not route-slot numbers.
  An expert hidden unit is a measured activation coordinate, not a named tactic.
  Normally unselected expert values are unobserved unless explicitly evaluated
  as extra offline counterfactual work.
- **Static versus dynamic:** a stored code/scale is a parameter. Activations,
  attention, routes/gates and contributions depend on the input board. A bright
  cell is not automatically evidence that the model recognized a strategy.
- **Sets versus moves:** a legal square with score **≥0** belongs to the approved
  set. Score magnitude is not calibrated confidence or preference. The wrapper
  restores the full set to raw coordinates before applying its fixed move order.
  Thus an unchanged canonical chosen move can hide an incorrect raw decision.
- **Colors:** follow the local legend. In study009, green fills mean legal set
  membership and dark outlines mean the chosen move—not the largest score.
- **Evidence:** a changed internal value, an output failure, a local restoration
  and a selective causal mechanism are different claims. Controls and surviving
  counterexamples are part of the explanation. Click embedded figures for SVGs.

## Report index

| Study | Question and measured result | Full report | Annotated figures |
|---|---|---|---|
| 002 | Which activations/parameters associate with tactics, and does removing them affect moves? E1.h0 removal breaks a particular winning fork, but controls reject a dedicated-fork-neuron claim. | [Original detailed report](docs/MODEL_INTERPRETABILITY.md) | [Circuit map](assets/interpretability/strategy-circuit-map.png), [board examples](assets/interpretability/strategy-board-comparisons.png), [symmetry map](assets/interpretability/symmetry-position-map.png) |
| 003 | Do effects vary with dose, donor, or combinations? **128 interventions** show contextual necessity, donor non-interchangeability and cancellation. Removing E1.h0 and E1.h1 together rescues **8** canonical positions that fail under at least one individual lesion. | [Preserved report](docs/research/study-003/REPORT.md) | [Necessity/dose](assets/interpretability/study-003/necessity-context.png), [patch/restoration](assets/interpretability/study-003/patch-and-restoration.png) |
| 004 | How do actual weights support individual candidate squares? **22 interventions / 66 legal relocation contrasts** accompany exact reconstruction of all **5,643 canonical scores**, with rounding residuals explicit. One E2.h2→lane5 path supports a fork square on one board and opposes a fork square on another. | [Preserved report](docs/research/study-004/REPORT.md) | [Square paths](assets/interpretability/study-004/square-paths.png), [position contrasts](assets/interpretability/study-004/position-contrasts.png) |
| 005 | Is attention only positional, or does it reflect board context/geometry? **19 interventions / 544 aligned legal relocation contrasts** show input-sensitive attention and downstream effects, but not a selective line detector. Position-mean attention causes **238/627** canonical selected-move failures; a selected-line lesion causes **15**, versus **12** equal-size/equal-moved-mass control failures. | [Preserved report](docs/research/study-005/REPORT.md) | [Attention overview](assets/interpretability/study-005/attention-overview005.png), [contrasts](assets/interpretability/study-005/attention-contrasts005.png) |
| 006 | Do learned expert choices and gates matter? Actual routing has **0/627** failures; uniform gates cause **194/627**, and swapping expert-to-gate assignment causes **291/627**. Matched tactical controls do not establish a named specialist. | [Router report](docs/research/study-006/REPORT006.md) | [Overview](docs/research/study-006/overview006.png), [cases](docs/research/study-006/cases006.png) |
| 007 | Is a candidate expert-output path sufficient? **354 bidirectional trials** show local rescue but preservation failures. On **30 identical route-fixed control records**, preserving candidate E3 fails **5** times versus **0** for control E0. | [Pathway report](docs/research/study-007/REPORT007.md), **[common-support clarification](docs/research/study-007/COMMON-SUPPORT007.md)** | [Overview](docs/research/study-007/overview007.png), [cases](docs/research/study-007/cases007.png), [exact controls](docs/research/study-007/matched-controls007.png) |
| 008 | Are decisions fragile to small stored-code changes? **76 one-code perturbations across 38 coordinates** change no legal full sets or chosen moves on all **627** canonical boards. Four occupied-square sign-flip observations are masked out. | [Integer robustness report](docs/research/study-008/REPORT008.md) | [Overview](docs/research/study-008/overview008.png), [actual boundary/masked-flip cases](docs/research/study-008/cases008.png) |
| 009 | Can componentwise coarser precision fail even though the one-code panel was benign? **24 specifications / four component scopes** produce canonical set changes for query/value/router/readout of **1/3/1/24**. Readout produces **91 raw chosen-move failures**; restoring router scores rescues some but introduces others. | [Coarse-precision report](docs/research/study-009/REPORT009.md) | [Overview](docs/research/study-009/overview009.png), [value mechanism](docs/research/study-009/mechanism009.png), [restoration damage](docs/research/study-009/restoration-damage009.png), [raw alignment](docs/research/study-009/raw-alignment009.png), [surviving example](docs/research/study-009/robust009.png) |
| 010 | What symmetry comes from learned computation versus fixed canonicalization? Direct off-contract inputs give **1514/4520** exact sets, versus **4520/4520** through the accepted wrapper. | [Symmetry report](docs/research/study-010/REPORT010.md) | [Comparison](docs/research/study-010/overview010.png), [eight orientations](docs/research/study-010/orbits010.png) |
| 011 | Which exact distinctions survive each stage? Merged/logit vectors distinguish **627** boards; ordered routes have **12** classes and route+gates **480**. Uniqueness is not semantic decoding. | [Collision report](docs/research/study-011/REPORT011.md) | [Stage census](docs/research/study-011/cardinality011.png), [controlled counterexamples](docs/research/study-011/collisions011.png) |
| 012 | Does imposed symmetry repair correctness? Four fixed aggregates are perfectly full-set equivariant but have only **1576/312/1388/1976** exact sets out of **4520**. | [Aggregation report](docs/research/study-012/REPORT012.md) | [Outcomes](docs/research/study-012/overview012.png), [actual counterexample](docs/research/study-012/case012.png) |
| 013 | How far can a stored head coordinate change before any legal membership flips? **18 exact maximal intervals**, with full endpoint/neighbor/restoration forwards and exhaustive signed16 checks. One-at-a-time only. | [Coordinate certificate report](docs/research/study-013/REPORT013.md) | [Exact intervals](docs/research/study-013/intervals013.png), [limiting boards](docs/research/study-013/witnesses013.png) |
| 014 | Do individually safe coordinate ranges compose? **31/36 original row corners fail**. A smaller **8/16 grid-scale box** certifies every combination of the 18 selected parameters on the audited domain. | [Joint certificate report](docs/research/study-014/REPORT014.md) | [Feasible bands](docs/research/study-014/joint014.png), [actual joint failure](docs/research/study-014/witness014.png) |
| 015 | How much does continuous self-play explore? **9 raw games / 7 trajectory symmetry classes**, all draws; only **37/627 canonical boards**. Fixed-seed sampler frequencies are nonuniform in source-bound host analysis. | [Self-play coverage report](docs/research/study-015/REPORT015.md) | [Complete games](docs/research/study-015/paths015.png), [routes/coverage](docs/research/study-015/routes015.png), [sampler](docs/research/study-015/sampler015.png) |
| 016 | Does worst-case safety imply the same wins against mistakes? Three fixed ties remain loss-free from empty in both roles, but O random-opponent win probabilities differ: **848/945, 704/945, 814/945**. | [Opponent-policy report](docs/research/study-016/REPORT016.md) | [Exact outcomes](docs/research/study-016/roles-outcomes016.png), [whole-policy branch example](docs/research/study-016/branching-example016.png) |

All new figure directories also contain the corresponding SVGs for zooming.
Counts are those of each declared design, not independent discoveries or
mutually exclusive samples. The report index is a synthesis; the original
reports remain byte-identical historical records.

## Measured examples and figures

### Local necessity is not a job title

[![Measured static parameters and board-dependent activations from study002](assets/interpretability/strategy-circuit-map.png)](assets/interpretability/strategy-circuit-map.svg)

*Study002: annotated parameter/activity map. Stored weights are static; observed
activations and routing depend on the board. Click the image for the SVG.*

On canonical board 170, X to play:

```text
. . .
. . O
O X X
```

The baseline selects center (square 5), a winning fork. Removing the E1.h0
activation changes the chosen move to square 2, which loses under best play.
Other fork boards survive the same removal, and other tactical categories are
also affected. This establishes an effect in context, not an exclusive fork
function. Study003 adds graded doses and matched counterexamples rather than
renaming the unit.

E3.h3 damage includes blocking failures, but also immediate-win failures and
many empty approved sets. Empty-set damage cannot be presented as selectively
forgetting to block. Similarly, a different equally optimal chosen move is not
a mistake; reports separate set changes, empty sets, nonoptimal selections and
optimal tie changes.

[![Study002 winning-fork example and counterexamples](assets/interpretability/strategy-board-comparisons.png)](assets/interpretability/strategy-board-comparisons.svg)

*Concrete tactical effects and counterexamples must be read together; the fork
failure does not establish an exclusive fork neuron.*

### Doses, donors and combinations

Study003 tests 128 interventions, including graded doses, natural donor patches,
pairs and upstream/restoration contrasts. A same-class donor activation need not
be interchangeable with a receiver's activation. Combined E1.h0/E1.h1 removal
rescues eight canonical positions that fail under at least one single lesion;
this cancellation is evidence against a simple additive necessity story, not
proof of a dedicated two-unit strategy circuit.

[![Study003 graded necessity and contextual counterexamples](assets/interpretability/study-003/necessity-context.png)](assets/interpretability/study-003/necessity-context.svg)

*Graded damage and surviving tactical counterexamples, with the declared
canonical/raw denominators. Whole-domain effects are not selective strategy
confirmation.*

[![Study003 donor patches, pair cancellation and restoration controls](assets/interpretability/study-003/patch-and-restoration.png)](assets/interpretability/study-003/patch-and-restoration.svg)

*Donor, pair and restoration results include unfavorable controls and newly
introduced damage. Restoration is not automatically evidence of mediation.*

### One stored connection can help opposite-looking outcomes

Study004 follows E2.h2 through output lane 5 and the final head. Its pre-round
contribution is **+47,587.29** to fork square 1 on canonical board 49, but
**−1,652.04** to fork square 5 on canonical board 170. Different signed final-head
rows account for the reversal. These are path bookkeeping values, not
probabilities, uniquely assigned causal shares or sums of independent lesion
effects. Shared integer-rounding residuals remain separate.

[![Study004 same routed unit supports one fork square and rejects another](assets/interpretability/study-004/square-paths.png)](assets/interpretability/study-004/square-paths.svg)

*The same stored connection has opposite-signed pre-round support through
different final-head rows. These are actual measured paths, not probabilities
or uniquely allocated causal shares.*

[![Study004 aligned legal board contrasts and output-path counterexamples](assets/interpretability/study-004/position-contrasts.png)](assets/interpretability/study-004/position-contrasts.svg)

*Legal relocation controls keep declared geometry/candidate alignment explicit.
An executed zero-gate expert is distinct from an unexecuted, unobserved expert.*

### Attention is contextual, but that does not identify a strategy detector

Local embedding/Q/K/V values are fixed by square, occupancy and side. A pair's
QK score can stay fixed while its attention probability changes because other
keys alter the normalization. The weighted values and projection then depend
on the whole board. Query row is **not** chosen output square: all rows feed the
flattened global readout and later learned computation.

Attention is heterogeneous, not uniformly broad. Replacing it with a positional
mean damages decisions, but large unnatural perturbations can cause generic
failure. Matched geometric controls were also damaging. Adding the tested
attention row/column features did not improve confirmation AUC for wins/forks
over simple controls; that negative result limits this particular feature/probe
family, not every possible representation of those concepts.

[![Study005 measured attention concentration and intervention controls](assets/interpretability/study-005/attention-overview005.png)](assets/interpretability/study-005/attention-overview005.svg)

*Input-sensitive attention matters to decisions, but damage from an override
is not itself evidence of a selective line or threat detector.*

[![Study005 legal board relocations and attention counterexamples](assets/interpretability/study-005/attention-contrasts005.png)](assets/interpretability/study-005/attention-contrasts005.svg)

*Actual probabilities, weighted values and projections are different quantities.
The candidate square is not automatically the corresponding attention query row.*

### Router usefulness: pair membership and gate assignment are different

Study006 holds each board's expert outputs fixed while comparing six possible
expert pairs under declared gate contracts. Extra outputs for normally
unselected experts are evaluated **offline**, not claimed as deployed sparse
compute. Reversing the pair **and its matching gates** preserves all results;
reversing only the expert assignment changes which vector receives which gate
and causes 291/627 selected-move failures. Replacing the actual pair's gates
with equal weights causes 194/627 failures. These counts include empty sets.

[![Study006 actual routing, alternative memberships and gate controls](docs/research/study-006/overview006.png)](docs/research/study-006/overview006.svg)

*Actual routing is correct on all 627 boards. The best fixed pair, selected on
training boards, still fails on 107/627 boards overall. Hindsight alternatives
are diagnostic bounds, not a proposed trained policy or a deployable oracle.*

[![Study006 same-board routing examples and counterexamples](docs/research/study-006/cases006.png)](docs/research/study-006/cases006.svg)

Only 19/627 boards preserve their complete legal sets under **all six** native
renormalized pairs. This supports input-dependent routing/gating relevance, but
does not identify an expert's tactical job. On test matched win/neutral records,
the training-selected fixed pair fails on 2/23 win records versus 3/23 neutral
records; block and fork comparisons have only 2 and 4 matched records,
respectively. Sparse/reused matches do not establish selective tactical effects.

### Pathway tests: local rescue does not establish sufficiency

Study007 tests whole expert output vectors **after routing**, retaining the
receiver's readout residual, actual gates and final head. It is not a complete
network circuit test. There are 354 directed task/role trials, 354 exact identity
controls and 708 exact restoration equalities. Natural route-fixed and
route-changing board contrasts are reported separately; their donor route
changes are not interventions on the receiver's upstream router.

[![Study007 pathway preservation and local restoration outcomes](docs/research/study-007/overview007.png)](docs/research/study-007/overview007.svg)

*Candidate and control aggregate rows have different cohorts. Their rescue
counts must not be interpreted as a head-to-head efficacy comparison.*

[![Study007 actual expert-vector rescue, insufficient path and surviving control](docs/research/study-007/cases007.png)](docs/research/study-007/cases007.svg)

The training-selected candidate E3 sometimes rescues a damaged output, but
preserving it while zeroing the other selected expert still fails on 10/112
route-fixed and 30/110 route-changing trials. This does not support sufficiency.
Those trials reuse boards and tactical labels; they are not independent samples.

**The exact common-support control is unfavorable to the candidate.** On the
same 30 directed route-fixed board-pair/task records, preserving E3 fails 5 times
versus 0 for E0; natural restoration rescues 0 versus 5. Gates remain the actual
receiver gates, not equalized across expert IDs, so this is also **not a
matched-capacity specialist comparison**.

[![Study007 exact common-support controls and one common-raw-frame board contrast](docs/research/study-007/matched-controls007.png)](docs/research/study-007/matched-controls007.svg)

*The supplement is a descriptive audit of saved outcomes, not new interventions.
It corrects two potential misreadings: unequal cohorts do not demonstrate E3
superiority, and training necessity ranking used the active neutral pool—not
exact geometry-matched neutrals. Natural relocation matching was geometric.
Original report/figures remain unchanged; read the clarification alongside them.*

### Integer decision-fragility: a bounded negative result

Study008 changes one stored integer code at a time by +1 or −1 across 38 declared
coordinates: all nine output biases, four router biases, eight norm2 weights,
eight norm2 biases, and one training-selected output-weight coordinate per row.
All 76 changes are valid and each full forward is recomputed. Every original
code is restored with all-stage baseline equality afterward.

[![Study008 zero legal decision changes and exact membership-boundary census](docs/research/study-008/overview008.png)](docs/research/study-008/overview008.svg)

**None of the 76 perturbations changes a legal full set or chosen move** on the
627 canonical boards, with original-coordinate wrapper outcomes checked too.
Among 2,270 legal scores there are no exact zeros; the nearest is +54, which
needs a decrease of 55 score units to leave the nonnegative membership set.
That is a score-space distance, **not a parameter-space robustness certificate**.
Four occupied-square sign-flip observations are removed by the fixed legal mask
and therefore are not hidden gameplay failures.

[![Study008 actual nearest legal boundary, occupied masked flip and robust example](docs/research/study-008/cases008.png)](docs/research/study-008/cases008.svg)

*No fragile legal case was found in this panel. The corrected figures replace
misleading generic preliminary labels; the original generated examples remain
preserved. The actual width-8 descriptor correction was frozen before any study008
intervention. Neither correction changes the scientific design after outcomes.*

This result does not establish universal robustness, minimum possible bit width
or why historical reduced-precision exports failed. A componentwise precision
conversion changes many effective weights/scales together; it is a separate
question from a one-code perturbation.

### Coarser precision: follow a numerical change all the way to a move

Study009 starts from the **decoded deployed packet**, not a float training
checkpoint. It independently approximates four declared matrices—query, value,
router and readout—with signed codes in −127…127. For each row, choose the
smallest power-of-two right shift whose rounded codes fit that range, then
increase the row exponent by the shift. Biases and all other components remain
unchanged. There is **zero clipping**. Each scope has six fixed approximation,
restoration and identity specifications, for 24 total.

This is a new packet-derived diagnostic, **not a verified reproduction of the
historical INT8 exports**, a new deployment candidate or a C64 speed/RAM result.
The study008 one-code panel used different coordinates; these two studies do
not isolate multiplicity as the sole reason for their different outcomes.

[![Study009 declared coarser-precision panel and canonical/raw outcomes](docs/research/study-009/overview009.png)](docs/research/study-009/overview009.svg)

| Approximate matrix | Canonical set changes /627 | Canonical wrong-or-empty choices /627 | Raw set changes /4520 | Raw wrong-or-empty choices /4520 |
|---|---:|---:|---:|---:|
| Query | 1 | 0 | 8 | 0 |
| Value | 3 | 1 | 20 | 11 |
| Router | 1 | 0 | 8 | 4 |
| Readout | 24 | 12 | 180 | 91 |

#### A. A small local change can propagate through gates to a sign crossing

On canonical board109, one displayed value-weight example changes from
`4735 × 2^-15` to `18 × 2^-7`. The **whole value matrix** is approximated; that
one displayed coefficient is an illustration, not isolated single-weight causal
attribution. The measured value activation changes 1505→1552, while query and
attention probabilities remain unchanged. Downstream normalization and routing
scores change; the selected expert pair stays `[2,3]`, but its Q15 gates change
`[32429,339]`→`[31670,1098]`.

The only approved legal square, internal square0, changes from **+17,305 to
−8,116**, emptying the set. Restoring the baseline router scores at the declared
cutpoint restores that square to **+15,354**, while the upstream approximation
remains in place. This identifies a contribution of that branch to this hybrid
case, not an exclusive strategic role or a natural mediation result.

[![Study009 actual value-activation, gate and final-membership chain](docs/research/study-009/mechanism009.png)](docs/research/study-009/mechanism009.svg)

#### B. Restoring the original gates is not a universally safe repair

For the readout approximation, restoring baseline router scores/gates reduces
canonical chosen failures **12→8**, but that combines **5 rescues and 1 newly
introduced failure**. Raw failures change **91→65**, with **34 rescues and 8 new
failures**. The same receiver boards are used; this is not an unequal-cohort
comparison.

Board157 makes the limitation concrete: its legal square0 is accepted at
**+16,341** in baseline and **+9,169** after readout approximation, but becomes
**−1,449** after restoring baseline router scores. The pair remains `[0,3]`.
Original gates can be incompatible with perturbed residual/normalization/expert
activity; this is an intentionally artificial mixed-state intervention.

[![Study009 restoration-created failure on an otherwise surviving board](docs/research/study-009/restoration-damage009.png)](docs/research/study-009/restoration-damage009.svg)

Eight self-cutpoint controls preserve every stage, and four clean-code
restorations recover the full baseline. Substituting baseline merged vectors
restores every final score, as expected for an unchanged deterministic final
head; that mechanical sufficiency does not discover a unique strategy circuit.

#### C. Correct canonical choices can conceal incorrect raw choices

The router approximation adds internal square0 to board528's set. Its canonical
chosen square8 remains correct, but an inverse-transformed raw orientation makes
the fixed tie rule select the new, nonoptimal member. The orbit has **4 wrong
choices out of 8 boards**, despite zero wrong canonical chosen moves for this
component. That is why full sets and actual raw-coordinate ties are separate
gates; neither can be replaced by multiplying canonical errors by eight.

[![Study009 canonical and raw-coordinate tie counterexample](docs/research/study-009/raw-alignment009.png)](docs/research/study-009/raw-alignment009.svg)

#### D. Changed internal activity is not automatically behavioral damage

For the empty board under query approximation, query values, attention,
readout, gates, merged activations and scores change, but all nine legal scores
remain nonnegative. The complete approved set and center tie-selected move
remain unchanged. This counterexample belongs beside the failure cases.

[![Study009 surviving empty-board example despite changed internal values](docs/research/study-009/robust009.png)](docs/research/study-009/robust009.svg)

### A worked forward pass: from stored codes to one actual move

The following two pages follow **canonical board 341** through the unchanged
network. They are measured arithmetic, not a proposed strategy diagram. Read
A–D first, then E–H. Lowercase a–i name squares; the eight vector lanes are latent
features, not eight other squares.

[![Actual board, static embedding codes and measured attention](docs/research/study-010-011-walkthrough/forward-attention1011.png)](docs/research/study-010-011-walkthrough/forward-attention1011.svg)

**A/B — input and embeddings.** Occupancy, absolute-position and side codes are
stored parameters. Their sum is input-dependent. The example shows the actual
eight-lane sum for query square e; the other squares are processed too.

**C/D — attention.** Rows are query squares and columns are key squares.
Every Q15 row sums to 32768. The illustrated weighted-value numerator for lane 0
is −54,675,153, rounded to −1669. Projection and a residual lead to the global
72→8 readout. Attention on query e is not a decision to play square e, and
attention mass is not move confidence.

[![Actual selected experts, integer merge, output head and legal masking](docs/research/study-010-011-walkthrough/forward-experts1011.png)](docs/research/study-010-011-walkthrough/forward-experts1011.svg)

**E/F — routed experts.** Expert IDs [3, 0] receive matching gates
[24294, 8474]. In lane 0, their outputs 520 and 4252 form weighted numerator
48,664,328. After the specified rounding and addition of readout residual 3820,
merged lane 0 is 5305. Other experts are unobserved, not measured zeros.

**G/H — head and wrapper.** All eight merged lanes feed each output row. For
square f, the actual stored-code dot product is 376,722,251; exponent −13 and
native bias −8029 produce score 37958. Thresholding all nine scores and masking
occupied squares gives {c, f}. The fixed priority chooses f in this frame.
A larger positive score is not a preferred move: membership, not ranking, is the
learned contract. The whole set must be inverse-mapped before raw-coordinate ties.
[Exact worked values](docs/research/study-010-011-walkthrough/walkthrough1011.json).

### Learned symmetry is different from wrapper-provided symmetry

Study010 deliberately bypasses canonicalization and feeds all **4,520 unique raw
boards** directly to the canonical-trained network. This is an **off-contract
diagnostic**, not a failure of the accepted game. The direct path returns the
correct complete legal set on **1,514/4,520** boards. The unchanged canonicalizing
wrapper remains correct on **4,520/4,520**.

[![Measured direct-network versus fixed-wrapper symmetry](docs/research/study-010/overview010.png)](docs/research/study-010/overview010.svg)

The direct path has 485 empty sets and 1,151 nonoptimal nonempty choices. Another
345 choices differ from the wrapper but are still optimal—not failures. Only
14/627 canonical boards keep the correct complete set across all eight direct
orientations. The 5,016 orbit observations reuse 4,520 distinct inputs; repeated
orientations of symmetric boards are not independent evidence.

[![One actual corner-X board through all eight direct orientations](docs/research/study-010/orbits010.png)](docs/research/study-010/orbits010.svg)

On this real example, moving X to a different corner changes direct predictions,
including false members. Some panels still choose the correct center while
approving other, nonoptimal squares. One correct chosen move therefore does not
establish complete-set correctness. Absolute positional embeddings and a global
readout allow orientation dependence, but this experiment does not isolate their
individual causal contributions. [Full study010](docs/research/study-010/REPORT010.md).

### Information survives even when routing metadata collides

Study011 compares **exact full integer vectors**, with shape-aware equality and
an independent tuple census—not a two-dimensional projection. The full merged
vectors and final logits distinguish all 627 canonical boards. Ordered routes
have only 12 classes; route plus exact gates has 480.

[![Exact representation class counts across measured stages](docs/research/study-011/cardinality011.png)](docs/research/study-011/cardinality011.svg)

Finite uniqueness means an arbitrary lookup decoder could distinguish the audited
boards. It does **not** establish a simple semantic decoder, generalization,
causal use of every distinction, or a named strategy circuit. Top-2 out of four
experts permits only 12 ordered routes by construction, so low route cardinality
is not proof that routing is useless.

[![Controlled routing collisions and distinct legal masks on actual boards](docs/research/study-011/collisions011.png)](docs/research/study-011/collisions011.svg)

Boards 452 and 413 have identical ordered experts [3, 0], exact gates [32768, 0],
ply, side, geometry counts and legal mask—yet different tactical labels and full
optimal sets. Their richer expert/merged/logit vectors remain distinct. A selected
zero-gate expert still executes; an unselected expert is unobserved. Separately,
boards with identical **signs** can have different legal sets because occupied
squares differ. No full-logit collision was found on these 627 boards; the sign
example must not be presented as one. [Full study011](docs/research/study-011/REPORT011.md).

### Perfect imposed symmetry still does not guarantee correct play

Study012 follows the symmetry finding with four **predeclared offline output
aggregations** across all eight orientations. It reuses the measured direct
logits and adds no neural forwards. Mean uses the sign of the exact integer sum;
there is no rounding of a small negative mean to zero. Scores are not calibrated
probabilities, and these are not deployed replacement policies.

[![Four perfectly equivariant policies with incorrect complete sets](docs/research/study-012/overview012.png)](docs/research/study-012/overview012.svg)

| External aggregation | Exact full sets /4520 | Empty sets | Nonoptimal nonempty choices |
|---|---:|---:|---:|
| Exact mean sign | 1576 | 304 | 1344 |
| Intersection | 312 | 3804 | 0 |
| Union | 1388 | 0 | 1763 |
| At least 4/8 votes | 1976 | 144 | 1182 |
| Accepted canonicalizing wrapper | 4520 | 0 | 0 |

All four aggregates pass full-set equivariance on every 36,160 raw-board/transform
observation per policy. That property says the set rotates consistently, **not
that the set contains exactly the correct moves**. Fixed coordinate priority can
still make selected moves non-equivariant; that is separate from set symmetry.

[![Actual aggregation counterexample with exact sums, extrema and votes](docs/research/study-012/case012.png)](docs/research/study-012/case012.svg)

A canonical branch supplies an exactly correct set. Consequently intersection
cannot add a false member, but it can discard every optimal member. Union cannot
omit an optimal member, but can add a nonoptimal square selected by raw priority.
Both constraints hold throughout the audit. This does not rule out every possible
ensemble; it answers exactly the four frozen algorithms.
[Full study012](docs/research/study-012/REPORT012.md).

### Exact parameter intervals: beyond a handful of harmless perturbations

Study013 asks a different question from the ±1 panel: **how far can one stored
parameter code move before any legal membership sign changes?** It fixes all
nine output biases and the descriptor-first column-0 weight in each output row,
for 18 coordinates. No coordinate was selected for producing an interesting
failure.

[![Exact safe stored-code intervals for 18 final-head coordinates](docs/research/study-013/intervals013.png)](docs/research/study-013/intervals013.svg)

For each coordinate, exact integer inequalities are intersected over every
applicable legal square on all 627 canonical boards, then clipped to signed16
code bounds. This gives a **maximal one-coordinate interval**, with every other
parameter, exponent, lookup table and wrapper operation held fixed. An independent
verifier enumerates every representable code and recovers the same intervals.

Two examples, in stored-code delta units:

| Coordinate, zero-based | Original code | Inclusive safe delta interval |
|---|---:|---:|
| Output bias[1] | 915 | [−54, +2108] |
| Output weight[1, 0] | −2869 | [−56, +1012] |

These units are not interchangeable. A bias-code change adds directly to the
integer score after dot-product rounding; a weight-code change affects the dot
through the board-specific merged activation and row scale. Bias exponents must
not be applied a second time. The proof retains half-away rounding and signed32
output clamping; scores remain arbitrary membership indicators, not probabilities.

[![Actual limiting boards at safe endpoints and the nearest failing codes](docs/research/study-013/witnesses013.png)](docs/research/study-013/witnesses013.svg)

The first displayed bias witness, canonical board 474, has only square a in its
approved set. Bias[0] can move from 1634 down to −1355, where its score is exactly
zero and membership remains valid. The next code, −1356, gives score −1 and an
empty set. The weight witness instead has multiple approved squares: removing a
member changes the complete set without necessarily changing the selected move.

**All 36 safe endpoints preserve every legal set.** All 36 immediately adjacent
in-range codes change at least one legal sign. There are no source-bound censored
sides. Each endpoint/neighbor is checked with a fresh full integer-network batch
over all 627 boards; another 72 full restoration batches recover all baseline
stages. These are host batches, not new C64 executions.

The endpoints also produce **259 occupied-square sign-crossing observations**,
summed over the different candidate runs. Those squares are legally masked out;
the count is not 259 distinct boards or 259 gameplay failures. Conversely, the
upper failing neighbor for bias[3] has **zero canonical chosen-move failures but
four wrong raw-coordinate choices**. Correct full-set inverse restoration and
fresh raw ties remain necessary even when canonical choices look unchanged.

Parent verification reruns five tests and the independent audit: **297,533,440
code–board sign evaluations** and **411,939 scalar head outputs**. All 14 generated
artifacts match their reproduced counterparts; the 69-entry source/evidence ZIP
rebuilds identically. The original 1,492 prior-research files and 51 protected
main/model/application files retain their hashes. The 655,400 public-wrapper
calls reported by the study are **composed checks using test-only neural-output
fixtures**, not that many separate neural forwards.

**These intervals do not certify simultaneous changes.** Nor do they establish
upstream robustness, generalization to new inputs, a lower-precision deployment,
or new speed/RAM results. All studied boards were already trained/audited.
[Full study013](docs/research/study-013/REPORT013.md) ·
[Exact certificates](docs/research/study-013/certificates013.json) ·
[Historical reproduction prerequisites](docs/research/study-013/REPRODUCTION.md).

### Individually safe changes can fail together—but a smaller joint region is certified

Study014 tests the gap left explicitly open by study013. Each selected output
row has two variable codes: its bias and column-0 weight. Combining the two
individually safe intervals creates a rectangle; combining all rows creates an
18-coordinate box. **The original independent ranges do not compose:** 31 of
36 full-network row-corner candidates change legal sets, and every one of the
nine original row rectangles is unsafe.

[![Exact feasible bands versus independent intervals and the accepted joint box](docs/research/study-014/joint014.png)](docs/research/study-014/joint014.svg)

The pale region shows jointly feasible bias/weight values. Orange rectangles
come from the independent study013 intervals; their corners can leave that
region. Green rectangles are jointly certified. The drawn shading samples the
boundary for display; the saved bands retain exact constraints for every
signed16 weight code.

**One actual counterexample:** on canonical board 38, square 0 has score 5463.
Moving only the bias to its safe endpoint gives 2474; moving only the weight
gives 1460. Changing both gives **−1529** and removes square 0 from the approved
set. That joint value comes from a complete new neural forward. The two
single-change values are independent scalar evaluations on the same saved
merged vector, consistent with study013's full endpoint checks. This example
changes the full set but not the selected move.

[![Real individually-safe but jointly-failing changes and an accepted extremum](docs/research/study-014/witness014.png)](docs/research/study-014/witness014.svg)

The shrink search was frozen before outcomes: scales 0/16 through 16/16, moving
each endpoint toward its original code with integer truncation toward zero.
**8/16 is the largest passing grid scale.** Scale 9/16 and every larger declared
scale fail. This is grid-maximal, not a continuously optimal or globally largest
box, and does not imply that exactly half is a universal robustness rule.

The accepted box certifies **every integer combination** of its 18 coordinates,
not merely the tested corners. For each legal member, take the exact worst-case
minimum rounded score over its row rectangle and require it to remain ≥0. For
each legal nonmember, require the maximum to stay <0. Final-head rows are
independent and upstream merged vectors remain fixed, so these inequalities
compose across rows. A separate decoder/scalar audit also checks feasible bias
bands across every signed16 weight value. This is a mathematical finite-domain
certificate backed by real neural witnesses—not a claim to have executed every
high-dimensional corner or parameter combination.

The two recorded runs each execute **117 full neural batches**: baseline,
58 candidates and 58 restorations. Parent acceptance reruns four tests with one
full-study integration test explicitly skipped, then independently recalculates
**589,824 row-weight codes**, **148,766,720 applicable board/weight constraints**
and **332,937 full-head scalar outputs**. It matches original and accepted extrema
to saved actual network outputs, verifies 15 byte-identical reproduced files,
and rebuilds the 67-entry evidence ZIP identically. No frozen evidence is
rewritten. Composed wrapper calls remain distinct from actual neural forwards.

The guarantee covers the same 627 canonical / 4,520 raw audited boards and only
these 18 final-head codes. Other weights, scales, lookup tables and wrapper code
are fixed. It is not upstream robustness, a new-domain guarantee, compression
of the deployed model, or a C64 performance result. The accepted game remains
unchanged. [Full study014](docs/research/study-014/REPORT014.md) ·
[Joint box certificates](docs/research/study-014/boxes014.json) ·
[Observed and constraint-only extrema](docs/research/study-014/extremum-witnesses014.json).

### Self-play variety is not exhaustive model coverage

Study015 follows every opening permitted by the accepted model and the game's
opening-only variation policy. It executes a fresh full neural forward for every
mark; the later turns use the actual fixed raw-coordinate tie order. These are
**host policy-emulation diagrams**, not screenshots or new native C64 replays.

[![Nine actual model-approved opening branches, each followed through a complete game](docs/research/study-015/paths015.png)](docs/research/study-015/paths015.svg)

All nine openings yield nine distinct raw move sequences, seven full-trajectory
rotation/reflection classes, and nine draws after nine marks. A trajectory class
uses one fixed transform over the entire ordered game, not a fresh orientation
at every step. The first deterministic game is **5 → 3 → 2 → 8 → 4 → 6 → 9 → 1 → 7**.
Every mark follows actual inference, including each empty-board opening.

[![Exact expert routes, gates and limited board coverage across self-play paths](docs/research/study-015/routes015.png)](docs/research/study-015/routes015.svg)

Across the nine games, 81 fresh game forwards visit only **37/627 canonical**
and **64/4,520 raw nonterminal boards**, with seven of the twelve ordered routes.
The empty board is evaluated nine times but covers one canonical position.
Terminal states are excluded from those denominators. Every visited position
has a draw value under optimal play, so this demonstration never exercises the
already-winning or already-losing positions present elsewhere in the domain.
Repeated draws cannot replace the exhaustive policy audit.

#### A correction to the opening-randomness description

The accepted sampler's rejection threshold and no-immediate-repeat rule do not
establish independent, uniformly distributed opening frequencies. Under an ideal
independent candidate source, the successful conditional transition would be
1/8 to each other square, with stationary marginal 1/9. **The shipped source uses
a fixed-seed deterministic LFSR instead.** Its state is separate from music and
animation and resets to `$A7`; these facts make it reproducible, not genuinely
random or automatically fair.

[![Ideal transition law versus the actual fixed-seed sampler orbit](docs/research/study-015/sampler015.png)](docs/research/study-015/sampler015.svg)

Source-bound host enumeration finds one transient transition followed by a
248-opening-event cycle. Counts for screen squares 1 through 9 within that
cycle are **31, 31, 31, 16, 17, 29, 41, 31, 21**. Only 26 of 72 possible directed
no-repeat transitions occur in that cycle, although all 72 are possible across
the separately enumerated 2,295 previous-opening/nonzero-state combinations.
Immediate-repeat prevention still holds. These are exact code-state findings,
not empirical native randomness measurements. A separate check executes the
**actual accepted PRG's sampler instructions** under py65: all 2,295 states
match the host census, including selected square, PRNG state and rejection
attempt count. It reproduces the same transient and cycle and passes 1,067
guard/skip cases. The parent rerun reproduces the complete evidence JSON
byte-for-byte. This is isolated assembled-subroutine parity in flat RAM,
not full native-game replay, physical-hardware acceptance or empirical fairness.
[Machine-code parity evidence](docs/research/study-015/machine-sampler-parity.json) ·
[Read-only harness](docs/research/study-015/machine-sampler-parity.py).

The current [game guide](docs/C64_GAME.md#how-the-first-marker-is-chosen) now
qualifies its earlier “uniform” wording; historical reports and accepted release
bytes remain unchanged. This changes no move approvals and no game behavior.
Self-play is frozen inference, not learning.

Parent checks rerun five tests and the independent arbitrary-integer whole-forward
audit, matching 1,701 game-stage arrays / 68,931 integer values and all 627
reference-board forwards. Eighteen artifacts reproduce byte-for-byte. The
independent auditor reconstructs packet decoding, geometry, complete-set inverse
mapping, raw ties, minimax membership and the sampler census. These are host
proofs, not a new native or physical-hardware acceptance claim.
[Full study015](docs/research/study-015/REPORT015.md) ·
[Complete game records](docs/research/study-015/games015.json) ·
[Sampler transitions](docs/research/study-015/opening-transitions015.json).

### Worst-case safety and random-opponent wins are different objectives

Study016 fixes three tie policies and both player roles before outcomes:
accepted raw priority, its reversal, and greatest raw-restored score **within the
legal approved set**. The latter two are offline counterfactuals, not runtime
changes. The human opponent is explicitly modeled as selecting uniformly among
currently empty squares on every turn, with play stopping immediately at a win
or full board.

[![Exact outcomes for three fixed tie policies in both player roles](docs/research/study-016/roles-outcomes016.png)](docs/research/study-016/roles-outcomes016.svg)

| Model role | Fixed tie policy | Exact win probability | Exact draw probability | Loss probability |
|---|---|---:|---:|---:|
| X, first | Accepted | 95/96 | 1/96 | 0 |
| X, first | Reversed | 95/96 | 1/96 | 0 |
| X, first | Greatest approved score, offline | 95/96 | 1/96 | 0 |
| O, second | Accepted | 848/945 | 97/945 | 0 |
| O, second | Reversed | 704/945 | 241/945 | 0 |
| O, second | Greatest approved score, offline | 814/945 | 131/945 | 0 |

All three retain worst-case draw safety from the empty board: independent
exhaustive traversal of every legal human reply finds **no losing history** in
any of the six panels. That does not mean every game draws against mistakes,
nor that a forced-loss position outside these reachable paths can be saved.
The accepted policy has the highest O win rate among these three under the
specified random opponent; this is neither a search for an optimal exploitation
policy nor a claim of superiority against arbitrary human behavior.

Expected total marks and supported complete-history counts also differ even
when X win probabilities agree. Histories do **not** have equal probability:
each receives the product of reciprocal human branching counts along its path.
The report retains exact rational game lengths and all reachable-state values.
No sampled win rate or statistical extrapolation replaces this enumeration.

[![Actual board with equally minimax-safe moves and different whole-policy continuation values](docs/research/study-016/branching-example016.png)](docs/research/study-016/branching-example016.svg)

With human X at h (screen square 8), model O approves {b, e, g, i}. Accepted
priority chooses e, with raw score 4262; the other two choose i, with score 54749.
Continuing each **whole fixed policy** gives win probabilities 97/105, 23/35 and
6/7 respectively against random legal replies. Reverse-priority and greatest-score
policies share that first move but differ later, so their outcome difference is
not attributed solely to the first choice. The largest membership score is not
the largest measured continuation win probability, and is not confidence.

Each analysis run binds all 627 canonical boards through real full-network
execution once, then restores logits/sets across all 4,520 raw boards. The
rational branching analysis reuses those validated outputs **offline**; a branch
visit is not a new forward and no lookup policy is installed in the game.
Parent verification reruns seven tests and the independent scalar decoder /
whole-network audit, matching **13,167 stage arrays and 533,577 integer values**.
A separately structured bottom-up rational dynamic program and explicit
complete-history traversal agree on outcomes, lengths, support and safety.

All 17 artifacts reproduce byte-for-byte, and the 84-entry evidence ZIP rebuilds
identically. Historical preservation retains an explicit exception for one
concurrently parent-edited verification document, with both hashes disclosed;
no accepted runtime, model or old isolated-study bytes are changed. These are
finite host analyses on already trained/audited boards, not new native C64,
physical-hardware or general-strength evidence.
[Full study016](docs/research/study-016/REPORT016.md) ·
[Measured branching board](docs/research/study-016/example016.json) ·
[Preservation disclosure](docs/research/study-016/preservation-exceptions016.json).

## Evidence, preservation and reproduction boundaries

Before new interventions, each follow-up reproduced **13,167 saved stage-vector
comparisons / 627 canonical boards** and the composed full-set wrapper outcomes
on **4,520 raw boards**. Validation splits group canonical boards to prevent
symmetry copies leaking between folds. These are **probe selection/confirmation
splits, not model-held-out generalization**: the frozen model was already
trained/audited on this finite domain.

Fork definitions differ between reports: studies002–004 use priority-gated
board/candidate labels, while study005's independent geometric fork candidates
also include positions those earlier gates exclude. Their positive counts must
not be compared as if they were the same task. Strict matching sometimes leaves
zero held-out tactical examples; the studies retain that absence rather than
relaxing the controls after seeing results.

Studies003/004/005 respectively reproduced **23 / 28 / 25** output artifacts
byte-for-byte. Their selected report, figure, frozen-experiment and verification
snapshots are now in this repository, bound by the
[consolidation manifest](docs/research/consolidation-manifest.json):

- [003 experiment](docs/research/study-003/experiment-manifest.json) / [verification](docs/research/study-003/verification.json)
- [004 experiment](docs/research/study-004/experiment-manifest.json) / [verification](docs/research/study-004/verification.json)
- [005 experiment](docs/research/study-005/experiment-manifest005.json) / [verification](docs/research/study-005/verification.json)

- [006 experiment](docs/research/study-006/experiment.json) / [verification](docs/research/study-006/verification.json)
- [007 experiment](docs/research/study-007/experiment.json) / [verification](docs/research/study-007/verification.json) / [common-support audit](docs/research/study-007/verification-common-support.json)
- [008 experiment](docs/research/study-008/experiment.json) / [descriptor amendment](docs/research/study-008/descriptor-amendment.json) / [visual amendment](docs/research/study-008/visual-amendment.json) / [verification](docs/research/study-008/verification.json)

Studies006–008 additionally reproduced **52 stage artifacts plus 5 supplementary
artifacts** byte-for-byte. Parent verification reran four focused tests,
independently recalculated the stored expert/head/gate and raw-wrapper audits,
and checked all 907 pre-existing research-file hashes. Selected report/figure
copies are bound by the same consolidation manifest; no scientific source or
old artifact was silently replaced.


Study009 reproduced **50 artifacts and both 152-entry source/evidence ZIPs**
byte-for-byte. Parent verification reran eight tests and independently
recalculated the audit, including **135,432 final-affine scalar checks** and
**108,480 actual public-wrapper calls** using explicitly test-only saved neural
logits. All **1,114** earlier research files remained hash-identical. This is not
a new C64 execution or a claim of 108,480 independent full neural forwards.

[009 experiment](docs/research/study-009/experiment.json) ·
[Verification](docs/research/study-009/verification.json) ·
[Historical reproduction prerequisites](docs/research/study-009/REPRODUCTION.md)

Studies010–012 add **eight measured PNG/SVG figure pairs**, including a two-page
worked forward. Independent parent verification passes **13 tests** and checks
all **51 byte-identical reproduced artifacts**, both deterministic ZIP rebuilds,
source hashes and the 1,258-entry initial / 1,414-entry pre012 inventories.
Numerical audits recompute 13,100 exact representation classes, the worked
embedding/attention/merge/head scalars, 162,720 aggregate membership scalars and
144,640 full-set equivariance checks. Audit writes were confined to fresh scratch
copies; all 1,492 research-checkout files retained their hashes. These are finite
host-side/composed checks, not additional native C64 runs or new model-held-out
observations. Reproduction prerequisites remain external.

- [010 manifest](docs/research/study-010/manifest010.json) / [historical verification](docs/research/study-010/verification.json)
- [011 manifest](docs/research/study-011/manifest011.json) / [historical verification](docs/research/study-011/verification.json)
- [012 manifest](docs/research/study-012/manifest012.json) / [historical verification](docs/research/study-012/verification.json)

**Documentation consolidation is not a merge of the research executables.**
Full raw vectors, donor/pair tables, source/evidence bundles and baseline
fixtures remain in the isolated research archive, not in the minimal game
package. Original report commands and absolute paths describe that historical
workspace; they are not portable fresh-clone instructions. The verification
snapshots are historical records, not claims that those complete raw directories
are shipped here. Study003 also retains broader legacy-test failures caused by
uncopied old training/float fixtures; its focused new-method tests and deterministic
reproduction are separate evidence. This index does not erase those limitations.

## What is worth probing next?

Studies006–012 now cover routing, pathway preservation, small-code and coarse-
precision diagnostics, learned versus fixed symmetry, exact representation
collisions, and externally imposed equivariance. The bounded designs are complete;
their conclusions and negative controls are retained above.

Study013 now supplies exact **one-coordinate** final-head certificates, rather
than extrapolating a benign ±1 test into broad robustness.

Study014 closes that particular composition question: the original intervals
fail jointly, while a smaller explicitly constrained box is certified.

Study015 now distinguishes visible game variety from full policy coverage and
qualifies the fixed-seed opening sampler's fairness. The accepted PRG's actual
sampler instructions now pass an exhaustive assembled-subroutine comparison;
this does not turn the full neural trajectory study into native replay evidence.

Study016 completes the declared three-policy/two-role comparison: all remain
worst-case safe from empty, while random-opponent outcomes differ as O. No
counterfactual tie policy is deployed and no further policy search is implied.

The current bounded research pass is complete through study016. Potential future
work should be separately scoped—for example native full-game checks for new
claims, new explicitly authorized models, or new interventions with selective
controls—not an unbounded extension of the present panels. Public publication
and refreshing the frozen application010 upload package remain separate steps.

Further experiments should address a genuinely new question rather than repeat
parameter ablations or enlarge a panel after seeing favorable outcomes. The
accepted model and application remain frozen throughout.

For the pathway study, patch direction, comparison distribution and output
metric must be declared before confirmation. Patching can test necessity and
restoration differently; neither direction automatically proves a complete
circuit.[1] For this membership-head model, use exact score margins plus complete
legal sets and chosen-move outcomes—not a categorical output softmax borrowed
from a language model.

Every new experiment should keep the deployed packet and numbered releases
unchanged, cap its search before evaluation, retain controls/counterexamples and
stop when the declared question has an answer—even if the answer is negative.

## Sources

[1] https://arxiv.org/abs/2404.15255 — How to use and interpret activation patching