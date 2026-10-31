# Canonical whole-integer policy: accepted host contract F9J2

## Outcome and boundaries

Direct conversion of the **effective weights decoded from the accepted 4,945-byte
F9C1 packet** passes the complete policy gate, without training. The selected
`F9J2` artifact is **6,110 bytes**, including every parameter, exponent,
descriptor, coordinate permutation, tie-order byte, and both nonlinear LUTs.

- Artifact: `artifacts/canonical-integer/verified/q11-w16-a32-early-interp/model.f9j`
- SHA-256: `6c2b3dc6ec2a26fbdd28b1d7c78abbd0fcfd285c3f45bea4357fcb9f3fefa8c9`
- Immutable source: `artifacts/canonical/qat/w8-h4-float-islands-int8-refine-s23/packed/model.f9c`
- Source SHA-256: `6e10652115c9f373f34b6158eeb6f87a1bec1e7db66a2ee8a96bf5b3dd380464`
- Data SHA-256: `a4539c7cde214440f3369085725ad32faaba03d5de3265c6a8333bdc12723597`

This is **whole-integer host inference**, not assembled whole-model C64
acceptance. No GPU work, training, environment changes, commit, or push was
performed. Existing F9I1 packets and their rejections remain unchanged. The
4 KiB stretch goal is not met and was not imposed at the expense of correctness.

The actual nine-token attention, learned Q/K/V and output projections,
normalizations, flattened learned readout, learned stable top-2 router, both
selected experts, residuals and learned membership head remain present. Every
one of nine experts is selected on the exhaustive domain; selection counts are
`[157,151,149,202,167,75,146,104,103]`. One canonical board has a different route
sequence from the floating source, without a policy error. Exact float-route or
float-logit equivalence is not an acceptance requirement.

## Diagnosis before more training

`RangeIntegerPolicy` changes only the old W8/Q8 final output boundary to INT32.
All preceding integer operations remain the frozen F9I1 operations. Exhaustive
results, complete board vectors and routes are under `artifacts/integer-range/`.

| Old W8/Q8 diagnostic | INT16 final output | INT32 final output |
|---|---:|---:|
| Board move errors | 70 | 69 |
| History move errors | 1,189 | 1,187 |
| Saturated elements | 2,893 | 0 |

Every old output equals the INT16 clamp of its widened counterpart, and **all
4,520 board route pairs agree**. Thus clipping is real but is **not the main
cause** of this old conversion's losses: removing it repairs only one board /
two histories. The old rejected F9I1 artifact is not reinterpreted or promoted.
The diagnostic writes no new F9I1 model claiming changed semantics.

Canonical conversion then separately tests precision, hidden range, attention
rounding, and LUT interpolation before any QAT. This is not latent master-island
conversion: `decode_model` first materializes the actual accepted packet's
weights; no checkpoint latent tensors enter conversion.

## Explicit numerical contract

`S=2**F`; selected `F=11`. Matrix codes are signed INT16, with independent
power-of-two exponents per output row (expert-major/output-major for expert
matrices). Other parameters are signed INT16 QF. Offline nearest rounding is
halfway away from zero, not PyTorch's default nearest/even. Parameter conversion
rejects overflow. Selected intermediate semantic activation codes and **final
membership scores** have signed **32-bit** boundaries. Final scores are not
clipped to INT16 merely for uniformity. Physical host tensors and arithmetic are
INT64, with separately measured widening needs below.

All divisions by positive denominators use nearest rounding, ties away from
zero, except softmax normalization, which uses floor. Each linear operation
computes the integer dot, shifts or rounds according to the serialized row
exponent, adds QF bias and applies its declared boundary. Expert matrices retain
source `[expert,input,output]` storage. Prefix accumulation maxima are measured,
not inferred solely from canceled final dots.

LayerNorm preserves the earlier explicit integer contract: rounded mean,
centered lanes, rounded average squared deviation, integer epsilon
`max(1,(S*S+50000)//100000)`, exact floor integer square root, rounded
`centered*S/root`, rounded QF affine multiply, and bias. It does not substitute
floating normalization. The supported F9J2 fractional-bit range is 6 through 11:
Q12's +8 GELU endpoint no longer fits its declared signed INT16 table and is
rejected rather than silently wrapped.

### Attention alternatives and changed rounding

All three serialized modes were exhaustively tested:

1. `legacy`: `round(dot*11585/(S*32768))`, the old Q15 factor placement.
2. `early`: `round(round(dot/S)*11585/32768)`, moving the first rescale before
   multiplication. This introduces one extra rounding at the QF dot boundary.
   The additional pre-final-round error is at most `11585/(2*32768)` destination
   codes; final rounded scores can differ by at most one code from `legacy`.
3. `rational`: `round(dot*181/(S*512))`. The smaller factor approximates
   `1/sqrt(8)` with error about -0.00003776559, and has one final rounding, but
   leaves a larger product than early rescaling.

For INT16 matrix weights, observed maximum absolute attention-factor products:

| QF | legacy | early | rational |
|---:|---:|---:|---:|
| Q8 | 32,853,461,270 | 128,338,630 | 513,291,022 |
| Q9 | 131,117,292,250 | 256,086,425 | 2,048,530,850 |
| Q10 | 523,845,838,075 | 511,570,430 | 8,184,384,695 |
| Q11 | 2,093,426,761,650 | **1,022,179,305** | 32,706,969,690 |

Only `early` keeps this actual Q11 stage within signed INT32. Raw Q11 attention
dots peak at 180,701,490. Q10 legacy passes policy, while Q10 early/rational each
lose one canonical set; changed rounding is not assumed harmless. Q11 passes
with all three modes, so early is selected for its smaller arithmetic burden.

### Nonlinear tables

The packet contains 513 unsigned INT16 exponent entries
`round(exp(-i/32)*32768)`, i=0..512, and 513 signed INT16 exact-erf GELU samples in
QF at i/32, i=-256..256. Floating math is confined to **offline conversion/LUT
generation**; decoding and inference use only integers.

Selected inference linearly interpolates adjacent integer samples: compute
`u=clamp(x*32+offset*S,0,512*S)`, `i=u//S`, `r=u%S`, then signed nearest-round
`(table[i]*(S-r)+table[min(i+1,512)]*r)/S`. This differs explicitly from the old
nearest-grid lookup. Exponent inputs are max-subtracted nonnegative gaps;
GELU uses offset 256. GELU below -8 is zero and above +8 is identity. Exponent
gaps beyond 16 use the last table value. No floating fallback exists.

Softmax divides each exponent times 32768 by the row sum using floor, then gives
all remaining probability units to the first maximum-score lane. Unsigned Q15
probabilities sum exactly to 32768. Router top-k ties favor lower expert ID.
Only selected experts run; both selected scores determine their softmax gates.

### Full-set coordinate wrapper

The neural head predicts membership at **integer score >= 0** on legal canonical
squares. Inverse-transform the entire predicted set, then select in the original
coordinate tie order `ebdfhcgia`. An empty set raises; there is no argmax repair,
minimax, lookup policy, or dead floating fallback. The public history wrapper
validates chronology/nonterminal status before canonicalizing. Serialized wrapper
bytes are checked against the supported transforms and ties before execution.

## Exhaustive results and rejection evidence

Thirty distinct arithmetic candidates were materialized and decoded. Every one
has zero independently scalar-verified logit and route mismatches on all 627
canonical boards. Four pass the full policy gate: Q10/W16 legacy, and Q11/W16
legacy/early/rational, all with INT32 boundaries and interpolation.

Selected artifact:

- **627 canonical sets**, **4,520 board sets/moves**, **294,778 history
  sets/moves**: zero errors; no empty predicted sets.
- **36,160** coordinate-transform combinations: zero errors.
- Decoded versus pre-serialization integer codes: exact. Complete logits/routes:
  zero decoded/materialized and independent Python arbitrary-int mismatches.
- Public singleton history wrapper exercised on one representative of **every
  board**: zero errors; expanded history gate uses every validated history index.
- Zero activation/output saturation events. Minimum legal signed membership
  margin: **110 Q11 codes = 0.0537109375**.

Representative rejected direct variants (interpolated, INT32 boundaries):

| Matrix bits | QF | Canonical set errors | History move errors | Bytes |
|---:|---:|---:|---:|---:|
| 8 | 8, legacy | 12 | 2,105 | 4,558 |
| 8 | 9, legacy | 9 | 921 | 4,558 |
| 8 | 10, legacy | 11 | 1,081 | 4,558 |
| 16 | 8, legacy | 2 | 32 | 6,110 |
| 16 | 9, legacy | 1 | 16 | 6,110 |
| 16 | 10, early | 1 | 32 | 6,110 |

With INT16 hidden boundaries, interpolated Q10/early loses 12 canonical sets and
Q11/early loses 82; observed expert outputs and residuals exceed INT16. With
INT32 boundaries but **nearest-grid** LUT lookup, Q10/early loses two sets and
Q11/early loses three. Increasing precision alone without fixing numerical
boundaries is insufficient. All candidate vectors, routes, board counterexamples
and every affected history identifier are retained in candidate directories.
`results/canonical-integer-summary.json` inventories all 30 candidates and hashes.

No QAT is needed for the passing direct conversion. Narrow INT8 matrices remain
a separate future optimization; their failures do not justify risking this
accepted reference or claim that uniform low precision is impossible.

## Exact encoded bytes

All multibyte integers are little-endian. Header `<4s10BHH>` is 18 bytes:
magic `F9J2`, F, width, expert width, E, top-k, activation bits, final score bits,
attention mode ID, interpolation flag, tensor count, factor, denominator. E and
k are explicit dynamic descriptors; no nine-expert count is inferred from packet
length. Current converter emits top-2; the decoded runtime supports declared E/k.
This is preparatory compatibility, not acceptance of an untested flexible model.

After the 81-byte wrapper come all descriptors, then all tensor payloads in
`integer_export.NAMES` order, then both LUTs. Descriptors encode `<BBH>` bits,
rank, exponent count, followed by unsigned-byte dimensions and signed-byte
exponents. INT8/INT16 payloads are two's complement. Loader checks metadata,
shapes, exponent counts/ranges, affine scales, wrapper and exact final length.
Identity is supplied by the external SHA-256 manifest, not an internal checksum.

| Component | Bytes |
|---|---:|
| Header | 18 |
| Eight coordinate transforms and original tie order | 81 |
| All tensor descriptors and row/affine exponents | 299 |
| All 1,830 signed INT16 parameter codes | 3,660 |
| Exponent and GELU LUTs | 2,052 |
| Alignment / implicit floating scales | 0 |
| **Complete model** | **6,110** |

## Actual widening and scratch burden — not a 6502 acceptance claim

Early attention is signed-INT32-safe on the exhaustive **supported** domain;
whole-model signed-INT32 arithmetic is **not** established:

| Selected stage | Observed maximum absolute value | Signed bits needed |
|---|---:|---:|
| Attention scaled | 1,022,179,305 | 31 |
| Readout dot / sequential prefix | 1,303,949,574 | 32 |
| Expert second-layer dot / prefix | 2,001,542,950 | 32 |
| Probability-weighted expert merge | 3,927,077,675 | **33** |
| Final output dot / prefix | 5,126,670,429 | **34** |
| Final output Q11 score | 898,107 | 21 |

Observed-input-envelope bounds also cover arbitrary matrix prefix accumulation:
`input_lane_abs_max * weight_code_abs_max * input_width`. Largest is
29,091,600,968 (36 signed bits), for the final output matrix. A signed **5-byte**
accumulator covers these finite measured envelopes; this is not yet an assembled
kernel. All measured prefixes and the separate conservative envelopes are in
candidate statistics. Neither this finite legal-domain check nor the host INT64
representation proves safety for every syntactically possible arbitrary INT32
activation vector. LayerNorm's actual centered square sums fit INT32, but its
host isqrt uses generic wide candidate squares; a range-bounded target isqrt,
division, interpolation and rounded rescale implementation still need proof.

Individual logical target buffers under the serialized INT32 activation contract:
288 bytes per 9x8 token tensor; 864 for Q/K/V together; 324 for 9x9 scores; 162
for unsigned probabilities; 64 for two expert outputs; 36 for final scores.
Wide accumulators require 5 bytes each under the above envelope, plus explicit
rounding/division/isqrt state. These are **not** a complete disjoint lifetime map
or proven peak RAM. The host expands parameters to 14,640 bytes and LUTs to
8,208 bytes, plus Python metadata and vectorized/prefix-instrumentation scratch;
that expansion is not the proposed packed target representation. Decoder/kernel
machine-code bytes, full-model cycles, peak target scratch, game residency and
full-model integration remain unmeasured/unstarted.

The separately developed signed-INT32-to-INT16 requantization kernel is only a
narrow arithmetic gate. Its INT16 saturation must **not** be applied to this
contract's wide final scores or intermediate expert outputs. It also does not
supply the 33–36-bit accumulation required above.

## Reproduction and tests

From `/home/ai/falken-9`, prefix commands with
`OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 .venv/bin/python`:

```text
scripts/evaluate_canonical_integer.py
scripts/evaluate_canonical_integer.py --frac 10 11 --bits 16 --attention early --activation-bits 16 --output artifacts/canonical-integer/narrow --summary artifacts/canonical-integer/narrow-summary.json
scripts/evaluate_canonical_integer.py --frac 10 11 --bits 16 --attention early --activation-bits 16 32 --nearest --output artifacts/canonical-integer/nearest --summary artifacts/canonical-integer/nearest-summary.json
scripts/evaluate_canonical_integer.py --frac 11 --bits 16 --attention early --public --output artifacts/canonical-integer/verified --summary artifacts/canonical-integer/verified-summary.json
artifacts/canonical-integer/finalize.py
-m pytest tests/test_range_integer*.py tests/test_canonical_integer*.py -q
-m pytest tests/test_integer_model*.py tests/test_integer_export.py tests/test_canonical_model.py tests/test_canonical_training.py tests/test_range_integer*.py tests/test_canonical_integer*.py -q
```

Actual results: **15 owned tests passed**, and **35 integrated regression tests
passed**, with only the existing missing-NumPy warning. Parallel flexible-model
work was not used as a prerequisite or silently certified. Durable red/green
logs cover range change, exporter, independent scalar runtime, exhaustive gate,
prefix bounds and LUT range validation. No full-suite acceptance is inferred
from this selected regression set.

Next stage: preserve this exact packet and build separately tested range-aware
6502 kernels and a concrete scratch lifetime map, then execute the full decoded
neural path and policy gate on target. No more training is required merely to
establish integer feasibility.
