# Resident F9J2 target: assembled attention-block proof

## Verified result — not whole-model inference

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
sampling of the rest; exact indices are in `results/runtime-summary.json`.
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
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 .venv/bin/python scripts/verify_runtime.py --canonical-limit 64
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

## Next concrete target work

Reuse the resident packet and extend the real path with a variable-size matrix
routine: the flattened readout has 72 inputs and needs 16-bit pointer advancement
rather than an 8-bit `column*4` offset. Add signed GELU interpolation and generalize
the proved norm machinery to norm2. Then implement stable dynamic-E top-2 routing,
selected expert tensors in their original `[expert,input,output]` orientation,
softmax gates, 40-bit merge, and **32-bit final scores without INT16 clipping**.
Only after exact logits/routes/sets pass the full canonical gate should a minimal
C64 PRG and the symmetry/history wrapper be packaged. D64 creation remains held
until an executable application exists.
