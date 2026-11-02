# Study005: bounded attention and board geometry

Baseline: 13167 exact saved-target stage vectors, 5643 logits, 627 canonical boards; complete legal sets/moves/ties reproduced over4520 raw boards. Frozen model5195 bytes. Host composed proof only; no new emulator execution.

## Outcomes
Actual attention is heterogeneous and often concentrated: mean row entropy 1.555435 bits (max log2(9)); effective keys 3.4230; zero fraction 0.0940792; mean row maximum 0.599631.
Position-mean P MSE (Q15 units squared): 42880578.228090. Within ply/query/key/own-opponent occupancy MSE: 5203803.589037. Local QKV within ply/square/occupancy MSE: 0.000000. Local QKV is token-local, not itself a whole-board detector; attention normalization and weighted values vary with the board.
Training-only line selection: {'line_id': 0, 'line': [0, 1, 2], 'train_matched_n': 103, 'mean_candidate_line_mass_contrast': -0.16560823014638956}. Eight fixed geometric groups ranked by natural training pair probability contrast, not lesion outcomes; one selected group confirmed alongside horizontal/diagonal and matched controls.

## Finite interventions (19, all retained)
|Intervention|Canonical errors/627|Set changes|Raw errors/4520|Route-order changes|Gate changes|
|---|---:|---:|---:|---:|---:|
|noop|0|0|0|0|0|
|uniform|233|441|1711|333|572|
|identity-attention|255|491|1902|428|589|
|position-mean|238|435|1712|334|569|
|half-position-mean|180|362|1320|216|550|
|horizontal-target-1of2|40|83|282|29|483|
|horizontal-target-2of2|68|146|496|63|507|
|horizontal-control-1of2|26|60|200|32|474|
|horizontal-control-2of2|59|123|416|63|494|
|diagonals-target-1of2|53|108|377|37|483|
|diagonals-target-2of2|85|187|635|75|504|
|diagonals-control-1of2|51|115|370|39|483|
|diagonals-control-2of2|68|167|512|75|500|
|training-line-target-1of2|9|15|78|8|408|
|training-line-target-2of2|15|38|131|16|432|
|training-line-control-1of2|4|14|24|7|406|
|training-line-control-2of2|12|31|83|12|429|
|value-position-mean|230|425|1707|300|561|
|projection-position-mean|243|450|1780|320|580|

All probability overrides have exact nonnegative Q15 row sums32768. Target/control masks have identical per-row cardinality, disjoint edges, and exactly equal moved mass min(target mass,control mass) × dose/2 floored. This caps removal, so full dose does NOT necessarily remove every target edge. Original masked mass is proportionally removed; transferred mass is apportioned to complement keys. Floors then largest remainders, low-key ties. Zero-weight redistribution uses uniform eligible keys; inactive rows are identity. Group controls avoid the selected group but can lie on other winning lines; they are not guaranteed semantically neutral. All19 are upstream: route-changing and route-unchanged outcomes reported separately in machine evidence; no post-routing attribution.

## Matched geometry and probe confirmation
Same-ply single mark relocation across legal nonterminal raw boards; fixed candidate stays empty; same per-mark corner/edge/center counts; same fold; label-positive receiver versus label-negative donor. Canonical donor is independently canonicalized and both attention axes plus value/projection rows realigned to receiver raw frame. No route matching is imposed; changed routes/gates explicitly retained. One lexicographic donor per positive candidate; donors may be reused.
|Task|Fold (0 train,1 val,2 test)|Positive candidates|Matched|
|---|---:|---:|---:|
|win|0|213|90|
|win|1|80|18|
|win|2|88|15|
|threat|0|349|145|
|threat|1|110|17|
|threat|2|129|28|
|fork|0|247|167|
|fork|1|105|28|
|fork|2|101|36|

|Task|Fold|Feature|Positives / N|AUC|Balanced accuracy|
|---|---:|---|---:|---:|---:|
|win|1|controls|80/433|0.8006728045325779|0.5068342776203966|
|win|2|controls|88/494|0.8119821988356472|0.5385412001791312|
|win|1|controls_plus_attention_rowcol|80/433|0.7931303116147309|0.529001416430595|
|win|2|controls_plus_attention_rowcol|88/494|0.8072100313479624|0.5429914912673534|
|win|1|controls_plus_projected_candidate_globalmean|80/433|0.805099150141643|0.5068342776203966|
|win|2|controls_plus_projected_candidate_globalmean|88/494|0.8131437527989253|0.5385412001791312|
|threat|1|controls|110/433|0.8170419363917816|0.6298761609907121|
|threat|2|controls|129/494|0.8133906764362323|0.6205904215779973|
|threat|1|controls_plus_attention_rowcol|110/433|0.821671826625387|0.6328736279200675|
|threat|2|controls_plus_attention_rowcol|129/494|0.8135712010194329|0.6399702665392375|
|threat|1|controls_plus_projected_candidate_globalmean|110/433|0.8159864902898959|0.6373205741626794|
|threat|2|controls_plus_projected_candidate_globalmean|129/494|0.8101518530317511|0.6294786025273442|
|fork|1|controls|105/433|0.7942653890824622|0.5112369337979094|
|fork|2|controls|101/494|0.7949638475297911|0.5060841962058801|
|fork|1|controls_plus_attention_rowcol|105/433|0.7859175377468061|0.5319976771196283|
|fork|2|controls_plus_attention_rowcol|101/494|0.7793817549693901|0.5233416471418134|
|fork|1|controls_plus_projected_candidate_globalmean|105/433|0.7851335656213705|0.5112369337979094|
|fork|2|controls_plus_projected_candidate_globalmean|101/494|0.7777945733504649|0.51598518630489|

Fixed ridge10 and threshold0.5; controls include ply and candidate identity one-hots plus own/opponent corner/edge/center counts. No tuning or added feature search. These are independent candidate labels, not output softmax choices. AUC/probe increments are descriptive correlates, not causal strategy circuits; no multiplicity significance claimed.

## Interpretation and limits
Attention, values and projected vectors respond to legal board relocations beyond aggregate occupancy counts. This is not evidence of a dedicated line/threat detector: local embedding/QKV are deterministic occupancy+position+side functions; probabilities vary in concentration; probability changes and actual P*V contributions must not be conflated. Actual Q/K/V and weighted-numerator differences are in matched-relocations005.json, while modified probabilities and downstream projections/logits are in intervention-vectors005.json. Query row never means chosen output square: all nine rows flow through residual, flatten/readout, GELU/norm, learned route/gate and output head.
Probability and value/projection changes must be compared separately; the largest PV/P-ratio example does NOT have small absolute P change. There is no uniformly weak-variation finding. Position-mean attention preserving behavior would only show finite-domain robustness at that override; catastrophic identity/group lesions are OOD damage, not selective tactical mediation. Unfavorable matched controls and explicit counterexample remain in examples005.json. Zero positives/zero matched cases are absence of evidence, not zero-error proof.
Selection split372/121/134 seed1729 is symmetry-grouped for probes/selection only. All627 were already model-trained/audited; no OOD/model-heldout claim; sparse fork support. Independent geometric fork candidates here include boards excluded by earlier has_fork tactical gating and are NOT the earlier six-positive-board test label. Donor availability restricts conclusions, not repaired through relaxed matching. No training, weight/game change, GPU, install, main checkout execution, merge, upload, services or publication.

## Artifacts and reproduction
Frozen experiment-manifest005.json precedes all new evaluation. Baseline-only command precedes root manifest. Reproduce with the recorded single-thread environment and dependency interpreter: `python study005_execute.py --output <fresh005-directory>` (full exact command in FINAL-STUDY-005.md). PNG/SVG rendered from measured JSON only; actual attention panels are unperturbed. Source hashes and preserved69+23+28 artifacts recorded in provenance005.json. Final verification binds independent tests and fresh deterministic bytes.

## Measured positive and negative interpretation
Training-only selected line [0, 1, 2] had positive-minus-negative line mass contrast -0.165608; a negative contrast is not a bright-line support detector. Test candidate AUC controls -> controls+attention: win 0.81198 -> 0.80721; threat 0.81339 -> 0.81357; fork 0.79496 -> 0.77938; unfavorable controls retained. Position-mean attention causes238/627 canonical selected-move failures (334 route-order changes). Selected-line full-dose lesion: 15 failures vs equal-size/equal-mass control 12; not selective strategic-circuit evidence.

## Execution repairs (no design change)
The first attempt stopped before interventions on NumPy JSON scalar serialization. A wrapper converts only NumPy scalars/arrays to JSON. All19 interventions then executed; the environment lacked matplotlib. No packages were installed: a Pillow/Canvas evidence-only renderer replaces the unavailable renderer. Frozen experiment source and manifest remain byte-identical; amendment-study005.json binds the execution/renderer repair. Original partial attempts retained separately. Concentration wording is generated to match actual entropy, not the unused generic broad-attention hypothesis.
