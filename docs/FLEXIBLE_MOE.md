# Flexible canonical fewer-expert neural MoE

## Scope and behavioral contract

These are new research architectures, not modified fixed-nine checkpoints or a
reinterpretation of F9C1. `FlexibleConfig` declares width D, expert hidden width H,
expert count E, active count K, and weight precision. Every model retains nine
position-labelled occupancy/side embeddings, learned Q/K/V and attention output
projections, two LayerNorms, learned global readout, learned router and trainable
two-layer GELU experts. Inference gathers and computes only selected K banks.
E=2/K=2 is a learned mixture but **not sparse**; K<E is sparse.

The authoritative pinned dataset is revision
`6ea253e1fa7de4a61eedeab6bbd9d8117af1fcb7`, SHA-256
`a4539c7cde214440f3369085725ad32faaba03d5de3265c6a8333bdc12723597`.
The unchanged audited loader validates all 294,778 nonterminal histories,
4,520 boards and 627 canonical patterns. Nine logits represent the *complete*
canonical optimal set: membership is logit >= 0 and the cell must be empty.
Inverse-map the entire predicted set, then select in original-coordinate
`ebdfhcgia` order. Empty prediction raises, with no heuristic, oracle, minimax,
lookup or legal-move fallback. Invalid/terminal histories use the existing
validated public history parser.

## Routing, gradients and compute

Routing uses descending stable sort, selecting lower expert IDs on exact ties.
For K>1, gate weights are a softmax of the K selected scores. For K=1, the gate
is the selected expert's probability from the **full E-way softmax**, without
singleton renormalization. This gate is not constant and backpropagates into the
router. Training and deployment use identical selected-expert forward execution;
there is no hidden dense all-expert training pass or stochastic inference.

`tests/test_flexible_model.py` proves router gradients are nonzero for E4K2,
E3K2, E2K1, E3K1, E4K1 and E2K2, as well as actual multiple-expert participation,
tensor dimensions, attention/projection/embedding/normalization gradients and
stable ties. Each saved training result also records the maximum router gradient
and deployed route histogram over all 627 supported patterns. Actual trained
participation, not the synthetic unit-test distribution, gates acceptance.

Per-board forward expert matrix MACs = `2*K*D*H`; the shared matrix/attention MAC
count is `45*D*D + 162*D + E*D + 9*D`. Training forward and inference forward have
the same K-bank count. Autograd backward and optimizer work are additional,
unmeasured training compute. The inventory excludes embedding additions, biases,
normalization, GELU, softmax, routing sort and coordinate wrappers. These counts
are **not** host-to-C64 speed estimates or measured 6502 cycles.

## Training and lineage

Training uses CPU, one Torch thread per process, deterministic seeds, AdamW with
zero weight decay, BCE on all legal canonical set bits, gradient norm clipping
at 5. Checkpoint ranking is canonical complete-set mistakes, then BCE. Training
halts on zero mistakes or the requested step/time budget; the saved best state
is reloaded before all gates. Failed candidates retain board and expanded
history counterexamples. Neither a zero-exit process nor logit parity alone is
an accepted policy.

The initial bounded scratch sweep compares W8/W6, H4, E4/E3, K2, seeds 11/23,
8000 steps or 40 seconds per candidate, LR .003. Successful float capacity is
required before quantizing that architecture. Warmstarts are explicitly separate
`pruned-source9` experiments: shared tensors come from the accepted canonical
W8H4E9K2 seed-23 FP32 checkpoint, and only the declared selected banks/router rows
are copied. Source bank participation was `[160,149,146,199,164,78,143,106,109]`;
stable descending usage gives `[3,4,0,1,2,6,8,7,5]`. This is training lineage, not a
claim of fresh initialization. SHA-256, selected source IDs and source config are
serialized in the checkpoint and experiment result.

Examples (run from repository root):

```sh
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 .venv/bin/python scripts/train_flexible.py \
  --sweep --steps 8000 --seconds 40
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 .venv/bin/python scripts/train_flexible.py \
  --output artifacts/flexible/pruned-source9 \
  --source artifacts/canonical/seed23-wide/w8-h4-float-s23/best.pt \
  --selected-experts 3,4,0,1 --experts 4 --seed 23 \
  --lr .001 --seconds 65 --steps 10000
.venv/bin/python scripts/evaluate_flexible.py PATH/packed/model.f9f \
  --output artifacts/flexible/independent-evaluation
.venv/bin/python -m pytest tests/test_flexible*.py -q
```

## Explicit F9F1 v1 packet layout

24-byte little-endian header, struct `<4s8BIII`:
magic `F9F1`; version 1; D; H; E; K; matrix bits (32 or 8); gating contract ID 1;
reserved byte 0; total parameter count; two reserved u32 zeros. Then 72 bytes
of the eight canonical square permutations and nine original-coordinate tie
indices. This explicitly serializes E and K; old F9C1 packets are rejected.

Tensor order is the new `FlexiblePolicy.named_parameters()` order. FP32 mode
stores little-endian FP32 values. INT8 mode quantizes **every tensor with >=2
dimensions**, including all embeddings, position matrix, router, output/readout,
attention projections, expert weights and expert bias banks. Quantization is
symmetric signed [-127,127], nearest/even rounding, no zero point. One FP32 scale
per matrix, or per leading expert for rank-three expert weights, is
`max(abs(weights), 1e-8)/127`. Scale bytes precede signed row-major codes. Vector
LayerNorm parameters and vector linear biases remain FP32 and are fully counted.
STE has exact quantized forward and identity backward; packed decoding never
requantizes materialized values. The decoder independently unpacks bytes and
validates lengths, wrapper, finite values, scales and reserved codes.

The complete byte ledger includes header, wrapper, INT8/FP32 tensors and scales;
no host nonlinear LUT or alignment bytes exist. Python decoder/runtime code and
activation scratch are **not** included in encoded model bytes; target kernel
bytes and RAM residency remain unmeasured. Checkpoint container size is reported
separately. No fixed-point arithmetic is claimed merely by INT8 weight storage.

## Gates and target handoff

Every completed candidate writes checkpoint/hash, full host evaluation,
`packed/model.f9f`, packed hash/weight inventory, exact QAT-to-decoded logit and
route parity, per-expert deployed selection counts and full decoded 627/4520/
294778 set+move evaluation. `scripts/evaluate_flexible.py` repeats the independent
CPU packet reload without consulting a training checkpoint. The existing fixed-
nine artifacts and base module are hash-checked without modification.

Integer adaptation must preserve: F9F1 E/K/gate metadata; nine-token embedding
and side semantics; LayerNorm epsilon 1e-5; attention scaling by sqrt(D); GELU,
normalization and softmax behavior or a separately parity-tested approximation;
stable lower-ID routing ties; full-E softmax for K1; expert gather ordering;
zero threshold set membership; occupied-cell mask; inverse whole-set restoration
and original-coordinate ties. Add range/rounding/saturation contracts, accumulator
bounds and independent integer oracle before 6502 kernels. FP32 vector islands,
FP32 scales and nonlinearities still require adaptation. No accepted host model
is an integer, assembled-inference, game-residency or physical-C64 acceptance.

## Recorded outcomes

Final machine-readable outcome inventory is `results/flexible-summary.json`.
Detailed rejected and accepted artifacts remain under `artifacts/flexible/`.

**13 completed training runs, one accepted host policy.** Summed per-run elapsed
training/evaluation time was 545.685 seconds; two CPU-one-thread jobs briefly
overlapped. The GPU preflight found only 9 MiB used, but no CUDA training was
needed. No other process was terminated and no owned training process remains.

| Candidate | Canonical complete-set mistakes | Outcome |
|---|---:|---|
| Scratch W8H4E4K2 seeds 11 / 23 | 29 / 3 | rejected bounded runs |
| Scratch W8H4E3K2 seeds 11 / 23 | 94 / 28 | rejected bounded runs |
| Scratch W6H4E4K2 seeds 11 / 23 | 206 / 104 | rejected bounded runs |
| Scratch W6H4E3K2 seeds 11 / 23 | 195 / 180 | rejected bounded runs |
| W8H4E4K2 selected source-nine banks [3,4,0,1] | 33 | rejected, source lineage retained |
| Scratch-lineage W8H4E4K2 seed23 LR .0002 refinement | **0** | **accepted FP32 host policy** |
| All-matrix INT8 direct materialization (no training) | 45 | rejected |
| All-matrix INT8 QAT LR .0002 | 1 | rejected |
| INT8 LR .00005 best-checkpoint refinement | 1 | rejected |
| Same INT8 LR, additional worst-64-pattern BCE weight .5 | 1 | rejected |

The last run changed only the objective by adding .5 times the worst-64-pattern
mean legal-bit BCE to the full legal-bit BCE. It retained every supervised bit
and the same deployment computation; its separate checkpoint/result records this
hard-mining coefficient. This targeted final attempt did not pass; no further
runs were launched. Low-bit formats were not attempted after INT8 failed.

### Exact host handoff

Accepted config: `width=8, expert_width=4, experts=4, active=2, precision=float`.
The accepted model descends from the *fresh E4* seed-23 run and its bounded
low-LR refinement, **not** from source-nine pruning.

- Checkpoint: `artifacts/flexible/refine-scratch/w8-h4-e4-k2-float-s23/best.pt`
- Checkpoint SHA-256: `0c4154dffc05195e79a3271655a853d8842fe20a220a5465229e3a813be6e3a5`
- Packet: `artifacts/flexible/refine-scratch/w8-h4-e4-k2-float-s23/packed/model.f9f`
- Packet SHA-256: `1dfbca8f62beeb000334c8a1163c0aaa3a50a858cbc3e5f3605ed4b589d6ce33`
- Complete encoded size: **5,725 bytes**, including 24-byte header, 81-byte
  coordinate wrapper and 5,620-byte FP32 tensor payload. Checkpoint container:
  11,923 bytes. This is not the under-4-KiB goal.
- Independently reloaded packet: **0 set and move errors** across 627 canonical
  patterns, 4,520 boards and 294,778 histories; exact logit and route parity.
- Deployed expert selection counts: **[301,258,355,340]**, all four participate;
  12 distinct ordered routes. Router gradient L1 reached 4.721517562866211.
- Forward matrix MAC inventory: 128 expert + 4,280 shared = 4,408 per board,
  with the exclusions stated above; **not a C64 speed claim**.

All-matrix INT8 packets are **1,749 complete bytes**: 24 header + 81 wrapper +
1,644 tensor payload (1,352 INT8 code bytes, 80 FP32 scale bytes and 212 retained
FP32 vector bytes). Exact decoded parity and participation pass, but the best
packets still miss **one canonical bit, eight boards and 1,152 histories**, for
both set and deterministic move gates. The independent INT8-rejection CLI reload
confirms those counts. They are **not accepted under-4-KiB models**.

Strict RED/GREEN cycles were exercised for config, neural routing/gradients,
quantization/packing, real training/checkpoint/CLI, history wrapper and hard
mining. The final owned test set passes 16 tests; an integrated snapshot passed
80 tests and 677 subtests while the parallel integer work was present. The only
warning is the preexisting Torch missing-NumPy warning; these modules do not use
NumPy. One ledger naming bug was caught by a failing test and corrected: FP32
vector-island bytes are now distinguished from all retained FP32 tensor bytes.
Metadata correction did not alter any model packet or checkpoint.

Final source hashes and reproducible commands are saved under
`artifacts/flexible/source-hashes-final.json` and `reproduction-commands.txt`.
All ten preexisting canonical model packets plus `falken9/model.py` retain their
before/after SHA-256 values. No base/canonical/integer modules, legacy packet
layouts, commits or remotes were changed by this work.
