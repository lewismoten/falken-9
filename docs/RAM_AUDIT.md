# RAM audit: existing CP64 evidence and provisional Falken-9 arenas

## Result and evidence boundary

**No continuously free model arena has been proven in the existing complete
CP64 game.** The count of proven integration-free bytes is therefore **0**, not a
claim that the machine has no unused RAM. A separate minimal harness could reserve
an 8 KiB model arena and 4 KiB activation arena as described below; that proposal
is not a game residency result. Full-game integration is unstarted.

This audit inspected existing sources, actual assembled labels, PRG headers and
asset byte lengths read-only. It did not rebuild or modify CP64, reuse old model
proofs for new kernels, exercise hardware, or prove title/INFO/replay/cancel
lifetimes for Falken-9. A source/map reservation is not a measured live allocation.

All ranges below are **start inclusive, end exclusive**. Classifications:

- **Exact:** a recorded symbol, serialized byte length, PRG load span, or directly
  sized source buffer. Exact location does not imply free or simultaneously live.
- **Reserved:** conservatively unavailable because of hardware/system use,
  a source origin/guard, or an existing writer/loader; padding is not headroom.
- **Provisional:** an allocation proposal for a new harness, not implemented RAM.

### Retained evidence paths

`artifacts/kernels/ram-audit.json` is the machine-readable inventory: SHA-256,
byte counts, PRG load/end addresses, complete parsed numeric symbols, all audited
asset metadata and the proposed ledger. Full source/map snapshots are retained
under `artifacts/kernels/ram-evidence/`, preserving these CP64-relative paths:

- `build/cp64.lbl` (older narrow proof map, explicitly not the complete-game map)
- `build/release-018.lbl` (resident full-game labels)
- `build/ai_opening_bundle.lbl`, `build/ai_opening_bundle.inc`
- `build/ai_opening_bundle.asm` (actual generated current bundle source)
- `src/art_embedded_title.asm` (resident source and fixed origins)
- `src/clock_pixel_probe.asm`, `src/info_markdown.inc`, `src/progress_work.inc`
- `scripts/tensor_batching.py`, `scripts/export_c64_layers.py`

Binary metadata is taken from original `build/CP64.PRG`, `build/AIOPEN.PRG`,
`build/ARCHIVE.PRG`, `build/assets/**/*.bin` and `build/layers/C9W*.PRG`. Original
model/tensor bytes are not copied into this repository. Audit source snapshots,
metadata, tracked generator `scripts/audit_cp64_ram.py`, `ram-audit.log` and kernel
artifacts are local ignored evidence, not a published derivative release.
Reproduce with `CP64_ROOT` pointing to the read-only original checkout:

```sh
CP64_ROOT=/path/to/original-cp64 python scripts/audit_cp64_ram.py
python -m pytest tests/test_kernels_ram_audit.py -q
```

The snapshot hash checks and disjointness arithmetic passed; observed red/green
logs are `17-ram-ledger-red.log` and `18-ram-ledger-green.log` in the same artifact
directory. The audit-integrity test skips when these optional ignored snapshots
are absent (for example, in a fresh clone); all kernel correctness tests still
require actual assembly and execution. The source root itself is not embedded
in the tracked audit documents.

### Actual image spans

| Image | File bytes | Loaded span | Loaded bytes |
|---|---:|---|---:|
| `CP64.PRG` | 45,057 | `$0801..$b800` | 45,055 |
| `AIOPEN.PRG` | 22,564 | `$6501..$bd23` | 22,562 |
| `ARCHIVE.PRG` | 2,852 | `$c000..$cb22` | 2,850 |

The two-byte PRG load address is not part of loaded RAM. CP64's resident PRG
includes filled gaps; its payload length is **not** the amount of executable code
or usable BASIC RAM. The current bundle's exclusive end `$bd23` matches
`tensor_group_code_end`; the resident entry/result ABI `$6a3c/$98ad` matches the
bundle labels. `build/cp64.lbl` instead has an earlier smaller layout (for example
`embedding_row=$12ab` versus the later fixed-history shell), so substituting that
map for `release-018.lbl` would overstate free memory. These are audited local
snapshots, not a claim of revalidated published release provenance.

Key binary identities (full metadata for every evidence file is in the JSON):

- `CP64.PRG`: `ae3b296fb0e6c1b603176465119718ad36cdabe1ecdb43b17d8ac09786747335`
- `AIOPEN.PRG`: `cb6e5bb1326655cf4afafe2bb6aaa1f3c6d4442f994e20a179a4802cbb1db20f`
- `ARCHIVE.PRG`: `ed944d51409926d26fa57eaddb4af07ed8c821e584861549ca1558f2dbc37175`

## Existing resident/display map

| Range | Classification | Evidence / reason not automatically free |
|---|---|---|
| `$0000..$0100` | Reserved | CPU port and ZP system state; resident pointers `$f7..$fe`. Experimental kernel `$e0..$ec` still needs explicit caller/IRQ ownership. |
| `$0100..$0200` | Reserved | 6502 hardware stack. |
| `$0200..$0400` | Reserved | System workspace, vectors, keyboard and cassette workspace. |
| `$0400..$0800` | Reserved | Live screen allocation plus sprite-pointer tail; actual 40x25 screen is 1,000 bytes. |
| `$0801..$2000` | Reserved | Resident shell, fixed history ABI `$18d0`, progress callback `$18f0`, scalar scratch `$1968..$197a`, restoration and IRQ/UI helpers. `progress_helpers_end=$1fc6`; gaps are not accepted allocations. |
| `$2000..$4000` | Reserved | Live bitmap reservation. Actual 8,000-byte game copy is `$2000..$3f40`; status/progress/labels write into this bitmap. |
| `$3800..$4000` | Exact, view-dependent | 2,048-byte title charset; overlaps the game bitmap footprint. Existing view restoration is necessary. |
| `$4000..$43e8` | Exact | 1,000-byte title screen backing plane. |
| `$4400..$49e0` | Exact extent, reserved | Clock-probe code and transport; source reserves before `$4c00`. Not a model hole. |
| `$4c00..$4fe8` | Exact | 1,000-byte title color backing plane. |
| `$5000..$5100` | Reserved | Resident native progress activity helpers. |
| `$5100..$5400` | Reserved | Work callback, counters, threshold selection and room to guard. |
| `$5400..$5772` | Exact | Resident progress threshold tables; next source origin `$5800`. |
| `$5800..$5be8` | Exact, view-dependent | INFO screen backing, 1,000 bytes. |
| `$5c00..$5fe8` | Exact, view-dependent | INFO color backing, 1,000 bytes. |
| `$6000..$7f40` | Exact, view-dependent | Blank game bitmap backing, 8,000 bytes. |
| `$8000..$83e8`, `$8400..$87e8` | Exact, view-dependent | Game screen/color backing, 1,000 bytes each. |
| `$8800..$8ca4` | Exact, view-dependent | X bitmap/screen/color patches: 900 + 144 + 144 = 1,188 bytes. |
| `$9000..$94a4` | Exact, view-dependent | O patch set, same 1,188 bytes. |
| `$9800..$9f08` | Exact | 1,800-byte patch destination metadata. |
| `$a600..$ab8d` | Exact destination, view-dependent | INFO archive character copy, 49 x 29 = 1,421 bytes. |
| `$b000..$b800` | Exact, view-dependent | Title charset restoration backing, 2,048 bytes. |
| `$b800..$bd8d` | Exact destination, view-dependent | INFO archive color copy, 1,421 bytes; loaded later, beyond initial PRG end. |
| `$d000..$e000` | Reserved | I/O, VIC/CIA/SID registers, and color RAM at `$d800..$dc00`; underlying RAM cannot be treated as ordinary visible RAM. |
| `$e000..$10000` | Reserved in conservative design | KERNAL ROM/vector visibility. Banking it out requires a different proven interrupt/ROM-call contract. |

The table intentionally contains overlapping view-dependent entries. It is not a
sum of simultaneous independent costs. The source's `$dd00/$d018` programming
selects VIC bank `$0000`, screen `$0400`, game bitmap `$2000`; title uses charset
`$3800`. The bundle contains historical UI helpers with other addresses, so
comments from those helpers are not substituted for the actual resident setup.

## Existing inference/pager map

| Range | Classification | Actual declaration / lifetime caveat |
|---|---|---|
| `$5800..$6133` | Exact, view-scoped | `HOT_CACHE_START/END`, 2,355-byte common tensor cache. Overwrites INFO backing and the start of game bitmap backing. |
| `$6501..$bd23` | Exact image span | Pageable inference code/data image; overlaps game/patch/archive/title backing. It requires existing art restoration, not persistent model residency. |
| `$a000..$c000` | Reserved visibility constraint | BASIC ROM overlay. Resident source saves `$01`, clears bit 0 for bundle execution and restores it. Flat Py65 memory alone does not prove this banking path. |
| `$c000..$c6c9` | Exact largest original tensor span | Largest audited individual C9W packet is `C9W02.PRG`, 1,737 loaded bytes. Grouped expert staging is a separate writer; its source validates end `$c4c8`. |
| `$c000..$cb22` | Exact archive LOAD span | INFO archive load (2,850 bytes) is wider than the largest tensor and overwrites model scratch. |
| `$c100..$c140` | Exact declared vector | Token vector, 32 INT16 lanes. Inside some later packet LOAD spans. |
| `$c140..$c180` | Exact declared vector | Position vector, same size. |
| `$c700..$c740` | Exact, aliased | Hidden vector / first-expert output. |
| `$c740..$c780` | Exact, aliased | Query vector / retained expert-one vector. |
| `$c780..$c7c0` | Exact | Key vector. |
| `$c7c0..$c800` | Reserved slot | Projection scratch base and next vector origin; not inferred free. |
| `$c800..$c840` | Exact | Value vector. |
| `$c840..$c880` | Reserved slot | Attention-score scratch to next declared base. |
| `$c880..$cac0` | Exact declared capacity | Nine 64-byte K history slots, 576 bytes; also residual alias at `$c880`. |
| `$c900..$c940` | Exact declared vector, overlapping | Attended output lies inside the declared K-history interval. A lifetime/ordering proof is required; the declarations alone do not establish coexistence or a defect. |
| `$cac0..$cd00` | Exact declared capacity | Nine 64-byte V history slots, 576 bytes. |
| `$ce00..$ce90` | Exact declared capacity | Nine positions x eight heads x INT16 causal scores, 144 bytes; router/output logits alias the base after attention. |

The K/V declarations total 1,152 bytes before scores or other activations, not a
new Falken-9 cache allocation. Deliberate aliases must be validated at the new
runtime's actual lifetimes. Gaps such as `$5772..$5800` (142 bytes),
`$6133..$6501` (974 bytes), and `$bd23..$c000` (733 bytes) are not a contiguous
8 KiB arena. The second intersects game bitmap backing; the third intersects the
archive-color destination and is under BASIC ROM. None has been promoted to a
free allocation. No full-game writer/transition coverage was executed here.

## Safe candidate accounting for a NEW minimal harness

These allocations are arithmetically disjoint and avoid ROM/I/O overlays, **if**
the new harness adopts them and removes all conflicting old assets/loaders. They
are a conservative design envelope, not measured residency. In particular, the
old resident title/probe/progress/INFO regions conflict with the proposed model
arena. Copying the current shell unchanged is not allowed by this proposal.

| Proposed range | Bytes | Reservation |
|---|---:|---|
| `$0000..$0400` | 1,024 | System/ZP/stack; select new kernel scratch only after caller/IRQ audit. |
| `$0400..$0800` | 1,024 | Screen and pointer reservation. |
| `$0800..$2000` | 6,144 | New resident code/loader/UI, including relocatable kernels. Not an actual compiled size. |
| `$2000..$4000` | 8,192 | Visible bitmap reservation; no persistent title charset overlap. |
| `$4000..$6000` | **8,192** | Candidate permanently retained encoded model, no later asset/page LOADs. |
| `$c000..$d000` | **4,096** | Candidate activations, attention scores, normalization, router/expert scratch and optional K/V, with an actual lifetime allocator still required. |
| `$d000..$10000` | 12,288 | Excluded I/O and KERNAL region. |

The candidate model + activation allocation is 12,288 bytes. `$6000..$c000` is
left unallocated by this conservative proposal, **not** declared safe/free for the
existing game. BASIC-overlay RAM is not needed for these two candidate arenas.
New initial loading still needs a non-overwriting destination/size contract;
keeping model bytes through title/INFO/replay/cancel requires future tests.

### Explicit cost categories

- **Model:** candidate capacity 8,192 bytes, stretch target 4,096 bytes; neither is
  an exported model result. Count packed weights, row padding, scales, biases,
  tensor descriptors, headers, tables and alignment. For R independently aligned
  rows of width D, bare weights cost `R*ceil(D/8)` binary,
  `R*ceil(D/4)` ternary or `R*D` INT8 bytes. All omitted fields remain extra.
- **Kernel code:** actual alternatives are 81, 103 and 151 bytes (binary,
  ternary, INT8). A hypothetical separately relocated collection is 335 code
  bytes before caller/loader; the three current raw images all start at `$2000`
  and cannot be loaded together unchanged. Decoder work is inside those bytes;
  there are no lookup tables.
- **Activation rows:** width 32 costs 32 bytes INT8 or 64 bytes INT16 per live
  vector. Two retained vectors cost 64/128 bytes. Do not assume rows can alias
  until consumer lifetimes are proved.
- **Accumulator/output:** INT16 is 2 bytes; INT32 is 4. Current kernel ZP reserve,
  including length/output/scratch, is 8 bytes binary/ternary or 13 bytes INT8;
  add the caller's 2-byte return frame. See `ARITHMETIC.md` for bounds.
- **Attention state:** for a possible nine-position, width-D design, separate
  K/V storage is `2*9*D*activation_bytes`; at D=32, INT16 that is 1,152 bytes.
  A full nine-token single-head INT16 score matrix alone is 162 bytes. Multiple
  heads, Q/K/V work vectors, normalization sums, retained residuals, router
  logits, both expert outputs and top-2 merge state are additional or need a
  verified reuse schedule. No complete Falken-9 activation peak is claimed.
- **Current isolated N=32 dot footprint:** code + input bytes + reserved ZP is
  125/151/228 bytes respectively, excluding caller and return frame. This is a
  microkernel resource measurement, not a resident-model bill of materials.

Before game integration can pass: assemble a new non-overlapping complete image;
export the full encoded model and count every byte; implement full integer
attention/normalization/router/top-2 experts; execute an accepted-input-to-result
path; assert all memory writers/load ranges and banking; prove every required
view/replay/cancel transition preserves model and live state; then measure CPU
and real I/O separately. None of those later gates is inferred from dot tests.
