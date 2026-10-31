# Four-expert whole-integer host candidates

## Outcome and immutable lineage

Direct materialization passes; **no QAT or training was needed**. All candidates
come from the actual effective weights decoded from the accepted 5,725-byte
F9F1 packet, not a latent training checkpoint:

- Source: `artifacts/flexible/refine-scratch/w8-h4-e4-k2-float-s23/packed/model.f9f`
- Source SHA-256: `1dfbca8f62beeb000334c8a1163c0aaa3a50a858cbc3e5f3605ed4b589d6ce33`
- Dataset SHA-256: `a4539c7cde214440f3369085725ad32faaba03d5de3265c6a8333bdc12723597`
- Architecture: nine actual tokens, width 8, hidden width 4, four learned experts,
  stable learned top-2 routing, selected-score softmax, only selected experts
  evaluated. The inherited learned attention and MoE remain intact.
- Existing frozen canonical/integer/flexible source modules and E9 artifacts
  were not modified. New wrappers reuse the existing tested F9J2 contract.

## Handoff artifacts

All paths below are beneath `artifacts/flexible-integer/`, ending in `model.f9j`.
All use A32, **INT32 final scores**, early attention scaling, interpolated LUTs.

| Directory | Bytes | Canonical / board / history move errors | Expert usage | Minimum legal signed integer margin |
|---|---:|---|---|---:|
| `q11-w16-a32-early-interp` | 5,195 | 0 / 0 / 0 | 301,258,355,340 | 54 |
| `q10-w16-a32-early-interp` | 5,195 | 0 / 0 / 0 | 301,258,355,340 | 18 |
| `q11-mixed-e2-output-projection` | 4,931 | 0 / 0 / 0 | 301,258,355,340 | 142 |
| `q10-mixed-e2-output-projection` | 4,931 | 0 / 0 / 0 | 300,259,355,340 | 65 |

SHA-256, in table order:

```text
fe180f8a931f9d92d8aa39da337bc819d0dbe4e6d971edcba00324fbc18a91c1
4c913d2f1aa0d39144d68f30fc843e793f994f0ad3df360155c7540b31f44dc0
084cc3cd264b80073eb82eb347504d60293f6f7f96ffb9419892ed902b941e28
94b46bcae2476a63716fb05c8820883e4e24b85960de7ea0d34c449bcd4f8faa
```

The simplest initial runtime handoff is Q11/W16. Mixed candidates use INT8 only
for `projection.weight`, `expert_w2`, and `output.weight`; every other matrix
remains INT16. They save 264 encoded bytes without narrowing activations.
Q11 mixed preserves every float route; Q10 mixed changes one canonical route
while preserving every required set and move. The summary's `best` sorts size
then observed accumulator magnitude, **not measured target execution time**.
The Q11 mixed packet is a precision-preserving alternative to that selection.

Three individually passing INT8 component variants are also preserved:
`q11-int8-expert_w2` (5,067 bytes), `q11-int8-output` (5,123), and
`q11-int8-projection` (5,131). Their exact hashes and gates are in
`results/flexible-integer-summary.json`.

## Exhaustive evidence

For every accepted candidate:

- 627 canonical **full optimal sets** exact; 4,520 board sets and deterministic
  moves exact; 294,778 history sets and moves exact.
- Independently serialized/reloaded packet versus in-memory conversion: zero
  logit and route discrepancies on all 627 canonical boards.
- Independent Python arbitrary-integer scalar forward versus materialized
  Torch integer forward: zero logit and route discrepancies on all 627 boards.
  The scalar oracle is reused from `tests/test_canonical_integer_model.py`;
  it does not call production integer arithmetic.
- Actual public `predict_history` called on one real representative history
  for **each of 4,520 boards**, with zero move discrepancies. Every dataset
  history is separately validated against its board by the pinned loader and
  expanded into the exhaustive history gate; this is not 294,778 wrapper calls.
- 1,254 selected-expert executions for the canonical batch, with every learned
  expert used; zero stored-activation/final-score saturation.
- Artifact, source-before/source-after, tensors, routes, logits, counterexamples,
  layer diagnostics for failures, and bounds are saved, not synthesized.

Verification command (18 tests passed; existing optional NumPy warning only):

```sh
.venv/bin/python -m pytest tests/test_flexible_integer_export.py \
  tests/test_flexible_integer_model.py tests/test_flexible_integer_exhaustive.py \
  tests/test_canonical_integer_export.py tests/test_canonical_integer_model.py \
  tests/test_canonical_integer_validation.py -q
```

This is the integrated owned-file/contract test set, not a claim that all
unrelated or concurrently modified repository tests ran.

## Byte inventory and arithmetic cost

| Component | W16 | Mixed |
|---|---:|---:|
| Matrix codes | 2,384 | 2,120 |
| Affine/bias/embedding codes | 426 | 426 |
| Signed power-of-two row exponents | 113 | 113 |
| Structural descriptors | 121 | 121 |
| Header | 18 | 18 |
| Coordinate/tie wrapper | 81 | 81 |
| Exp and GELU tables, 513 x 2 bytes each | 2,052 | 2,052 |
| Total encoded packet, no alignment/compression | **5,195** | **4,931** |

`inventory_detail.tensors` lists every tensor shape, width, byte count and row
exponent. No floating inference tensors/scales are retained. LUT generation and
conversion use floating point **offline only**. There is no LUT compression or
runtime decompression. Host source-file byte counts and SHA-256 are external
inventory entries, **not 6502 binary sizes**. Assembled decoder/kernel size,
zero-page and stack use are explicitly unknown until target implementation.

A conservative non-aliasing scalar schedule proposal totals **3,076 scratch
bytes**: seven 9x8 INT32 token buffers, 81 INT32 attention scores, 81 UINT16
probabilities, eight global INT32 vectors, selected hidden/output vectors,
router scores, gates/indices, output logits, wide scalar temporaries and wrapper
work. The report itemizes these. This is neither actual Torch allocation nor
an implemented target lifetime map. Packet plus proposed scratch excludes
code, stack, zero-page, display/loader lifetimes and other application memory;
**no target RAM capacity or residency is assumed or proven**.

Structural computation is 4,408 multiply-accumulates per board: 3,112 learned
matrix MACs and 1,296 QK/PV attention MACs. Mixed precision changes the stored
weight width of 712 matrix MACs (projection 576, selected expert W2 64, output
72); it does not remove those operations. Fewer experts reduce router work,
but top-2 expert execution remains top-2. No C64 cycle/speed claim follows from
packet width or host timing.

## Accumulator requirements

Reports include sequential prefixes, final sums, and dot envelopes. Envelopes
use corpus-observed operand maxima with fan-in; they are conservative over
this evaluated corpus, **not universal bounds for arbitrary unsupported input**.

| Configuration | Largest observed signed bits | Largest matrix envelope bits | Attention dot / weighted / expert mixture envelope bits |
|---|---:|---:|---|
| Q11 W16 or accepted Q11 mixed | 34 | 36 | 31 / 32 / 36 |
| Q10 W16 or accepted Q10 mixed | 33 | 35 | 29 / 31 / 35 |

Norm numerator/affine/square sums, interpolation numerators, softmax numerators,
attention dot and weighted prefixes, selected-expert mixture prefixes, and
all learned-matrix prefixes are observed separately. INT64 is the host
reference intermediate type. A target implementation must support at least
the recorded bounds plus rounding/shift/division implementation needs; a
40-bit accumulator design is a candidate, **not a target proof**. In particular,
32-bit-only accumulators are not justified even for Q10 mixed. Do not clamp the
ranking/set logits to INT16: final scores remain signed INT32.

F9J2 target requirements: dynamic E=4/K=2 descriptors and expert indexing,
per-tensor INT8/INT16 dispatch for mixed variants, signed per-output row binary
exponents, half-away-from-zero division, integer floor sqrt and norm epsilon,
Q15 softmax with remainder assigned to stable first argmax, interpolated exp /
GELU LUTs, early attention rounding, and the encoded coordinate/tie wrapper.
K=1 flexible full-E gating is intentionally rejected by these wrappers because
it is not the selected-softmax F9J2 top-2 contract.

## Rejected bounded variants and localization

Fourteen variants were evaluated; seven passed and seven remain rejected.
All failed packets and all affected board/history identifiers remain saved.

| Q11 INT8 scope | Canonical set errors | Board move errors | History move errors |
|---|---:|---:|---:|
| All matrices | 26 | 82 | 2,066 |
| Expert W1 only | 2 | 8 | 1,152 |
| Key only | 2 | 8 | 288 |
| Query only | 1 | 0 | 0 |
| Readout only | 24 | 108 | 3,320 |
| Router only | 1 | 4 | 8 |
| Value only | 3 | 11 | 300 |

The query-only failure at canonical index 490 misses one membership despite
zero move errors: eight board sets / 32 history sets fail. Float minimum legal
signed margin is 4.232733; integer minimum is -2,176 Q11 units. Query max layer
error is 0.020410, projected attention 0.032108, norm2 0.209939, router 0.317124,
and output 10.923431. Routes reorder `[1,2]` to `[2,1]` (same selected set).

The router-only failure at canonical index 528 has float minimum legal signed
margin 5.347322 versus -14,944 integer units. Router layer error is 0.087425;
the selected set changes `[2,0]` to `[2,3]`, and output error reaches 14.343959.
`layer-diagnosis.json` preserves full compared layer vectors, boards, logits
and signs for these and every other failed canonical board. These are
localized failed variants, not evidence that INT8 is intrinsically impossible.
No blind refinement, seed search, QAT, oracle fallback, or float inference was
used: the directly passing baseline and mixed candidates already satisfy the
host gate, so target execution is the next missing acceptance stage.

## Reproduction

```sh
.venv/bin/python scripts/evaluate_flexible_integer.py
.venv/bin/python scripts/evaluate_flexible_integer.py --frac 10 \
  --component-int8 expert_w2 output.weight projection.weight \
  --output artifacts/flexible-integer/q10-mixed-e2-output-projection
```

No full-model 6502 execution, physical hardware acceptance or whole-application
RAM residency has been demonstrated by this work. No background process is
left running by these synchronous evaluations; no commit or push was made.
