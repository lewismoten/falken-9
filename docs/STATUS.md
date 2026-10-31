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
| Compact attention/nine-expert/top-2 models | Active implementation/training workstream | Actual checkpoints and exhaustive move/set gates required |
| Binary/ternary/integer arithmetic | Active implementation/benchmark workstream | Independently checked assembled 6502 kernels and explicit rounding/accumulation contract required |
| C64 memory map and residency audit | Active audit workstream | Real live-range map; model/code/graphics/scratch must be counted separately |
| Materialized quantized complete model | Unstarted acceptance | Fake-QAT, packed decoding and integer oracle must agree before promotion |
| Full assembled neural inference | Unstarted | Dot-product kernels alone are not a complete neural runtime |
| RAM-resident game integration | Unstarted | No model-data loads after initial load; complete game and view lifecycle |
| Physical-hardware testing | Unstarted | Emulator evidence is not physical C64 acceptance |

Initial development environment: Python 3.11.16, PyTorch 2.14.0, pytest 9.1.1, py65 1.2.0. The independent project environment was installed successfully; CUDA training is available, but no target-performance claim follows from GPU training speed.

A model is not accepted merely because it has a small checkpoint or draws in self-play. Preserve exact deterministic move gates, packed-artifact byte counts and target-execution evidence as separate milestones. Results summaries will be updated as real experiments finish.
