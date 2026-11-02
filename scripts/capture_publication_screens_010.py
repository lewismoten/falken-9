"""Native VICE captures of frozen application010; never assembles or edits it."""
from pathlib import Path
import hashlib
import json
import shutil
from PIL import Image
from scripts.verify_quit_keys import KeyVice
from scripts.verify_graphical_stock_rom import DEFAULT_VICE_ROOT

ROOT = Path(__file__).resolve().parents[1]
ACCEPTED = 'c571353a61c8a663050c33809b6ca880d29aebc969c545a717da2644eed3143a'
PRG = Path('artifacts/app/010-graphical/falken9-010-graphical.prg')
OUT = Path('build/publication-screens-010/native')
PUBLIC = Path('assets/screenshots')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def protected_files():
    roots = ['artifacts/app/010-graphical', 'assets/game-art', 'src/app']
    return {str(p.relative_to(ROOT)): digest(p) for root in roots
            for p in sorted((ROOT / root).rglob('*')) if p.is_file()}


def capture():
    targets = [PUBLIC / ('falken9-010-' + name + '.png')
               for name in ('title', 'quit-session')]
    provenance_path = PUBLIC / 'application010-additional-provenance.json'
    assert all(not (ROOT / p).exists() for p in targets + [provenance_path]), 'Never replace publication captures'
    assert digest(ROOT / PRG) == ACCEPTED
    before = protected_files()
    evidence = ROOT / OUT
    evidence.mkdir(parents=True, exist_ok=False)
    (evidence / 'protected-before.json').write_text(json.dumps(before, indent=2) + '\n')
    built = json.loads((ROOT / PRG.parent / 'build.json').read_text())
    assert built['prg_sha256'] == ACCEPTED
    v = KeyVice(built, ROOT / PRG, evidence, DEFAULT_VICE_ROOT, audio=True)
    frames = []
    try:
        v.setup_keys()
        assert v.value('view') == 0
        v.command('delete')
        # More than a full PAL VIC frame, even at the minimum two cycles/instruction.
        v.steps(100000)
        title_clock = v.clock()
        assert v.value('view') == 0
        for index, name in enumerate(('title', 'quit-session')):
            if index:
                # A real native-window key enters the stock-ROM scanner and normal dispatcher.
                v.event('q', True)
                v.steps(100000)
                v.event('q', False)
                v.steps(100000)
                assert v.value('view') == 3
                assert v.value('audio_enabled') == 0
                assert v.memory(0x314, 2) == b'\x31\xea'
                assert all(v.memory(a)[0] == 0 for a in (0xd404, 0xd40b, 0xd412, 0xd418))
            start_clock = v.clock()
            native = evidence / (name + '.png')
            v.command(f'screenshot "{native}" 2')
            v.steps(100000)
            later_clock = v.clock()
            assert later_clock - start_clock > 19656
            settled = evidence / (name + '-settled.png')
            v.command(f'screenshot "{settled}" 2')
            assert native.read_bytes() == settled.read_bytes(), 'VIC pixels not stable'
            assert v.value('view') == (3 if index else 0)
            shutil.copyfile(settled, ROOT / targets[index])
            with Image.open(settled) as image:
                size = list(image.size)
            frames.append(dict(path=str(targets[index]), sha256=digest(settled), dimensions=size,
                               view=v.value('view'), stable_repeat_equal=True,
                               settled_cycles=later_clock-start_clock,
                               capture_clock=later_clock,
                               input_sequence=[] if not index else ['native XTest q key-down', '100000 executed instructions', 'native XTest q key-up', '100000 executed instructions'],
                               native_evidence=str(OUT / settled.name)))
        raw = (ROOT / PRG).read_bytes()
        load = int.from_bytes(raw[:2], 'little')
        labels = built['labels']
        start, end = labels['model'], labels['model_end']
        assert v.memory(start, end-start) == raw[2+start-load:2+end-load]
        # The BASIC autostart stub overlays the core prefix, restored at startup.
        # $0800 precedes the PRG load address; use its frozen runtime transport.
        core_path = ROOT / PRG.parent / 'core/runtime.bin'
        core = core_path.read_bytes()[:labels['code_end']-0x800]
        assert v.memory(0x800, len(core)) == core
        app = (ROOT / PRG.parent / 'app.bin').read_bytes()
        assert v.memory(0x8000, len(app)) == app
        (evidence / 'events.json').write_text(json.dumps(v.events, indent=2) + '\n')
    finally:
        v.close()
    after = protected_files()
    assert before == after, 'Frozen executable, model, game art or application source changed'
    assert digest(ROOT / PRG) == ACCEPTED
    rom = DEFAULT_VICE_ROOT / 'usr/share/vice/C64'
    provenance = dict(
        schema_version=1, game_title='Crystal Palace 9', model_identity='Falken-9',
        visible_model_badge='FALCON-9 / 1.0 (unaltered accepted application spelling)',
        source=dict(path=str(PRG), sha256_before=ACCEPTED, sha256_after=digest(ROOT / PRG),
                    build_map_path=str(PRG.parent / 'build.json'), build_map_sha256=digest(ROOT / PRG.parent / 'build.json')),
        method='Untouched native VICE monitor PNG output; byte-copy only; no crop, redraw, scaling, compilation or screen-RAM strings',
        emulator=dict(program='VICE x64', executable_sha256=digest(DEFAULT_VICE_ROOT / 'usr/bin/x64'),
                      timing='PAL', mode='stock C64 ROM, PRG autostart; sound enabled, dummy audio sink, warp',
                      roms={p.name:digest(p) for p in [rom/'kernal-901227-03.bin', rom/'basic-901226-01.bin', rom/'chargen-901225-01.bin']}),
        boundary='Native isolated Xvfb/XTest key-down/up; real KERNAL scanner/application dispatch. Not browser, physical C64 or D64 launch acceptance. Title view 0 -> fresh title Q -> session-quit view 3; never a game-menu return.',
        settling='100000 executed instructions before title capture; two identical PNGs 100000 instructions apart for each view, exceeding one 19656-cycle PAL VIC frame',
        checks=dict(executable_hash_before_after_equal=True, protected_files_before_after_equal=True,
                    live_model_bytes_equal_PRG=True, live_core_bytes_equal_frozen_runtime=True, live_app_bytes_equal_frozen_app=True,
                    session_quit_view=3, audio_disabled=True, stock_irq_restored=True, sid_gates_volume_zero=True),
        protected_snapshot=str(OUT/'protected-before.json'), screenshots=frames)
    (ROOT / provenance_path).write_text(json.dumps(provenance, indent=2) + '\n')
    print(json.dumps(provenance, indent=2))
    return provenance


if __name__ == '__main__':
    capture()
