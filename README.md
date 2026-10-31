# Falken-9

A new C64-first neural tic-tac-toe policy project. The goal is a compact, RAM-resident model with real attention, learned routing and mixture-of-experts execution—not a stored move table. Crystal-9's published original-model release is preserved separately.

## Model v1.0.0

The stable release uses the **5,195-byte four-expert integer model**, with two learned router-selected experts active per inference. The complete model stays in RAM during gameplay; there are no per-turn model-data disk loads.

![Falken-9 resident neural tic-tac-toe: a completed draw in the C64 emulator](assets/screenshots/falken9-model-v1.0.0-draw.png)

*Actual emulator screenshot supplied by Lewis Moten: a completed human-X/model-O draw. The image is preserved unchanged.*

**Emulator-tested only.** Physical C64/1541 compatibility and performance have not been verified.

The neural core passes all 627 canonical boards; the assembled symmetry/set-selection wrapper passes all 4,520 unique boards through a documented composed proof. The packaged PRG and true-drive D64 both complete draw/win/replay lifecycles under stock-ROM VICE. At the target browser, the PRG also passes complete matches, occupied-input recovery, terminal locking and replay. D64 browser autostart and its opening response pass, but later interaction remains unconfirmed because a host advertising iframe intercepted keyboard events. See [browser acceptance and its format-specific limits](docs/BROWSER_001.md).

Expert count and active top-k remain optimization variables for separate research, not a requirement to keep nine experts. The smaller 4,931-byte mixed-precision candidate passes host gates but is not assembled and is **not** the model-v1.0.0 deployment.

## Model inspection

### Decoded tensor workflow

[![Decoded Falken-9 tensor workflow: embeddings, full board attention, readout, learned routing and four experts](assets/model-v1.0.0-tensor-workflow.png)](assets/model-v1.0.0-tensor-workflow.svg)

Each heatmap cell is one decoded scalar parameter from the accepted model, not a bit or byte. All four expert banks are shown; only two router-selected experts execute per inference. Color intensity is normalized per source tensor and is not comparable across tensors. This is a documentation inspector, **not a reconstructable model-data PNG**.

[Workflow guide](docs/TENSOR_WORKFLOW.md) · [Zoomable SVG](assets/model-v1.0.0-tensor-workflow.svg) · [Tensor/geometry metadata](assets/model-v1.0.0-tensor-workflow.json)

### Executable ONNX graph

[Download the self-contained ONNX graph](inspection/falken9-model-v1.0.0.onnx) and open it in Netron. This is an **exact-integer inspection representation**, not the compact C64 deployment packet: ONNX Runtime matches the independent integer reference on all 627 canonical boards, with zero score or expert-route differences. History validation, symmetry restoration and final move selection remain outside the graph.

[![Native Netron rendering of the Falken-9 integer forward graph](artifacts/inspection/netron/falken9-model-v1.0.0.png)](artifacts/inspection/netron/falken9-model-v1.0.0.svg)

[Inspection guide](docs/INSPECTION_GRAPH.md) · [Zoomable Netron SVG](artifacts/inspection/netron/falken9-model-v1.0.0.svg) · [Source/tensor manifest](inspection/manifest.json) · [Validation](inspection/validation.json)

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
- [Four-expert whole-integer candidates and mixed-precision inventory](docs/FLEXIBLE_INTEGER.md)
- [Assembled resident attention-block proof and memory map](docs/TARGET_RUNTIME.md)
- [Resident playable application, build commands and exact test sequences](docs/APP.md)
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
