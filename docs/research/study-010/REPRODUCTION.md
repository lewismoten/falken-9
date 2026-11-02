# Reproducing Research010/011 (not C64 application010)

## Prerequisites and immutable boundary

Use the hash-pinned isolated snapshot `/home/ai/falken9-strategy-study-003`, not the accepted game checkout. The already installed `/home/ai/falken-9/.venv/bin/python` is borrowed **only for dependency imports** (PyTorch, NumPy, Pillow, pytest); every project module must resolve inside the isolated snapshot. No install is needed. Matplotlib is not installed and is not used by the final renderer.

Original model, fixtures and earlier evidence are external prerequisites, not redistributable bundle payloads. `preservation-010-011-initial.json` pins all 1,258 files discovered before this work; the model is5,195 bytes with SHA-256 `fe180f8a931f9d92d8aa39da337bc819d0dbe4e6d971edcba00324fbc18a91c1`. Original studies003–009, all numbered artifacts and source/evidence bundles remain unchanged. Do not re-run `study1011_freeze.py` over existing manifests.

A fresh output directory is required for each measurement run. Commands below were actually exercised with the `*-reproduced` names; choose new names when repeating again.

```sh
cd /home/ai/falken9-strategy-study-003
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=/home/ai/falken9-strategy-study-003
PY=/home/ai/falken-9/.venv/bin/python

$PY study1011_run.py 010 --out artifacts/interpretability/study-010-reproduced
$PY study1011_run.py 011 --out artifacts/interpretability/study-011-reproduced
$PY study1011_audit.py 010 artifacts/interpretability/study-010-reproduced
$PY study1011_audit.py 011 artifacts/interpretability/study-011-reproduced
$PY study1011_render.py \
  --d10 artifacts/interpretability/study-010-reproduced \
  --d11 artifacts/interpretability/study-011-reproduced \
  --walk artifacts/interpretability/study-010-011-walkthrough-reproduced
$PY -c "from study1011_audit import audit_walkthrough; print(audit_walkthrough('artifacts/interpretability/study-010-011-walkthrough-reproduced','artifacts/interpretability/study-011-reproduced/baseline011.npz'))"
$PY -m pytest -q -p no:cacheprovider test_study1011.py
```

Each fresh process rechecks the model/baseline, import locations and prior-file hashes. D4 measurement intentionally passes noncanonical orientations directly into the canonical-trained network: this is **off-contract**, not a shipping-app failure. Output integer scores are membership signs, never categorical confidence. Source bytes are not altered by any intervention because these studies do not modify parameters at all.

## What to compare

* Study010: `results010.json`, `examples010.json`, exact measurements/baseline NPZ, `independent-audit010.json`, two figure pairs and report.
* Study011: all25 stage scopes,12 applicable per-expert scopes, `classes011.json`, board/label/null-mask records,22 collision examples, independent audit, two figure pairs and report.
* Walkthrough: exact static parameter snippets versus dynamic activations;8 embedding sums,8 weighted-value components,8 merge components,9 head scalars and complete-set/priority audit; two figure pairs and illustrated synthesis.

`study1011_finalize.compare()` compares **every file** by SHA-256, not selected metrics. Deterministic NPZ and ZIP writers fix entry order, timestamps, permissions and compression. Final evidence includes both outputs and reports; no elapsed-time metadata is inside the reproducibility boundary. Final verification records preserve wall-time/audit metadata separately.

```sh
$PY -c "from pathlib import Path; from study1011_finalize import compare; r=Path('artifacts/interpretability'); print(compare(r/'study-010-final',r/'study-010-reproduced')); print(compare(r/'study-011-final',r/'study-011-reproduced')); print(compare(r/'study-010-011-walkthrough',r/'study-010-011-walkthrough-reproduced'))"
```

The finalizer is one-shot and refuses to overwrite verified handoffs/ZIPs. Do not invoke it again over existing outputs; its `compare()` and archive-reader checks are safe to use read-only.

## Preserved issues and limitations

* First011 JSON write failed on NumPy scalar metadata; original partial evidence remains in `artifacts/interpretability/study-011-attempt1-incomplete-json`, and a RED→GREEN serialization regression documents the correction. No stage, cohort or manifest changed.
* First plotting draft assumed unavailable Matplotlib. No install was attempted. Exact draft source is preserved as `study1011_render_attempt1_matplotlib.py`; final figures use the existing Pillow TrueType renderer plus native SVG.
* Native inspection caught one walkthrough heading overlap. The failing layout test, original draft visual ZIP and corrected text-box checks are retained. Measured numbers are unchanged.
* Source/evidence ZIPs intentionally exclude ROM/model binaries, checkpoints, environments, credentials and private-host addresses. They require the original hash-pinned snapshot to execute, rather than pretending to be a self-contained model release.
* No main game/model/build/packet/docs/packages, training, target execution, cloud/GPU/service or publication changes. Parent owns any integration into the main report.

## Reading order

1. [Illustrated synthesis and actual forward walkthrough](artifacts/interpretability/study-010-011-walkthrough/ILLUSTRATED-SYNTHESIS1011.md)
2. [Research010: learned versus wrapper symmetry](artifacts/interpretability/study-010-final/REPORT010.md)
3. [Research011: exact collisions and information retention](artifacts/interpretability/study-011-final/REPORT011.md)

Every displayed PNG links to a native, selectable-text SVG. Reports retain negative findings, original-coordinate ties, inactive/null expert semantics and the already-trained finite-domain caveat.
