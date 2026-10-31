#!/usr/bin/env python3
"""Prepare a local-only, allowlisted graphical Falken-9 release."""
import ast
from pathlib import Path
import sys
import argparse
import hashlib
import json
import re
import shutil
import tempfile
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reproduce_graphical_release import CORE_SHA, MODEL_SHA, disk_recipe, verify

PUBLIC_STEM = 'falken-9-c64-e4-k2-q11-w16-a32-graphical'
FIXED = [
    'LICENSE',
    'inspection/falken9-model-v1.0.0.onnx', 'inspection/manifest.json', 'inspection/validation.json',
    'artifacts/inspection/netron/falken9-model-v1.0.0.png',
    'artifacts/inspection/netron/falken9-model-v1.0.0.svg',
    'artifacts/inspection/netron/netron-interface.png', 'artifacts/inspection/netron/provenance.json',
    'assets/model-v1.0.0-tensor-workflow.png', 'assets/model-v1.0.0-tensor-workflow.svg',
    'assets/model-v1.0.0-tensor-workflow.json',
]

ROOT = Path(__file__).resolve().parents[1]
ART_SUFFIXES = {'.png', '.json', '.md', '.txt', '.map', '.inc'}


def safe_source(root, name):
    root = Path(root).resolve()
    path = root/name
    if path.is_absolute() and not path.is_relative_to(root):
        raise ValueError(f'source outside root: {name}')
    if '..' in Path(name).parts or any(p.is_symlink() for p in [path, *path.parents] if p != root.parent):
        raise ValueError(f'unsafe path or symlink: {name}')
    if not path.is_file():
        raise ValueError(f'missing release dependency: {name}')
    return path


def source_inventory(root):
    """Exact Python import closure plus a narrow assembly/art input allowlist."""
    root = Path(root).resolve()
    pending = ['scripts/build_graphical_app.py', 'scripts/build_runtime.py', 'scripts/compile_graphics.py']
    found = {'scripts/bootstrap_64tass.sh'}
    while pending:
        name = pending.pop()
        if name in found:
            continue
        path = safe_source(root, name)
        found.add(name)
        for node in ast.walk(ast.parse(path.read_text())):
            imports = []
            if isinstance(node, ast.Import):
                imports = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    raise ValueError(f'relative Python imports need explicit packaging: {name}')
                imports = [node.module or '']
                imports += [f'{node.module}.{a.name}' for a in node.names]
            for imp in imports:
                if imp.split('.')[0] in {'scripts', 'falken9'}:
                    candidate = imp.replace('.', '/')+'.py'
                    if (root/candidate).is_file():
                        pending.append(candidate)
                    elif not (root/imp.replace('.', '/')).is_dir() and imp == imports[0]:
                        raise ValueError(f'missing local module {imp}')
                elif imp.split('.')[0] not in sys.stdlib_module_names | {'PIL'}:
                    raise ValueError(f'unpinned build dependency {imp} in {name}')
    for directory in ('src/runtime', 'src/app'):
        found.update(str(p.relative_to(root)) for p in (root/directory).rglob('*')
                     if p.is_file() and p.suffix in {'.asm', '.inc'})
    art = root/'assets/game-art'
    found.update(str(p.relative_to(root)) for p in art.rglob('*')
                 if p.is_file() and (p.suffix in ART_SUFFIXES or p.name in {'LICENSE', 'NOTICE'}))
    if not any(n.startswith('assets/game-art/') and n.endswith('.png') for n in found):
        raise ValueError('missing graphical PNG source assets')
    for name in found:
        safe_source(root, name)
    return sorted(found)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def record(path, name):
    raw = Path(path).read_bytes()
    return dict(path=name, bytes=len(raw), sha256=digest(raw))


def sanitized(value):
    """Keep report content, remove machine-specific absolute path values."""
    if isinstance(value, dict):
        return {k: sanitized(v) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitized(v) for v in value]
    if isinstance(value, str) and value.startswith('/'):
        return '[local-path]/'+Path(value).name
    return value


def stage(*, candidate, model, evidence, screenshots, output, archive, metadata, source_root=ROOT):
    candidate, model, evidence = Path(candidate).resolve(), Path(model).resolve(), Path(evidence).resolve()
    output, archive, source_root = Path(output).resolve(), Path(archive).resolve(), Path(source_root).resolve()
    if output.exists() or archive.exists():
        raise ValueError('output and archive must not already exist')
    if archive.is_relative_to(output) or output.is_relative_to(candidate) or output == source_root:
        raise ValueError('upload, archive, candidate and source paths must not overlap')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', metadata.get('release_id', '')):
        raise ValueError('release_id must be a safe filename token')
    if not re.fullmatch(r'[0-9a-f]{40}', metadata.get('source_revision', '')):
        raise ValueError('source_revision must be an exact Git revision')
    prgs, disks = sorted(candidate.glob('*.prg')), sorted(candidate.glob('*.d64'))
    if len(prgs) != 1 or len(disks) != 1:
        raise ValueError('candidate must contain exactly one PRG and D64')
    prg, disk, packet = prgs[0].read_bytes(), disks[0].read_bytes(), model.read_bytes()
    if len(packet) != 5195 or digest(packet) != MODEL_SHA:
        raise ValueError('unpinned accepted model')
    build = json.loads((candidate/'build.json').read_text())
    if build.get('prg_sha256') != digest(prg) or build['core']['model_sha256'] != MODEL_SHA or build['core']['image_sha256'] != CORE_SHA:
        raise ValueError('candidate build identity differs from frozen contract')
    at = 2+0x4000-int.from_bytes(prg[:2], 'little')
    if prg[at:at+len(packet)] != packet:
        raise ValueError('candidate PRG does not embed supplied model at $4000')
    recipe = disk_recipe(disk, prg)
    report = json.loads(evidence.read_text())
    if report.get('status') != 'passed' or report.get('artifact', {}).get('prg_sha256') != digest(prg) or report.get('artifact', {}).get('d64_sha256') != digest(disk):
        raise ValueError('evidence must report passed and bind exact PRG/D64 hashes')
    shots = [Path(p) for p in screenshots]
    descriptions = metadata.get('screenshots', [])
    if not shots or len(shots) != len(descriptions) or len({p.name for p in shots}) != len(shots):
        raise ValueError('each screenshot needs unique bound metadata')
    for shot, desc in zip(shots, descriptions):
        if shot.name != desc.get('name') or digest(shot.read_bytes()) != desc.get('sha256') or not desc.get('caption'):
            raise ValueError('screenshot metadata must bind filename, SHA256 and caption')
        if not shot.read_bytes().startswith(b'\x89PNG\r\n\x1a\n') or shot.suffix != '.png':
            raise ValueError('screenshots must be actual PNG inputs')
    sources = source_inventory(source_root)
    for name in FIXED + ['scripts/render_tensor_workflow.py', 'scripts/reproduce_graphical_release.py']:
        safe_source(source_root, name)
    graph = json.loads((source_root/'inspection/manifest.json').read_text())
    if graph['source_packet']['sha256'] != MODEL_SHA or digest((source_root/graph['onnx']['path']).read_bytes()) != graph['onnx']['sha256']:
        raise ValueError('inspection graph lineage mismatch')
    netron = json.loads((source_root/'artifacts/inspection/netron/provenance.json').read_text())
    if netron['source_onnx_sha256'] != graph['onnx']['sha256']:
        raise ValueError('Netron source graph mismatch')
    for row in netron['files']:
        p = safe_source(source_root, row['path'])
        if digest(p.read_bytes()) != row['sha256'] or p.stat().st_size != row['bytes']:
            raise ValueError('Netron rendering mismatch')
    tensors = json.loads((source_root/'assets/model-v1.0.0-tensor-workflow.json').read_text())
    if tensors['source']['sha256'] != MODEL_SHA:
        raise ValueError('tensor workflow model mismatch')
    for ext, row in tensors['outputs'].items():
        if digest((source_root/f'assets/model-v1.0.0-tensor-workflow.{ext}').read_bytes()) != row['sha256']:
            raise ValueError('tensor workflow rendering mismatch')
    output.parent.mkdir(parents=True, exist_ok=True)
    archive.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='f9-stage-', dir=output.parent) as temp:
        tree = Path(temp)/'upload'
        tree.mkdir()
        def put(name, raw):
            path = tree/name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        def put_json(name, obj):
            put(name, (json.dumps(obj, indent=2, sort_keys=True)+'\n').encode())
        for name in FIXED:
            put(name, (source_root/name).read_bytes())
        for name in ('NOTICE', 'THIRD_PARTY.md'):
            if (source_root/name).is_file():
                put(name, safe_source(source_root, name).read_bytes())
        for name in sources + ['scripts/render_tensor_workflow.py']:
            put('source/'+name, (source_root/name).read_bytes())
        put('reproduce.py', (source_root/'scripts/reproduce_graphical_release.py').read_bytes())
        put('model.f9j', packet)
        put(PUBLIC_STEM+'.prg', prg)
        put(PUBLIC_STEM+'.d64', disk)
        put_json('validation/candidate.json', sanitized(report))
        put_json('validation/build.json', sanitized(build))
        put_json('release-metadata.json', metadata)
        for shot in shots:
            put('assets/screenshots/'+shot.name, shot.read_bytes())
        put('requirements-build.txt', b'# Python 3.11+; assembler: 64tass V1.60.3243\nPillow==13.0.0\n')
        put('.gitignore', b'__pycache__/\n*.pyc\n.venv/\n')
        main_shot = descriptions[0]
        readme = f'''---
license: apache-2.0
library_name: custom
pipeline_tag: other
tags:
- commodore-64
- tic-tac-toe
- custom-integer-runtime
---
# Falken-9

Runnable graphical Commodore 64 neural tic-tac-toe. Download the
[game disk]({PUBLIC_STEM}.d64) or [PRG]({PUBLIC_STEM}.prg).

**Emulator-tested only.** Physical C64/1541 compatibility and performance are
unverified. Acceptance scope is recorded in [candidate evidence](validation/candidate.json);
this package does not infer browser acceptance from desktop emulator tests.

![{main_shot['caption']}](assets/screenshots/{main_shot['name']})

Compact custom F9J2 integer model: 5,195 bytes, four learned experts with two
active, Q11/W16/A32. Not GGUF, Transformers, or hosted inference. The original
model-v1.0.0 identity is preserved; this is a separate application release.

[Rebuild and controls](DEPLOYMENT.md) · [Exact inventory](release-manifest.json) ·
[License](LICENSE) · [Decoded tensors](assets/model-v1.0.0-tensor-workflow.svg)

[Exact-integer inspection ONNX](inspection/falken9-model-v1.0.0.onnx), not the C64
packet; history validation, inverse symmetry and policy selection are external.
[Validation](inspection/validation.json) and [native Netron view](artifacts/inspection/netron/falken9-model-v1.0.0.svg)
are preserved documentation evidence, not new release gameplay measurements.
'''
        put('README.md', readme.encode())
        guide = '''# Falken-9 graphical deployment

## Controls and acceptance

Title: `1` human/model, `2` two humans, `0` model/model. Return starts the
selected mode; cursor up/down changes selection. `I` opens model INFO; `Q`
returns to title. On the title, `Q` ends at a reset/reload screen, not BASIC.
Game: row-major `123 / 456 / 789`, `R` replay, `Q` title.

Wait for the ready/terminal status before the next key. Rendering and inference
are synchronous; cancellation/input during those protected intervals is not
supported. The changing decorative button subset indicates real-work activity,
not percentage progress. The dark-blue model/version badge is static.

Minimal test: title `1`, then human `5,2,4,9,7`, waiting each turn, gives
`OXO / XXO / XOX` and DRAW. Replay, then human `1,2,4` gives
`XXO / XO. / O..` and O WINS. Invalid `0` and occupied cells add no marks.
Title `2`, then `1,4,2,5,3`, waiting for redraws, gives X WINS.
Title `0` plays a complete neural-versus-neural game. Candidate-specific
browser and stock-ROM scopes remain distinct in the supplied evidence.

Board squares are row-major 1–9; wrapper result 0 means invalid/no result.
Internally occupancy is 0 empty / 1 X / 2 O; chronology uses letters a–i.
Original-coordinate tie order is `ebdfhcgia`. Canonicalization and inverse
symmetry restoration are outside the learned network. No stored move policy.
See `release-metadata.json` for candidate-specific controls, screenshot captions
and browser limitations, and `validation/candidate.json` for exact supplied gates.
Emulator-only evidence does not establish physical-machine/drive acceptance.

## Build from this upload tree

Python 3.11+ and 64tass V1.60.3243 are required. No ROMs, sibling repository,
training checkpoint, dataset, PyTorch, installed model package or Git is needed.
Install Pillow==13.0.0 using `requirements-build.txt`. Build products and the
assembler bootstrap must remain OUTSIDE the upload tree to preserve checksums:

```sh
python3 -m venv ../falken-build-env
../falken-build-env/bin/python -m pip install -r requirements-build.txt
mkdir -p ../falken-tools/scripts
cp source/scripts/bootstrap_64tass.sh ../falken-tools/scripts/
sh ../falken-tools/scripts/bootstrap_64tass.sh
TASS64="$(cd ../falken-tools && pwd)/build/tools/64tass/usr/bin/64tass" \\
  ../falken-build-env/bin/python reproduce.py --output ../falken-rebuilt
python3 reproduce.py --verify-only
```

The bootstrap uses apt/dpkg-deb and pins package 1.60.3243-1build1; elsewhere
install 64tass V1.60.3243 yourself and set TASS64. The reproducer checks its
reported version before building. Dependency installation/bootstrap may require
network access; the actual build consumes only this staged tree and assembler.
The published packet is injected into build_runtime before importing the
application builder. No ignored model path is read. The canonical D64 writer
recreates every sector from the newly assembled PRG and small disk-label recipe,
not a binary disk template. Exact PRG, D64, embedded packet and core digests must
match. The rebuild is not a replay of emulator lifecycle or exhaustive NN gates.

## Inspection and provenance

Artwork provenance: ChatGPT-assisted generation, with Lewis Moten's manual
GIMP cleanup/layout and editing. Original indexed PNG/JSON bytes are retained;
the application adds separate identity, INFO, control and activity overlays.
See NOTICE and source/assets/game-art/provenance.json. Source-compiler hashes
describe the original compilation; overlaid/compressed runtime derivatives
are reproducible from the application builder and bound by the final PRG hash.

ONNX/Netron exports are shipped unchanged with source/tensor manifests, render
provenance and validation. They are inspection-only; the minimal game rebuild
does not regenerate ONNX or drive Netron. Regeneration of the decoded tensor
workflow is optional: `python reproduce.py --render-tensors ../tensor-workflow`
loads the staged packet directly; run it from this package root.
It needs pinned Pillow plus DejaVu Sans at the font path recorded in the shipped
JSON. Render bytes also depend on the font and rendering stack; the game rebuild
does not depend on this system font. Documentation images are not model packets.

Dataset lineage: lewismoten/tic-tac-toe at revision
`6ea253e1fa7de4a61eedeab6bbd9d8117af1fcb7`, manifest SHA-256
`0258d03ac9a2fd5bbf590736f9758d982d5f179e7415a4ca771418b22b1f2777`.
The corpus is not needed to reproduce the disk. Existing numerical evidence
covers 627 canonical forwards and a composed 4,520-board wrapper proof, not
4,520 newly executed neural forwards. See source and asset provenance records
for attribution; existing first-party Apache-2.0 and third-party exceptions remain.

SHA256SUMS detects changes, not authenticity: it is not a signature. It covers
every distributable file except itself. The manifest inventory excludes itself
and SHA256SUMS to avoid recursive hashes. Absolute path values in build/evidence
JSON are redacted; original input digests are retained in the release manifest.
'''
        put('DEPLOYMENT.md', guide.encode())
        files = [record(p, p.relative_to(tree).as_posix()) for p in sorted(tree.rglob('*')) if p.is_file()]
        manifest = dict(schema='falken9-graphical-release-v1', project='Falken-9', repo_id='lewismoten/falcon-9',
                        publication='local-only; no remote upload performed', release_id=metadata['release_id'],
                        source_revision=metadata['source_revision'], model_tag='model-v1.0.0',
                        model_revision='81252dc1137bf418159c19104d71317ba3063691',
                        model=record(tree/'model.f9j', 'model.f9j'),
                        prg=record(tree/(PUBLIC_STEM+'.prg'), PUBLIC_STEM+'.prg'),
                        disk={**record(tree/(PUBLIC_STEM+'.d64'), PUBLIC_STEM+'.d64'), 'recipe':recipe},
                        core_image_sha256=CORE_SHA, original_numbered_candidate=dict(prg_name=prgs[0].name, d64_name=disks[0].name),
                        original_input_sha256=dict(evidence=digest(evidence.read_bytes()), build=digest((candidate/'build.json').read_bytes())),
                        source_inventory=sources, files=files,
                        inventory_exclusions=['release-manifest.json', 'SHA256SUMS'])
        put_json('release-manifest.json', manifest)
        sums = ''.join(f'{digest(p.read_bytes())}  {p.relative_to(tree).as_posix()}\n' for p in sorted(tree.rglob('*')) if p.is_file())
        put('SHA256SUMS', sums.encode())
        verify(tree)
        # ZIP contains upload contents, not an extra parent or preparation notes.
        with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as z:
            for p in sorted(tree.rglob('*')):
                if p.is_file():
                    info = zipfile.ZipInfo(p.relative_to(tree).as_posix(), date_time=(2026, 1, 1, 0, 0, 0))
                    info.compress_type = zipfile.ZIP_DEFLATED
                    info.external_attr = 0o100644 << 16
                    z.writestr(info, p.read_bytes())
        with zipfile.ZipFile(archive) as z:
            extracted = Path(temp)/'extracted'
            z.extractall(extracted)
            verify(extracted)
            for p in tree.rglob('*'):
                if p.is_file() and p.read_bytes() != (extracted/p.relative_to(tree)).read_bytes():
                    raise ValueError('ZIP byte mismatch')
        shutil.copytree(tree, output)
    verify(output)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('candidate', 'model', 'evidence', 'output', 'archive', 'metadata'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--screenshot', type=Path, action='append', required=True)
    args = parser.parse_args()
    result = stage(candidate=args.candidate, model=args.model, evidence=args.evidence,
                   screenshots=args.screenshot, output=args.output, archive=args.archive,
                   metadata=json.loads(args.metadata.read_text()))
    print(json.dumps(dict(repo_id=result['repo_id'], disk=result['disk'], publication=result['publication']), indent=2))


if __name__ == '__main__':
    main()
