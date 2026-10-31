# Falken-9 arithmetic experiment v1

## Acceptance boundary

Implemented: independently testable integer scalar/packing contracts, **three
INT8-activation dot products and one INT16-activation binary dot product**,
assembled as NMOS 6502 code and executed by Py65. This is not a model exporter,
complete integer inference, a resident C64 application, gameplay acceptance, or a
hardware/VICE timing result. Attention, normalization, learned router/top-2 expert
execution and model integration remain outside this kernel gate.

The dot-product kernels consume raw integer rows. They do not apply a scale,
bias, activation, rounding or saturation. A separate assembled requantization
helper now implements signed INT32 shifting/rounding and INT16 saturation; it is
not yet linked into a complete neural layer or model.

## Integer and serialization contract

- Activations in the initial three gates are signed INT8, two's complement,
  -128..127. The separately documented `binary16` extension uses signed INT16.
- Binary weights: -1/+1; code `0 -> -1`, `1 -> +1`.
- Ternary weights: -1/0/+1; code `00 -> 0`, `01 -> +1`, `10 -> -1`.
  `11` is reserved and rejected, never treated as zero.
- Signed INT8 weights use ordinary two's-complement bytes, -128..127.
- Within a binary byte, lane 0 occupies bit 0. Within a ternary byte, lane 0
  occupies bits 0..1. Continue toward the most significant bits, then advance
  one byte. Rows are independently byte-aligned. Unused high padding bits are
  zero. No sign plane, row header, scale, bias or zero-point is implicit.
- Example binary `[-1,+1,-1,+1,+1,-1,-1,+1,+1]` is `9a 01`.
  Ternary `[0,+1,-1,0]` is `24`.
- All multibyte integers are little-endian two's complement. For example,
  INT16 -257 is `ff fe`. Results are exact, unsaturated integer sums.
- `packing.unpack` enforces exact byte count, zero padding and valid codes.
  The assembled routines require an already validated buffer/length. Ternary
  additionally rejects an encountered reserved code with carry set; it does not
  examine unused padding. Neither routine bounds-checks target input addresses.
- Scale grouping/serialized scale fields are deliberately not chosen here. A
  later export must declare their size, signed exponent interpretation and
  placement explicitly rather than treating raw weight bits as a complete model.

`arithmetic.round_shift(v,s)` uses nearest rounding, exact halfway cases **away
from zero**, for division by `2**s`; `s=0` is the identity and negative shifts are
rejected. Examples for `s=1`: -5 -> -3, -3 -> -2, -1 -> -1, 1 -> 1, 3 -> 2.
`requantize` rounds first, then clamps to the signed destination interval.
`dot` validates activation range/length and raises on accumulator overflow;
it never silently wraps. `encode_signed` accepts 8/16/32-bit little-endian output.
There is no division, softmax or normalization approximation in this gate.

## Accumulator proof and alternatives

For dimension N, activation width A and maximum absolute integer weight W,
`abs(sum) <= N * 2**(A-1) * W`. This includes the asymmetric signed minimum.
Every partial sum has the same conservative bound. Bias would add its absolute
bound and is **not included** below. A positive bound must not exceed the signed
accumulator maximum; merely fitting its magnitude in an unsigned word is unsafe.

| N | INT8 x binary/ternary bound | INT16 x binary/ternary bound | INT8 x INT8 bound |
|---:|---:|---:|---:|
| 8 | 1,024 | 262,144 | 131,072 |
| 12 | 1,536 | 393,216 | 196,608 |
| 16 | 2,048 | 524,288 | 262,144 |
| 24 | 3,072 | 786,432 | 393,216 |
| 32 | 4,096 | 1,048,576 | 524,288 |

Thus binary/ternary x INT8 safely use INT16 for all tested dimensions. Full-range
INT8 weights require INT32 here; a 32-lane all-(-128) row produces +524,288.
INT16 activations with low-bit weights require INT32 at these dimensions and
would double activation storage (32 lanes: 64 instead of 32 bytes). INT16 x INT8
has bound 134,217,728 at N=32 and also fits INT32. INT16 x INT16 at N=32 does not.
The INT16-activation binary extension below now has actual assembled timing.
INT16-activation ternary and INT8-weight alternatives remain bounds/storage
comparisons only. No complete-model precision/quality measurement follows.

## Target ABI and memory ownership

Each `.asm` is an alternative standalone raw code image starting at `$2000`.
They are not linked together and are not directly launchable C64 PRGs. Code has
an assembler guard against crossing `$2100`. Fixed addresses simplify isolated
proofs; relocation/pointers and a full caller remain later work.

| Item | Binary | Ternary | Signed INT8 |
|---|---|---|---|
| Entry | `$2000` | `$2000` | `$2000` |
| Code bytes | 81 | 103 | 151 |
| Code end, exclusive | `$2051` | `$2067` | `$2097` |
| Input dimension | `$e0`, 0..32 | same | same |
| Activation row | `$3000`, N bytes | same | same |
| Weight row | `$3100`, ceil(N/8) bytes | `$3100`, ceil(N/4) bytes | `$3100`, N bytes |
| Output | `$e1..$e2`, INT16 LE | same | `$e1..$e4`, INT32 LE |
| Reserved ZP including N/output/scratch | `$e0..$e7`, 8 bytes | same | `$e0..$ec`, 13 bytes |
| Actual scratch stores, excluding result | `$e3,$e6,$e7` | `$e3,$e4,$e6,$e7` | `$e5..$ec` |

All clobber A/X/Y and status; carry is clear on success, decimal mode is clear on
return. Ternary reserved-code failure returns carry set and an unspecified
partial output. N and input buffers are unchanged. The routines use no JSR/PHA
or lookup tables; caller's two-byte return frame is consumed by RTS. The harness
seeds SP=$fd and verifies SP=$ff after return. Scratch starts poisoned, and entry
starts with decimal mode set to verify the explicit CLD. No interrupt-safety or
KERNAL ownership of these experimental ZP bytes is asserted.

At N=32, code + actual input bytes + reserved ZP costs are 125/151/228 bytes for
binary/ternary/INT8 respectively. Output bytes are already counted in ZP; add
2 bytes for the caller return frame, plus caller/loader code not provided here.
These figures exclude fixed-address holes and are **not complete model sizes**.
A 32-lane weight row costs 4/8/32 bytes, before any future scale/bias/header.
The raw images contain code only: the harness supplies input bytes directly.
The current `$2000` entry conflicts with CP64's visible bitmap, so these are not
drop-in game kernels. See `RAM_AUDIT.md` before assigning integration addresses.

## Reproduction and strict TDD evidence

Use the project environment with `pytest` and `py65`. Run
`sh scripts/bootstrap_64tass.sh` to install pinned 64tass into ignored
`build/tools/64tass` without sudo (apt/dpkg-deb hosts), or install 64tass and set
`TASS64` to its executable. The benchmark no longer depends on a sibling checkout.
Measured tool versions are recorded in `results/kernel-summary.json`.

```sh
OMP_NUM_THREADS=1 python -m pytest tests/test_arithmetic*.py tests/test_packing*.py tests/test_kernels*.py -q
OMP_NUM_THREADS=1 python scripts/benchmark_kernels.py
```

Tests were written and run before each implementation slice. Durable local logs
under ignored `artifacts/kernels/` record these observed red -> green gates:

| Behavior | Red | Green |
|---|---|---|
| Signed rounding/saturation | `01-arithmetic-red.log` | `02-arithmetic-green.log` |
| Bit codebooks/padding | `03-packing-red.log` | `04-packing-green.log` |
| Dot bounds/endian contract | `05-dot-red.log` | `06-dot-green.log` |
| Binary assembled execution | `07-binary-red.log` | `08-binary-green.log` |
| Ternary assembled execution | `09-ternary-red.log` | `10-ternary-green.log` |
| Signed INT8 assembled execution | `11-int8-red.log` | `12-int8-green.log` |
| Benchmark reporting | `13-benchmark-red.log` | `14-benchmark-green.log` |
| Return status/stack contract | `15-abi-red.log` | `16-abi-green.log` |
| RAM ledger/evidence integrity | `17-ram-ledger-red.log` | `18-ram-ledger-green.log` |

Missing-feature reds were import/attribute/absent-source failures, not numerical
failures of a fabricated stub. `final-tests.log` records the complete owned suite.
The independent test oracle uses Python integer multiply/sum and independently
constructs packed bytes, not production pack/unpack or a translation of assembly.
Binary tests cover empty/partial-byte rows, signs and extrema; ternary tests also
cover every four-lane valid code combination and reserved-code rejection. INT8
checks all 65,536 activation/weight pairs **within 2,048 same-weight 32-lane dot
rows**, plus mixed-sign random rows and the overflow-for-INT16 example. This is
not a claim of independently checking each product in isolation.

## Measured CPU cycles

The benchmark defines **ten named vectors per kernel per N**, 150 executions:
zero activations, four full-sign/extreme combinations, alternating extrema,
zero-or-balanced weights, sparse-or-binary weights, and two seeded mixed rows.
Binary has no zero weight, so the corresponding cases use balanced/nonzero signs.
Exact bytes, oracle/target outputs and per-vector cycles are in
`artifacts/kernels/vectors.json`; its canonical JSON digest is in the summary.

| N | Binary mean / observed worst | Ternary mean / observed worst | INT8 mean / observed worst |
|---:|---:|---:|---:|
| 8 | 533.6 / 546 | 639.4 / 762 | 3,165.9 / 3,830 |
| 12 | 791.8 / 810 | 976.4 / 1,130 | 4,778.4 / 5,730 |
| 16 | 1,039.5 / 1,066 | 1,298.4 / 1,498 | 6,312.0 / 7,630 |
| 24 | 1,546.9 / 1,586 | 1,906.5 / 2,234 | 9,476.4 / 11,430 |
| 32 | 2,055.0 / 2,106 | 2,514.4 / 2,970 | 12,612.8 / 15,230 |

Counts include entry initialization, packed-bit decoding, sign handling,
accumulation and RTS. They exclude caller JSR, interrupts, VIC steals, ROM/I/O and
input loading. Worst means **maximum among these defined vectors**, not an
exhaustive or universal upper bound. Ternary skips arithmetic for actual decoded
zeros; INT8 uses eight shift/add iterations per product. Different weight
precision and accumulator widths make this a kernel comparison, not an
accuracy-equivalent model comparison. No wall-time or whole-inference speedup is
inferred. Actual binary images, assembly logs and labels are retained alongside
the vectors; source/image SHA-256 values are recorded in the tracked summary.

## INT16-activation binary extension

`src/kernels/binary16.asm` multiplies signed INT16 activations by the same packed
binary codebook, accumulating an exact signed INT32 result. N is 0..32 in `$e0`;
activations start at `$3000` (two little-endian bytes per lane), packed weights at
`$3100`, and output occupies `$e1..$e4`. Scratch/output stores are confined to
`$e1..$e8`. A/X/Y/P are clobbered; carry/decimal are clear on return. Caller owns
these fixed addresses; the image is not linked into the game. Code is 122 bytes
at `$2000`; no rescaling, bias or nonlinear activation is included.

`tests/test_kernels_binary16.py` was observed red before implementation, then
passed all 30 subcases across N=0/8/12/16/24/32. Tests cover extrema, signs, zero
and seeded mixed vectors against Python integer multiplication/sum, poisoned RAM,
unexpected-write guards, caller-stack return and initially set decimal mode.
The 32-lane maximum conservative accumulator magnitude is 1,048,576.

`python scripts/benchmark_int16_kernel.py` performs 50 defined measured vectors:

| N | Mean cycles | Observed worst cycles |
|---:|---:|---:|
| 8 | 811.2 | 821 |
| 12 | 1,208.5 | 1,225 |
| 16 | 1,593.8 | 1,613 |
| 24 | 2,374.6 | 2,405 |
| 32 | 3,157.6 | 3,197 |

See `results/kernel16-summary.json`. Timing boundaries/exclusions are the same
as above. These measurements do not prove that INT16 activations preserve any
trained model's behavior. The host `F9Q1` research export uses a different ternary
code assignment from these raw kernel experiments; it is not a drop-in kernel
payload. Future target exports must explicitly convert and test their codebooks.

## Assembled signed requantization helper

`src/kernels/requantize.asm` accepts signed INT32 input in `$e0..$e3` and a
right-shift count 0..31 in `$e4`, preserving both. It rounds nearest with exact
halfway cases away from zero, then clamps to INT16 in `$e5..$e6`. Carry reports
whether clamping occurred. Scratch is `$e7..$ec`; A/X/P are clobbered and decimal
mode is clear on return. Caller owns those addresses and validates the shift.
The standalone image starts at `$2000`, occupies 154 bytes, and is not linked
into the game. It does not handle wider-than-INT32 intermediates.

`tests/test_kernels_requantize.py` was observed failing before implementation,
then passed **640 subcases**: 20 signed extrema/zero/tie/boundary values at every
shift 0..31. The independent Python integer oracle checks value and saturation
flag; poisoned-RAM guards check input preservation and unexpected writes. This
does not exhaust all possible INT32 inputs.

`python scripts/benchmark_requantize.py` records the same defined cases in
`results/requantize-summary.json`. Selected mean / observed-worst cycles:

| Shift | Mean cycles | Observed worst |
|---:|---:|---:|
| 0 | 139.5 | 170 |
| 8 | 369.55 | 403 |
| 16 | 595.2 | 633 |
| 24 | 816.2 | 844 |

Counts include entry through RTS, not caller JSR, interrupts, VIC stalls or I/O.
This is an arithmetic building block, not evidence that quantized activations
preserve a trained policy or that complete Falken-9 inference runs on the C64.
Final output scores may need a wider representation; do not apply this INT16
clamp to them merely for uniformity.
