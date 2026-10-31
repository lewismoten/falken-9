# Resident F9J2 target: complete four-expert neural forward

## Current accepted neural gate — 627/627 canonical boards

The separate **four-expert, top-2, Q11/W16/INT32** packet is now executed through
**every neural stage** by actual assembled NMOS 6502 instructions. It is the
unchanged **5,195-byte** packet at
`artifacts/flexible-integer/q11-w16-a32-early-interp/model.f9j`, SHA-256
`fe180f8a931f9d92d8aa39da337bc819d0dbe4e6d971edcba00324fbc18a91c1`.
There are no host inference callbacks, injected activations, board-policy tables,
local-feature fusion tables, or replacement weights in this path.

`full_forward` accepts the nine canonical occupancy bytes at `$7020`. It executes
the existing embedding/norm1/QKV/81-score/softmax/attention-projection/residual path,
then adds:

- A variable-fan-in matrix kernel with **16-bit advancing input pointers**, including
  all 72 flattened readout inputs and their original learned row exponents/biases.
- Exact signed GELU interpolation, including negative LUT samples, both tails,
  and nearest-ties-away rounding.
- Complete integer norm2 (mean, centered squares, variance, isqrt, division, affine).
- Dynamic-`EXPERT_COUNT` stable top-2 ranking, lower-index-first ties, and selected-score
  softmax gates. A gate of 32,768 is unsigned, not a negative INT16 weight.
- Both genuinely selected W1/GELU/W2 expert paths in the packet's original
  `[expert,input,output]` orientation, with each expert's exponents and biases.
- Signed-40 gated merging, the readout residual, and **nine INT32 final scores**
  without INT16 clipping.

All **627 canonical boards** passed comparisons of **every retained stage vector,
router scores, selected indices, gates, both expert hidden/output vectors, merged
vector, and final logits** against an independent arbitrary-integer oracle.
A second independently implemented complete scalar oracle also matched every
logit and route. Expert selection counts were **301, 258, 355, 340**.
The empty-board complete pass was exercised before the varied-route/range and
exhaustive gates; its routes are `[1, 2]` and logits are
`[561150, 447961, 281555, 94790, 275926, 34652, 189453, 501705, 175355]`.

The executed canonical logits also passed **all optimal sets and original-coordinate
`ebdfhcgia` tie-selected moves** for **4,520 unique boards / 294,778 histories**.
That expansion uses the existing **host symmetry/inverse-set wrapper**, not an
assembled wrapper or additional neural execution for each history. The distinction
is part of the acceptance record: **whole neural forward is accepted; a complete
C64 game/application is not**. History validation, canonicalization, inverse mapping,
set selection, UI, launch, and game lifecycle remain to be assembled/integrated.
No PRG, D64, browser, VICE, physical-C64, or interactive-game claim is made.

### Four-expert artifact, map, safety, and measured CPU cycles

Evidence (not published application artifacts) is under
`artifacts/runtime/full-forward/q11-w16-e4/`: exact raw image and build/listing/labels,
frozen source snapshots, four durable JSONL checkpoint shards, `summary.json`, and
`safety-audit.json`. `results/runtime-summary.json` now describes this successor.
The raw image SHA-256 is
`838aa62a854aa58bd603c7525b52dc67c4c4b01ea0f50f58982475959ec61961`.

| Range | Four-expert ownership |
|---|---|
| `$0800..$1d7f` | 5,503 code/static-metadata bytes |
| `$4000..$544b` | All 5,195 original packet bytes, including both LUTs |
| `$6000..$6da0` | Existing attention/local activation reservation |
| `$7000..$7100` | Existing board/control/softmax ABI reservation |
| `$7200..$7600` | Readout, norm2, router, selected expert, merge, logits, controls |

Zero page `$20..$80`, stack `$100..$200`, and untouched screen `$400..$800`
reservations remain as below. Total explicit allocation is **16,842 bytes**,
including reserved screen/stack and scratch gaps. The raw transport is **19,531
bytes**, including **8,833 filled gap bytes**, not a PRG. Assembly overlap guards
still keep code below the model and the entire model below scratch.

Every Py65 CPU write was checked against the writable map, including writes of
unchanged values and stack writes: **725,122,178 writes** across 627 complete
executions. Every instruction PC remained inside assembled code, stack balance
was checked, and code/model bytes were rechecked unchanged after every board.
The lowest stack write was `$01ec`. These are emulator-visible writes, not a
claim to count physical NMOS dummy bus writes.

The E4 bounds were recomputed, **not copied from E9**. All 54 local combinations
have maximum absolute embedding/normalized/Q/K/V values
**8,156 / 6,289 / 11,875 / 9,065 / 6,775**; centered local maximum is **7,830**.
Norm2 centered maximum across the complete canonical domain is **12,402**.
Both centered-square and attention K/V INT16 narrowing sites retain runtime guards.
The largest stored score magnitude is **1,336,531**, illustrating why final scores
must not be clipped to INT16.

The independent oracle records every ordered dot-product prefix and each row's
sum-of-absolute-products envelope. The largest observed signed prefix is
**5,463,132,850**; the largest exact absolute-product envelope is **8,110,071,082**.
The deliberately coarser `max_abs_input * max_abs_weight * fan_in` bound reaches
**33,446,567,616** (36 signed bits). All are below signed-40's positive limit
**549,755,813,887**. `safety-audit.json` retains per-stage input maxima, each coarse
matrix bound, and decoder/host-contract source hashes. Actual MAC operand limits,
per-add signed-40 overflow detection, checked INT32 matrix outputs, invalid-board
errors, and caller error propagation remain active. The public entry clears decimal
mode through the board front end. Internal helpers use their caller's established
arithmetic state; they are not a general untrusted-INT32 API.

Measured complete `full_forward` work across the 627 actual executions:

- Minimum: **8,050,591 CPU cycles**.
- Mean: **8,087,911.196172249 CPU cycles**.
- Maximum observed: **8,110,463 CPU cycles**.

These are Py65 entry-through-RTS CPU cycles, excluding caller JSR, IRQs, VIC stalls,
ROM/disk time, and wall time. Four bounded CPU workers completed all shards; no
partial sample was promoted to an exhaustive result. The final complete repository
suite passed **109 tests and 677 subtests** in **152.96 seconds**; its only warning
is the pre-existing missing-NumPy PyTorch initialization warning. The durable log
is `full-suite-final.log`. This host test-run duration is not C64 inference time.

### Reproduce without replacing the frozen E9 evidence

```sh
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 .venv/bin/python -m pytest tests/test_runtime*.py -q
.venv/bin/python scripts/verify_runtime.py --full-forward --canonical-limit 627 --workers 4 \
  --output artifacts/runtime/full-forward/q11-w16-e4-rerun \
  --summary artifacts/runtime/full-forward/q11-w16-e4-rerun/result.json
```

`build(model=..., output=...)` accepts only the explicitly SHA-pinned E9 and E4
packets. Calling `build()` with no arguments still selects E9, and reproduces its
original raw image byte-for-byte. The E9 64-board frozen raw/checkpoint identities
below were independently rechecked and remain unchanged. Do not rerun a verifier
into `artifacts/runtime/verified/`; that earlier evidence is immutable.

## Frozen earlier E9 attention-only proof (historical scope)

The rest of this document describes the retained **E9** gate, not the new E4
whole-neural gate. Its old missing-stage statements and allocation/cycle figures
apply only to that frozen executable.

### Verified E9 result — not whole-model inference

The accepted **6,110-byte** F9J2 packet is embedded unchanged at `$4000` and
remains resident throughout real NMOS 6502 execution. Its SHA-256 remains
`6c2b3dc6ec2a26fbdd28b1d7c78abbd0fcfd285c3f45bea4357fcb9f3fefa8c9`.

Implemented and executed, from nine input occupancy bytes:

1. Original occupancy, absolute-position and side-to-move embedding sums.
2. Integer LayerNorm: rounded mean, centered square sum, rounded variance plus
   epsilon 42, exact floor integer square root, variable-denominator signed
   nearest division, and original learned affine parameters.
3. Original Q/K/V matrix projections and their per-row power-of-two exponents.
4. All 81 single-head attention dot products and the accepted **early** rescale.
5. Max-stabilized nine-key softmax: interpolation of the original exp LUT,
   unsigned floor division, and remainder allocation to the first maximum.
6. All 72 probability-weighted V lanes.
7. Original learned attention output projection and embedding residual addition.

**All 54 local occupancy/position/side combinations** match the independent
Python arbitrary-int front-end oracle, including mean, variance, root, embedding,
normalized lanes, and Q/K/V. The complete board-to-attention-residual entry matches
**64 deterministically sampled canonical boards out of 627**, with **zero stage
vector mismatches**. The sampling includes canonical index zero and fixed-seed
sampling of the rest; exact indices are in `artifacts/runtime/verified/summary.json`.
Additional assembled unit cases cover eight arbitrary occupancy boards for
attention and three for projection/residual, including repeated requests without
resetting model RAM. These arbitrary boards are arithmetic stress inputs, not
claims that invalid histories are legal.

**Not implemented:** flattened readout, GELU interpolation/application, norm2,
router ranking/gates, selected expert MLPs, expert merge, final 32-bit membership
scores, history validation, symmetry/full-set wrapper, or application UI. Thus
there are no target logits/routes/policy sets to accept yet. The full 627-board
whole-forward gate is **unaccepted**, and no PRG, D64, playable-game, browser,
VICE, or physical-C64 acceptance is claimed. No policy lookup, feature-fusion
lookup, injected intermediate, host inference callback, or precomputed answer is
used by the target. Python emits only static tensor/pointer metadata and copies
the exact original packet.

## Build and reproduce

Use the existing project environment and pinned local 64tass. No install or
model conversion is required:

```sh
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 .venv/bin/python -m pytest tests/test_runtime*.py -q
.venv/bin/python scripts/build_runtime.py
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 .venv/bin/python scripts/verify_runtime.py --canonical-limit 64 \
  --output artifacts/runtime/full-forward/e9-attention-rerun \
  --summary artifacts/runtime/full-forward/e9-attention-rerun/result.json
```

`TASS64` can override the assembler path. The default is
`build/tools/64tass/usr/bin/64tass` (1.60.3243). `runtime.bin` is a **raw** image
loaded at `$0800`, not a C64 auto-start PRG. The Py65 harness enters a named routine
with a real 6502 return frame and executes instructions until RTS returns. The
board ABI is nine bytes at `$7020`, each 0..2. `board_attention_block` recomputes
side parity, validates occupancy range, and starts the entire implemented path.
A/X/Y/P are clobbered, decimal is cleared, carry indicates success/error, and
caller stack balance is asserted. The harness supplies an interrupt-disabled
caller; no KERNAL coexistence or interrupt-safe ZP ownership is assumed.

The independent scalar reference lives in `tests/test_runtime_frontend.py` and
`tests/test_runtime_attention.py`; the verifier imports those references only for
comparison **after** target execution. They are not called by target instructions.

## Actual standalone memory map

Ranges are start-inclusive/end-exclusive and are **not** inherited free RAM from
an old game. Code, model, activation, stack and screen reservations are disjoint.
All reside below BASIC/I/O/KERNAL overlays; this proof needs no banking operation.

| Range | Bytes | Ownership |
|---|---:|---|
| `$0020..$0080` | 96 | Math scratch, operands/results, indirect pointers |
| `$0100..$0200` | 256 | Reserved hardware stack |
| `$0400..$0800` | 1,024 | Reserved screen; target leaves it unchanged |
| `$0800..$150d` | 3,341 | Assembled code plus static pointer/row metadata |
| `$4000..$57de` | 6,110 | Entire original packet, descriptors, exponents, both LUTs |
| `$6000..$6da0` | 3,488 | Scratch and retained full-stage INT32 arrays, including gaps |
| `$7000..$7100` | 256 | ABI input/control and exp/probability scratch reservation |
| **Allocated total** | **14,571** | Includes screen/stack reservations; excludes unallocated holes |

The model's 2,052 LUT bytes are **already included** in the 6,110-byte packet.
Decoder address metadata and routines are included in code bytes, not hidden
additional model data. No UI renderer or loader is included. Complete-game assets
would add their actual allocations. The raw image spans `$0800..$57de`:
**20,446 bytes**, including **10,995 filled gap bytes**. Its transport size is not
the sum of live code and model sizes, nor evidence those filled addresses are
free in another program.

The every-write regression instruments actual Py65 memory writes for the complete
board entry and rejects any write outside the declared writable ranges, including
writes that store the existing value. Model, executable and screen are protected;
model identity is rechecked after each of the 64 canonical executions. This is a
new isolated allocation proof, not an old-game lifecycle proof.

## Arithmetic widths, bounds and guards

All stored activations/results are INT32; intermediate sums are signed INT40.
`mac40` accepts a preserved signed INT32 operand and signed INT16 weight, but
**does not claim the universal INT32-by-INT16 domain fits 40 bits**. It explicitly
rejects operand magnitude above 8,388,607, and checks signed overflow at every
40-bit accumulated addition. The permitted model-domain envelope is much smaller.
Every caller propagates the relevant failure. Parameters and input operand remain
unchanged; arithmetic scratch is caller-clobbered. Overflow leaves an unspecified
partial accumulator, not a successful saturated answer.

| Implemented-stage bound | Magnitude bound |
|---|---:|
| Embedding | 11,478 |
| Centered embedding lane | 22,956 |
| Eight centered squares | 4,215,823,488 |
| Q/K/V lane, exhaustive 54-local-input observation | 11,272 |
| Eight-term attention dot, conservative from that exhaustive envelope | 1,016,463,872 |
| Probability-weighted V sum, since probabilities sum to 32,768 | 369,360,896 |
| Eight-term projection dot | 2,767,411,264 |
| Positive signed-40 limit | 549,755,813,887 |

The centered-square weight is separately guarded for exact INT16 representation.
K/V lanes are likewise checked before their INT16 use in attention. This narrows
**those proven local intermediates**, not general activation storage or final
scores. Projection outputs are checked for INT32 representation. The residual
bound is also far below INT32: divide its dot bound by the smallest projection
scale denominator 32,768, round, then add the embedding bound. The prototype
returns errors rather than implementing saturation outside its proven domain;
the pinned accepted model has no activation saturation on the legal domain.

`scale40` supports shifts 0..39 and nearest ties away, including signed-40
minimum. `divide40` uses a positive unsigned-32 denominator, signed-40 numerator,
and nearest ties away. `floor40` is used only with **nonnegative** numerators.
`sqrt40` consumes any unsigned-40 input and returns its exact floor square root
using twenty radix-four steps. Exp interpolation uses the packet's unsigned INT16
entries, including 32,768; it must not reinterpret that endpoint as signed INT16.
Q11 interpolation algebraically reduces to adjacent samples weighted by a
0..63 remainder divided by 64, preserving the original integer result exactly.

## Evidence and measured CPU work

The assembled image SHA-256 is
`340c754d42ae531d44ccb4f4aac28bf0923ef6d93b795f23fa1f5cb84334b62d`.
Frozen sources, raw image, assembly listing/labels, pointer metadata, build
manifest, all 64 complete stage-vector checkpoints, cycles and hashes are under
`artifacts/runtime/verified/`. The checkpoint JSON SHA-256 is
`4fdf539561fea62bc9e0e6479998d2483093c389d84230cad5ba741942d5538d`.

Measured `board_attention_block` cycles over those 64 boards:

- Minimum: **6,770,938**.
- Mean: **6,813,096.4375**.
- Maximum observed: **6,847,345**.

This is Py65 entry-through-RTS CPU work only, excluding caller JSR, interrupts,
VIC stalls, ROM, disk I/O, and real wall-time. It is neither a whole-forward
benchmark nor a universal worst-case bound.

Strict test-first logs under `artifacts/runtime/` preserve red/green gates for
math, variable division/isqrt, the real front end, exp interpolation, full-board
attention, projection/residual, layout/write guards, and the durable verifier.
The final owned runtime suite passed **8 tests**. The complete repository suite
passed **98 tests and 677 subtests** (`18-full-suite.log`); the pre-existing missing
NumPy initialization warning remains and did not require an environment change.
A discovered empty-board attention-max bug (INY overwrote subtraction's N flag)
was fixed before acceptance; its input and failing values are retained under
`artifacts/runtime/counterexamples/` and are covered by the assembled empty-board
regression. No remaining mismatches were observed in the declared proof set.

## Historical E9 successor plan (completed for E4 above)

Reuse the resident packet and extend the real path with a variable-size matrix
routine: the flattened readout has 72 inputs and needs 16-bit pointer advancement
rather than an 8-bit `column*4` offset. Add signed GELU interpolation and generalize
the proved norm machinery to norm2. Then implement stable dynamic-E top-2 routing,
selected expert tensors in their original `[expert,input,output]` orientation,
softmax gates, 40-bit merge, and **32-bit final scores without INT16 clipping**.
Only after exact logits/routes/sets pass the full canonical gate should a minimal
C64 PRG and the symmetry/history wrapper be packaged. D64 creation remains held
until an executable application exists.
