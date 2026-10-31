# Numeric C64 application — test 002

Application-only revision of the stable model-v1.0.0 deployment. The 5,195-byte
model, complete neural core, occupancy encoding, symmetry restoration and tie
priority remain unchanged. The tagged model release and frozen test 001 PRG/D64
are preserved. See [test 001 architecture and proof boundaries](APP.md).

## Controls and mapping

```text
1 2 3       a b c
4 5 6  <->  d e f
7 8 9       g h i
```

Use **1–9** to select a square; **R** replays. Empty squares show dim numbers.
Legacy A–I/a–i and their screen-code aliases remain accepted for compatibility
in this text application; they are not additional model tokens. The graphical
UI is separate future work and will need to reserve its own navigation keys.

The input adapter stores the same lowercase letter history as test 001. The
model still receives nine occupancy values (0 empty, 1 X, 2 O), and emits nine
signed scores, not a tenth invalid class. The original-coordinate tie order
remains `ebdfhcgia` (numeric `5,2,4,6,8,3,7,9,1`).

`move_result` at `$784d` is a public **binary byte**, not an ASCII character:
1–9 names the selected model move, and 0 means invalid/no result. It is separate
from the legacy `selected_move` zero-based index at `$7849` and from occupancy.
`restore_set` sets it only after a legal set member is selected. `policy_request`
clears it before validation, so malformed/terminal requests cannot return a
stale success. The UI also clears it on replay and each nonempty input, including
invalid/occupied/terminal input; idle polling does not erase a successful result.
Carry remains the callable wrapper's success/error indicator. A zero input key
is invalid and does not invoke the network. No literal `!` neural token exists.

## Build and verify

Requires the existing local accepted model/dataset, project environment and
64tass; no training or external model service is involved.

```sh
.venv/bin/python scripts/build_app.py
.venv/bin/python scripts/verify_app.py
.venv/bin/python -m pytest tests/test_app*.py -q
# Optional locally installed stock ROMs, never redistributed:
.venv/bin/python scripts/verify_app.py --vice-root /path/to/local/vice-root
```

Generated release files:

- `artifacts/app/002-numeric/falken9-002-numeric.prg`
- `artifacts/app/002-numeric/falken9-002-numeric.d64`
- `results/app-002-summary.json`: hashes, exact proof scopes and acceptance.

The verifier refuses to use the frozen 001 directory. It runs the assembled
wrapper against all 4,520 unique nonterminal boards using the existing frozen
627-forward logits (a composed proof, not 4,520 new neural executions). It also
runs complete numeric-key draw/model-win matches, with seven actual neural
forwards, in both the PRG and the PRG extracted from the validated disk. Optional
stock-ROM VICE acceptance exercises PRG and true-1541 D64 autostart separately.

## Manual test sequences

Wait for each model response:

- `5 2 4 9 7` → draw, internal history `ecbhdfiag`.
- `R`, then `1 2 4` → O wins on squares 3–5–7, history `aebcdg`.
- Occupied square or `0` during play → invalid feedback, unchanged board,
  no additional inference. The same input after a terminal result stays locked.
- `R` → empty numbered board and cleared public result.

**Emulator-only.** New numeric controls require their own browser launch and
interaction acceptance; test 001 browser evidence does not establish test 002.
Physical C64/1541 compatibility and performance remain unverified. Graphical
art integration, inference activity lights and the dark-blue identity badge
are not included in this revision.
