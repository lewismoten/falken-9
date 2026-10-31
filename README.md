# Falken-9

A new C64-first neural tic-tac-toe policy project. The goal is a compact, RAM-resident model with real attention, learned routing and mixture-of-experts execution—not a stored move table. Crystal-9's published original-model release is preserved separately.

Expert count and active top-k are optimization variables, not a requirement to keep nine experts. New candidates compare smaller learned expert banks while preserving genuine MoE.

**Research status:** a **6,110-byte whole-integer** attention/MoE model passes all 294,778 published histories on the host. A separate **four-expert** float model also passes; its smaller INT8 attempt is rejected for remaining policy errors. Exact local constant folding offers a storage/computation tradeoff. Assembled range-aware inference is now in development; no Falken-9 model is yet accepted as a complete C64 deployment. Physical hardware has not been tested.

## Plan and evidence

- [Plan of action and competing approaches](docs/PLAN.md)
- [Dataset provenance and symmetry findings](docs/DATASET.md)
- [Current stage status](docs/STATUS.md)
- [Trained reference candidates and exhaustive results](docs/TRAINING.md)
- [Arithmetic contract and measured 6502 kernels](docs/ARITHMETIC.md)
- [Read-only C64 RAM audit and provisional allocations](docs/RAM_AUDIT.md)
- [Canonical optimal-set host model](docs/CANONICAL_MODEL.md)
- [Whole-integer direct-conversion experiments and rejected candidates](docs/INTEGER_MODEL.md)
- [Accepted canonical whole-integer reference and range contract](docs/CANONICAL_INTEGER.md)
- [Configurable smaller expert-bank experiments](docs/FLEXIBLE_MOE.md)
- [Exact local constant folding: storage versus computation](docs/LOCAL_FUSION.md)
- [Dataset audit](results/dataset-audit.json)
- [Symmetry audit](results/symmetry-audit.json)

## Setup and verify

Python 3.11 or later:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python scripts/prepare_dataset.py
.venv/bin/python scripts/audit_symmetry.py
.venv/bin/python -m pytest tests/test_policy.py tests/test_dataset.py tests/test_symmetry.py
```

For assembled kernel tests, install 64tass 1.60.3243 or run the project-local
bootstrap on an apt/dpkg-deb host (no sudo):

```sh
sh scripts/bootstrap_64tass.sh
.venv/bin/python -m pytest -q
.venv/bin/python scripts/benchmark_kernels.py
.venv/bin/python scripts/benchmark_int16_kernel.py
```

The tests and benchmarks use the explicit `TASS64` environment variable, a PATH
assembler, or the ignored project-local bootstrap. They do not require another
model repository to be installed beside Falken-9. The optional historical RAM
audit separately requires a read-only CP64 checkout and its generated maps.

Choose the appropriate PyTorch CPU/CUDA wheel for your training host. Training may use CUDA; deployment targets the C64, not CUDA execution. The dataset preparation/audit tools use only the Python standard library. `--offline` verifies already-downloaded data without network access.

The primary corpus contains 294,778 legal nonterminal histories and 4,520 unique nonterminal boards. All histories reaching the same board have consistent labels. Dihedral canonicalization reduces those nonterminal boards to 627 representatives; preserving the complete optimal move set and restoring original-coordinate tie order is essential. This is an input/label audit, not an accepted neural policy.

The target gate is exact deterministic legal moves under tie order `ebdfhcgia`, evaluated over the complete supported domain using the actual exported arithmetic. Matching host training accuracy alone does not establish packed integer or assembled C64 correctness.

Downloaded data, checkpoints, build products and D64 images are Git-ignored. Reproducible code and concise evidence summaries are tracked. Apache-2.0 applies to project material under the repository license; upstream dataset provenance is retained.
