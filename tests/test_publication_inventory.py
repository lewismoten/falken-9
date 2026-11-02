"""Packaging-only regressions; fixture app bytes are NOT graphical011 acceptance."""
import json
import shutil
from pathlib import Path

import pytest
from scripts import prepare_publication as pub

ROOT = Path(__file__).resolve().parents[1]


def test_selected_indexed_inventory_rebases_original_and_dark_aliases():
    mapping, aliases, inventory = pub.indexed_presentation(ROOT)
    assert len(inventory['figures']) == 39
    assert len([p for p in mapping if p.endswith('.png')]) == 39
    assert all('/publication-indexed/' in p for p in mapping if p.endswith('.png'))
    assert not any('candidates' in p or 'contact-sheet' in p for p in mapping)
    source = 'docs/research/study-009/overview009.png'
    dark = 'assets/interpretability/publication-dark/study-009/overview009.png'
    selected = 'assets/interpretability/publication-indexed/study-009/overview009.png'
    assert aliases[source] == aliases[dark] == selected
    assert mapping[dark.replace('.png', '.svg')].endswith('.svg')
    assert 'candidates' not in json.dumps(inventory)
    attention = inventory['attention_display']
    assert attention['values'] == 81
    assert attention['transform'] == 'square-root'
    assert attention['source_sha256'] == 'ec81bed1e5bcb42b1cc78688e48106b457ae3ddd6302946b577d39ed00c1c317'


@pytest.fixture
def consumer_fixture(tmp_path):
    """Use old real executable bytes solely to exercise packaging mechanics."""
    root = tmp_path/'source'
    root.mkdir()
    def copy(source, destination=None):
        target = root/(destination or source)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/source, target)
        return target
    manifest = json.loads((ROOT/'assets/interpretability/publication-indexed/manifest.json').read_text())
    copy('assets/interpretability/publication-indexed/manifest.json')
    for figure in manifest['figures']:
        for entry in (figure['original'], figure['indexed']):
            copy(entry['path'])
        stem = Path(figure['original']['path'])
        svg = stem.with_suffix('.svg')
        if (ROOT/svg).is_file():
            copy(str(svg))
        if '/publication-dark/' in str(stem):
            original = 'docs/research/'+str(stem).split('/publication-dark/')[1]
            for ext in ('.png', '.svg'):
                if (ROOT/Path(original).with_suffix(ext)).is_file():
                    copy(str(Path(original).with_suffix(ext)))
    for name in ('LICENSE', 'NOTICE'):
        copy(name)
    report = '\n'.join('![Figure]('+f['original']['path']+')' for f in manifest['figures'])
    (root/'report.md').write_text(report)
    (root/'README.md').write_text('Source README')
    (root/'docs').mkdir(exist_ok=True)
    (root/'docs/C64_GAME.md').write_text('# Emulator-tested game\n')
    for name in ('MODEL_INTERPRETABILITY.md', 'MODEL_RESEARCH.md'):
        (root/'docs'/name).write_text('# Narrative\n')
    descriptor = {'schema': 'falken9-publication-application-v1', 'revision': '011',
                  'release_id': 'falken-9-model-v1.0.0-app011', 'screenshots': []}
    sources = {'model': 'artifacts/flexible-integer/q11-w16-a32-early-interp/model.f9j',
               'prg': 'artifacts/app/010-graphical/falken9-010-graphical.prg',
               'd64': 'artifacts/app/010-graphical/falken9-010-graphical.d64'}
    for kind, source in sources.items():
        destination = 'fixture/'+Path(source).name
        p = copy(source, destination)
        descriptor[kind] = pub.record(p, destination)
    for index in range(5):
        source = manifest['figures'][index]['indexed']['path']
        destination = 'assets/screenshots/fixture-'+str(index)+'.png'
        p = copy(source, destination)
        descriptor['screenshots'].append({'path': destination, 'sha256': pub.sha(p),
            'prg_sha256': descriptor['prg']['sha256'], 'method': 'packaging fixture only',
            'source_artifact': descriptor['prg']['path']})
    for kind in ('screenshot_provenance', 'validation'):
        p = root/'publication'/(kind+'.json')
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({'fixture_only': True, 'prg_sha256': descriptor['prg']['sha256']}))
        descriptor[kind] = {'path': str(p.relative_to(root)), 'sha256': pub.sha(p)}
    (root/'publication/application-release.json').write_text(json.dumps(descriptor))
    (root/'publication/model-card.md').write_text('---\nlicense: apache-2.0\n---\n# Fixture only\n![Game]('+descriptor['screenshots'][0]['path']+')\n')
    return root


def test_descriptor_bound_consumer_stage(consumer_fixture, tmp_path):
    output = tmp_path/'upload'
    manifest = pub.stage_release(consumer_fixture, output)
    assert manifest['release_id'].endswith('app011')
    assert manifest['publication']['target_repository'] == 'lewismoten/falken-9'
    assert len(manifest['screenshots']) == 5
    report = (output/'report.md').read_text()
    assert report.count('publication-indexed/') == 39
    assert 'application010' not in (output/'c64/README.md').read_text()
    paths = {e['path'] for e in manifest['files']}
    assert len([p for p in paths if p.endswith('.png')]) == 44
    assert not any('candidates' in p or 'presentation.json' in p or 'baseline' in p for p in paths)
    assert pub.verify_package(output, consumer_fixture)['passed']


@pytest.mark.parametrize('mutation', ['revision', 'digest', 'binding', 'escape', 'symlink'])
def test_bad_descriptor_rejected_before_output(consumer_fixture, tmp_path, mutation):
    path = consumer_fixture/'publication/application-release.json'
    d = json.loads(path.read_text())
    if mutation == 'revision': d['revision'] = '010'
    elif mutation == 'digest': d['prg']['sha256'] = '0'*64
    elif mutation == 'binding': d['screenshots'][0]['prg_sha256'] = '0'*64
    elif mutation == 'escape': d['validation']['path'] = '../outside.json'
    else:
        p = consumer_fixture/d['validation']['path']
        target = tmp_path/'evidence.json'
        target.write_bytes(p.read_bytes())
        p.unlink(); p.symlink_to(target)
    path.write_text(json.dumps(d))
    with pytest.raises(ValueError): pub.stage_release(consumer_fixture, tmp_path/'upload')
    assert not (tmp_path/'upload').exists()


def rewrite_manifest_checksums(output, manifest):
    (output/'manifest.json').write_text(json.dumps(manifest))
    names = sorted(str(p.relative_to(output)) for p in output.rglob('*') if p.is_file() and p.name != 'SHA256SUMS')
    (output/'SHA256SUMS').write_text(''.join(pub.sha(output/n)+'  '+n+'\n' for n in names))


@pytest.mark.parametrize('mutation', ['method', 'source', 'prg', 'evidence', 'extra'])
def test_rechecks_accepted_inventory_not_just_self_asserted_hashes(consumer_fixture, tmp_path, mutation):
    output = tmp_path/'upload'
    manifest = pub.stage_release(consumer_fixture, output)
    if mutation == 'method': manifest['screenshots'][0]['method'] = 'invented capture'
    elif mutation == 'source': manifest['screenshots'][0]['source_artifact'] = 'other.prg'
    elif mutation == 'prg': manifest['screenshots'][0]['prg_sha256'] = '0'*64
    elif mutation == 'evidence': manifest['provenance'] = {}
    else:
        (output/'operator-notes.txt').write_text('not part of the approved consumer inventory')
        manifest['files'].append(pub.record(output/'operator-notes.txt', 'operator-notes.txt'))
    rewrite_manifest_checksums(output, manifest)
    with pytest.raises(ValueError): pub.verify_package(output, consumer_fixture)


@pytest.mark.parametrize('text', ['baselines/conditional-c64/example.prg', 'conditional-tictactoe-002.prg', 'Conventional C64 baseline'])
def test_conventional_material_cannot_reenter_public_prose(text):
    with pytest.raises(ValueError, match='conventional'):
        pub.public_text(text)


def test_missing_descriptor_has_actionable_error(tmp_path):
    with pytest.raises(ValueError, match='application-release.json'):
        pub.load_application_release(tmp_path)
