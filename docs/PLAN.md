# Falken-9: C64-first neural policy development plan

## Goal and acceptance contract

Build a new small neural tic-tac-toe policy specifically for the Commodore 64, not another proof that an unchanged desktop-oriented model can be paged from disk. The preferred deployment loads its complete model once, retains it in RAM during play, and performs every subsequent move without model-data disk access. Keep Crystal-9 and its published disk immutable.

Preserve real attention, projections, normalization, a learned router and mixture-of-experts execution. **Expert count is a search variable, not a nine-expert requirement.** The owner explicitly authorizes fewer experts and different configurations provided genuine learned MoE remains demonstrable on the C64. Prioritize 3/4 experts with top-2 routing; also evaluate top-1 variants with a documented trainable routing/gating contract. Search expert count, active count, hidden dimensions and precision jointly rather than assuming a CUDA-friendly width of 32 is needed. A CUDA warp's thread count is not an architectural correctness requirement; GPU training throughput is secondary to measured C64 inference cost. Reducing widths may reduce training throughput without making the model invalid.

**Behavior gate:** identical deterministic legal moves under the published tie order, not identical logits. Compare every supported nonterminal legal history, retain mismatch examples, and reject continuation after terminal play. A few draws or good average accuracy do not pass. Existing model behavior and the dataset targets must be reconciled before claiming equivalence to either. Do not silently replace neural inference with minimax or a move table. Host training checkpoints are research artifacts until the exported arithmetic and target execution pass their gates.

Dataset: https://huggingface.co/datasets/lewismoten/tic-tac-toe at immutable revision `6ea253e1fa7de4a61eedeab6bbd9d8117af1fcb7`. The primary file declares 294,778 histories; the nonterminal board view declares 4,520 boards. The deterministic tie order is `ebdfhcgia`. Verify bytes, row totals, legal histories, target legality and all-optimal move order; preserve the manifest and dataset license. Large downloaded data and checkpoints are ignored, not Git-committed.

## Approach A: compact chronological attention/MoE

- Keep raw chronological history with BOS and position embeddings.
- Search model widths 8, 12, 16 and 24, with compatible head counts; expert hidden widths can be smaller than the model width.
- Begin with a single attention block, configurable small expert banks and learned routing. Keep the existing nine/top-2 model as a frozen reference, not a restriction on derivatives.
- Establish a trainable reference before aggressive weight/activation quantization.
- Preserve a per-game K/V cache only if a tested memory-lifetime map proves validity. Compare full-prefix recomputation against append-only computation; neither is assumed exact without a test.

Benefit: closest conceptual lineage to Crystal-9. Risk: redundant chronology and repeated prefix execution may be unnecessary for a board policy.

## Approach B: board-state attention/MoE (parallel candidate)

- Validate that published history labels are consistent for each unique board, then train on board features while preserving a raw-history public input validator.
- Use the nine squares as position-labelled tokens with occupancy and side-to-move features; compare a compact global readout against per-square logits.
- Keep genuine attention, learned routing and top-2 expert computation. This is a deliberately different representation, not an unchanged causal-history model.
- Full board attention has a fixed token count and no persistent K/V requirement. It may cost more at early turns than a chronological model, so benchmark rather than assume superiority.
- Evaluate all published histories, not only unique boards, before acceptance. A host optimization may deduplicate equivalent evaluations only after proving the runtime is strictly board-dependent.

Benefit: eliminates order redundancy and exposes a smaller supervised state space. Risk: positional tie preferences and routing must still be learned exactly.

## Approach C: symmetry-aware policy

- Inspect rotations/reflections and inverse move-coordinate mapping independently of training.
- Do not assume the original runtime already canonicalizes boards.
- Fixed original-coordinate tie order is not rotation-equivariant on symmetric positions. A canonical board plus a single selected canonical move can therefore break exact baseline behavior.
- Explore prediction of all equally optimal moves followed by the published original-coordinate tie order, but only promote it if set prediction is exhaustive and exact. Distinguish this documented selection rule from a stored policy table.
- Keep this approach separate until the raw-history/board baselines and inverse mappings are tested.

## Initial verified findings

`results/dataset-audit.json` verifies all 294,778 histories and 4,520 unique nonterminal boards with zero board-label conflicts or independent minimax target mismatches. `results/symmetry-audit.json` reduces those boards to 627 dihedral representatives. Inverse-mapping the complete canonical optimal set preserves every target; inverse-mapping only a selected canonical target fails 406 boards. Approach C therefore has a tested coordinate/label contract, but no learned model or C64 implementation is accepted by that audit.

## Precision approaches: search jointly with width

Expert-bank search: compare E=3/4 with top-2 first, then E=2/3/4 with top-1 where meaningful. Fewer stored experts primarily reduce model bytes; fewer active experts can also reduce expert arithmetic. Neither change alone reduces shared attention/readout cost. A two-expert/top-2 model is a learned mixture but not sparse expert selection; label it accordingly. A top-1 softmax over only the selected expert is constant and gives no useful router gradient through that gate, so require a tested training strategy, routing participation evidence and clearly separate training versus deployed compute. Reject a fixed expert or hardcoded route masquerading as learned MoE. New expert-count layouts must have explicit versioned metadata; do not reinterpret fixed-nine legacy packets silently.

1. **Binary weights** (`-1,+1`): packed sign bits, add/subtract kernels, preferably shared scales. Binary weights are not binary activations; no XNOR/popcount speed claim without actual kernels and measurements.
2. **Ternary weights** (`-1,0,+1`): compare dense two-bit codes with any sparse format, counting index/skip overhead and decoder cost. Zeros only save time when the actual implementation skips useful work cheaply.
3. **INT2/INT3/INT4**: compare compact narrow networks, not just the same architecture re-rounded repeatedly. Byte/nibble-friendly decoding may beat a denser irregular bit layout.
4. **Mixed precision**: retain more precision for sensitive embeddings/router/output/norm components while binarizing or ternarizing bulk expert/projection matrices.
5. **Activation/accumulator alternatives**: signed INT8 versus INT16 state, with INT16 or INT32 accumulation justified by explicit bounds. Model scale/bias bytes and activation scratch are part of the cost.

Keep floating-point latent weights/optimizer state during training where useful, but quantize the forward path to the declared inference contract. A failed seed does not prove a representation impossible. Compare multiple bounded seeds/widths, preserve rejection evidence, and do not keep extending a stagnant run without a strategy change.

## Arithmetic contract and implementation sequence

### Contract v0: research/training reference

Define token order, board/chronology encoding, masking, attention layout, router top-2 ordering, nonlinearities and deterministic output tie handling. This may use host floating point to establish capacity. It is **not** C64 integer acceptance.

### Contract v1: target arithmetic

- Specify exact signed weight codebooks and bit order, scale grouping and serialized endianness.
- Prefer symmetric, zero-point-free fixed point and power-of-two/shared scales when they preserve behavior. Do not require the old FP16 scales.
- Specify every activation range, accumulator width, bias placement, shift and rescale boundary.
- Define signed rounding, right shifts, overflow/saturation, division and normalization/softmax approximations explicitly, including lookup-table inputs and endpoints.
- Stable router ties select lower expert ID; output ties use `ebdfhcgia`. Mask occupied squares before output selection.
- Compare a separately written integer oracle, materialized packed decoder and quantization-aware forward path. Matching failures show parity, not acceptable gameplay.
- Implement vertical 6502 dot-product gates first (binary, ternary, low-bit integer), with poisoned scratch/overflow cases and measured emulator cycles. Include unpacking and accumulators; a host operation count is not a CPU benchmark.
- Extend target gates to projection, attention, normalization, router, both selected experts and final legal move. Full inference remains unstarted until those gates actually execute.

## RAM residency and cost contract

Preferred **encoded-model target**: at most 8 KiB, with 4 KiB as a stretch goal, not a claimed result. Search budgets may be revised with documented evidence. Count weights, scales, biases, headers, tables and alignment. Also report decoder/kernel code separately and together with the model.

Build a live-memory ledger covering resident program, zero page/stack, BASIC/KERNAL/I/O banking constraints, VIC bank/bitmap/screen/color planes, UI/marks, model, activations, score/normalization buffers, router/expert scratch and optional K/V state. The C64's nominal RAM is not entirely available to the model.

Start with a conservative hypothetical arena for algorithm comparison, clearly labelled provisional; audit the real Crystal Palace assembled map before advertising integration capacity. View-scoped assets may be paged on screen transitions, but the model must not be overwritten. Prove intervals disjoint and exercise replay/cancel/title/INFO transitions. Distinguish an isolated resident inference harness from complete game integration.

A passing host file-size estimate is not target RAM residency. Require a packed artifact, real decoder, assembled layout assertions and complete accepted-input-to-result execution before claiming the model fits and runs.

## Ordered work and advancement gates

| Stage | Required work | Gate to advance |
|---|---|---|
| 0 | Clone fresh repository; discover compute; document scope | Existing releases untouched; no unrelated GPU work disturbed |
| 1 | Pin/download and audit published dataset | Declared digests/counts; history legality and board-label consistency |
| 2 | Define arithmetic/representation contracts and tests | Red/green tests for rounding, packing, tie/mask semantics |
| 3 | Train compact attention/MoE references | Real saved checkpoints; exhaustive counts and counterexamples |
| 4 | Quantization/width/scale search | Materialized-runtime agreement and zero deterministic move misses |
| 5 | Packed export and memory ledger | Complete encoded byte inventory and bounded peak live scratch |
| 6 | Assembled kernels and full integer inference | Independent oracle parity; actual CPU cycles and memory assertions |
| 7 | Resident C64 harness, then complete game | No model-data loads after initial load; complete games/lifecycle |
| 8 | Publish distinct derivative | Immutable checksums, lineage, exact acceptance scope and remote verification |

Use a fail-fast progression: dataset/parity correctness first, small smoke training, bounded capacity runs, exhaustive evaluation, then longer refinement only for viable candidates. Automatically advance passing stages; preserve and diagnose failures rather than substituting fabricated evidence. Do not publish an incomplete derivative as an accepted model. Do not overwrite original releases, terminate unrelated processes, or consume an already-owned GPU.

## Evidence, operations and reporting

- Use deterministic seeds, explicit hyperparameters, exact dataset/source digests and environment versions.
- Save checkpoints, per-stage machine-readable results and counterexamples under ignored artifact directories; track concise summaries and reproducible scripts.
- Train one model process on the available GPU; avoid uncontrolled parallel model launches. CPU arithmetic/data validation can run with bounded threads.
- Use tests before new implementation; run smoke execution and exhaustive evaluations on actual produced artifacts.
- Report completed, active and unstarted components separately. CPU microbenchmarks, host policy accuracy, packed-runtime agreement and target acceptance are distinct claims.
- Testing is emulator-only unless physical hardware is actually exercised. No wall-time or physical compatibility claim from host arithmetic or cycle counts alone.

## Graphical UI follow-up: inference activity buttons

Numeric controls are adopted at the application boundary: row-major `123 / 456 /
789`, with public binary move results 1–9 and 0 for invalid/no result. The model
keeps its existing nine occupancy inputs, nine score outputs and original tie
semantics; no retraining or learned invalid class is required. Application 002
implements the text controls; use the same mapping in the future graphical UI.
Do not conflate public result 0 with internal square index 0 or occupancy 0.

For the future graphical console, place decorative computer buttons below the play field and let a changing subset blink during neural inference. This is an **activity indicator**, not a percentage or completed-work claim. Use animation state independent of model inputs, routing, tie selection and any gameplay randomness. Update only a reserved presentation footprint, preserve the board and all live neural buffers, and stop/reset the lights when inference completes, errors, or is canceled. Animate at safe, bounded real-computation checkpoints without introducing model-data loads; preserve caller registers, flags and zero-page ownership. Keep the verified `001` game/model artifacts unchanged and test the animation as a separate UI revision.

## Graphical UI follow-up: title model/version identity

When reusing the shared game artwork, identify this deployment on the title screen with `falken-9` and `v1.0` directly below it in the lower-right corner. Align the model/version block with the existing Info/Quit footer row so the Falken-9 disk can be distinguished from the Crystal-9 disk without relying on filenames. Render both model and version in dark blue as static, non-interactive identification: no highlighted shortcut letter, selection styling, blinking, or keyboard binding. Keep the actionable Info (`I`) and Quit (`Q`) controls visually distinct. Reserve a non-overlapping area that preserves footer controls, their highlight states and the shared artwork. Include the badge on first title entry and after every return/replay/restoration path, and verify it in actual emulator pixels. Keep the original Crystal-9 release and the frozen Falken-9 `001` artifacts unchanged; apply this identity treatment in the graphical UI revision.
