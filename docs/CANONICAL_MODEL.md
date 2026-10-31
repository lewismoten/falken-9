# Canonical full-optimal-set learned policy

## Outcome

A separately trained **width 8 / expert width 4** canonical policy predicts every published optimal move set exactly. The smallest accepted encoded candidate is **4,945 bytes** (`F9C1`), including all weights, six FP32 scales, header, eight coordinate permutations, and original tie order. This is below the 8 KiB encoded-model objective, **not** below 4 KiB. It is a **host-FP32 research result**, not resident C64 or integer-inference acceptance.

Accepted artifact:

- `artifacts/canonical/qat/w8-h4-float-islands-int8-refine-s23/best.pt`
- Checkpoint SHA-256: `fca53d3712105f2647f43897bd66846a940046028c30db414f7b410a8b74402a`
- `artifacts/canonical/qat/w8-h4-float-islands-int8-refine-s23/packed/model.f9c`
- Encoded SHA-256: `6e10652115c9f373f34b6158eeb6f87a1bec1e7db66a2ee8a96bf5b3dd380464`

`results/canonical-summary.json` contains the full candidate inventory, checkpoint hashes, source hashes, environment, commands, payload inventory, direct-materialization results, and final evaluations. Every run preserves its best checkpoint, evaluation JSON, all failing-board examples, and all affected-history identifiers under ignored `artifacts/canonical/`.

## Learned representation and inference contract

`CanonicalPolicy` subclasses the actual `CompactPolicy`, not a replacement MLP. It retains nine position-labelled occupancy tokens, side embedding, both normalizations, Q/K/V projections, genuine full self-attention and residual, flattened learned readout, nine experts, stable lower-ID top-2 router ties, both selected expert computations, and learned nine-square output.

Training canonicalizes each published board and explicitly transforms **the complete `optimal_moves` set**, rejecting conflicting canonical labels. The 294,778 legal histories give 4,520 boards and **627 canonical nonterminal patterns**. BCE supervises every legal canonical square's membership; occupied squares are masked. This is not training a selected canonical target.

Public `predict_history(history)` validates nonterminal chronology, canonicalizes the board, executes the network, takes legal logits **>= 0** as the predicted set, inverse-maps that set, then selects the first move under **original-coordinate `ebdfhcgia`**. Empty predicted sets raise an error; no oracle, minimax, lookup, argmax repair, or heuristic fallback is used in inference. `canonical_training` reads labels only for supervision/evaluation and is not imported by the inference module.

## Exhaustive verification

For both accepted float W8/H4 and final INT8-island W8/H4:

- **627/627** canonical full sets exact, zero membership-bit errors.
- **4,520/4,520** boards: zero deterministic-move errors and zero set errors.
- **294,778/294,778** histories: zero deterministic-move errors and zero set errors.
- **36,160** board/transform combinations: zero transformation or full-set-restoration errors, including board stabilizers.
- Final fake-QAT versus independently decoded encoded-file CPU execution: **0 maximum absolute logit error**, identical routes, both exhaustive gates pass.
- Independently reloaded final encoded model exercises the public history wrapper on a representative history for **every one of the 4,520 boards**, with zero move errors.
- Singleton execution on all 627 canonical boards has zero set errors. Singleton/bulk logits differ by up to `0.000492095947265625`; exact logits across batch sizes are **not** claimed. Final legal signed membership margin is about `0.208855`.

Every primary history is validated against its board and indexed to an evaluated board-dependent neural result; this deduplication is an exhaustive evaluation optimization, not an inference policy table. Pinned data revision is `6ea253e1fa7de4a61eedeab6bbd9d8117af1fcb7`, SHA-256 `a4539c7cde214440f3369085725ad32faaba03d5de3265c6a8333bdc12723597`.

Verification command: `OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 .venv/bin/python -m pytest tests -q` returned **48 passed and 37 subtests passed**. The only warning is the environment's missing optional NumPy installation. New tests cover real inherited network gradients, original-coordinate ties, empty/nonfinite-set rejection, canonical label conflicts, real training/checkpoint reload, direct materialization, and independently scalar-decoded packet parity for nine precision combinations.

## Bounded search: actual outcomes

All candidates used one CPU process and one Torch thread. GPU preflight found an unrelated inference service occupying the GPU; it was left untouched, and no CUDA training was launched. Float initialization seeds were 11 and 23. AdamW used zero weight decay, full canonical batches, BCE, and gradient clipping at 5. Initial float learning rate was 0.003. Counts below are the saved best checkpoint, not the last step.

| Candidate | Canonical set errors | History move errors | Complete encoded bytes | Outcome |
|---|---:|---:|---:|---|
| Float W4/H4, seed 11 | 253 | 42,813 | 3,033 | rejected |
| Float W4/H4, seed 23 | 241 | 44,037 | 3,033 | rejected |
| Float W6/H6, seed 11 | 104 | 23,988 | 5,953 | rejected |
| Float W6/H6, seed 23 | 12 | 2,112 | 5,953 | rejected |
| Float W8/H4, seed 11 | 2 | 128 | 7,417 | rejected |
| Float W8/H4, seed 11, LR 0.001 refinement | 2 | 128 | 7,417 | stopped; no gain |
| Float W8/H4, seed 23 | **0** | **0** | **7,417** | accepted host reference, step 3,300 |
| Float W8/H8, seed 11 | **0** | **0** | 9,865 | accepted host reference, step 1,400; over 8 KiB |
| W8/H4 ternary bulk, float islands | 269 | 53,680 | 4,385 | rejected after 4,000 QAT steps |
| W8/H4 binary bulk, float islands | 299 | 52,590 | 4,281 | rejected after 4,000 QAT steps |
| W8/H4 float bulk, INT4 islands | 269 | 44,609 | 4,529 | rejected after 4,000 isolated QAT steps |
| W8/H4 float bulk, INT8 islands | 1 | 108 | 4,945 | near gate after 4,000 isolated QAT steps |
| W8/H4 float bulk, INT8 islands, LR 0.0002 refinement | **0** | **0** | **4,945** | accepted at refinement step 2,200 |

Low-bit candidates initialize from the passing float W8/H4 seed-23 teacher. **Direct quantization was exhaustively evaluated and independently decoded before QAT**: ternary bulk 457 canonical set errors, binary bulk 455, INT4 islands 353, INT8 islands 2. Thus none was promoted by parity alone. Bulk QAT explicitly allows full-network adaptation; island-only stages freeze every non-island tensor. Frozen tensors remain bit-identical in both initial and refined INT8 runs, with predecessor frozen-tensor digests retained. All rejected candidates remain preserved; these bounded failures are not proofs of architectural impossibility. Summed candidate training/evaluation durations were about 298 seconds; GPU training time was zero.

## Packet and quantization details

`F9C1` has a fixed 16-byte little-endian header (`<4sBBBBII`: magic, width, hidden width, bulk mode, island bits, parameter count, reserved zero), followed by 72 permutation bytes and 9 tie-order indices. Tensor order is inherited `CompactPolicy.named_parameters()`. Tensor shapes are derived from dimensions; there is no per-tensor name/shape metadata cost. Quantized tensors begin with their counted FP32 scales, then LSB-first fixed-width codes. Only final-byte bit padding is used. Binary codes represent -1/+1; ternary codes 0/1/2 represent 0/+1/-1 and code 3 is rejected. Integer islands use symmetric signed two's-complement codes, round-to-nearest/even, and one FP32 max-absolute scale per tensor. The standalone decoder materializes FP32 weights without re-quantization. Tests independently decode each scalar with a different bit-extraction approach.

The final candidate quantizes **position, occupancy embedding, side embedding, readout matrix, router matrix, and output matrix to INT8**. All Q/K/V/projection matrices, expert matrices, biases, and normalization parameters remain FP32. Its exact inventory is:

- Weight/code bytes: **4,824**.
- Six FP32 scale values: **24** bytes.
- Header: **16** bytes; symmetry/tie data: **81** bytes.
- Total: **4,945** bytes; **1,830** parameters.
- No nonlinear LUT or alignment bytes are used by this **host** format. Host LayerNorm, square root, softmax and GELU still require their normal runtime implementation; zero LUT bytes does not mean free nonlinearities.

There is no on-target decoder/kernel code byte count or accepted scratch-memory ledger yet. The materialized host decoder expands weights; it does **not** demonstrate execution while packed or whole-system C64 RAM residency.

## CPU evidence, not 6502 claims

Final decoded CPU neural-only benchmark: approximately **379,384 boards/second**, one thread, batch 627, ten measured repetitions after warm-up. Canonicalization/restoration are excluded. Actual public-wrapper execution over all 4,520 boards took about **2.116 seconds** on this host, including validation, transforms, singleton network calls and restoration. Results vary with host scheduling and batch shape.

Architecture accounting gives 4,448 learned/attention dense multiplications per board, excluding normalization, nonlinearities, gate weighting and bias additions. This is an operation count, **not a 6502 speed or cycle measurement**. No GPU throughput is extrapolated to target hardware.

## Reproduction and next gate

Run from the repository root; all invocations use `OMP_NUM_THREADS=1 MKL_NUM_THREADS=1` and `.venv/bin/python`:

```text
scripts/train_canonical.py --steps 5000 --seconds 90
scripts/train_canonical.py --output artifacts/canonical/seed23 --shapes 4x4,6x6 --seeds 23 --steps 5000 --seconds 45
scripts/train_canonical.py --output artifacts/canonical/seed23-wide --shapes 8x4 --seeds 23 --steps 6000 --seconds 45
artifacts/canonical/run_stages.py
artifacts/canonical/refine_int8.py
scripts/evaluate_canonical.py artifacts/canonical/seed23-wide/w8-h4-float-s23/best.pt --output artifacts/canonical/independent-reload
artifacts/canonical/verify_public.py
-m pytest tests -q
```

The rejected seed-11 float W8/H4 continuation called `train_candidate` on its saved best with seed 11, 4,000 steps, 45-second bound and LR 0.001 (`artifacts/canonical/refine.log`). The artifact scripts contain the complete teacher/source paths and quantization-stage settings. Current CLI supports `--teacher`, `--precision` and `--island-precision` with a mandatory direct-materialization gate. Candidate directories are not overwritten by the CLI; choose a fresh output root when repeating.

**Next stage:** preserve the accepted 4,945-byte checkpoint and packet; separately parity-test per-row or shared-scale quantization of its remaining FP32 bulk groups, rather than extending the badly regressed binary/ternary runs. Define and test target activation/accumulator ranges, rounding, nonlinear approximations, packed execution and 6502 layer slices before claiming target acceptance. No C64 inference, physical hardware, assembled full-model cycles, residency, or game integration is claimed here. Frozen base float-W8 and original Crystal-9/C64 releases were not modified; no commit or push was performed.
