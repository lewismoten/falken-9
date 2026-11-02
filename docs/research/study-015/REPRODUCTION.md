# Study015 — reproduction and boundaries

The accepted application and model are not modified. Study015 is complete and stops here.

## Inputs

Python dependencies already present in the borrowed project environment: CPU PyTorch, NumPy and Pillow. No installation is performed. The ZIP deliberately omits the model and all PRG/D64/binary release payloads. Supply the separately obtained frozen **5,195-byte** packet at:

`artifacts/flexible-integer/q11-w16-a32-early-interp/model.f9j`

Required SHA-256:
`fe180f8a931f9d92d8aa39da337bc819d0dbe4e6d971edcba00324fbc18a91c1`

`manifest015.json` binds every snapshot input, including the supplied model. It was frozen before the empty-board discovery and trajectory outcomes. The complete source assembly snapshots are evidence only, not build instructions; this study never compiles or launches the game.

## Execute from this directory

Choose nonexistent output directories. In the isolated original workspace:

```sh
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export PYTHONPATH="$PWD"
PY=/home/ai/falken-9/.venv/bin/python
"$PY" -m unittest test_study015 -v
"$PY" study015_run.py fresh015
"$PY" study015_audit.py fresh015 > fresh015/independent-audit015.json
"$PY" study015_render.py fresh015
```

The stand-alone auditor has its own packet reader and arbitrary-int whole-network arithmetic, geometric canonicalizer, minimax, restoration and ties. It does not import production decoder/forward/wrapper code. It checks all 21 stages on all81 game steps and all627 reference boards, plus opening discovery and the2,295-state sampler census. Minimax is strictly an offline audit, never a move fallback.

The new runner executes every game mark using a fresh real neural forward; it never consults the saved full-domain logits to play a move. The627 reference forwards occur after the branch games. Stages retain routes and active expert observations; inactive zero-filled array slots are placeholders, not observed zero activations.

`results015/` contains the measured report and three annotated PNG/SVG pairs. Same-workspace deterministic reruns must reproduce every output byte. A fresh extraction changes only the recorded absolute import paths in `results015.json`; compare every other artifact byte-for-byte and compare that file with only `imports` removed. No other discrepancy is allowed. The archived input fixture hashes must match; they reuse previously accepted target-stage evidence and do not constitute fresh native replay.

The ZIP extraction smoke test supplies the model from the isolated study's frozen copy, executes fresh forwards, the stand-alone audit and figures, and checks those comparisons. `verification015.json` records this test and preservation. It is a separate external verification artifact and is not recursively included in the ZIP that it hashes.

## Limits

Host policy/PRNG emulation only: no new native C64 execution, physical/browser replay, timing, empirical RNG fairness, novel-input generalization or learning. One fixed transform must map an entire ordered sequence to call trajectories D4-equivalent. The ideal no-repeat1/8 conditional law and1/9 stationary law are not properties established for the fixed seed's actual deterministic orbit. See the sampler figure and report for exact orbit counts.
