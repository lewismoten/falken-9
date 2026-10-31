# Exact local constant folding: storage versus target computation

## Why this is possible

In the accepted F9J2 architecture, each square's first normalization and Q/K/V
projections depend only on its occupancy, its absolute position, and side to
move. They do not depend on the other squares until attention executes. There
are 54 local feature combinations (2 sides, 9 positions, 3 occupancies).

`falken9.local_fusion` evaluates those local operations **using the original
integer parameters and exact integer arithmetic**, before deployment. It stores
local feature vectors, not histories, board IDs, optimal targets or moves. The
remaining attention, projection/readout, second normalization, learned router,
selected experts and membership head still execute on the input board. This is
compiler-style local constant folding, not a move-policy lookup table.

An optimized target using these tables must not claim to recompute the folded
first-normalization/projection arithmetic on every turn. It retains the exact
function but trades extra data for less runtime work. The ordinary unoptimized
integer model remains immutable and separately executable.

## Verified variants

Source: `artifacts/canonical-integer/verified/q11-w16-a32-early-interp/model.f9j`

Source SHA-256:
`6c2b3dc6ec2a26fbdd28b1d7c78abbd0fcfd285c3f45bea4357fcb9f3fefa8c9`

| Variant | Extra INT16 data | Actual source + table bytes | Runtime work structurally removed per board |
|---|---:|---:|---|
| First norm only | 864 | 6,974 | Nine first-normalization calls; all Q/K/V projections remain |
| First norm + Q/K/V | 2,592 | 8,702 | Nine first-normalization calls and 1,728 Q/K/V matrix MACs |

The figures count the **unchanged complete source packet plus a separately
serialized raw table**, retaining original unused parameters/descriptors. No
stripped optimized packet, compiled target-code size or allocated target scratch
is claimed. The norm-only variant stays below the preferred 8 KiB model-data
objective; the larger variant does not, although that is an optimization target,
not a physical C64 capacity limit.

Tables are signed INT16 little-endian. The norm table shape is
`[side=2][square=9][occupancy=3][lane=8]`; the Q/K/V table shape is
`[side=2][square=9][occupancy=3][projection=3][lane=8]`, projection order Q/K/V.
The last dimension is contiguous. Actual generated ranges are -5,731..6,440 and
-11,272..8,085 respectively, so storing INT16 is lossless here. No new parameter
quantization or floating-point inference is introduced.

Both variants were independently executed against the unfused reference:

- Zero full-logit and route differences across every canonical input.
- Zero optimal-set and deterministic-move errors on 627 canonical patterns,
  4,520 original boards and all 294,778 published histories.
- All 36,160 coordinate-transform checks remain passing.
- Actual serialized tables were read back and matched the generated codes.
- The immutable source packet SHA-256 remains unchanged.

This is a **host exact-integer proof** and structural operation reduction, not a
measured 6502 speedup or a whole-system residency result. The extra table must be
counted and placed alongside code, model, activations and UI in target tests.

## Reproduce

```sh
OMP_NUM_THREADS=1 .venv/bin/python -m pytest tests/test_local_fusion.py -q
OMP_NUM_THREADS=1 .venv/bin/python scripts/audit_local_fusion.py
```

The CLI accepts `--source`, `--dataset`, `--artifacts` and `--output`. It generates
ignored `artifacts/local-fusion/norm1.bin` and `norm1-qkv.bin`, full policy
verification results, and tracked `results/local-fusion-summary.json` with exact
source/table digests and byte inventories. Source compilation requires no labels
or minimax; the dataset is used only for exhaustive acceptance after compilation.
