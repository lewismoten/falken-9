# Reproduce study009 in the preserved isolated snapshot

Study009 is a packet-derived host diagnostic, not a deployment export, historical INT8 candidate reproduction, or new C64 execution.

## Prerequisites

Use `/home/ai/falken9-strategy-study-003` as the project root. The source/evidence ZIP is deliberately not a self-contained model release: it excludes the frozen packet, ROM/model binaries and environment. It requires the original preserved snapshot (the1114 input files identified by `preservation-before009.json`), including original target fixture shards, earlier preservation manifests and reports used by the baseline guard. Obtain those from their existing authoritative locations; do not invent substitute fixtures or float-master weights.

The authoritative source packet is5195 bytes with SHA-256:
`fe180f8a931f9d92d8aa39da337bc819d0dbe4e6d971edcba00324fbc18a91c1`.

Borrow the existing interpreter for dependencies only. All project imports must originate in the isolated root. No build, training, main checkout modification or deployment is involved.

```bash
cd /home/ai/falken9-strategy-study-003
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$PWD"
PY=/home/ai/falken-9/.venv/bin/python
# Choose a NEW directory; never overwrite any earlier study.
$PY study009_run.py --out artifacts/interpretability/study-009-your-reproduction
$PY study009_render.py --out artifacts/interpretability/study-009-your-reproduction
$PY study009_verify.py --out artifacts/interpretability/study-009-your-reproduction --result your-independent-audit009.json
# The report uses the immutable independently audited first-run results.
$PY study009_report.py --out artifacts/interpretability/study-009-your-reproduction
$PY -m pytest -q -p no:cacheprovider test_study009.py
```

The test module intentionally targets the saved `study-009-final` artifacts for independent recount. `study009_finalize.check_artifacts()` byte-compares the two already exercised `study-009-final` and `study-009-reproduced` trees; its CLI writes final metadata and bundles once and must not be used to overwrite an existing release.

The runner replays13167 original target stage vectors and5643 logits before any approximation, executes24×627 complete canonical integer forwards, and calls the original public history wrapper for all24×4520 raw outcomes using test-only saved canonical logits. The independent audit repeats public wrapper execution and reconstructs quantization, norm2, route/gate, mixture and head arithmetic with Python scalar checks.

Five annotated PNG/SVG pairs bind actual boards, stored codes/exponents, stages, routes/gates and signed legal sets. The deterministic evidence ZIP contains the50 final artifacts, selected research/support source, manifests, scalar audit and test logs. It omits final metadata that contains the bundle's own SHA, avoiding circular hashes. The reproduced ZIP must be byte-identical.

Draft renderer evidence remains preserved unchanged in `study009-render-original-evidence.zip`; its caption/arrow corrections did not alter the frozen design or any numerical result. All earlier studies are immutable. Final metadata and exact per-file hashes are in `verification-study009.json` and `FINAL-STUDY-009.json`.
