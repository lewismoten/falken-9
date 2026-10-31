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
| Whole-model integer reference/export | Active next-stage workstream | Explicit integer normalization/attention/activation/scales, materialization parity and exhaustive move gate |
| Smaller canonical-set model search | Active next-stage workstream | Train on 627 canonical boards; predict optimal set, inverse-map, preserve original-coordinate ties |
| Full assembled neural inference | Unstarted | Dot-product kernels alone are not a complete neural runtime |
| RAM-resident game integration | Unstarted | No model-data loads after initial load; complete game and view lifecycle |
| Physical-hardware testing | Unstarted | Emulator evidence is not physical C64 acceptance |

## Verified first-wave outcomes

`results/training-summary.json` records 11 actual candidates. Four pass the host deterministic policy gate. The smallest float reference and final mixed ternary archive were independently evaluated again by the parent on CPU: zero board/history mismatches. Each candidate's saved checkpoint digest was verified. Floating-point or fake-quant success is not integer or C64 acceptance.

`results/kernel-summary.json` records 150 measured INT8-activation executions; `results/kernel16-summary.json` records 50 measured INT16-activation/binary executions. Both include unpacking and exact integer accumulation, but exclude caller JSR, interrupts, VIC stalls and I/O. They are not full-inference timings.

The integrated first-wave suite, including the project-local assembler bootstrap, portability tests and INT16 binary extension, passed **28 tests plus 37 subtests**. Active next-stage integer/canonical tests are excluded until those workstreams finish and are reviewed. PyTorch emits a nonblocking optional-NumPy warning; the exporter does not require NumPy.

Environment: Python 3.11.16, PyTorch 2.14.0, pytest 9.1.1, py65 1.2.0, 64tass 1.60.3243. The independent project Python environment and assembler bootstrap were both exercised successfully. CUDA training is available, but no target-performance claim follows from GPU training speed.

The 8 KiB encoded-model goal is an optimization target, not a claim that a C64 cannot hold a larger model. The RAM audit proposes a conservative new-harness layout; complete game residency remains unproven at every size.

A model is not accepted merely because it has a small checkpoint or draws in self-play. Preserve exact deterministic move gates, packed-artifact byte counts and target-execution evidence as separate milestones. Results summaries will be updated as real experiments finish.
