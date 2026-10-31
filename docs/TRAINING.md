# Initial compact policy training

## Scope and representation

These are new Falken-9 research models trained from scratch, not imports or
modified checkpoints from Crystal-9. Reusing its Python environment does not
reuse its model code. Dependencies: Python 3.11 and PyTorch; tests use stdlib `unittest` or pytest.
The archive uses stdlib `struct`, not NumPy. Parent owns packaging and input
validation. New commands use the parent's subsequently created project `.venv`;
the already-running initial jobs retain their original interpreter/provenance.

Approach B deliberately replaces chronological tokens with exactly nine board
square tokens, in `a..i` order, occupancy `0=empty,1=X,2=O`. Each token receives
learned occupancy, square-position and side-to-move embeddings. Side to move
is derived from occupancy parity on validated legal boards. There is no history,
lookup table, game solver or persistent state in neural inference. The external
history validator must reject malformed, repeated-square and terminal histories;
`CompactPolicy.forward` is a board-tensor research API, not that validator.

Architecture: one pre-LayerNorm, one-head all-to-all self-attention with learned
Q/K/V/output projections and residual; flattened nine-token learned global
readout plus GELU; second LayerNorm; learned nine-way router; stable descending
router scores (lower expert ID wins exact ties); softmax gates over top two;
**only those two experts** gather/execute their matrices; GELU expert hidden
states; gated residual; nine learned output logits. Occupied moves are masked
before stable `ebdfhcgia` selection. Width and expert-hidden width searched:
8, 12, 16. All arithmetic here remains host floating point.

Fixed nine-token attention costs `4*9*d*d + 2*81*d` multiply-accumulates
(projection and attention products, not normalization/softmax/GELU). A comparable
chronological attention layer with BOS plus history has `L=1..9` tokens on these
nonterminal examples and costs `4*L*d*d + 2*L*L*d`. Thus board attention is more
expensive early and equal at maximum length, not automatically faster. The
flattened readout adds `9*d*d`; selected experts add `4*d*h`, router/output
add `18*d`. These are algebraic host operation counts, **not 6502 cycles**.
For `h=d`, counted matrix MACs are 4,576 / 9,216 / 15,424 at widths 8 / 12 / 16,
excluding embeddings, nonlinearities, normalization, routing sort and masking.
There is no K/V cache. The benefit is one fixed board-dependent function and
4,520 unique supervised patterns instead of redundant chronology.

The immutable history file has SHA256
`a4539c7cde214440f3369085725ad32faaba03d5de3265c6a8333bdc12723597`.
The self-contained loader checks equal selected labels for every duplicate board
and retains an index for every one of 294,778 histories. The parent independently
audited legal histories, all minimax targets, digests and board-label consistency
in `results/dataset-audit.json`. Inference reads only the board tensor, so evaluating
4,520 distinct boards then expanding their predictions to **every history** is
an exact exhaustive move gate, not sampling. Every mismatch is retained in
`counterexamples.jsonl` (empty files are intentional for passing models).
Training is exhaustive supervised fitting, not a held-out generalization claim.

## Reproduction

From the repository root, use the independent project `.venv` (Python 3.11.16,
torch 2.14.0+cu130). The initial search used an existing compatible environment;
its exact historical interpreter/argv are retained in per-run provenance. The
commands below normalize interpreter paths to the self-contained project setup.
One CUDA process uses the RTX 3080 Ti; no unrelated process is killed.

```sh
CUBLAS_WORKSPACE_CONFIG=:4096:8 OMP_NUM_THREADS=1 PYTHONPATH=. CUDA_VISIBLE_DEVICES=0 .venv/bin/python scripts/train_search.py --candidates 8:8:float,12:12:float,16:16:float --steps 20000 --seconds 150 --eval-every 100 --seed 1101 --output artifacts/training/float-search
CUBLAS_WORKSPACE_CONFIG=:4096:8 OMP_NUM_THREADS=1 PYTHONPATH=. CUDA_VISIBLE_DEVICES=0 .venv/bin/python scripts/train_search.py --candidates 8:8:binary,8:8:ternary,12:12:binary,12:12:ternary,16:16:binary,16:16:ternary --steps 15000 --seconds 90 --eval-every 100 --seed 1101 --output artifacts/training/quant-search
OMP_NUM_THREADS=1 PYTHONPATH=. .venv/bin/python scripts/evaluate_model.py --checkpoint artifacts/training/float-search/w8-h8-float/best.pt --output artifacts/training/float-search/w8-h8-float/cpu-reload --device cpu
OMP_NUM_THREADS=1 PYTHONPATH=. .venv/bin/python -m unittest discover -s tests -v
```

The train commands' stdout/stderr are saved to `artifacts/training/{float,quant}-search.log`.
Deterministic seed 1101, full-batch AdamW, learning rate .003, no weight decay,
CE over legal squares, gradient norm clip 5; deterministic PyTorch algorithms;
TF32 disabled. Model initialization is reseeded before each candidate. Each
candidate exits early on zero training-board misses or its time/step bound;
best checkpoints minimize `(board_mismatches, loss)`, not last epoch. Each has
`best.pt`, `result.json`, `evaluation.json`, complete `counterexamples.jsonl`.
`result.json` records argv, environment, steps, loss trace, tensor-by-tensor
inventory, checkpoint bytes and SHA256. The initial search hard training limits
sum to 990 seconds (three 150-second limits and six 90-second limits); actual
early-stopped float time is much lower.

## Observed float results

All three pass 4,520 boards and all 294,778 histories with **zero misses**, both
GPU best-checkpoint evaluation and independently reloaded CPU evaluation.

| width/hidden | parameters | FP32 tensor bytes | checkpoint bytes | best step | CE | training+gate seconds |
|---|---:|---:|---:|---:|---:|---:|
| 8/8 | 2,442 | 9,768 | 16,211 | 7,700 | 0.0028165952 | 40.524 |
| 12/12 | 5,142 | 20,568 | 26,899 | 1,100 | 0.0045619668 | 6.039 |
| 16/16 | 8,834 | 35,336 | 41,427 | 2,000 | 0.0009965365 | 12.229 |

Width eight establishes capacity, but its raw FP32 tensors exceed the 8 KiB
encoded-model target. A `.pt` file's Python/container overhead is not model RAM.
No float candidate is integer-accepted or C64-ready.

## Mixed binary/ternary experiments and archive contract

The six bulk matrix groups Q/K/V/output-attention projections, `expert_w1` and
`expert_w2` are quantized in forward; embeddings, readout, router, output head,
normalization and biases stay FP32. One FP32 mean-absolute scale per projection
matrix and per expert matrix (22 scales). Binary codes are -1/+1, with zero
latent weight choosing +1. Ternary codes are -1/0/+1, threshold `abs(w)>=.7*scale`.
Straight-through gradients update latent masters; the detached scales are
recomputed each forward. This is mixed weight-only fake quantization, **not
binary activations, integer attention, isolated predecessor QAT or C64 acceptance**.
Each experiment starts from its own deterministic random weights; it does not
silently quantize or overwrite an accepted float checkpoint.

`falken9.export` writes `F9Q1`, little-endian uint32 JSON-header length, JSON
metadata, then tensor payload. Binary values pack one bit LSB-first
(0=-1,1=+1); ternary values pack two bits LSB-first (0=-1,1=0,2=+1;3 invalid).
Remaining tensors are little-endian FP32. Shapes, offsets, byte counts, scales
and exact codebooks are recorded. JSON scale/header overhead is intentionally
counted. This is an inspectable host research archive, not an optimized C64
format. The independent decoder materializes FP32 matrices; fake-versus-decoded
CPU logits are exhaustively compared, and both paths get full policy gates.
Matching failures are parity evidence, never accepted gameplay.

For a packed archive, independently rerun:

```sh
OMP_NUM_THREADS=1 PYTHONPATH=. .venv/bin/python scripts/evaluate_model.py --packed artifacts/training/quant-search/w8-h8-binary/model.f9q --output artifacts/training/quant-search/w8-h8-binary/packed-cli --device cpu
```

Observed initial low-bit results (all rejected):

| width/hidden | precision | board misses / 4,520 | history misses / 294,778 | full archive bytes |
|---|---|---:|---:|---:|
| 8/8 | mixed binary | 520 | 12,985 | 7,077 |
| 8/8 | mixed ternary | 448 | 11,024 | 7,272 |
| 12/12 | mixed binary | 262 | 5,472 | 11,109 |
| 12/12 | mixed ternary | 146 | 3,084 | 11,519 |
| 16/16 | mixed binary | 35 | 620 | 16,343 |
| 16/16 | mixed ternary | 6 | 54 | 17,059 |

Every initial packed decoder has exactly zero maximum absolute logit error
versus CPU fake quantization on all 4,520 boards and identical policy miss totals.
The width-eight archives meet 8 KiB as files but fail gameplay; width-sixteen
ternary is near the behavior gate but exceeds the size target. Neither is a
deployable acceptance. These bounded results are not a precision impossibility
claim. The scales and FP32 islands are fully included in the archive size.

A single deliberate learning-rate change, .003 -> .0003, restarts optimization
from the original 16/16 ternary best checkpoint with all latent tensors trainable,
same seed and unchanged representation. It reaches 2 board misses / 156 history
misses (CE 0.0027869391) in 89.581 seconds, still rejected. Minimizing unique-board
misses can increase weighted-history misses; neither nonzero result passes.
The immutable initial checkpoint is retained. The further bounded .00003 retry
is recorded separately, not overwriting its predecessor. **It passes** at step
8,300 after 48.969 seconds: zero board/history misses, GPU CE 0.0012397536,
CPU fake/decoded CE 0.0012229929. CPU fake and decoded logits match exactly on
all 4,520 boards; the separately reloaded packed CLI also has zero history
misses. CPU/GPU logits are not claimed bit-identical: scale reductions remain
host floating arithmetic, and policy correctness is checked independently.

Accepted **host-only mixed-weight** artifact:
`artifacts/training/ternary-refinement-lr3e-5/w16-h16-ternary/model.f9q`.
It is 17,062 bytes (14,216 payload + 2,846 header), 5,632 two-bit weight values,
3,202 FP32 values, 22 FP32 scales represented in the counted JSON header.
The latent checkpoint contains 8,834 parameters / 35,336 FP32 tensor bytes.
Archive SHA256:
`1088a8430ead34fe560dcf53d97136ca1c55a223ea58e7efa1cdb5f1f42b5966`.
This passes behavior and host packed-decoder parity, **not the 8 KiB target**,
integer arithmetic, 6502 execution or C64 residency.

```sh
CUBLAS_WORKSPACE_CONFIG=:4096:8 OMP_NUM_THREADS=1 PYTHONPATH=. CUDA_VISIBLE_DEVICES=0 .venv/bin/python scripts/train_search.py --candidates 16:16:ternary --initialize artifacts/training/quant-search/w16-h16-ternary/best.pt --steps 15000 --seconds 90 --lr .0003 --eval-every 100 --seed 1101 --output artifacts/training/ternary-refinement
CUBLAS_WORKSPACE_CONFIG=:4096:8 OMP_NUM_THREADS=1 PYTHONPATH=. CUDA_VISIBLE_DEVICES=0 .venv/bin/python scripts/train_search.py --candidates 16:16:ternary --initialize artifacts/training/ternary-refinement/w16-h16-ternary/best.pt --steps 15000 --seconds 90 --lr .00003 --eval-every 100 --seed 1101 --output artifacts/training/ternary-refinement-lr3e-5
OMP_NUM_THREADS=1 PYTHONPATH=. .venv/bin/python artifacts/training/postprocess.py
OMP_NUM_THREADS=1 PYTHONPATH=. .venv/bin/python artifacts/training/build_summary.py
```

The two refinements keep the combined hard training limits at 1,170 seconds,
below approximately twenty minutes, with earlier step/zero-miss stops permitted.
Quantized results are recorded in `results/training-summary.json`; rejected
checkpoints/counterexamples are preserved. The initial low-bit job imported the
training module before automatic packed postprocessing was added, so its six
saved checkpoints are explicitly postprocessed with the same tested
`falken9.training.packed_gate` function after training; their original results
remain preserved in the search summary. Future CLI runs do this automatically.

## TDD evidence and unfinished gates

`artifacts/training/tdd-*-red.log` and `tdd-*-green.log` preserve missing-feature
failures followed by passing model, training/checkpoint, CLI, quantization,
packed decoder and exhaustive packed-gate tests. These use actual autograd,
optimizers, files and roundtrips, not mocked model outputs. The full parent test
suite is run separately after integration.

Final verification: 11 real candidates, four host policy passes (three float,
one mixed ternary), 730.030 aggregate recorded training-plus-gate seconds;
all counterexample line counts checked against declared history mismatches.
Project-environment full suite: **25 passed, 7 subtests passed** in
`artifacts/training/full-suite-final.log`. PyTorch emits one optional-NumPy
initialization warning in the project environment; the exporter no longer
requires NumPy and every test passes. Both initial training jobs and both
refinement jobs exited zero; **no GPU training remains running**.

Proper successor: preserve this accepted host archive as an immutable teacher,
define a fixed-point activation/accumulator/scale/rounding contract, write an
independent materialized integer oracle and failing parity tests, then attempt
direct materialization before bounded isolated activation/normalization QAT.
Freeze and hash untouched codebooks/scales/tensors at each scoped stage. Reduce
FP32 islands and header/scale overhead as explicit separately gated layouts;
the existing 17,062-byte file does not satisfy the resident model target.
Run all 294,778 history moves again for each arithmetic/layout candidate.
Do not advance to a C64-ready claim until independently decoded integer
inference, assembled 6502 execution and residency/game integration all pass.

Unstarted: independently specified integer arithmetic/normalization/softmax,
integer fake/materialized parity, 6502 kernels/full inference, RAM map and
resident game integration. No target timing or C64-ready claim is made.
Canonical optimal-set Approach C remains separate: the baseline already proves
board capacity; a canonical selected-move target is explicitly unsafe under the
original-coordinate tie order. No symmetry shortcut is applied to these models.
