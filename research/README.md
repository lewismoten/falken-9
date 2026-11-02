# Research source and evidence (GitHub only)

This tree preserves the numerical probes, independent audits, tests, renderers and model-free traces for studies **003–016**. It is not part of the Hugging Face model package. No model, checkpoint, ROM, PRG, D64, environment or nested source ZIP is included.

Start with the [reproduction guide](../docs/RESEARCH_REPRODUCTION.md). Existing illustrated reports remain under [docs/research](../docs/research/) and figures under [assets/interpretability](../assets/interpretability/); they are not copied again here.

## Run the verified portable subset

From the repository root, with Python 3.11+:

```sh
python3 -B research/validate.py
python3 -B -m unittest discover -s tests -p test_research_inventory.py -v
# Existing CPU environment needs pytest, NumPy, PyTorch, Pillow and py65.
PYTHONDONTWRITEBYTECODE=1 python3 -B research/reproduce.py
# Run only one source group:
PYTHONDONTWRITEBYTECODE=1 python3 -B research/reproduce.py --group 015
```

The validator/security suite uses only the standard library. The method runner reconstructs each group's retained original members in a disposable temporary directory, verifies that project imports resolve there, and runs an explicit allowlist of original tests. It neither loads a model nor invokes historical finalizers. Its recorded [method results](method-test-results.json) are evidence for that narrow scope, **not a claim that every archived test passes in a fresh clone**.

## Questions and source groups

The command for every row is `python3 -B research/reproduce.py --group GROUP`. Studies 010/011 share one source group; 007 has a separate common-support supplement.

| Group | Question | Principal original entrypoints | Original report |
|---|---|---|---|
| 003 | Do dose curves, donor patches and restoration distinguish pathway effects from general damage? | `scripts/model_strategy_study003.py`, `falken9/strategy_patching.py`, original strategy tests/renderers | [003](../docs/research/study-003/REPORT.md) |
| 004 | Which executed hidden/expert/head paths support each empty candidate square, with exact rounding residuals? | `scripts/model_strategy_study004.py`, `falken9/strategy_square004.py` | [004](../docs/research/study-004/REPORT.md) |
| 005 | Do controlled attention-mass relocations selectively alter geometric/tactical behavior? | `study005_run.py`, `study005_audit.py`, `study005_core.py` | [005](../docs/research/study-005/REPORT.md) |
| 006 | What do router pair membership and gate values contribute separately? | `research678_run.py`, `research678_audit.py`, `research678_core.py` | [006](../docs/research/study-006/REPORT006.md) |
| 007 | Can bounded natural expert-output transfers preserve or rescue behavior on matched common support? | `research678_run.py`, `research678_audit.py`; supplement `research678_handoff.py` | [007](../docs/research/study-007/REPORT007.md) |
| 008 | Where do bounded one-code edits approach integer legal-membership sign boundaries? | `research678_stage008.py`, `research678_run.py`, descriptor tests | [008](../docs/research/study-008/REPORT008.md) |
| 009 | How does packet-derived signed8 approximation differ from one-code noise and cutpoint restoration? | `study009_run.py`, `study009_verify.py`, `study009_core.py` | [009](../docs/research/study-009/REPORT009.md) |
| 010-011 | How much symmetry belongs to the network versus its wrapper; which exact representations collide? | `study1011_run.py`, `study1011_audit.py`, `study1011_core.py`, walkthrough/renderers | [010](../docs/research/study-010/REPORT010.md), [011](../docs/research/study-011/REPORT011.md) |
| 012 | Can exact external D4 aggregation replace canonicalization while retaining correct complete sets? | `study012.py`, `study012_audit.py` | [012](../docs/research/study-012/REPORT012.md) |
| 013 | What are the exact safe signed16 intervals for individual output coordinates? | `study013_run.py`, `study013_verify.py`, `study013_core.py` | [013](../docs/research/study-013/REPORT013.md) |
| 014 | Which simultaneous output-coordinate boxes are certified safe, rather than merely individually safe? | `study014_run.py`, `study014_verify.py`, `study014_core.py` | [014](../docs/research/study-014/REPORT014.md) |
| 015 | Which real-forward play paths, routing patterns and deterministic opening-sampler states occur? | `study015_run.py`, `study015_audit.py`, `study015_core.py` | [015](../docs/research/study-015/REPORT015.md) |
| 016 | How do fixed tie policies and player roles change exact random-opponent outcomes and supported games? | `study016.py`, `audit016.py`, `scalar_reference015.py` | [016](../docs/research/study-016/REPORT016.md) |

## Inventory contract

[inventory.json](inventory.json) records **every discovered selected-archive member**, including exclusions: source group, exact original archive-relative name, uncompressed size and SHA-256. Group records bind the verified original ZIP filename/digest, member count and expansion audit. An excluded member's hash identifies the original bytes; it does not claim those bytes are present here.

- `included`: original bytes stored once under `studies/`.
- `reference`: byte-identical original content already stored elsewhere in this repository (including another group's source/data). No symlink or duplicate extraction is needed.
- `excluded`: explicit reason; presentation copies may additionally point to their existing repository location. Nested archives, transient test logs, visual drafts and unrelated build/training scripts are excluded.

The source-group directories are **content-deduplicated**, not independent complete checkouts. Do not run a script directly there and assume its neighboring imports or old fixture layout exist. `reproduce.py` materializes the referenced original members before executing its allowlisted tests.

**Study003 exception:** no study003 source/evidence ZIP was found in the supplied research workspace. Its actual source/tests, experiment manifest and final evidence were recovered directly, with per-file hashes and `source_kind: filesystem-recovery`; there is no invented archive filename or SHA. All other primary groups and the 007 supplement have independently matched the supplied ZIP pins. This curation is an expanded **subset**, never a claim of full original-archive byte identity.

Original scientific source is retained byte-for-byte, including historical absolute preservation paths. The new inventory contains only relative member/repository paths and symbolic source group IDs. Those historical paths are provenance constraints, not consumer instructions; do not edit frozen manifests or bypass integrity failures. No remote writes, model changes, commits or publication were performed.
