"""Exact-byte publication011 capture/release contract, not a new runtime gate."""
import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope='module')
def release():
    path = ROOT/'publication/application-release.json'
    if not path.exists():
        pytest.skip('Run python -m scripts.prepare_publication_app_011 first')
    return json.loads(path.read_text())


def test_release011_exact_relative_inventory(release):
    assert release['schema'] == 'falken9-publication-application-v1'
    assert release['revision'] == '011'
    assert release['release_id'] == 'falken-9-model-v1.0.0-app011'
    assert len(release['screenshots']) == 5
    entries = [release[key] for key in ('model', 'prg', 'd64', 'screenshot_provenance', 'validation')]
    entries += release['screenshots']
    for item in entries:
        path = Path(item['path'])
        assert not path.is_absolute() and '..' not in path.parts
        assert sha(ROOT/path) == item['sha256']
        if 'bytes' in item:
            assert (ROOT/path).stat().st_size == item['bytes']
    assert '/home/' not in json.dumps(release)
    assert release['model']['bytes'] == 5195
    assert release['model']['sha256'] == 'fe180f8a931f9d92d8aa39da337bc819d0dbe4e6d971edcba00324fbc18a91c1'


def test_all_five_captures_are_new_native_frames_bound_to_final_prg(release):
    from PIL import Image
    expected = {'title', 'gameplay', 'info-inspiration', 'info-bottom', 'quit-session'}
    paths = {str(Path('assets/screenshots')/f'falken-9-011-{name}.png') for name in expected}
    assert {item['path'] for item in release['screenshots']} == paths
    provenance = json.loads((ROOT/release['screenshot_provenance']['path']).read_text())
    assert provenance['emulator']['timing'] == 'PAL'
    assert 'Not browser or physical' in provenance['boundary']
    assert provenance['protected_before_after_identical']
    for item in release['screenshots']:
        assert item['prg_sha256'] == release['prg']['sha256']
        assert item['source_artifact'] == release['d64']['path']
        assert item['method'].startswith('Untouched native VICE monitor PNG')
        assert sha(ROOT/item['native_evidence']) == item['sha256']
        with Image.open(ROOT/item['path']) as image:
            assert image.format == 'PNG' and image.width >= 320 and image.height >= 200


def test_native_and_complete_game_evidence_is_exact_and_preservation_holds(release):
    from scripts.build_app import extract_disk
    validation = json.loads((ROOT/release['validation']['path']).read_text())
    assert validation['status'] == 'passed'
    for key in ('py65_games', 'extracted_disk_games', 'native_lifecycle'):
        gate = validation[key]
        assert gate['status'] == 'passed'
        assert gate['prg_sha256'] == release['prg']['sha256']
    assert validation['native_lifecycle']['d64_true_drive_autostart']
    assert validation['native_lifecycle']['timing'] == 'PAL'
    assert validation['native_lifecycle']['full_logits_equal_to_py65']
    assert validation['native_info']['status'] == 'passed'
    assert validation['native_footer']['quit_colors'] == [12, 6, 6, 6]
    assert extract_disk(ROOT/release['d64']['path']) == (ROOT/release['prg']['path']).read_bytes()
    assert sha(ROOT/'artifacts/app/010-graphical/falken9-010-graphical.prg') == 'c571353a61c8a663050c33809b6ca880d29aebc969c545a717da2644eed3143a'
    assert validation['protected_sources_unchanged']
    scanner = json.loads((ROOT/'artifacts/operations/deployment/011/publication-final/native-input/current/summary.json').read_text())
    assert scanner['prg_sha256'] == release['prg']['sha256']
    assert scanner['stack'] == 255
    assert next(row for row in scanner['records'] if row['key'] == 'Shift+i')['view'] == 0
    assert next(row for row in scanner['records'] if row['key'] == 'i/continued')['view'] == 1
