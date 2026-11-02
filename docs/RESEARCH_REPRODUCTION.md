# Research reproduction: portable methods versus historical acceptance

The [research source inventory](../research/README.md) covers studies003–016, including shared010–011 and the007 common-support supplement. This is **GitHub-side scientific source/evidence**, not a Hugging Face upload tree. The model/game release and this research integration have separate acceptance boundaries.

## 1. What works without the model

Run from a fresh repository checkout using Python3.11+:

```sh
python3 -B research/validate.py
python3 -B -m unittest discover -s tests -p test_research_inventory.py -v
```

These standard-library checks validate complete study coverage, original-source/test presence, inventory member closure, the size/hash of every retained or referenced member, absence of unindexed curated files, and security rejection of traversal, absolute/drive/backslash paths, duplicate ZIP names, symlinks, special files and excessive expansion. ZIPs are **not** required for retained-file verification. If all original ZIPs are separately available in one directory, `research/validate.py --archives DIRECTORY` additionally checks their pinned archive hashes, CRCs and every member digest without extraction. The original003 ZIP is explicitly unavailable, not silently treated as verified.

The actual model-free original method tests run with an existing CPU environment containing `pytest`, `numpy`, `torch`, `Pillow` and `py65`:

```sh
PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  python3 -B research/reproduce.py
# Any one group (010/011 share a group):
python3 -B research/reproduce.py --group 010-011
# Optional new report, never an existing report path:
python3 -B research/reproduce.py --group 015 --report /your/scratch/new-method-result.json
```

No installation is performed by these commands. The runner uses a temporary directory (honoring `TMPDIR`), materializes byte-identical referenced dependencies, asserts that `falken9` imports originate in that disposable copy, disables Python/pytest cache writes, and executes only explicit test node IDs. It validates the source inventory both before and after. Numerical artifacts under `research/studies/` and historical sibling workspaces are never used as output directories. The checked-in [method-test-results.json](../research/method-test-results.json) records the actual exercised nodes and interpreter. The exact tested dependency versions are in the [validation report](../research/validation-results.json).

Covered methods include donor alignment/inactive-expert rejection, independent signed rounding and geometry, attention apportionment/mass conservation, router/gate identities, expert-indexed patching, code-boundary validation, exact collision equality despite forced hash collisions, D4 alignment, exact ensemble sign aggregation, exhaustive small integer interval/band/extrema controls, sampler bounds, rational terminal DP and inverse-coordinate negative controls. The per-group questions and original probe/audit/render entrypoints are in the [source index](../research/README.md#questions-and-source-groups).

**This is not an all-tests-pass assertion.** An initial method selection demonstrated that two003 fixture-dependent tests require the saved runtime fixture and model, and004's full bookkeeping test loads the model. They are deliberately not in the model-free allowlist. The complete original test sources remain preserved. Full-run, rendering, finalization, historical preservation and target-dependent tests were not rerun as part of the portable subset. No hidden skip is counted as a portable pass.

## 2. Obtain and verify the frozen model separately

The unchanged authorized F9J2 packet is committed as
[`releases/falken-9-v1.0.0/model.f9j`](../releases/falken-9-v1.0.0/model.f9j).
It is also distributed by [lewismoten/falken-9](https://huggingface.co/lewismoten/falken-9);
the public `model.f9j` at immutable Hub revision
`c659b516d7ebea16e1905f4951bdd7d95df32ffb` was downloaded and verified.
Do **not** export a replacement, reconstruct it from activations, or use an
approximate model with the same nominal precision. The verified bytes establish
identity independently of the distribution host.

Required packet:

- File size: **5,195 bytes**.
- SHA-256: `fe180f8a931f9d92d8aa39da337bc819d0dbe4e6d971edcba00324fbc18a91c1`.
- Historical relative location: `artifacts/flexible-integer/q11-w16-a32-early-interp/model.f9j`.

Check the committed packet read-only:

```sh
python3 -B research/check_model.py releases/falken-9-v1.0.0/model.f9j
```

The model and accepted PRG/D64 are in the versioned release directory, not
`research/`. Historical binaries required by older experiments remain separate;
the current game cannot substitute for their exact pins. ROMs, checkpoints,
environments, nested ZIPs and transient service/test logs are not redistributed.

## 3. Inspection/materialization is portable; full historical acceptance is not automatic

The deduplicated on-disk group is not a standalone import root. To inspect a group's retained layout independently:

```sh
# Choose a nonexistent directory outside the repository.
python3 -B research/reproduce.py --materialize 016 --destination /your/scratch/study016-copy
```

This copies only retained original members and resolves their references; no code is executed. Groups006–012 retain their original `source/` prefix, so the reported source root may be `study-copy/source`. It is still an explicit subset: excluded prose/figures/logs/nested archives are not magically restored. Existing presentation links are not rewritten inside preserved code or reports. Obtain the model separately before attempting any full neural run, and use only new output directories in a disposable materialization.

### Historical numerical commands (not portable acceptance promises)

The following identify the original execution surfaces. They are not invoked by the safe-method runner. For003–014, inspect all bound preservation inputs and historical absolute roots **before** running them; some dependencies intentionally refer to other original workspaces or accepted application files. Do not change a frozen manifest to make a failing check disappear.

| Study/group | Historical numerical/audit entrypoints | Additional prerequisites/limits |
|---|---|---|
| 003 | `python scripts/model_strategy_study003.py --output NEW`; `python scripts/render_strategy_study003.py --study NEW` | Exact model, original frozen full-forward shards and earlier baseline/manifest hashes. Direct filesystem recovery, not a verified standalone003 ZIP. |
| 004 | `python scripts/model_strategy_study004.py --output NEW`; `python scripts/render_strategy_study004.py --study NEW` | `requirements-study004.json`, prior69 baseline and23 study003 evidence hashes; fixed-path finalizer must not be run in an occupied frozen tree. |
| 005 | `study005_run.py`, `study005_audit.py`, `study005_render.py` | Inspect their actual CLI and manifest-bound original paths; attention control unit tests do not rerun full-network interventions. |
| 006–008 | `research678_run.py`, `research678_audit.py`, `research678_stage008.py` | Frozen per-study `experiment-studyNNN.json`, prior005 relocation inputs, saved target shards, original preservation manifests; 007 supplement adds common-support audit/source. |
| 009 | `study009_run.py`, `study009_verify.py`, `study009_render.py` | Exact packet-derived row conversion, fixed24 overrides and original preservation inputs; the scalar quantizer test alone is not24 full runs. |
| 010–011 | `study1011_run.py`, `study1011_audit.py`, `study1011_render.py` | Frozen orientation/census experiments, exact independent label/serialization contracts; retained baseline/measurement NPZ files are existing evidence, not newly held-out data. |
| 012 | `study012.py`, `study012_audit.py` | Frozen010 inputs and exact rational sign/group contracts; symmetry alone does not establish policy correctness. |
| 013 | `python study013_run.py --out NEW`; `python study013_verify.py NEW` | Bound `manifest013.json`, trace inputs and historical original/main preservation roots; full signed16 code census/endpoint neural verification not repeated here. |
| 014 | `STUDY014_INTEGRATION=1 STUDY014_OUT=NEW python -m unittest test_study014 -v`; `python study014_verify.py NEW` | `manifest014.json`, prior013 certificates, frozen main/prior preservation roots. Do not mix direct-script versus imported-unittest invocation when comparing path/import provenance bytes. |
| 015 | `python study015_run.py NEW`; `python study015_audit.py NEW`; `python study015_render.py NEW` | Exact packet, bound010 traces/source snapshots. All new forwards/figures need fresh output. Relocation changes recorded absolute import provenance; numerical equivalence is not full-byte identity of that metadata. |
| 016 | `python study016.py NEW`; `python audit016.py NEW`; `python render016.py NEW` | Exact packet and bound source inputs. Rational branch enumeration is not fresh neural execution; imported paths can change after relocation. `finish016.py` retains original-machine preservation assumptions. |

`NEW` must be a nonexistent output directory under a scratch copy, never a preserved `resultsNNN` or `*-final` tree. Renderers require Pillow and the original DejaVu Sans/Mono fonts for byte-identical PNG/SVG rendering. Historical numerical runs also require PyTorch/NumPy and their original versions; the safe-method results do not assert cross-version bit-identical output. No full historical finalizer was executed during this integration.

## 4. Study015 genuine-machine sampler harness

The original [machine-sampler-parity.py](research/study-015/machine-sampler-parity.py) is already retained with the documentation; it is linked here, **not duplicated or silently rewritten**. It imports `py65.devices.mpu6502.MPU` and executes genuine assembled reset/resolver subroutines, with instruction bounds, audited writes and native JSR/RTS/carry/decimal checks. It is distinct from the model-free host sampler test.

Actual excluded binary dependencies are:

- `falken9-010-graphical.prg`, SHA-256 `c571353a61c8a663050c33809b6ca880d29aebc969c545a717da2644eed3143a`.
- `falken9-010-graphical.d64`, SHA-256 `2570b642780ea6dd2e64c1b915e4bf3143fd8d86e1f9e2224f483f53d9bdb21d`.
- Matching `app.lst`, `src/app/auto_demo.asm`, study015 sampler census/opening transitions and original independent auditor. The model-free assembly listing/source snapshots and study015 numeric fixtures are retained through the inventory; PRG/D64 are not.

Its original globals and one source-file path intentionally use historical absolute locations. Merely downloading a different/current game or adding the model cannot satisfy those binary pins. The historical command, valid only where those exact original locations exist, is:

```sh
python -B docs/research/study-015/machine-sampler-parity.py --output HISTORICAL_SCRATCH/new-sampler-result.json
```

`HISTORICAL_SCRATCH` must resolve under the harness's original scratch root; otherwise it rejects the output. A future portable adapter must take explicit binary/listing/source/fixture paths and normalize them in **new wrapper code only**, preserving this source's bytes and reporting the adapter's own hash. No full game replay, ROM/I/O, hardware acceptance, empirical RNG fairness or physical timing follows from isolated py65 parity. This integration verifies the linked harness and its declared binary pins, but does not claim a fresh portable execution of that historical harness.

## 5. Preservation, privacy and provenance

Original retained archive members are copied verbatim. `research/inventory.json` binds each member's original archive-relative path, digest, size and source group, even for explicit exclusions. Archive SHA pins identify originals, not newly rebuilt subsets. Global content deduplication avoids repeated source trees, NPZ traces and already-curated figures/reports. There are no extracted symlinks or bundled inner archives. Full original ZIP member/hash audit was executed at curation time; public integrity checks need only the expanded subset and referenced repository files.

The machine inventory publishes no original absolute workspace roots, private host URLs, tokens or credential material. Some immutable scientific sources/manifests retain historical local paths needed to explain original preservation checks. They are not shell-ready fresh-clone instructions; no credential-bearing filesystem or connection configuration is shipped. URL-host scanning of retained textual sources found only Hugging Face, GitHub and the standard SVG namespace. Preserved code is not globally path-rewritten or rehashed under a false original identity.

All work is local preparation. No remote upload, push, commit, model mutation or accepted-application change is authorized or performed by these entrypoints.
