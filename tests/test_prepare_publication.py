from pathlib import Path
import json
import re
import subprocess
import sys

import pytest
from scripts import prepare_publication as pub
from test_publication_inventory import consumer_fixture  # shared packaging-only fixture

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def real_application():
    if not (ROOT/pub.DESCRIPTOR).is_file():
        pytest.skip('Verified application-release.json has not arrived; parent runs final staging')
    return pub.load_application_release(ROOT)


def test_stage_real_consumer_release(tmp_path, real_application):
    output = tmp_path/'upload'
    manifest = pub.stage_release(ROOT, output)
    for kind, target in pub.DESTINATIONS.items():
        assert (output/target).read_bytes() == (ROOT/real_application[kind]['path']).read_bytes()
    card = (output/'README.md').read_text()
    assert card.startswith('---\nlicense: apache-2.0\n')
    for link in ('model.f9j', 'c64/falken-9-c64.prg', 'c64/falken-9-c64.d64', 'c64/README.md', 'model.json', 'manifest.json', 'SHA256SUMS'):
        assert ']('+link+')' in card, 'Hub-root consumer link was incorrectly sent to GitHub: '+link
    assert len(re.findall(r'!\[', (output/'report.md').read_text())) == 39
    assert manifest['report']['inline_figures'] == 39
    for name in ('tensor-workflow', 'netron-dark'):
        assert (output/'assets/interpretability/publication-indexed/model-inspection'/(name+'.png')).is_file()
        assert (output/'assets/interpretability/model-inspection'/(name+'.svg')).is_file()
        assert not (output/'assets/interpretability/model-inspection'/(name+'.png')).exists()
    assert (output/'assets/interpretability/model-inspection/netron-original.svg').is_file()
    assert not (output/'assets/interpretability/model-inspection/netron-original.png').exists()
    for shot in real_application['screenshots']:
        assert (output/shot['path']).read_bytes() == (ROOT/shot['path']).read_bytes()
        assert Path(shot['path']).name in (output/'c64/README.md').read_text()
    assert len(manifest['screenshots']) == 5
    assert manifest['game_title'] == 'Crystal Palace 9'
    assert manifest['model_identity'] == 'Falken-9'
    assert manifest['release_id'] == 'falken-9-model-v1.0.0-app011'
    assert not (output/'docs/research/study-009/overview009.png').exists()
    assert not (output/'assets/interpretability/publication-dark/study-009/overview009.png').exists()
    assert (output/'assets/interpretability/publication-indexed/study-009/overview009.png').is_file()
    assert 'publication-indexed/study-009/overview009.png' in (output/'docs/research/study-009/REPORT009.md').read_text()
    assert not (output/'assets/interpretability/publication-dark/contact-sheet.png').exists()
    assert not (output/'assets/interpretability/publication-dark/source-report.md').exists()
    assert manifest['publication']['performed'] is False
    paths = {str(p.relative_to(output)) for p in output.rglob('*') if p.is_file()}
    assert {'LICENSE', 'NOTICE', 'manifest.json', 'SHA256SUMS', 'model.json', 'c64/README.md'} <= paths
    assert not any(Path(p).suffix in pub.FORBIDDEN_SUFFIXES for p in paths)
    assert not any(p.startswith(('source/', 'tests/', 'research/studies/', 'pages/', 'artifacts/')) for p in paths)
    assert pub.verify_package(output)['passed']
    assert len(manifest['files']) == len(paths)-2


def test_cli_stages_from_unrelated_working_directory(tmp_path, real_application):
    result = subprocess.run([sys.executable, str(ROOT/'scripts/prepare_publication.py'), '--output', str(tmp_path/'upload')], cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['passed']


@pytest.mark.parametrize('name', ['../escape', '/absolute', 'c64/../../escape', 'bad\\name', '', '.', 'a//b', 'a/./b'])
def test_rejects_unsafe_package_names(name):
    with pytest.raises(ValueError):
        pub.safe_relative(name)


def test_modified_payload_and_extra_source_are_rejected(tmp_path, consumer_fixture):
    output = tmp_path/'upload'
    manifest = pub.stage_release(consumer_fixture, output)
    image = output/manifest['screenshots'][0]['path']
    original = image.read_bytes()
    image.write_bytes(original+b'changed')
    with pytest.raises(ValueError, match='Inventory mismatch'):
        pub.verify_package(output, consumer_fixture)
    image.write_bytes(original)
    (output/'probe.py').write_text('not a consumer artifact')
    with pytest.raises(ValueError, match='Unexpected'):
        pub.verify_package(output, consumer_fixture)


def test_dark_presentation_aliases_rebase_both_formats_without_touching_originals(tmp_path):
    source = 'docs/research/study-009/example009'
    target = 'assets/interpretability/publication-dark/study-009/example009'
    for stem, payload in [(source, b'original'), (target, b'dark')]:
        for suffix in ('.svg', '.png'):
            p = tmp_path/(stem+suffix)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(payload+suffix.encode())
    before = {str(p.relative_to(tmp_path)): p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    aliases = pub.presentation_aliases(tmp_path)
    assert aliases == {source+ext: target+ext for ext in ('.png', '.svg')}
    prose = '[![Measured](example009.png)](example009.svg)'
    rewritten = pub.rewrite_markdown(prose, 'docs/research/study-009/REPORT.md', 'docs/research/study-009/REPORT.md', aliases)
    assert rewritten == '[![Measured](../../../'+target+'.png)](../../../'+target+'.svg)'
    assert before == {str(p.relative_to(tmp_path)): p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}


def test_dark_aliases_reject_incomplete_presentation_pairs(tmp_path):
    p = tmp_path/'assets/interpretability/publication-dark/study-009/example009.svg'
    p.parent.mkdir(parents=True)
    p.write_text('<svg/>')
    with pytest.raises(ValueError, match='Incomplete dark presentation'):
        pub.presentation_aliases(tmp_path)


def test_no_overwrite_and_deterministic_transport(tmp_path, consumer_fixture):
    first, second = tmp_path/'first', tmp_path/'second'
    pub.stage_release(consumer_fixture, first)
    before = {str(p.relative_to(first)): p.read_bytes() for p in first.rglob('*') if p.is_file()}
    with pytest.raises(ValueError, match='already exist'):
        pub.stage_release(consumer_fixture, first)
    assert before == {str(p.relative_to(first)): p.read_bytes() for p in first.rglob('*') if p.is_file()}
    pub.stage_release(consumer_fixture, second)
    pub.archive_release(first, tmp_path/'first.zip', consumer_fixture)
    pub.archive_release(second, tmp_path/'second.zip', consumer_fixture)
    assert (tmp_path/'first.zip').read_bytes() == (tmp_path/'second.zip').read_bytes()
