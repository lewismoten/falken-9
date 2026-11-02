#!/usr/bin/env python3
"""Stage a consumer-only Hub release; never upload or rewrite frozen releases."""
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit, unquote
import argparse
import hashlib
import json
import posixpath
import re

import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
GITHUB = 'https://github.com/lewismoten/falken-9/blob/main/'
MODEL_SHA256 = 'fe180f8a931f9d92d8aa39da337bc819d0dbe4e6d971edcba00324fbc18a91c1'
DESCRIPTOR = 'publication/application-release.json'
INDEXED_MANIFEST = 'assets/interpretability/publication-indexed/manifest.json'
PRESENTATION_INVENTORY = 'assets/interpretability/presentation-inventory.json'
GIT_RELEASE = 'releases/falken-9-v1.0.0/'
# Original descriptor paths remain immutable provenance. These reviewed Git
# mirrors let fresh checkouts stage the same accepted bytes without Hub access.
GIT_RELEASE_SOURCES = {
    'artifacts/flexible-integer/q11-w16-a32-early-interp/model.f9j': GIT_RELEASE+'model.f9j',
    'artifacts/app/011-graphical-final/falken-9-011-graphical.prg': GIT_RELEASE+'falken-9-c64.prg',
    'artifacts/app/011-graphical-final/falken-9-011-graphical.d64': GIT_RELEASE+'falken-9-c64.d64',
    'artifacts/operations/deployment/011/publication-final/summary.json': GIT_RELEASE+'application-validation.json',
}
DESTINATIONS = {'model': 'model.f9j', 'prg': 'c64/falken-9-c64.prg', 'd64': 'c64/falken-9-c64.d64'}
FORBIDDEN_SUFFIXES = {'.py', '.asm', '.inc', '.npz', '.onnx', '.pt', '.pth', '.bin', '.log', '.zip', '.sh', '.mjs', '.js', '.rom', '.ogg', '.sid'}
LINK = re.compile(r'\]\(([^)]+)\)')
IMAGE = re.compile(r'!\[[^\]]*\]\(([^)]+)\)')
PRIVATE = re.compile(r'/home/ai|https?://(?:localhost|127\.|10\.|192\.168\.|[^\s/]+\.ts\.net)|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|\b(?:ghp_[A-Za-z0-9]{24,}|sk-[A-Za-z0-9]{24,})')
CONVENTIONAL = re.compile(r'conventional(?:[- /]c64)?[- /]baseline|simplified conventional|artifacts/baseline|baselines/conditional-c64|conditional-tictactoe-|baseline-c64', re.I)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def record(path, relative):
    return {'path': relative, 'bytes': Path(path).stat().st_size, 'sha256': sha(path)}


def safe_relative(name):
    if not isinstance(name, str):
        raise ValueError('Publication path must be a string')
    p = PurePosixPath(name)
    if not name or p.is_absolute() or '..' in p.parts or '\\' in name or '?' in name or '#' in name or str(p) != name or name == '.':
        raise ValueError('Unsafe publication path: ' + name)
    return p


def source_file(root, name):
    safe_relative(name)
    path = root/name
    if not path.exists() and not path.is_symlink() and name in GIT_RELEASE_SOURCES:
        path = root/GIT_RELEASE_SOURCES[name]
    if not path.is_file() or not path.resolve().is_relative_to(root) or any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('Missing or symlink publication input: ' + name)
    return path


def checked_entry(root, entry, require_bytes=False):
    if not isinstance(entry, dict) or not re.fullmatch(r'[0-9a-f]{64}', entry.get('sha256', '')):
        raise ValueError('Invalid publication digest')
    path = source_file(root, entry.get('path'))
    if sha(path) != entry['sha256'] or ((require_bytes or 'bytes' in entry) and path.stat().st_size != entry.get('bytes')):
        raise ValueError('Publication input digest/size mismatch: ' + entry['path'])
    return path


def load_application_release(source_root):
    """Resolve accepted bytes at runtime, not from an obsolete numbered build."""
    root = Path(source_root).resolve()
    try:
        descriptor = json.loads(source_file(root, DESCRIPTOR).read_text())
    except (OSError, ValueError) as exc:
        raise ValueError('A verified ' + DESCRIPTOR + ' is required: ' + str(exc)) from exc
    if descriptor.get('schema') != 'falken9-publication-application-v1' or descriptor.get('revision') != '011' or descriptor.get('release_id') != 'falken-9-model-v1.0.0-app011':
        raise ValueError('Expected final graphical011 application descriptor')
    for kind in DESTINATIONS:
        checked_entry(root, descriptor[kind], require_bytes=True)
    if descriptor['model']['sha256'] != MODEL_SHA256:
        raise ValueError('Frozen model digest mismatch')
    shots = descriptor.get('screenshots', [])
    if len(shots) != 5 or len({s['path'] for s in shots}) != 5:
        raise ValueError('Exactly five distinct final application screenshots are required')
    for shot in shots:
        checked_entry(root, shot)
        if not shot['path'].endswith('.png') or shot.get('prg_sha256') != descriptor['prg']['sha256'] or shot.get('source_artifact') not in {descriptor['prg']['path'], descriptor['d64']['path']} or not shot.get('method'):
            raise ValueError('Screenshot executable provenance mismatch')
    for kind in ('screenshot_provenance', 'validation'):
        path = checked_entry(root, descriptor[kind])
        public_text(path.read_text())
        json.loads(path.read_text())
    verify_application_bytes(*(source_file(root, descriptor[k]['path']) for k in ('model', 'prg', 'd64')))
    return descriptor


def verify_application_bytes(model_path, prg_path, d64_path):
    packet = Path(model_path).read_bytes()
    prg = Path(prg_path).read_bytes()
    if len(packet) != 5195 or packet[:4] != b'F9J2' or sha(model_path) != MODEL_SHA256:
        raise ValueError('Wrong frozen custom model packet')
    offset = 2 + 0x4000 - int.from_bytes(prg[:2], 'little')
    if offset < 2 or prg[offset:offset+len(packet)] != packet:
        raise ValueError('PRG does not embed supplied frozen packet')
    from scripts.build_app import extract_disk
    try:
        extracted = extract_disk(d64_path)
    except (AssertionError, KeyError, IndexError) as exc:
        raise ValueError('Invalid D64') from exc
    if extracted != prg:
        raise ValueError('D64 does not contain exact accepted PRG')


def public_text(text):
    # Historical research paths are not consumer instructions or private metadata.
    text = re.sub(r'/home/ai/falken9-[A-Za-z0-9_-]+', 'ARCHIVE_ROOT', text)
    text = text.replace('/home/ai/falken-9', 'SOURCE_ROOT').replace('/home/ai/cp64', 'CP64_SOURCE_ROOT')
    for host in ('github.com/lewismoten/', 'huggingface.co/lewismoten/', 'lewismoten.github.io/'):
        text = text.replace(host+'falcon-9', host+'falken-9')
    if PRIVATE.search(text):
        raise ValueError('Private path, endpoint or credential pattern in public text')
    if CONVENTIONAL.search(text):
        raise ValueError('Abandoned conventional baseline material in consumer text')
    return text


def rewrite_markdown(text, source, destination, mapping):
    def replace(match):
        target = match.group(1)
        if target.startswith(('#', 'http://', 'https://', 'mailto:', 'data:')):
            return match.group(0)
        url = urlsplit(target)
        source_target = posixpath.normpath(posixpath.join(posixpath.dirname(source), unquote(url.path)))
        if source_target.startswith('../') or source_target.startswith('/'):
            raise ValueError('Markdown link escapes source root: ' + target)
        if source_target in mapping:
            name = posixpath.relpath(mapping[source_target], posixpath.dirname(destination) or '.')
        else:
            name = GITHUB + source_target
        return '](' + name + ('?' + url.query if url.query else '') + ('#' + url.fragment if url.fragment else '') + ')'
    return public_text(LINK.sub(replace, text))


def presentation_aliases(root):
    """Legacy SVG aliases; indexed_presentation supplies the PNG replacements."""
    root = Path(root).resolve()
    folder = root/'assets/interpretability/publication-dark'
    aliases = {}
    for svg in sorted(folder.glob('study-*/*.svg')):
        relative = svg.relative_to(folder)
        original = root/'docs/research'/relative
        for suffix in ('.png', '.svg'):
            source, derived = original.with_suffix(suffix), svg.with_suffix(suffix)
            if any(not p.is_file() or p.is_symlink() for p in (source, derived)):
                raise ValueError('Incomplete dark presentation pair: ' + str(relative))
            aliases[str(source.relative_to(root))] = str(derived.relative_to(root))
    return aliases


def indexed_presentation(source_root):
    """Only the 39 selected rasters and their zoomable SVG companions may ship."""
    root = Path(source_root).resolve()
    manifest = json.loads(source_file(root, INDEXED_MANIFEST).read_text())
    figures = manifest['figures']
    if manifest.get('complete') is not True or len(figures) != 39:
        raise ValueError('Expected 39 complete indexed report figures')
    mapping, aliases, inventory = {}, {}, []
    palette_counts = {(16, 4): 0, (32, 8): 0}
    for figure in figures:
        original, selected = figure['original'], figure['indexed']
        checked_entry(root, original, require_bytes=True)
        path = checked_entry(root, selected, require_bytes=True)
        if not selected['path'].startswith('assets/interpretability/publication-indexed/') or 'candidates' in PurePosixPath(selected['path']).parts or path.suffix != '.png':
            raise ValueError('Unselected/candidate presentation raster')
        pair = (selected['colors'], selected['bit_depth'])
        if pair not in palette_counts:
            raise ValueError('Unexpected indexed PNG palette')
        raw = path.read_bytes()
        if raw[:8] != b'\x89PNG\r\n\x1a\n' or raw[24:26] != bytes((selected['bit_depth'], 3)):
            raise ValueError('Selected PNG is not expected indexed bit depth')
        palette_counts[pair] += 1
        if selected['path'] in mapping:
            raise ValueError('Duplicate selected PNG')
        mapping[selected['path']] = selected['path']
        names = {original['path']}
        if '/publication-dark/' in original['path']:
            names.add('docs/research/'+original['path'].split('/publication-dark/')[1])
        elif original['path'].startswith('docs/research/'):
            names.add('assets/interpretability/publication-dark/'+original['path'].removeprefix('docs/research/'))
        companions = []
        for name in sorted(names):
            aliases[name] = selected['path']
            svg = str(PurePosixPath(name).with_suffix('.svg'))
            if (root/svg).is_file():
                source_file(root, svg)
                mapping[svg] = svg
                companions.append(record(root/svg, svg))
        inventory.append({'source': dict(original), 'indexed': dict(selected), 'svg_companions': companions})
    if palette_counts != {(16, 4): 35, (32, 8): 4}:
        raise ValueError('Expected 35 four-bit and four eight-bit indexed PNGs')
    # Preserve the original zoomable inspector without its duplicate full-color PNG.
    original_inspector = 'assets/interpretability/model-inspection/netron-original.svg'
    if (root/original_inspector).is_file():
        source_file(root, original_inspector)
        mapping[original_inspector] = original_inspector
    public_inventory = {'schema': 'falken9-public-presentation-v1', 'display_only': True,
        'scope': 'Palette-reduced display derivatives, not model data or replacement scientific evidence. Original evidence remains in GitHub.',
        'source_manifest': {'path': INDEXED_MANIFEST, 'sha256': sha(root/INDEXED_MANIFEST), 'shipped': False},
        'figures': inventory,
        'attention_display': {'figure': 'forward-attention1011', 'values': 81, 'arithmetic': 'actual Q15 attention values',
            'transform': 'square-root', 'scale': {'0': 'dark', '1': 'bright blue'},
            'source_artifact': 'baseline010.npz', 'source_sha256': 'ec81bed1e5bcb42b1cc78688e48106b457ae3ddd6302946b577d39ed00c1c317',
            'source_shipped': False, 'boundary': 'Display transformation only; the underlying scientific values are unchanged.'}}
    return mapping, aliases, public_inventory


def narrative_inventory(root):
    names = ['docs/MODEL_INTERPRETABILITY.md', 'docs/MODEL_RESEARCH.md', 'docs/research/study-007/COMMON-SUPPORT007.md']
    names += ['docs/research/study-%03d/REPORT%s.md' % (i, '' if i <= 5 else '%03d' % i) for i in range(3, 17)]
    return {name: name for name in names if (root/name).is_file()}


def stage_release(source_root, output):
    root, output = Path(source_root).resolve(), Path(output).resolve()
    if output.exists():
        raise ValueError('Publication output must not already exist')
    if output == root or root.is_relative_to(output):
        raise ValueError('Publication output overlaps source root')
    application = load_application_release(root)
    mapping = {application[k]['path']: v for k, v in DESTINATIONS.items()}
    mapping.update({'README.md': 'README.md', 'report.md': 'report.md', 'docs/C64_GAME.md': 'c64/README.md', 'LICENSE': 'LICENSE', 'NOTICE': 'NOTICE'})
    mapping.update(narrative_inventory(root))
    selected, aliases, presentation = indexed_presentation(root)
    mapping.update(selected)
    for shot in application['screenshots']:
        mapping[shot['path']] = shot['path']
    evidence = {}
    for kind in ('screenshot_provenance', 'validation'):
        target = 'provenance/application-'+kind.replace('_', '-')+'.json'
        mapping[application[kind]['path']] = target
        evidence[kind] = dict(record(source_file(root, application[kind]['path']), target), source_path=application[kind]['path'])
    rewrite_mapping = dict(mapping, **aliases)
    for original, mirror in GIT_RELEASE_SOURCES.items():
        if original in mapping:
            rewrite_mapping[mirror] = mapping[original]
    # The card is authored in its Hub-root layout, not repository-source layout.
    for destination in list(mapping.values()) + ['model.json', 'manifest.json', 'SHA256SUMS', PRESENTATION_INVENTORY]:
        rewrite_mapping.setdefault(destination, destination)
    rewrite_mapping['assets/interpretability/publication-dark/presentation.json'] = PRESENTATION_INVENTORY
    rewrite_mapping['assets/interpretability/model-inspection/provenance.json'] = PRESENTATION_INVENTORY
    rewrite_mapping[INDEXED_MANIFEST] = PRESENTATION_INVENTORY
    # Validate all planned inputs and public prose before creating output.
    payloads = {}
    for source, destination in sorted(mapping.items()):
        safe_relative(destination)
        src = source_file(root, 'publication/model-card.md' if source == 'README.md' else source)
        if src.suffix.lower() == '.md':
            # Card paths already use the public root, but still need indexed aliases.
            text = rewrite_markdown(src.read_text(), source, destination, rewrite_mapping)
            payloads[destination] = text.encode()
        elif source == 'NOTICE':
            text = src.read_text().replace('source/assets/game-art/provenance.json in the public upload package, or\nassets/game-art/provenance.json in the development repository.', 'assets/game-art/provenance.json in the GitHub development repository\n(https://github.com/lewismoten/falken-9).')
            payloads[destination] = public_text(text).encode()
        else:
            data = src.read_bytes()
            if src.suffix in ('.json', '.svg'):
                # Evidence is copied unchanged: never silently modify verified hashes.
                if PRIVATE.search(data.decode()):
                    raise ValueError('Private content in publication input: '+source)
            payloads[destination] = data
    figure_paths = IMAGE.findall(payloads['report.md'].decode())
    if len(figure_paths) != 39 or set(figure_paths) != {f['indexed']['path'] for f in presentation['figures']}:
        raise ValueError('All 39 report images must select the indexed manifest derivatives')
    model = {'schema': 'falken9-custom-model-v1', 'format': 'F9J2', 'artifact': 'model.f9j', 'bytes': 5195, 'sha256': MODEL_SHA256,
        'version': 'model-v1.0.0', 'source_model_commit': '81252dc1137bf418159c19104d71317ba3063691',
        'architecture': {'tokens': 9, 'width': 8, 'expert_hidden': 4, 'experts': 4, 'top_k': 2},
        'arithmetic': 'Q11/W16/A32; exact target integer contract',
        'outputs': 'Nine signed complete-optimal-set membership scores; nonnegative means approved before external legal masking',
        'external_contract': ['history validation', 'board canonicalization', 'full-set inverse restoration', 'legal masking', 'raw-coordinate deterministic ties'],
        'runtime': 'Custom Falken-9 runtime in GitHub source repository', 'not_supported': ['Transformers auto-loading', 'GGUF', 'Ollama', 'hosted Hub inference'],
        'source_repository': 'https://github.com/lewismoten/falken-9'}
    payloads['model.json'] = (json.dumps(model, indent=2)+'\n').encode()
    payloads[PRESENTATION_INVENTORY] = (json.dumps(presentation, indent=2)+'\n').encode()
    output.mkdir(parents=True)
    for destination, data in sorted(payloads.items()):
        dest = output/destination
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    paths = sorted(payloads)
    manifest = {'schema': 'falken9-consumer-release-v1', 'release_id': application['release_id'], 'application_revision': application['revision'],
        'publication': {'performed': False, 'target_repository': 'lewismoten/falken-9', 'purpose': 'Prepared consumer package; this manifest does not establish remote publication'},
        'application_descriptor': {'path': DESCRIPTOR, 'sha256': sha(root/DESCRIPTOR), 'shipped': False},
        'artifacts': {k: record(output/n, n) for k, n in DESTINATIONS.items()}, 'model': model,
        'report': {'path': 'report.md', 'inline_figures': 39, 'source_sha256': sha(root/'report.md'), 'staged_sha256': sha(output/'report.md'),
            'scope': 'Studies through016; historical scientific evidence and limitations retained; indexed display derivatives, links rebased, historical workstation paths removed'},
        'screenshots': [dict(record(output/e['path'], e['path']), caption=e['method'], method=e['method'], source_artifact=e['source_artifact'], prg_sha256=e['prg_sha256'], source_prg_sha256=e['prg_sha256']) for e in application['screenshots']],
        'provenance': evidence, 'presentation_inventory': PRESENTATION_INVENTORY,
        'source_repository': 'https://github.com/lewismoten/falken-9', 'game_title': 'Crystal Palace 9', 'model_identity': 'Falken-9',
        'excluded': ['conventional comparison program', 'test scripts', 'research probes and raw numeric fixtures', 'assembly/source code', 'art source planes', 'GitHub Pages launcher code', 'music preview (GitHub Pages only)', 'training/checkpoint files', 'ROMs/emulator binaries', 'private operator notes', 'palette candidates and contact sheets'],
        'files': [record(output/n, n) for n in paths]}
    (output/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    (output/'SHA256SUMS').write_text(''.join(sha(output/n)+'  '+n+'\n' for n in sorted(paths+['manifest.json'])))
    verify_package(output, root)
    return manifest


def verify_package(output, source_root=None):
    output = Path(output).resolve()
    application = load_application_release(ROOT if source_root is None else source_root)
    manifest = json.loads((output/'manifest.json').read_text())
    if manifest['release_id'] != application['release_id'] or manifest['application_revision'] != '011' or manifest['publication']['target_repository'] != 'lewismoten/falken-9':
        raise ValueError('Wrong release identity')
    inventory = {e['path']: e for e in manifest['files']}
    if len(inventory) != len(manifest['files']):
        raise ValueError('Duplicate inventory entry')
    all_paths = list(output.rglob('*'))
    if any(p.is_symlink() for p in all_paths):
        raise ValueError('Symlink package file')
    actual = {str(p.relative_to(output)) for p in all_paths if p.is_file()}
    if actual != set(inventory) | {'manifest.json', 'SHA256SUMS'}:
        raise ValueError('Unexpected or missing package file')
    selected, _, presentation = indexed_presentation(Path(source_root or ROOT))
    evidence_paths = {'provenance/application-screenshot-provenance.json', 'provenance/application-validation.json'}
    expected_files = (set(DESTINATIONS.values()) | {'README.md', 'report.md', 'c64/README.md', 'LICENSE', 'NOTICE', 'model.json', PRESENTATION_INVENTORY, 'manifest.json', 'SHA256SUMS'}
        | set(narrative_inventory(Path(source_root or ROOT))) | set(selected)
        | {s['path'] for s in application['screenshots']} | evidence_paths)
    if actual != expected_files:
        raise ValueError('Unexpected or missing approved consumer inventory file')
    for name, entry in inventory.items():
        safe_relative(name)
        p = output/name
        if p.suffix.lower() in FORBIDDEN_SUFFIXES or CONVENTIONAL.search(name) or 'candidates' in p.parts or p.name == 'contact-sheet.png':
            raise ValueError('Non-consumer file included: '+name)
        if p.stat().st_size != entry['bytes'] or sha(p) != entry['sha256']:
            raise ValueError('Inventory mismatch: '+name)
        if p.suffix.lower() in ('.md', '.json', '.svg') or p.name in ('NOTICE', 'LICENSE'):
            if PRIVATE.search(p.read_text()):
                raise ValueError('Private content: '+name)
        if p.suffix == '.png' and not p.read_bytes().startswith(b'\x89PNG\r\n\x1a\n'):
            raise ValueError('Invalid PNG')
        if p.suffix == '.md':
            public_text(p.read_text())
            for target in LINK.findall(p.read_text()):
                if target.startswith(('#', 'http://', 'https://', 'mailto:')):
                    continue
                resolved = (p.parent/unquote(urlsplit(target).path)).resolve()
                if not resolved.is_relative_to(output) or not resolved.is_file():
                    raise ValueError('Broken local link: '+name+' -> '+target)
    entries = {}
    for line in (output/'SHA256SUMS').read_text().splitlines():
        digest, name = line.split('  ', 1)
        safe_relative(name)
        if name in entries or sha(output/name) != digest:
            raise ValueError('Checksum mismatch: '+name)
        entries[name] = digest
    if set(entries) != actual-{'SHA256SUMS'}:
        raise ValueError('Incomplete checksums')
    for kind, name in DESTINATIONS.items():
        expected = application[kind]
        if record(output/name, name) != manifest['artifacts'][kind] or sha(output/name) != expected['sha256'] or (output/name).stat().st_size != expected['bytes']:
            raise ValueError('Frozen artifact mismatch')
    verify_application_bytes(*(output/DESTINATIONS[k] for k in ('model', 'prg', 'd64')))
    if manifest['application_descriptor']['sha256'] != sha(Path(source_root or ROOT)/DESCRIPTOR):
        raise ValueError('Application descriptor changed')
    shots = manifest['screenshots']
    if len(shots) != 5:
        raise ValueError('Screenshot count changed')
    for staged, accepted in zip(shots, application['screenshots']):
        expected = dict(record(output/accepted['path'], accepted['path']), caption=accepted['method'], method=accepted['method'], source_artifact=accepted['source_artifact'], prg_sha256=accepted['prg_sha256'], source_prg_sha256=accepted['prg_sha256'])
        if staged != expected or staged['sha256'] != accepted['sha256']:
            raise ValueError('Screenshot provenance mismatch')
    if set(manifest['provenance']) != {'screenshot_provenance', 'validation'}:
        raise ValueError('Missing required public provenance')
    for kind, evidence in manifest['provenance'].items():
        target = 'provenance/application-'+kind.replace('_', '-')+'.json'
        if evidence != dict(record(output/target, target), source_path=application[kind]['path']) or sha(output/target) != application[kind]['sha256']:
            raise ValueError('Public provenance mismatch')
    if json.loads((output/PRESENTATION_INVENTORY).read_text()) != presentation:
        raise ValueError('Presentation provenance mismatch')
    expected_png = {p for p in selected if p.endswith('.png')} | {s['path'] for s in shots}
    if {p for p in actual if p.endswith('.png')} != expected_png:
        raise ValueError('Unexpected/duplicate presentation PNG')
    for name in selected:
        if sha(output/name) != sha(Path(source_root or ROOT)/name):
            raise ValueError('Presentation asset mismatch')
    figure_paths = IMAGE.findall((output/'report.md').read_text())
    if manifest['report']['inline_figures'] != 39 or len(figure_paths) != 39 or set(figure_paths) != {f['indexed']['path'] for f in presentation['figures']}:
        raise ValueError('All 39 report images must select the indexed manifest derivatives')
    return {'passed': True, 'files': len(actual), 'checksums': len(entries), 'report_figures': len(figure_paths), 'artifacts': manifest['artifacts']}


def archive_release(output, archive, source_root=None):
    output, archive = Path(output).resolve(), Path(archive).resolve()
    if archive.exists() or archive.is_relative_to(output):
        raise ValueError('Archive must be new and outside upload tree')
    verify_package(output, source_root)
    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in sorted(output.rglob('*'), key=lambda p: str(p.relative_to(output))):
            if p.is_file():
                info = zipfile.ZipInfo(str(p.relative_to(output)), (1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                z.writestr(info, p.read_bytes(), compresslevel=9)
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:
            raise ValueError('Archive CRC failed')
        if set(z.namelist()) != {str(p.relative_to(output)) for p in output.rglob('*') if p.is_file()}:
            raise ValueError('Archive inventory mismatch')
        for name in z.namelist():
            if z.read(name) != (output/name).read_bytes():
                raise ValueError('Archive member mismatch')
    return record(archive, archive.name)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path)
    ap.add_argument('--archive', type=Path)
    ap.add_argument('--verify', type=Path)
    args = ap.parse_args()
    if args.verify:
        print(json.dumps(verify_package(args.verify), indent=2))
    else:
        if not args.output:
            ap.error('--output is required for staging')
        stage_release(ROOT, args.output)
        result = verify_package(args.output)
        if args.archive:
            result['archive'] = archive_release(args.output, args.archive)
        print(json.dumps(result, indent=2))
