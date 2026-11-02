# Research012: optional finite group-aggregation follow-up

Run only inside the isolated snapshot; do not edit accepted application010, the frozen model, or010/011 handoffs. This is the **one** optional follow-up justified in `NOVELTY-STUDY-012.md` after010/011 independently verified. `experiment-study012.json` predeclares exactly four fixed algorithms before aggregate outcomes.

## Executed reproduction

The immutable source is `artifacts/interpretability/study-010-final/measurements010.npz`, SHA-256 `7d0e07c6e406925530a6b3feb1bf9422c536a9c168786c9bb5eaafef7679aad5` (the authoritative exact hash is in the manifest; use the code's hash check). Model remains5,195 bytes, SHA-256 `fe180f8a931f9d92d8aa39da337bc819d0dbe4e6d971edcba00324fbc18a91c1`. Dependency interpreter is borrowed only; project imports stay isolated. No install or new neural forward is performed.

```sh
cd /home/ai/falken9-strategy-study-003
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=/home/ai/falken9-strategy-study-003
PY=/home/ai/falken-9/.venv/bin/python
$PY study012.py --out artifacts/interpretability/study-012-reproduced-clean
$PY study012_audit.py artifacts/interpretability/study-012-reproduced-clean
$PY -m pytest -q -p no:cacheprovider test_study1011.py test_study012.py
$PY -c "from study1011_finalize import compare; print(compare('artifacts/interpretability/study-012-final','artifacts/interpretability/study-012-reproduced-clean'))"
```

Choose a fresh unused output name on another repetition. Do not rerun the one-shot freeze/finalizer over existing numbered artifacts. Output NPZ and source/evidence ZIPs use deterministic entry order, timestamps and permissions; all files, not only result metrics, are compared.

## Independent checks

The audit never calls the aggregation implementation. It constructs all8 branches for every4,520 raw board directly from the already measured raw logits, rather than trusting canonical-output expansion. Python-integer sum/all/any/count conditions independently verify162,720 membership scalars and144,640 full-set board/transform checks across the four policies. It separately checks minimax sets, exact raw ties, false/missing members, controls and the predeclared example IDs2/9. These are finite reused observations, not new independent/model-heldout samples.

The exact mean uses a sum-sign comparison (rational mean numerator /8), not an integer-rounded average. Nonnegative scores are membership, not categorical confidence. All four policies enforce full-set D4 equivariance externally, but none matches the correct complete-set wrapper. There is no deployed algorithm or speed/RAM claim.

## Preserved issues

* Freeze's output redirection created an empty in-flight `freeze-study012.log` that its own inventory captured. After completion, the first execution correctly rejected its changed hash. The completed log was preserved separately as `freeze-study012-completed.log`, and the originally captured empty file restored. Neither manifest nor numeric scope was amended; all1,414 prior files subsequently compare exactly. The empty first output directory is preserved as `study-012-attempt1-selflog`.
* The first case-figure legend described blue fills but omitted red false members. A failing caption regression prompted a wording-only fix; original native PNG/SVG/metadata are preserved in `study012-original-visual.zip`. Numerical results did not change; a clean full rerun uses the final renderer.
* Original010/011 reports, synthesis, source hashes and170-entry ZIPs remain immutable. The new `SYNTHESIS010-012.md` adds012 without replacing older synthesis.

The source/evidence bundle excludes model/ROM binaries, environments, credentials and private hosts. Existing hash-pinned model/snapshot are external prerequisites; measured-logit evidence is not a model binary. Stop here—no013, no broader algorithm panel, retraining or target changes.

## Read

* [Combined illustrated synthesis and actual forward walkthrough](artifacts/interpretability/study-012-final/SYNTHESIS010-012.md)
* [Full012 report](artifacts/interpretability/study-012-final/REPORT012.md)
* `FINAL-STUDY-012.{md,json}` and `verification-study012.json`
