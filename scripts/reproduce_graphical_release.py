#!/usr/bin/env python3
"""Rebuild a staged Falken-9 graphical release without training artifacts."""
from pathlib import Path


def geometry():
    counts = [0] + [21]*17 + [19]*7 + [18]*6 + [17]*5
    offsets = {}
    for track in range(1, 36):
        for sector in range(counts[track]):
            offsets[track, sector] = len(offsets)*256
    return counts, offsets


def make_disk(prg, recipe):
    """Canonical single-file D64; no emulator, ROM, Git or template required."""
    counts, offsets = geometry()
    order = [17,19,16,20,15,21,14,22,13,23,12,24,11,25,10,26,9,27,8,28,7,29,6,30,5,31,4,32,3,33,2,34,1,35]
    available = [(t, s) for t in order for s in range(counts[t])]
    chunks = [prg[i:i+254] for i in range(0, len(prg), 254)]
    if not chunks or len(chunks) > len(available):
        raise ValueError('PRG does not fit single-file disk')
    disk = bytearray(174848)
    chain = available[:len(chunks)]
    used = {(18, 0), (18, 1), *chain}
    for i, chunk in enumerate(chunks):
        at = offsets[chain[i]]
        disk[at:at+2] = bytes(chain[i+1] if i+1 < len(chain) else (0, len(chunk)+1))
        disk[at+2:at+2+len(chunk)] = chunk
    directory = offsets[18, 1]
    disk[directory:directory+2] = bytes([0, 255])
    entry = directory+2
    disk[entry:entry+3] = bytes([0x82, *chain[0]])
    bam = offsets[18, 0]
    for key, size, at in [('file_name', 16, entry+3), ('disk_name', 16, bam+0x90), ('disk_id', 11, bam+0xa0)]:
        value = bytes.fromhex(recipe[key])
        if len(value) != size:
            raise ValueError(f'invalid {key}')
        disk[at:at+size] = value
    disk[entry+28:entry+30] = len(chain).to_bytes(2, 'little')
    disk[bam:bam+4] = bytes([18, 1, 0x41, 0])
    for track in range(1, 36):
        at = bam+4*track
        for sector in range(counts[track]):
            if (track, sector) not in used:
                disk[at] += 1
                disk[at+1+sector//8] |= 1 << (sector % 8)
    return bytes(disk)


def disk_recipe(disk, prg):
    """Accept only an exactly reconstructable disk, including unused sectors."""
    _, offsets = geometry()
    bam, entry = offsets[18, 0], offsets[18, 1]+2
    recipe = dict(file_name=disk[entry+3:entry+19].hex(),
                  disk_name=disk[bam+0x90:bam+0xa0].hex(),
                  disk_id=disk[bam+0xa0:bam+0xab].hex())
    if make_disk(prg, recipe) != disk:
        raise ValueError('candidate disk is not the canonical single-file D64')
    return recipe


MODEL_SHA = 'fe180f8a931f9d92d8aa39da337bc819d0dbe4e6d971edcba00324fbc18a91c1'
CORE_SHA = '838aa62a854aa58bd603c7525b52dc67c4c4b01ea0f50f58982475959ec61961'


def sha(data):
    import hashlib
    return hashlib.sha256(data).hexdigest()


def check_markdown_links(root):
    import re
    from urllib.parse import unquote, urlsplit
    root = Path(root).resolve()
    for page in root.rglob('*.md'):
        for target in re.findall(r'\]\(([^\s)]+)\)', page.read_text()):
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            path = (page.parent/unquote(parsed.path)).resolve()
            if not path.is_relative_to(root) or not path.is_file():
                raise ValueError(f'broken or unsafe local link: {page.name}: {target}')


def verify(root):
    """Verify exact inventory; SHA256SUMS excludes only itself."""
    import json
    root = Path(root).resolve()
    expected = {}
    for line in (root/'SHA256SUMS').read_text().splitlines():
        digest, name = line.split('  ', 1)
        rel = Path(name)
        if rel.is_absolute() or '..' in rel.parts or name in expected:
            raise ValueError('unsafe or duplicate checksum path')
        expected[name] = digest
    actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p != root/'SHA256SUMS'}
    if actual != set(expected):
        raise ValueError('checksum inventory mismatch')
    for name, digest in expected.items():
        path = root/name
        if any(p.is_symlink() for p in [path, *path.parents]):
            raise ValueError('symlink in release')
        if sha(path.read_bytes()) != digest:
            raise ValueError(f'checksum mismatch: {name}')
    manifest = json.loads((root/'release-manifest.json').read_text())
    if sha((root/'model.f9j').read_bytes()) != MODEL_SHA:
        raise ValueError('unpinned model')
    for row in manifest['files']:
        path = root/row['path']
        if path.stat().st_size != row['bytes'] or sha(path.read_bytes()) != row['sha256']:
            raise ValueError(f'manifest mismatch: {row["path"]}')
    check_markdown_links(root)
    return manifest


def reproduce(root, output, assembler=None):
    """Use the staged packet directly; build products stay outside upload tree."""
    import importlib
    import json
    import os
    import re
    import shutil
    import subprocess
    import sys
    root, output = Path(root).resolve(), Path(output).resolve()
    manifest = verify(root)
    if output == root or output.is_relative_to(root) or output.exists():
        raise ValueError('rebuild output must be new and outside upload tree')
    executable = assembler or os.environ.get('TASS64') or shutil.which('64tass')
    if not executable:
        executable = str(root/'source/build/tools/64tass/usr/bin/64tass')
    version = subprocess.run([executable, '--version'], check=True, capture_output=True, text=True).stdout
    if not re.search(r'\bV1\.60\.3243\b', version):
        raise ValueError('expected 64tass V1.60.3243')
    os.environ['TASS64'] = str(Path(executable).resolve())
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(root/'source'))
    runtime = importlib.import_module('scripts.build_runtime')
    setattr(runtime, 'FOUR_MODEL', root/'model.f9j')
    setattr(runtime, 'MODEL', root/'model.f9j')
    builder = importlib.import_module('scripts.build_graphical_app')
    built = builder.build(output=output/'build')
    raw = Path(built['prg_path']).read_bytes()
    if sha(raw) != manifest['prg']['sha256']:
        raise ValueError('rebuilt PRG differs from accepted candidate')
    packet = (root/'model.f9j').read_bytes()
    at = 2+0x4000-int.from_bytes(raw[:2], 'little')
    if raw[at:at+len(packet)] != packet:
        raise ValueError('rebuilt PRG does not embed the staged model')
    if built['core']['image_sha256'] != CORE_SHA:
        raise ValueError('rebuilt core differs from frozen core')
    disk = make_disk(raw, manifest['disk']['recipe'])
    if sha(disk) != manifest['disk']['sha256']:
        raise ValueError('rebuilt D64 differs from accepted candidate')
    (output/manifest['prg']['path']).write_bytes(raw)
    (output/manifest['disk']['path']).write_bytes(disk)
    report = dict(status='passed', scope='byte-exact rebuild, not new emulator or hardware acceptance',
                  model_sha256=MODEL_SHA, prg_sha256=sha(raw), d64_sha256=sha(disk),
                  core_image_sha256=built['core']['image_sha256'], assembler=version.strip())
    (output/'rebuild-verification.json').write_text(json.dumps(report, indent=2)+'\n')
    verify(root)
    return report


def main():
    import argparse
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--assembler')
    parser.add_argument('--verify-only', action='store_true')
    parser.add_argument('--render-tensors', type=Path, metavar='OUTPUT_STEM')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    if args.render_tensors:
        import importlib
        import sys
        verify(root)
        if args.render_tensors.resolve().is_relative_to(root):
            parser.error('tensor output must be outside upload tree')
        sys.dont_write_bytecode = True
        sys.path.insert(0, str(root/'source'))
        renderer = importlib.import_module('scripts.render_tensor_workflow')
        setattr(renderer, 'ROOT', root)
        result = renderer.render(root/'model.f9j', args.render_tensors)
        verify(root)
        print(json.dumps(dict(source=result['source'], outputs=result['outputs']), indent=2))
    elif args.verify_only:
        verify(root)
        print('All release checksums verified.')
    elif args.output is None:
        parser.error('--output outside the upload tree is required for a rebuild')
    else:
        print(json.dumps(reproduce(root, args.output, args.assembler), indent=2))


if __name__ == '__main__':
    main()
