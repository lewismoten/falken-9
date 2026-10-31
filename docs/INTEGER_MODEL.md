# Whole-model integer reference: direct W8 conversion rejected

## Outcome and proof boundary

The accepted float W8/H8 checkpoint is unchanged. This experiment executes the
complete nine-token attention → readout → normalization → learned router →
stable top-2 of nine experts → legal-output policy with **integer-only inference**.
It materializes every parameter, scale exponent, descriptor, and LUT into a real
`model.f9i`. It is a derivative numerical contract, not float-logit parity.

Eight direct conversions were exhaustively checked against all **4,520 boards /
294,778 histories**. All eight are **rejected** for gameplay. In each case:

- Materialized decoding and pre-serialization integer tensors agree exactly.
- An independent Python arbitrary-width scalar forward agrees on **every logit
  and route on every board**, not just the selected move.
- Board-only execution maps back to every audited history; every missed history
  is preserved in its candidate's `counterexamples.jsonl`.
- There are zero INT64 overflows under the stated analytic bounds; saturations
  are intentional, counted separately, and are not called overflows.

| Bulk matrix bits | Activation fractional bits | Board misses | History misses | Complete bytes | Saturated elements |
|---:|---:|---:|---:|---:|---:|
| 8 | 6 | 217 | 5,851 | 5,153 | 0 |
| 4 | 6 | 1,267 | 37,967 | 4,161 | 0 |
| 8 | 7 | 102 | 2,220 | 5,153 | 185 |
| 4 | 7 | 1,249 | 38,231 | 4,161 | 260 |
| 8 | 8 | **70** | **1,189** | **5,153** | 2,893 |
| 4 | 8 | 1,242 | 37,892 | 4,161 | 3,310 |
| 8 | 9 | 99 | 2,193 | 5,153 | 9,746 |
| 4 | 9 | 1,250 | 38,097 | 4,161 | 10,900 |

INT4 here means INT4 only for query/key/value/projection/readout and expert
matrices; router/output remain INT8, embeddings/norm affine/biases INT16. No
binary/ternary training-export codebook is reused. This avoids its known codebook
difference from the assembled arithmetic kernels.

Best direct candidate: `artifacts/integer/w8-int8-q8/model.f9i`, SHA-256
`e25fd7ce61bb2c77e1eef960d2e5d97bc4f4124ff34f1b2d4672ef73df05c4b9`.
Source SHA-256:
`03757d5e2bcedbb2edc53b826bcc790588564ecea85c416045742eecbc73c577`.
Every candidate hash and exact stage maximum is in `results/integer-summary.json`.

**Unstarted:** QAT, W12 comparison, assembled whole-model inference, linked target
code size, target scratch lifetime allocation, RAM residency, C64 game integration.
The artifact-size target alone is met, but neither gameplay nor C64 acceptance is.
No GPU work or background jobs were launched by this evaluator.

## Numerical contract

`F = frac`, `S = 2**F`. Semantic activations are signed INT16 codes with real value
`code/S`; the host physically stores them in INT64 tensors so arithmetic cannot
silently overflow at INT16. Every named activation boundary rounds as specified
and clamps to `[-32768,32767]`. Counters count saturated **elements**, not boards.
The output logits use the same scale and saturation, including occupied logits.
This is a known range limitation; it is not hidden by the legal selection mask.

All divisions by a positive integer use nearest rounding with exact halfway
cases **away from zero**, except probability normalization, which intentionally
uses floor. Matrix weights have symmetric codes `[-127,127]` or `[-7,7]` and
power-of-two row exponents: real weight = `code * 2**exponent`. Offline conversion
chooses `ceil(log2(max(abs(row))/maximum_code))`; scales are per output row, per
expert where applicable. Matrix dot products are rescaled, biases added in QF,
then saturated. INT16 embeddings/norm affine/biases use exponent `-F`.

### LayerNorm

1. Mean = rounded sum / width.
2. Center each lane using that integer mean (centered scratch may exceed INT16).
3. Variance = rounded sum of centered squares / width.
4. Add `max(1, round(1e-5*S*S))` integer epsilon.
5. Compute **exact floor integer square root**, with a 31-step integer bit search.
6. Normalize by rounded `centered*S/root`; multiply QF affine gamma, round / S,
   add QF beta, and saturate.

This is not FP32 LayerNorm: integer mean, variance, epsilon, floor square root,
and low-variance behavior all matter. No floating reciprocal-square-root or
floating initialization runs during inference.

### Attention and routing softmax

Attention dot products use one global head over all nine tokens, matching the
source model. Multiply Q2F Q·K by the serialized Q15 approximation of `1/sqrt(d)`
(W8: **11585**), divide by `S*32768` with signed nearest rounding, and saturate QF
scores. This preserves genuine input-dependent attention and learned projections.

A 513-entry unsigned INT16 exponent table has entry
`round(exp(-i/32)*32768)` for `i=0..512`. Runtime subtracts the maximum, rounds
the nonnegative gap onto the 1/32 grid, and clamps to index 512. Exponent lookup
has bounded domain `[0,16]`; tails are explicitly clamped, not extrapolated.
Probability codes are `floor(exp_code*32768/sum(exp_codes))`, then all remainder
is assigned to the **first maximum-score** lane. They sum exactly to 32768.
Probabilities require **unsigned** INT16 because one visible lane can have 32768.
The sum cannot be zero because a maximum-score lane always indexes entry zero.

The router ranks its learned integer scores directly, stable lower expert ID on
a tie. Only its selected two scores enter the same softmax; only selected experts
are evaluated. Both weighted outputs are merged with rounded division by 32768.

### GELU and output

A separate 513-entry signed INT16 table samples exact-erf GELU at `i/32`,
`i=-256..256`, in QF. Input rounds to the nearest grid point; below -8 the result
is zero, above +8 it is identity. Runtime uses only integer indexing/comparisons.
Offline generation uses Python floating math, explicitly confined to `convert`.

Output selection masks occupied cells, then chooses maximum under fixed
`ebdfhcgia`; the router's lower-ID tie rule is a different rule.

### Rounding and approximation accounting

- Each nearest integer rescale introduces at most half a destination code before
  saturation. Weight rounding is at most half its row's power-of-two scale.
- LUT input-grid rounding is at most 1/64 in real units before explicit clipping.
- GELU table-value rounding is at most half a QF code; tails use the above rule.
- Softmax floor leaves fewer than N probability units for deterministic remainder
  assignment. No claim of exact real softmax or FP32 LayerNorm error is made.
- For best Q8, all **2,893** saturation events occur at final output only;
  intermediate activations do not saturate. Observed largest wide intermediate
  is **18,151,540,190**, so an INT32 whole-model claim would already be false.

## Accumulator proof and widening burden

For W8 with full INT16 activation domain and INT8 codes, the 72-lane readout
absolute dot bound is **301,989,888**, within signed INT32 before scaling/bias.
This does **not** prove the remaining model uses INT32:

| Intermediate | Conservative absolute bound |
|---|---:|
| Attention 8-lane INT16 × INT16 dot | 8,589,934,592 |
| Above multiplied by W8 Q15 factor | 99,514,392,248,320 |
| LayerNorm centered square sum, width 8 | 34,358,689,800 |
| Probability-weighted INT16 sum, normalized probabilities | 1,073,741,824 |

All are safely within INT64. Matrix-rescale exponents are validated in `[-24,16]`;
the loose 72-lane dot times `2**16` also fits INT64. Centered values are bounded by
65535; `centered*S*gamma` has the reported conservative bound, likewise below
INT64. Isqrt candidate squares stay below `2**62`. Probability numerators are at
most `32768**2`, and softmax denominators at most `9*32768`.

Actual per-candidate intermediate maxima and analytic bounds are machine-readable.
The Python scalar oracle uses arbitrary-width integers independently of torch.
Widening, shifts, division/isqrt, and nonlinear tables still need assembled target
implementations; the existing binary16 dot kernel does not establish those gates.

## Exact materialization and sizes

All multibyte fields are little-endian, no alignment/padding beyond a last nibble.
Header `<4sBBBBH>` (10 bytes): magic `F9I1`, fractional bits, width, expert width,
tensor count 21, attention Q15 factor. Tensor IDs/order are the `NAMES` tuple in
`integer_export.py`, part of this versioned fixed architecture contract.

All descriptors precede all parameter payloads. Each descriptor is `<BBH>`:
bits, rank, exponent count; then `rank` unsigned-byte dimensions and the declared
number of signed INT8 exponents. Offsets/lengths are derived from validated shape
and bit width. Expert matrices retain source `[expert,input,output]` orientation;
row exponents are expert-major/output-major. Other matrices are `[output,input]`.

INT8/INT16 use two's-complement bytes. INT4 uses signed two's-complement nibbles,
first scalar in low nibble, second in high nibble; unused last high nibble is zero.
No implicit float scale or omitted bias remains. The final bytes are exactly
`513H` exponent entries then `513h` GELU entries. Decoder checks magic, dimensions,
precision class, exponent count/range, padding, and exact total length. The external
SHA-256 manifest provides identity; the binary has no internal checksum.

| Component | INT8 baseline | INT4 bulk |
|---|---:|---:|
| Header | 10 | 10 |
| All descriptors/exponents | 335 | 335 |
| All parameter codes including INT16 islands | 2,756 | 1,764 |
| Both LUTs | 2,052 | 2,052 |
| **Complete encoded model** | **5,153** | **4,161** |

### Model, scratch, and code are separate

Encoded bytes are not target peak RAM. This host implementation decodes all 2,442
parameter codes to INT64 (19,536 bytes) and both LUTs to INT64 (8,208 bytes), plus
unmeasured Python metadata. It vectorizes batches of 256 and allocates INT64
intermediates; host peak scratch is **not measured** and is not claimed to fit C64.

For a future single-board target schedule, one INT16 token tensor is 144 bytes,
Q/K/V together 432, attention score and unsigned probability matrices 162 each.
These are **individual logical buffers, not a disjoint lifetime map or peak**;
wide accumulators, division/isqrt state, expert/readout state, legal board and
routes must also be allocated. Full target scratch/code/residency are unstarted.
Runtime/export/evaluator host source byte counts and hashes are recorded separately
in the summary, not passed off as assembled 6502 decoder/kernel size.

## Reproduction and strict TDD evidence

From `/home/ai/falken-9`, no install or GPU required:

```sh
OMP_NUM_THREADS=1 .venv/bin/python scripts/evaluate_integer.py \
  --bits 8 4 --frac 6 7 8 9 --scalar-oracle
OMP_NUM_THREADS=1 .venv/bin/python -m pytest tests/test_integer_model*.py \
  tests/test_integer_export*.py -q
OMP_NUM_THREADS=1 .venv/bin/python -m pytest tests/ -q
```

The script reloads source and materialized candidates, checks immutable source
hashes before/after each candidate, preserves complete board logits/routes, and
writes `results/integer-summary.json`. The independent oracle intentionally lives
in tests and is loaded only when `--scalar-oracle` is selected, not by inference.
No label, history index, oracle move, or solver is consulted by `IntegerPolicy`.

Durable observed red/green logs under `artifacts/integer/`:

- `01-arithmetic-red.log` → `02-arithmetic-green.log`.
- `03-export-red.log` → `04-export-green.log`.
- `05-network-red.log` → `08-network-green.log`. Logs 06/07 retain a genuine
  initially incorrect no-saturation fixture assumption at Q9/Q8; the independent
  oracle already agreed. The zero-saturation fixture was explicitly restricted
  to Q6, not used to erase measured Q8/Q9 output saturations.
- `09-evaluation-red.log` → `10-evaluation-green.log`.
- `11-validation-red.log` → `12-validation-green.log`.
- `13-bounds-red.log` → `14-bounds-green.log`.
- `search-final.log`, per-candidate `evaluation.json`, `board-results.json`,
  `counterexamples.jsonl`, and `final-full-suite.log` retain final real executions.

The full suite passed with the existing optional missing-NumPy warning; the
environment was not changed or the warning hidden.

## Diagnosis and next scoped experiment

A separate read-only CPU float comparison reverified zero source move misses.
For best integer Q8, 297 boards have different route sequences; 20 of its 70 move
misses also have route differences. Therefore final-output-only fitting cannot be
assumed to repair the upstream contract. Output saturation is another explicit
limitation (float source extrema observed approximately -408 to +349).

Next **proposed, not run** QAT scope: retain W8 Q8 INT8 and this exact forward
contract, freeze every tensor except `norm2.weight`/`norm2.bias`, and optimize only
that affine pair through a surrogate whose forward is materialized-integer exact.
This changes one trainable scope, not the architecture, data, or all float weights.
Snapshot frozen hashes and rerun every parity/gameplay gate. Its sufficiency is
unknown; direct conversion failures are not a proof that integer W8 is impossible.
A separate direct-conversion experiment could give final logits a coarser scale,
but that would require an explicit new serialized contract, not reinterpretation
of these rejected artifacts.
