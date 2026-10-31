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
| Four-expert whole-integer conversion | Active next-stage workstream | Convert the effective passing four-expert weights; preserve the accepted nine-expert integer reference |
| Full assembled neural inference | Active implementation workstream, unaccepted | Range-aware arithmetic and coherent target layer slices; dot-product kernels alone are not complete inference |
| RAM-resident game integration | Unstarted | No model-data loads after initial load; complete game and view lifecycle |
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
