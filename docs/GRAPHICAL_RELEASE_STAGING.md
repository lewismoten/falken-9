# Local graphical release staging

This is preparation for the intentionally spelled Hub target
`lewismoten/falcon-9`, project **Falken-9**. No remote write, credentials or Hub
client are involved. Stage only a final accepted graphical candidate; synthetic
packaging test fixtures are not acceptance evidence.

## Required inputs

- A dedicated candidate directory with exactly one `*.prg`, one `*.d64`, and
  `build.json` produced by the graphical builder. It must preserve the frozen
  model and core digests in `docs/DEPLOYMENT_PLAN.md`.
- The accepted 5,195-byte `model.f9j` supplied explicitly with `--model`.
- An evidence JSON with top-level `status: "passed"` and
  `artifact.prg_sha256`, `artifact.d64_sha256` binding the exact candidate.
  Include actual lifecycle, graphics, ROM, browser and numerical proof scopes
  as additional fields. This adapter format does not invent or rerun gates.
- Actual final PNG screenshots, each with filename, SHA-256 and caption bound
  in metadata. The first is foregrounded in the model card. The stager checks
  identity and PNG signature, not whether its contents depict the claimed game.
- A metadata JSON containing `release_id`, exact 40-character `source_revision`,
  and an ordered `screenshots` list. Add `controls`, `browser_limitations`,
  artwork acknowledgments and any other candidate-specific information; it is
  preserved as `release-metadata.json`. Do not put secrets or host identities
  in metadata or free-text evidence. Absolute path-valued strings in build and
  evidence JSON are redacted with original input digests retained.

Metadata shape (substitute measured values; these are schema placeholders):

```json
{
  "release_id": "003-graphical",
  "source_revision": "<exact revision of integrated source>",
  "screenshots": [
    {"name": "final-game.png", "sha256": "<digest of actual capture>",
     "caption": "<exact scope of this emulator capture>"}
  ],
  "controls": {"moves": "1-9", "other_keys": "<verified controls>"},
  "browser_limitations": "<actual format-specific acceptance boundary>"
}
```

The integrated tree must contain `scripts/build_graphical_app.py` with
`build(output=...)`, `scripts/compile_graphics.py`, and `assets/game-art/`.
They are intentionally not substituted by numeric code when absent. The
returned build structure must expose `prg_path` and `core.image_sha256` as in
`build_app.build`.

## Exact staging inventory

- Root accepted `model.f9j`, descriptively named graphical PRG and D64. Manifest
  binds the public downloads to original numbered candidate names/digests.
- Generated model card, deployment guide, candidate metadata, root LICENSE,
  optional existing root NOTICE/THIRD_PARTY.md, requirements and checksum files.
- `validation/candidate.json` and `validation/build.json` (path-sanitized).
- Supplied screenshot files only, under `assets/screenshots/`.
- The existing three `assets/model-v1.0.0-tensor-workflow.{png,svg,json}` files.
- Existing `inspection/{falken9-model-v1.0.0.onnx,manifest.json,validation.json}`;
  all four explicitly named native Netron render/provenance files under
  `artifacts/inspection/netron/`. No research artifact directory is copied.
- One expanded `source/` tree: graphical build/runtime/compiler scripts and
  recursively resolved local Python imports; bootstrap script; all `.asm` and
  `.inc` inputs under `src/{runtime,app}`; graphics source files under
  `assets/game-art` restricted to `.png`, `.json`, `.md`, `.txt`, `.map`, `.inc`,
  LICENSE and NOTICE. This dynamic narrow art allowlist accommodates the final
  compiler's input set without mirroring unrelated repository content.
- Original standalone tensor renderer at `source/scripts/render_tensor_workflow.py`,
  plus a root `reproduce.py` that loads the staged packet directly.

Excluded: checkpoints, ignored model artifact paths, dataset copies, training,
research matrices, test trees, raw logs, generated tensor PRGs/tables, ROMs,
installed environments, Git metadata, duplicate source archives and upload
instructions. The ZIP is the single transport wrapper, outside the upload root.

The minimal build's only Python third-party dependency is pinned
`Pillow==13.0.0`; local imports with additional unpinned packages are rejected.
64tass is checked at V1.60.3243. Existing bootstrap pins the apt package
`1.60.3243-1build1`, checks its version, and needs apt/dpkg-deb/network availability.
No assembler binary or font is redistributed.

## Stage and prove the final candidate

Run from the integrated repository, with real inputs:

```sh
python scripts/stage_graphical_release.py \
  --candidate /path/to/frozen-numbered-candidate \
  --model /path/to/accepted/model.f9j \
  --evidence /path/to/final-evidence.json \
  --metadata /path/to/release-metadata.json \
  --screenshot /path/to/final-game.png \
  --output distribution/huggingface/upload \
  --archive distribution/huggingface/falken-9-c64-e4-k2-q11-w16-a32-graphical.zip
```

Outputs must be absent. The stager validates frozen model/core identities,
embedded model bytes, canonical single-file D64 reconstruction, evidence and
screenshot hash bindings, ONNX/tensor/Netron lineage, every shipped checksum,
local Markdown links and extracted ZIP bytes. It does **not** silently claim a
clean final rebuild: execute it explicitly from both independent delivered trees:

```sh
cd distribution/huggingface/upload
TASS64=/path/to/64tass python reproduce.py --output ../rebuilt-expanded
python reproduce.py --verify-only
cd ..
python -m zipfile -e falken-9-c64-e4-k2-q11-w16-a32-graphical.zip extracted
cd extracted
TASS64=/path/to/64tass python reproduce.py --output ../rebuilt-extracted
```

Use an isolated Python environment with `requirements-build.txt` installed.
The generated deployment guide gives the assembler bootstrap command, performed
outside the checksummed upload tree. Rebuild reports stay outside that tree.
The reproducer injects root `model.f9j` into `scripts.build_runtime` **before**
importing the graphical builder, so captured `FOUR_MODEL` imports use the staged
packet. `build_runtime` parses packet descriptors and copies original resident
bytes; it needs neither PyTorch nor the original training/export closure.

D64 construction is independent of `build_app.package_disk`'s numeric naming,
Git-ignore assertion and live-game gate. It does not bypass candidate acceptance:
staging requires hash-bound passed evidence. It recreates the complete standard
single-file disk from rebuilt PRG bytes plus filename/disk-name/ID metadata,
then compares every byte against the accepted candidate. Noncanonical layouts
or hidden nonzero unused sectors are rejected, not silently re-encoded.

The exact ONNX and Netron files are immutable **inspection payloads**, not inputs
to the disk build. Full ONNX regeneration/627-board validation is deliberately
not advertised by the minimal build: the development exporter imports PyTorch,
ONNX, NumPy, an oracle test and dataset-loading/training modules. Those are not
needed to rebuild C64 code and are not included as an unused research closure.
The optional tensor renderer is executable via
`python reproduce.py --render-tensors ../tensor-workflow`; DejaVu Sans is required
at the font path recorded in its JSON. Rendering can vary with the font/stack;
the stager preserves existing PNG/SVG bytes and their source lineage unchanged.

Keep upload directions and suggested commit text beside the upload root and
outside its ZIP. Extract the ZIP and upload its **contents**, not an enclosing
folder or the ZIP alone. Publication is still an explicit future user action.

## Focused tests

```sh
F9_RELEASE_TEST_MODEL=/path/to/accepted/model.f9j \
TASS64=/path/to/64tass \
python -m unittest discover -s tests -p test_graphical_release.py -v
```

Tests use the actual accepted model and actual frozen-core assembler build, plus
an explicitly synthetic application fixture. They rebuild expanded and extracted
packages byte-for-byte, execute the staged tensor workflow, and test identity,
checksum, local-link, import-closure, symlink and hidden-disk-data rejection.
This proves the packaging pipeline, not final graphical gameplay acceptance.
