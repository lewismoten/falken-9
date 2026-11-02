# Reproduce study013

This isolated host study changes no deployed model, game or prior research.

## Prerequisites

- CPU Python 3.11+, NumPy, PyTorch and Pillow; DejaVu Sans / DejaVu Sans Mono fonts.
- Original 5,195-byte frozen packet at `artifacts/flexible-integer/q11-w16-a32-early-interp/model.f9j`, SHA-256 `fe180f8a931f9d92d8aa39da337bc819d0dbe4e6d971edcba00324fbc18a91c1`. The source/evidence ZIP intentionally excludes the model.
- Included bounded study010 trace inputs and prior preservation manifests. The historical exact preservation checks require the unchanged source research root and main accepted application010 files at the paths in `study013_run.py`. This is disclosed as a local historical reproduction, not a standalone fresh-clone claim.
- `manifest013.json` is the original chmod444 preconfirmation manifest. Do not edit it or the hash-bound source/input files to bypass an integrity failure.

## Commands actually exercised

From `/home/ai/falken9-coordinate-study-013`:

```sh
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=/home/ai/falken9-coordinate-study-013
PY=/home/ai/falken-9/.venv/bin/python
$PY -m unittest test_study013
$PY study013_run.py --out results013
$PY study013_run.py --out reproduced013
$PY study013_verify.py results013
```

The interpreter supplies dependencies only; every project import is asserted inside the new isolated workspace. Output directories must not already exist. `verification013.json` records exact byte equality across all14 outputs of the two complete runs, including the two PNG/SVG pairs and report. The independent verifier enumerates every signed16 code against every applicable legal board observation, independently decodes packet bytes, reproduces full-head scalar arithmetic, and checks reachability/minimax/D4/raw sets/ties. The public-wrapper fixture uses saved outputs only for composed host validation; it is never installed in the application.

Read `results013/REPORT013.md`; click/open its SVG counterparts for scalable text. Full per-coordinate constraints, both limiting sides, endpoint/neighbor neural outputs and scalar byte-offset evidence are retained in JSON/NPZ. `FINAL-STUDY-013.json` and `verification013.json` identify final artifacts. No training, package installation, GPU, deployment, external service or target timing is involved. Stop after013.
