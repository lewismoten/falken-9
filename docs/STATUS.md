# Development status

This file distinguishes verified work from active experiments and target integration that has not yet happened.

| Component | State | Evidence / next gate |
|---|---|---|
| Fresh Falken-9 repository | Completed | Separate Forgejo clone; original Crystal-9/C64 release untouched |
| Plan and competing approaches | Completed | `PLAN.md`: chronological, board-state, symmetry/set candidates; joint width/precision search |
| Pinned dataset | Completed | Five JSONL digests/counts, manifest and upstream provenance verified |
| History/target audit | Completed | 294,778 histories; zero independent minimax mismatches; 4,520 consistent boards |
| Legal input/output contract | Completed, host | Reject malformed/repeated/terminal histories; legal masking; deterministic `ebdfhcgia` ties |
| Symmetry coordinates | Completed, host | Eight invertible mappings; 627 nonterminal canonical boards; zero full-set inverse-map mismatches |
| Single canonical-target shortcut | Rejected | 406 deterministic board mismatches; preserve set prediction instead |
| Compact attention/nine-expert/top-2 float references | Host behavior gate passed | Width/hidden 8/8, 12/12, 16/16: all 294,778 histories pass; CPU checkpoint reloads also pass |
| Smallest host-correct reference | Completed, research | Width 8/8, 2,442 parameters; 9,768 raw FP32 tensor bytes, not an integer deployment |
| Mixed ternary 16/16 | Host behavior and packed parity passed | 17,062 encoded bytes; still FP32 activations/islands/scales, exceeds preferred 8 KiB target |
| Initial binary/ternary search | Six rejected candidates retained | Complete counterexamples and actual checkpoints; low bit count alone does not pass gameplay |
| Assembled arithmetic kernels | Completed, isolated | Binary/ternary/INT8 weights with INT8 inputs, plus binary weights with INT16 inputs; real Py65 correctness/cycle gates |
| C64 memory map audit | Completed, read-only/provisional | No complete-game arena proven free; 8 KiB model + 4 KiB scratch proposed only for a new harness |
| Whole-model integer reference/export | Implemented; direct candidates rejected | Best INT8/Q8: 5,153 bytes, 70 board / 1,189 history misses; decoder and independent scalar oracle agree exactly |
| Canonical-set host model | Host behavior and packed parity passed | Width 8, expert width 4: 4,945 encoded bytes; zero set/move errors on all 294,778 histories; remaining floating arithmetic prevents target acceptance |
| Four-expert learned MoE | Host float gate passed | W8/H4/E4/K2, 5,725 bytes; all four experts participate; zero set/move errors across the published domain |
| Four-expert INT8 attempt | Rejected | 1,749 bytes but one canonical error affects eight boards / 1,152 histories; exact decoder parity does not imply gameplay acceptance |
| Canonical whole-integer model | Host integer gate passed | 6,110-byte F9J2, Q11/W16/A32, early attention rescale and interpolated LUTs; zero set/move errors; five-byte accumulation still needed on target |
| Local norm / QKV constant folding | Exact host integer parity passed | Extra 864 / 2,592 bytes; removes local first-normalization work, optionally QKV projections; no target-speed claim |
| Four-expert whole-integer conversion | Host integer gate passed | 5,195-byte W16 baseline and 4,931-byte mixed W8/W16 packets; zero set/move errors, independent scalar/materialized parity and public-wrapper checks |
| Assembled attention-block inference | Partial target gate passed | Entire unchanged 6,110-byte reference resident; exact embedding/norm/QKV/attention/projection/residual on 64 canonical boards; 3,341 code bytes |
| Full assembled neural forward | Exhaustive neural gate passed | Four-expert W16 packet 5,195 bytes; all intermediate vectors/logits/routes exact on 627 canonical boards, no model-data loads or mutation |
| Assembled history/symmetry/set-selection wrapper | Composed exhaustive gate passed | All 4,520 unique boards; real wrapper instructions with hash-verified logits from the prior 627 neural executions, not 4,520 rerun forwards |
| RAM-resident game integration | Packaged PRG and true-drive D64 passed | Complete human-X/model-O draw and O-win games, replay, terminal/invalid recovery, unchanged resident model and no per-turn LOAD |
| Target-browser / physical-keyboard acceptance | Active separate acceptance | Stock-ROM monitor-queue tests do not establish browser key-event behavior |
| Physical-hardware testing | Unstarted | Emulator evidence is not physical C64 acceptance |

## Verified first-wave outcomes

`results/training-summary.json` records 11 actual candidates. Four pass the host deterministic policy gate. The smallest float reference and final mixed ternary archive were independently evaluated again by the parent on CPU: zero board/history mismatches. Each candidate's saved checkpoint digest was verified. Floating-point or fake-quant success is not integer or C64 acceptance.

`results/kernel-summary.json` records 150 measured INT8-activation executions; `results/kernel16-summary.json` records 50 measured INT16-activation/binary executions. Both include unpacking and exact integer accumulation, but exclude caller JSR, interrupts, VIC stalls and I/O. They are not full-inference timings.

The integrated first-wave suite, including the project-local assembler bootstrap, portability tests and INT16 binary extension, passed **28 tests plus 37 subtests**. Active next-stage integer/canonical tests are excluded until those workstreams finish and are reviewed. PyTorch emits a nonblocking optional-NumPy warning; the exporter does not require NumPy.

Environment: Python 3.11.16, PyTorch 2.14.0, pytest 9.1.1, py65 1.2.0, 64tass 1.60.3243. The independent project Python environment and assembler bootstrap were both exercised successfully. CUDA training is available, but no target-performance claim follows from GPU training speed.

The 8 KiB encoded-model goal is an optimization target, not a claim that a C64 cannot hold a larger model. The RAM audit proposes a conservative new-harness layout; complete game residency remains unproven at every size.

## Second-wave verified outcomes

The integrated suite passed **48 tests plus 37 subtests**. Both new artifact hashes were verified. Independent parent execution of the decoded 4,945-byte canonical packet reproduced zero canonical-set, board, history and coordinate-transform errors. Re-running the best integer candidate with the independent scalar oracle reproduced its exact 5,153-byte artifact and rejected result (70 board / 1,189 history errors).

All eight initial whole-integer candidates have materialized-decoder and independent scalar logit/route parity, but none passes gameplay. The best candidate saturates only at final output (2,893 elements); its observed attention-scaled intermediate exceeds INT32. Those facts motivate range/scale diagnosis before blindly extending training. See `INTEGER_MODEL.md` and `CANONICAL_MODEL.md` for distinct acceptance boundaries.

The owner clarified that expert count is configurable: demonstrate learned MoE on the C64 rather than preserve nine experts. The next architecture search varies expert-bank size and active top-k alongside width and precision; fixed-nine results remain frozen references.

## Third-wave verified outcomes

The integrated pre-fusion suite passed **80 tests plus 677 subtests**. Parent verification independently reproduced the exact 6,110-byte whole-integer artifact, its zero errors, independent scalar parity and public wrapper gate. Parent independently decoded and evaluated the four-expert packet: all four experts participate, with canonical selection counts `[301,258,355,340]` and no policy/set errors.

The accepted integer model uses no floating inference. However, selected intermediates exceed INT32: observed expert merging needs 33 bits and output prefixes 34; measured-input envelopes require 36. Early attention rescaling keeps its factor product within INT32 without sacrificing the accepted policy. These widths must be implemented and measured on the 6502, not silently narrowed.

The legacy final-output widening experiment repaired only one board / two histories. It did not solve the old model's integer accuracy loss. The passing contract instead came from the canonical model with carefully tested precision, range and LUT interpolation, without QAT. Rejected old contracts remain rejected.

Local constant folding was subsequently tested on every canonical input and the complete policy domain. Norm-only adds 864 bytes to the original source (6,974 combined bytes) and skips nine first-normalization calls; norm-plus-QKV adds 2,592 bytes (8,702 combined) and skips those calls plus 1,728 matrix MACs. Both preserve exact integer logits/routes. These tables encode only local features, not a board/move policy. See `LOCAL_FUSION.md`; compiled target residency and speed remain unproven.

A model is not accepted merely because it has a small checkpoint or draws in self-play. Preserve exact deterministic move gates, packed-artifact byte counts and target-execution evidence as separate milestones. Results summaries will be updated as real experiments finish.

## Fourth-wave verified outcomes

Parent verification reran the **complete repository suite: 98 tests plus 677 subtests passed**. The existing optional NumPy initialization warning remains. The previous stage was independently reviewed and pushed as `0550592`.

Four-expert whole-integer direct materialization succeeded without training/QAT. Fourteen bounded variants yielded seven accepted and seven rejected candidates. Q11/W16/A32 encodes 5,195 bytes; Q11 and Q10 variants using W8 for projection, expert W2 and output encode 4,931 bytes. All accepted candidates pass full optimal-set and move gates on the published domain. Q11 mixed retains the float model's canonical routes; Q10 mixed changes one route but preserves every set and move. Expert usage and finite-domain prefix/envelope bounds are recorded in `FLEXIBLE_INTEGER.md`; neither mixed precision nor fewer stored experts is claimed to prove faster target execution.

The assembled target now computes real embedding, integer LayerNorm, Q/K/V, all attention scores and softmax probabilities, weighted V, learned projection and residual. It retains the entire original nine-expert reference packet unchanged. Independent arbitrary-integer references agree on all 54 local feature combinations and 64 deterministic canonical-board samples. Parent checked the frozen executable and checkpoint hashes. The allocated standalone proof map totals 14,571 bytes, including model/code/scratch and reserved screen/stack; this is not full-game residency. Attention-block CPU work over those 64 boards is 6,770,938–6,847,345 cycles, excluding IRQ/VIC/ROM/disk/wall-time. No whole-forward, PRG, D64 or gameplay acceptance is claimed. See `TARGET_RUNTIME.md`.

## Fifth-wave verified outcomes

The complete four-expert Q11/W16 neural forward now executes real NMOS 6502 instructions: readout72/GELU, norm2, dynamic stable top-2 learned routing/gates, both selected expert MLPs, gated merge/residual and signed INT32 final membership scores. The model packet stays unchanged in RAM. All 627 canonical boards passed independent arbitrary-integer stage-vector, logit and route comparison. Applying the host inverse-symmetry/full-set/tie wrapper to those target logits yields zero set/move errors on 4,520 boards and 294,778 histories. The wrapper itself is not assembled yet.

Parent reran the complete suite: **109 tests plus 677 subtests passed**. Parent independently reconciled all four checkpoint shards into exactly the canonical indices 0..626 and verified the image digest `838aa62a854aa58bd603c7525b52dc67c4c4b01ea0f50f58982475959ec61961`. Code is 5,503 bytes, model is 5,195 bytes, and the actual standalone allocation is 16,842 bytes including scratch and reserved screen/stack. Raw contiguous image size is 19,531 bytes, including filled holes; that is not the live allocation total.

The exhaustive audit checked 725,122,178 emulator-visible writes, stack balance, executed instruction ranges and code/model immutability. Actual largest dot prefix was 5,463,132,850; recomputed finite-domain coarse envelopes reach 33,446,567,616, within signed40. Complete forward measured 8,050,591–8,110,463 CPU cycles, excluding IRQ/VIC/ROM/disk/wall-time. The complete neural forward is accepted for this standalone emulated core; no PRG/D64, assembled wrapper, playable game, complete-game residency or physical-hardware acceptance follows from it.

## Sixth-wave application outcomes

The complete resident game now invokes the unchanged accepted neural core through an assembled chronological-history validator, eight-transform canonicalizer, inverse full-set/legal-mask and original-coordinate tie selector. All 4,520 unique boards pass the composed wrapper gate using hash-verified frozen target logits. This does not mean 294,778 assembled wrapper calls or 4,520 additional neural forwards.

The packaged PRG and byte-identical PRG extracted from the D64 complete an optimal-human draw and a deliberately nonoptimal-human O win, replay, invalid/occupied-input recovery and terminal locking through the actual game input loop. Every model response executes the network; model/code remain unchanged and no per-turn LOAD occurs. The BASIC launch restores the sixteen core bytes overlaid by its SYS stub. Neural execution saves/restores KERNAL zero page and disables IRQ while using its scratch; IRQ-enabled GETIN resumes afterward.

Parent independently reran **116 tests plus 677 subtests**, with two optional-ROM tests skipped in the default suite. Parent then independently exercised both exact frozen transports in stock-ROM VICE: each passed complete draw/win lifecycles, seven neural requests and all seven full-logit comparisons, with code/model immutability. ROM monitor-injected keyboard queues remain distinct from physical/browser key events. Physical hardware and RESTORE/NMI during computation remain untested. Fine-grained layer progress and optional AI-vs-AI/title modes are not implemented; the current full-forward busy phase is intentionally honest. See `APP.md` for exact artifacts, byte digests and replay sequences.
