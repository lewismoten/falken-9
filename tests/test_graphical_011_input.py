"""Executed input regressions; byte streams are not browser-focus proof."""
import hashlib
import json
import os
import time
from pathlib import Path

import pytest

from scripts.build_graphical_app import ROOT, build
from scripts.verify_graphical_app import GraphicalMachine


@pytest.fixture(scope='module')
def built(tmp_path_factory):
    return build(tmp_path_factory.mktemp('input011'))


def selector_row(game):
    rows = [r for r in (9, 11, 13)
            if game.cpu.memory[0x400 + r * 40 + 9] == 44]
    assert len(rows) == 1, rows
    row = rows[0]
    assert game.cpu.memory[0xd800 + row * 40 + 9] != 0
    return row


@pytest.mark.parametrize('key', [0x49, 0x69])
def test_info_letter_variants_return_through_getin_continuation(built, key):
    # $49 is native unshifted I, $C9 native Shift+I; $69 is the existing
    # ASCII lowercase compatibility path, not a claim about the ROM scanner.
    game = GraphicalMachine(built)
    game.until_input()
    title = game.planes()
    for _ in range(3):
        game.key(key)
        assert game.get('view') == 1
        assert game.get('info_scroll') == 0
        game.key(0x11)
        assert game.get('info_scroll') == 1
        game.key(0x91)
        assert game.get('info_scroll') == 0
        game.key('Q')
        assert game.get('view') == 0 and game.planes() == title
        game.key(0)  # Empty GETIN must resume, not fall through/lose the stack.
        assert game.cpu.sp == 255 and game.cpu.memory[1] == 0x37
    assert game.neural_calls == 0 and game.immutable_intact()


def test_arrows_follow_artwork_row_order_including_wrap_and_return(built):
    authority = json.loads((ROOT / 'assets/game-art/title/selection.json').read_text())
    assert [authority['states'][s]['row'] for s in ('one', 'two', 'auto')] == [9, 11, 13]
    game = GraphicalMachine(built)
    game.until_input()
    for row, text in [(9, '1 PLAYER VS AI'), (11, '2 PLAYER VS PLAYER'), (13, '0 AI VS AI')]:
        assert game.text(row)[11:11 + len(text)] == text
    assert selector_row(game) == 9
    for key, mode, row in [(0x11, 2, 11), (0x11, 0, 13), (0x11, 1, 9),
                           (0x91, 0, 13), (0x91, 2, 11), (0x91, 1, 9),
                           (0x11, 2, 11)]:
        before = game.planes()
        game.key(key)
        assert game.get('mode') == mode and selector_row(game) == row
        changed = {i for old, new in zip(before, game.planes())
                   for i in range(1000) if old[i] != new[i]}
        assert changed <= {r * 40 + 9 for r in (9, 11, 13)}
        assert game.cpu.sp == 255
    # RETURN starts the visually selected two-human mode, without inference.
    game.key(13)
    assert game.get('view') == 2 and game.get('mode') == 2
    assert game.neural_calls == 0
    game.key('Q')
    assert game.get('view') == 0 and selector_row(game) == 11
    game.key(0x49)
    assert game.get('view') == 1
    game.key('Q')
    assert selector_row(game) == 11 and game.immutable_intact()


def test_screen_code_i_is_not_a_kernal_letter_alias(built):
    game = GraphicalMachine(built)
    game.until_input()
    title = game.planes()
    game.key(0x09)  # Custom charset glyph I is not GETIN's native I byte.
    assert game.get('view') == 0 and game.planes() == title
    game.key(0x49)
    assert game.get('view') == 1


def test_input_change_preserves_frozen_neural_core_and_model(built):
    frozen = ROOT / 'artifacts/app/010-graphical'
    old = json.loads((frozen / 'build.json').read_text())
    game = GraphicalMachine(built)
    assert game.original_core == (frozen / 'core/runtime.bin').read_bytes()[:old['labels']['code_end'] - 0x800]
    prg = (frozen / 'falken9-010-graphical.prg').read_bytes()
    load = int.from_bytes(prg[:2], 'little')
    assert game.original_model == prg[2 + 0x4000 - load:2 + 0x4000 - load + 5195]


@pytest.mark.skipif(not os.environ.get('F9_INPUT_NATIVE_DIR'),
                    reason='Set F9_INPUT_NATIVE_DIR to retain native VICE evidence')
@pytest.mark.parametrize('frozen', [True, False], ids=['frozen010', 'current'])
def test_native_scanner_getin_contract_and_continuation(built, frozen):
    from scripts.verify_quit_keys import KeyVice
    from scripts.verify_graphical_stock_rom import DEFAULT_VICE_ROOT

    if frozen:
        image_dir = ROOT / 'artifacts/app/010-graphical'
        built = json.loads((image_dir / 'build.json').read_text())
    digest = hashlib.sha256(Path(built['prg_path']).read_bytes()).hexdigest()
    assert digest == built['prg_sha256']
    output = Path(os.environ['F9_INPUT_NATIVE_DIR']).resolve() / ('frozen010' if frozen else 'current')
    v = KeyVice(built, built['prg_path'], output, DEFAULT_VICE_ROOT, audio=False)
    records = []
    try:
        v.setup_keys()
        v.command('delete')
        v.steps(100000)

        def event(sym, down):
            code = v.x.XKeysymToKeycode(v.d, sym)
            assert v.xt.XTestFakeKeyEvent(v.d, code, int(down), 0)
            v.x.XSync(v.d, 0)
            # XSync reaches the X server, not VICE's asynchronous GTK queue.
            time.sleep(0.05)

        def pulse(name, sym, expected_byte, view, mode, shift=False):
            v.command('delete')
            v.command(f"break {v.labels['input_received']:04x}")
            if shift:
                event(0xffe1, True)  # Shift_L
            event(sym, True)
            v.steps(100000)
            pc, regs = v.registers()
            assert pc == v.labels['input_received'], (name, hex(pc))
            assert regs[0] == expected_byte, (name, regs)
            event(sym, False)
            if shift:
                event(0xffe1, False)
            v.command('delete')
            v.steps(200000)
            assert v.value('view') == view and v.value('mode') == mode
            if view == 0:
                row = {1: 9, 2: 11, 0: 13}[mode]
                assert v.memory(0x400 + row * 40 + 9)[0] == 44
            records.append(dict(key=name, getin=expected_byte, view=view, mode=mode))

        for mode in (2, 0, 1):
            pulse('Down', 0xff54, 0x11, 0, mode)
        for mode in (0, 2, 1):
            pulse('Up', 0xff52, 0x91, 0, mode)
        pulse('i', ord('i'), 0x49, 1, 1)
        pulse('Down/info', 0xff54, 0x11, 1, 1)
        assert v.value('info_scroll') == 1
        pulse('Up/info', 0xff52, 0x91, 1, 1)
        assert v.value('info_scroll') == 0
        pulse('q', ord('q'), 0x51, 0, 1)
        # Preserve frozen010's key contract: shifted I remains ignored.
        pulse('Shift+i', ord('i'), 0xc9, 0, 1, shift=True)
        v.command(f'screenshot "{output / "shift-i.png"}" 2')
        pulse('i/continued', ord('i'), 0x49, 1, 1)
        pulse('q/continued', ord('q'), 0x51, 0, 1)
        v.command(f"break {v.labels['input_wait']:04x}")
        v.command('x')
        assert v.registers()[1][3] == 255
        (output / 'summary.json').write_text(json.dumps(dict(
            prg_sha256=digest, records=records,
            boundary='Native XTest + stock ROM scanner/GETIN; not browser/physical C64',
            stack=255), indent=2) + '\n')
    finally:
        v.close()
    assert hashlib.sha256(Path(built['prg_path']).read_bytes()).hexdigest() == digest
