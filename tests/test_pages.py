"""Static build inventory; runtime/browser acceptance is a separate gate."""
import hashlib
import importlib.util
import json
from pathlib import Path

def test_pages_build_copies_exact_prg_d64_and_excludes_host_assets(tmp_path):
    assert importlib.util.find_spec('scripts.build_pages'),'missing reproducible Pages build'
    from scripts.build_pages import build_pages
    from scripts.build_graphical_app import build
    from scripts.build_app import package_disk
    candidate=tmp_path/'candidate';b=build(candidate)
    gate=dict(status='passed',prg_sha256=b['prg_sha256'],draws=1,model_wins=1,executed_neural_calls=7)
    disk=package_disk(b,gate,candidate,stem='falken9-007-graphical',title='FALKEN9 GRAPHIC')
    # A source-art PNG supplies a unit-test image, NOT an emulator screenshot claim.
    shot=Path('assets/game-art/title/image.png')
    out=tmp_path/'pages';manifest=build_pages(candidate,out,shot)
    for kind,source in [('prg',Path(b['prg_path'])),('d64',Path(disk['path']))]:
        record=manifest[kind];raw=(out/record['path']).read_bytes()
        assert raw==source.read_bytes()
        assert len(raw)==record['bytes'] and hashlib.sha256(raw).hexdigest()==record['sha256']
        assert record['path'].startswith('downloads/')
    assert (out/'screen.png').read_bytes()==shot.read_bytes()
    assert json.loads((out/'release.json').read_text())==manifest
    assert not any('huggingface' in str(p) or p.suffix in ('.wav','.log','.bin') for p in out.rglob('*'))
