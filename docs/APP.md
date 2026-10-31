# Resident C64 application — test 001

The application is a complete human-X versus neural-O game, not an opening-only
slice. No source-model changes or training were required. The accepted E4/K2,
Q11/W16/A32 model and the complete accepted core remain byte-identical.

## Build, verify, play

From the repository root, with the existing project environment, model, dataset,
and 64tass available:

```sh
.venv/bin/python scripts/build_app.py
.venv/bin/python scripts/verify_app.py
.venv/bin/python -m pytest tests/test_app*.py -q
```

`build_app.py` creates `build/app/falken9-001-resident.prg`. The verifier executes
the wrapper, complete live-neural games, creates the disk only after the exact
PRG passes, extracts its identical PRG and executes both games again. It freezes
the verified artifacts and sources under `artifacts/app/001-resident/` and writes
`results/app-summary.json`. D64s, build files, and bulky evidence remain ignored.

- PRG: `artifacts/app/001-resident/falken9-001-resident.prg` (33,162 bytes)
- SHA-256: `faa07bd4b9aa1c40894098407046d29a3310b52ab5dcdf0cc47ba6daf98f3b47`
- Disk: `artifacts/app/001-resident/falken9-001-resident.d64` (174,848 bytes)
- SHA-256: `b26580db7ed064360f3fb3ffdf15105645b9f242239e72e57137a447f80925a2`

Load/autostart the PRG, or load the disk's first file and run it. The BASIC line
is `10 SYS32768`. Stock-ROM VICE autostart was verified for both transports.
This is **not** a claim of launch/keyboard acceptance at the target browser.

**A–I** selects a square (`ABC / DEF / GHI`); **R** starts a fresh match, including
at a terminal board. Empty cells retain dim address letters. X is light red;
O is light blue. An accepted human X is drawn **before** neural execution.
Invalid/occupied input recovers without invoking the network. Terminal input
cannot continue the game. The model is resident and there is no per-turn LOAD.
The screen shows a truthful full-neural-forward busy phase, followed by move
commit and the next input/result. It has no fabricated completion meter.
**Fine-grained per-layer progress is not implemented**; the immutable core has
no application callback hooks. Replay is processed at input boundaries, not
as cancellation during a forward. AI-vs-AI/title modes are not included.

## Protocol and inference boundary

- `validate_history`: `history` at `$7800`, byte `history_length` at `$7809`.
  Length 0–9; lower/uppercase A–I accepted; repeated, malformed, overlength,
  and continuation-after-terminal histories return carry set. Occupancy is
  `original_board` at `$7810`: 0 empty, 1 X, 2 O. Terminal is 0 ongoing, 1 X,
  2 O, 3 draw; side is the next chronological mark. A final terminal board is
  accepted by this rules validator so the game can display its result.
- `policy_request` rejects terminal histories and every invalid history before
  inference. It explicitly calls the accepted `full_forward`; there is no
  runtime fixture, native callback, minimax, heuristic, or fallback.
- `canonicalize_board` evaluates all eight geometry permutations and retains
  the lexicographic minimum, with first-transform stability on equal boards.
  Original-to-canonical indices are retained in `selected_transform`.
- `restore_set` gathers the **entire** canonical legal `logits >= 0` set back
  to original coordinates, masks occupied original cells, then selects using
  `ebdfhcgia`. Zero is included. A negative-only legal result returns an error,
  never an invented move. It does not map only one canonical winning square.
- Public assembly routines clobber A/X/Y/status. Use labels from the matching
  build; only the explicitly described byte buffers are stable interfaces.

## RAM, BASIC launch, and IRQ ownership

| Region | Use |
|---|---|
| `$0020–$007f` | Accepted core zero-page scratch; saved/restored around each request |
| `$0100–$01ff` | Hardware stack; app starts at SP `$ff` |
| `$0400–$07ff` | Fixed screen, no CHROUT/scrolling; KERNAL cursor blinking disabled |
| `$0800–$1d7e` | Accepted neural code, restored before first use |
| `$4000–$544a` | Original 5,195-byte model including tables |
| `$6000–$6d9f`, `$7000–$70ff`, `$7200–$75ff` | Accepted runtime scratch/vectors |
| `$7800–$78ff` | App state and saved KERNAL zero page (`$7880–$78df`) |
| `$8000–$8988` | App code, static text/geometry, immutable 16-byte core backup |
| `$d800–$dbff` | Color RAM |

The PRG loads at `$0801`; its BASIC SYS stub temporarily overlays the initial
core bytes. App entry at `$8000` restores **all sixteen** original bytes starting
at `$0800`, including the byte before the PRG load address. Tests compare the
whole core after startup, so the first MAC instructions are not silently lost.
The entire model is loaded once inside the contiguous PRG. Gaps are included
in the transport size, not counted as learned weights.

IRQ scanning is enabled only in the KERNAL GETIN input loop. The application
executes SEI before modifying the board or invoking inference, saves KERNAL's
`$20–$7f` image, executes the whole request, restores those bytes, and only then
returns to IRQ-enabled input. It never replaces the IRQ vector or changes `$01`.
VIC bank 0/standard uppercase ROM characters are selected directly. The game
owns its stack and does not return to BASIC. RESTORE/NMI handling and physical
hardware are not acceptance claims; avoid RESTORE during computation.

## Evidence and exact proof scopes

1. **Composed exhaustive wrapper:** all 4,520 unique nonterminal boards use an
   actual assembled chronological-history validator, all-eight canonicalizer,
   full-set inverse, legal mask and tie selection. Canonical board and selected
   permutation are independently compared with the host geometry contract.
   Neural logits are **TEST ONLY** fixtures from the 627 previously executed
   canonical target forwards. Shards are read from the frozen evidence manifest
   and their hashes verified. There are zero move/set errors. This composes
   with the prior 627-core proof; it is **not** 4,520 new neural executions or
   294,778 assembled chronological-wrapper calls.
2. **Live packaged PRG:** the actual input loop completes a draw and an O win,
   seven newly executed full forwards, legal model results, terminal locking,
   invalid/repeated input recovery, replay, retained board/colors, and input-loop
   return. Per-write/PC guards enforce the app/core writable map. Code and model
   remain unchanged; deepest observed stack write is `$01ea`; final SP is `$ff`.
   The deliberately narrow GETIN-only shim poisons KERNAL zero page, supplies
   actual N/Z return flags, and is explicitly distinct from ROM evidence.
3. **Extracted disk PRG:** byte-identical to the passed PRG; both complete games
   execute again. BAM free counts and allocation reachability, directory block
   count, sector chains and exclusion of track 18 file data are checked.
4. **Stock-ROM VICE:** both PRG autostart and D64 true-1541-drive autostart complete
   those same two games through genuine ROM GETIN/IRQ, with seven full logits
   identical to Py65 for each route, immediate X before neural entry, unchanged
   IRQ vector/core/model, SP `$ff`, `$01=$37`, invalid-input recovery and replay.
   Input is monitor-injected KERNAL queue data, not a physical/browser keyboard.
   Genuine VIC screenshots `vice/{draw,model-win}.png` and
   `vice-d64/{draw,model-win}.png` were captured after a rendered frame.

Reproducible local-ROM acceptance (ROMs are **not** redistributed):

```sh
F9_RUN_VICE=1 F9_VICE_ROOT=/path/to/local/vice-root \
  .venv/bin/python -m pytest tests/test_app_003_rom.py -q
# Expected root layout: usr/bin/x64, usr/lib/x86_64-linux-gnu,
# usr/share/vice/C64/{kernal-901227-03,basic-901226-01,chargen-901225-01}.bin
# The true-drive route also requires local 1541 ROMs under usr/share/vice.
```

Manual replay matrix (wait for each model response):

- `E B D I G` → chronological `ecbhdfiag`, draw.
- `R`, then `A B D` → chronological `aebcdg`, O wins on C–E–G.
- Terminal `A`/`I` must not change the board; `R` clears it.
- An occupied square or `!` during input must recover without a model request.

Target-browser launch/physical key handling and a physical C64 remain untested.
No artifacts were published externally; no original CP64 files or frozen neural
evidence were modified.
