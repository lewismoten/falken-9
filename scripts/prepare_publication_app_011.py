"""Build and gate application011, capturing untouched native publication PNGs.

No upload. Never overwrite a release directory or numbered publication asset.
Monitor-queue lifecycle input and XTest session-Q evidence are kept distinct.
"""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

from scripts.build_graphical_app import build, ROOT
from scripts.build_runtime import FOUR_MODEL, FOUR_SHA
from scripts.build_app import package_disk, extract_disk
from scripts.verify_graphical_app import verify_games
from scripts.verify_graphical_stock_rom import Vice, DEFAULT_VICE_ROOT, verify as verify_native
from scripts.verify_info_010 import verify as verify_info
from scripts.verify_quit_keys import KeyVice

FINAL = ROOT / 'artifacts/app/011-graphical-final'
EVIDENCE = ROOT / 'artifacts/operations/deployment/011/publication-final'
PROVENANCE = ROOT / 'assets/screenshots/application011-provenance.json'
RELEASE = ROOT / 'publication/application-release.json'
NAMES = ('title', 'gameplay', 'info-inspiration', 'info-bottom', 'quit-session')
ACCEPTED010 = 'c571353a61c8a663050c33809b6ca880d29aebc969c545a717da2644eed3143a'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rel(path):
    return str(Path(path).resolve().relative_to(ROOT))


def record(path):
    return dict(path=rel(path), bytes=Path(path).stat().st_size, sha256=digest(path))


def save(path, obj):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, indent=2) + '\n')


def protected():
    roots = ('src/app', 'src/runtime', 'assets/game-art', 'artifacts/app/010-graphical')
    files = [p for root in roots for p in (ROOT/root).rglob('*') if p.is_file()]
    files += [FOUR_MODEL, ROOT/'scripts/build_graphical_app.py', ROOT/'scripts/compile_graphics.py']
    files += list((ROOT/'assets/screenshots').glob('*010*'))
    return {rel(p): digest(p) for p in sorted(set(files))}


class PublicationVice(Vice):
    setup_keys = KeyVice.setup_keys
    event = KeyVice.event
    steps = KeyVice.steps
    clock = KeyVice.clock

    def capture(self, name):
        # Disable only the two normal foreground stops; work tracing stays off.
        self.command('disable 1')
        self.command('disable 2')
        self.steps(100000)
        start = self.clock()
        first = self.output/(name+'-first.png')
        self.command(f'screenshot "{first}" 2')
        self.steps(100000)
        end = self.clock()
        path = self.output/(name+'.png')
        self.command(f'screenshot "{path}" 2')
        assert end-start > 19656
        assert first.read_bytes() == path.read_bytes(), ('Unsettled framebuffer', name)
        self.command('enable 1')
        self.command('enable 2')
        self.resume()
        return path


def native_input_gate(built):
    """Opt in only the current011 scanner test; leave frozen010 untouched."""
    env = os.environ.copy()
    env['F9_INPUT_NATIVE_DIR'] = str(EVIDENCE/'native-input')
    result = subprocess.run([sys.executable, '-m', 'pytest', '-q',
                             'tests/test_graphical_011_input.py', '-k',
                             'native_scanner and current'], cwd=ROOT, env=env,
                            capture_output=True, text=True)
    (EVIDENCE/'native-input-tests.txt').write_text(result.stdout+result.stderr)
    assert result.returncode == 0, result.stdout+result.stderr
    path = EVIDENCE/'native-input/current/summary.json'
    summary = json.loads(path.read_text())
    assert summary['prg_sha256'] == built['prg_sha256']
    return dict(status='passed', evidence=record(path),
                pytest_output=record(EVIDENCE/'native-input-tests.txt'),
                boundary=summary['boundary'], keys=summary['records'])


def prepare():
    targets = [ROOT/'assets/screenshots'/('falken-9-011-'+name+'.png') for name in NAMES]
    assert all(not p.exists() for p in [FINAL, EVIDENCE, PROVENANCE, RELEASE, *targets]), 'Refuse to overwrite release/evidence/assets'
    before = protected()
    assert FOUR_MODEL.stat().st_size == 5195 and digest(FOUR_MODEL) == FOUR_SHA
    assert digest(ROOT/'artifacts/app/010-graphical/falken9-010-graphical.prg') == ACCEPTED010
    EVIDENCE.mkdir(parents=True)
    save(EVIDENCE/'protected-before.json', before)
    tests = subprocess.run([sys.executable, '-m', 'pytest', '-q',
                            'tests/test_graphical_011_presentation.py',
                            'tests/test_graphical_011_input.py'], cwd=ROOT, capture_output=True, text=True)
    (EVIDENCE/'focused-tests.txt').write_text(tests.stdout+tests.stderr)
    assert tests.returncode == 0, tests.stdout+tests.stderr
    print('Focused tests passed', flush=True)
    b: dict = build(FINAL)
    print('Built '+b['prg_sha256'], flush=True)
    native_input = native_input_gate(b)
    print('Current011 stock-ROM native scanner gate passed', flush=True)
    games = verify_games(b, EVIDENCE/'py65')
    print('Complete Py65 games passed', flush=True)
    disk = package_disk(b, games, FINAL, stem='falken-9-011-graphical', title='FALKEN-9 011')
    d64 = Path(disk['path'])
    assert extract_disk(d64) == Path(b['prg_path']).read_bytes()
    # Exercise the exact extracted disk payload through the complete-game shim.
    extracted = verify_games(b, EVIDENCE/'py65-extracted-d64', prg=extract_disk(d64))
    print('Extracted D64 complete games passed', flush=True)
    native = verify_native(b, d64, EVIDENCE/'native-d64', DEFAULT_VICE_ROOT, games)
    print('Stock-ROM PAL true-drive full lifecycle passed', flush=True)
    info = verify_info(b, d64, EVIDENCE/'native-info-all-offsets')
    print('Stock-ROM INFO all offsets passed', flush=True)
    captures = {}
    v = PublicationVice(b, d64, EVIDENCE/'native-presentation', DEFAULT_VICE_ROOT)
    try:
        decode = {n: c for c, n in b['charset_codes'].items()}
        text = lambda row: ''.join(decode.get(x, '?') for x in v.memory(0x400+row*40, 40))
        assert text(22)[30:38] == 'FALKEN-9'
        captures['title'] = (v.capture('title'), 'monitor KERNAL queue navigation; title at genuine D64 autostart')
        v.key('I')
        assert v.value('view') == 1 and 'FALKEN-9 / MODEL INFO' in text(1)
        raw = Path(b['path']).read_bytes()
        start = b['labels']['info_chars']-b['load']
        count = (b['labels']['info_line_colors']-b['labels']['info_chars'])//29
        lines = [''.join(decode.get(c, '?') for c in raw[start+i*29:start+(i+1)*29]) for i in range(count)]
        inspiration = max(0, next(i for i, line in enumerate(lines) if 'INSPIRATION' in line)-1)
        for _ in range(inspiration):
            v.key(0x11)
        assert v.value('info_scroll') == inspiration
        captures['info-inspiration'] = (v.capture('info-inspiration'), 'monitor KERNAL queue I and cursor-down scrolling')
        for _ in range(count-18-inspiration):
            v.key(0x11)
        assert v.value('info_scroll') == count-18
        captures['info-bottom'] = (v.capture('info-bottom'), 'monitor KERNAL queue cursor-down to actual bottom clamp')
        v.key('Q')
        v.key('2')
        footer = b['game_footer']

        def check_footer(show):
            for cell, glyph in zip(footer['replay_cells'], footer['glyphs']):
                assert v.memory(0x2000+cell*8, 8) == (bytes.fromhex(glyph) if show else bytes(8))
            assert [v.memory(0x400+c)[0] >> 4 for c in footer['quit_cells']] == [12, 6, 6, 6]

        check_footer(False)
        v.capture('human-active')
        for key in '14253':
            v.key(key)
        assert v.value('terminal') == 1
        check_footer(True)
        v.capture('human-ended')
        v.key('R')
        assert v.value('terminal') == 0
        check_footer(False)
        v.capture('human-replayed')
        v.key('Q')
        v.key('0')
        assert v.value('terminal') == 3
        check_footer(False)
        # No long extra settle here: automatic terminal hold is intentionally finite.
        Vice.capture(v, 'auto-ended')
        v.key('Q')
        v.key('I')
        assert v.value('view') == 1
        v.capture('info-after-auto')
        v.key('Q')
        assert v.value('view') == 0
        # Native-window Q, not a queue write, ends the actual session.
        v.setup_keys()
        v.command('delete')
        v.steps(100000)
        v.event('q', True)
        time.sleep(.05)
        v.steps(100000)
        v.event('q', False)
        time.sleep(.05)
        v.steps(100000)
        assert v.value('view') == 3 and v.value('audio_enabled') == 0
        assert v.memory(0x314, 2) == b'\x31\xea'
        assert all(v.memory(a)[0] == 0 for a in (0xd404, 0xd40b, 0xd412, 0xd418))
        first = v.output/'quit-session-first.png'
        v.command(f'screenshot "{first}" 2')
        v.steps(100000)
        session = v.output/'quit-session.png'
        v.command(f'screenshot "{session}" 2')
        assert first.read_bytes() == session.read_bytes()
        captures['quit-session'] = (session, 'XTest native-window q key-down/up through stock-ROM scanner; view 3, audio off, stock IRQ restored')
        save(v.output/'events.json', v.events)
    finally:
        v.close()
    # Gameplay shows a real newly executed model response in the full native gate.
    captures['gameplay'] = (EVIDENCE/'native-d64/gameplay.png', 'monitor KERNAL queue human move plus complete native neural response; settled native VICE PNG')
    frames = []
    for name, target in zip(NAMES, targets):
        source, input_method = captures[name]
        shutil.copyfile(source, target)
        assert digest(source) == digest(target)
        frames.append(dict(path=rel(target), sha256=digest(target), prg_sha256=b['prg_sha256'],
                           method='Untouched native VICE monitor PNG; no crop, scaling, repaint or pixel editing. '+input_method,
                           source_artifact=rel(d64), native_evidence=rel(source)))
    assert protected() == before, 'Protected model/source/010 bytes changed'
    rom = DEFAULT_VICE_ROOT/'usr/share/vice/C64'
    provenance = dict(schema='falken9-application011-screenshots-v1', revision='011',
                      prg=record(b['prg_path']), d64=record(d64), screenshots=frames,
                      emulator=dict(program='VICE x64', sha256=digest(DEFAULT_VICE_ROOT/'usr/bin/x64'), timing='PAL',
                                    launch='stock C64 ROMs, genuine1541 D64 autostart; sound enabled; warp',
                                    roms={p.name: digest(p) for p in (rom/'kernal-901227-03.bin', rom/'basic-901226-01.bin', rom/'chargen-901225-01.bin')}),
                      boundary='Emulator-tested only. Lifecycle and INFO input are monitor-injected KERNAL queue bytes; session Q is an isolated native XTest key-down/up. Not browser or physical C64/drive acceptance.',
                      source_snapshot=rel(EVIDENCE/'protected-before.json'), protected_before_after_identical=True)
    save(PROVENANCE, provenance)
    # Keep the release-facing evidence relative and free of operator/local paths.
    summary = dict(schema='falken9-application011-validation-v1', status='passed', revision='011',
                   prg=record(b['prg_path']), d64=record(d64), model=record(FOUR_MODEL),
                   focused_tests=dict(status='passed', evidence=rel(EVIDENCE/'focused-tests.txt'),
                                      native_scanner_optional_tests='Default opt-in cases skipped here; current011 separately executed below'),
                   native_scanner_input=native_input,
                   py65_games=games, extracted_disk_games=extracted, native_lifecycle=native,
                   native_info=info, native_footer=dict(human_active_hidden=True, human_terminal_visible=True,
                   human_replay_hidden=True, auto_terminal_hidden=True, quit_colors=[12,6,6,6], info_after_auto=True),
                   screenshots=frames, screenshot_provenance=record(PROVENANCE),
                   model_unchanged=True, accepted010_prg_sha256=ACCEPTED010, protected_sources_unchanged=True,
                   boundary=provenance['boundary'], publication='local preparation only; no upload or push')
    save(EVIDENCE/'summary.json', summary)
    release = dict(schema='falken9-publication-application-v1', revision='011',
                   release_id='falken-9-model-v1.0.0-app011', model=record(FOUR_MODEL),
                   prg=record(b['prg_path']), d64=record(d64), screenshots=frames,
                   screenshot_provenance=record(PROVENANCE), validation=record(EVIDENCE/'summary.json'))
    assert len(release['screenshots']) == 5
    for item in [release[k] for k in ('model','prg','d64','screenshot_provenance','validation')]+frames:
        assert not Path(item['path']).is_absolute() and '..' not in Path(item['path']).parts
        assert digest(ROOT/item['path']) == item['sha256']
    assert '/home/' not in json.dumps(release) and '/home/' not in json.dumps(summary)
    save(RELEASE, release)
    print(json.dumps(release, indent=2), flush=True)
    return release


if __name__ == '__main__':
    prepare()
