"""Validate publication bytes against frozen input and retained native evidence."""
import hashlib
import json
from pathlib import Path
from PIL import Image
from scripts.capture_publication_screens_010 import ACCEPTED, PRG, ROOT

PROVENANCE = ROOT / 'assets/screenshots/application010-additional-provenance.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_exact_accepted_input_and_no_mutation():
    p = json.loads(PROVENANCE.read_text())
    assert sha(ROOT / PRG) == ACCEPTED
    assert p['source']['sha256_before'] == p['source']['sha256_after'] == ACCEPTED
    assert sha(ROOT / p['source']['build_map_path']) == p['source']['build_map_sha256']
    snapshot = json.loads((ROOT / p['protected_snapshot']).read_text())
    assert all(sha(ROOT / path) == value for path, value in snapshot.items())
    assert p['checks']['live_model_bytes_equal_PRG']
    assert p['checks']['live_core_bytes_equal_frozen_runtime']
    assert p['checks']['live_app_bytes_equal_frozen_app']


def test_untouched_settled_native_frames():
    p = json.loads(PROVENANCE.read_text())
    assert len(p['screenshots']) == 2
    assert [s['view'] for s in p['screenshots']] == [0, 3]
    for s in p['screenshots']:
        target = ROOT / s['path']
        native = ROOT / s['native_evidence']
        assert target.read_bytes() == native.read_bytes()
        assert sha(target) == s['sha256']
        assert s['settled_cycles'] > 19656
        assert s['stable_repeat_equal']
        with Image.open(target) as image:
            assert list(image.size) == s['dimensions'] == [384, 272]
            assert image.format == 'PNG'


def test_real_title_q_session_boundary():
    p = json.loads(PROVENANCE.read_text())
    events = json.loads((ROOT / 'build/publication-screens-010/native/events.json').read_text())
    assert [(e['key'], e['down'], e['source']) for e in events] == [
        ('q', True, 'XTestFakeKeyEvent'), ('q', False, 'XTestFakeKeyEvent')]
    assert p['checks']['session_quit_view'] == 3
    assert p['checks']['audio_disabled']
    assert p['checks']['stock_irq_restored']
    assert p['checks']['sid_gates_volume_zero']
    assert p['game_title'] == 'Crystal Palace 9'
    assert p['model_identity'] == 'Falken-9'


def test_public_provenance_has_no_private_paths_or_endpoints():
    text = PROVENANCE.read_text()
    for forbidden in ('/home/', '/tmp/', '127.0.0.1', 'localhost', 'ip4://'):
        assert forbidden not in text
    p = json.loads(text)
    for s in p['screenshots']:
        assert not Path(s['path']).is_absolute()
        assert not Path(s['native_evidence']).is_absolute()
