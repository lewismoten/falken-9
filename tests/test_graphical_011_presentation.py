"""Release011 literal naming and state-dependent footer, executed on NMOS6502."""
from pathlib import Path
import pytest
from scripts.build_graphical_app import build
from scripts.verify_graphical_app import GraphicalMachine
from scripts.verify_app import AppMachine

@pytest.fixture(scope='module')
def built(tmp_path_factory):
    return build(tmp_path_factory.mktemp('presentation011'))

def test_falken_identity_on_title_and_entire_info_view(built):
    game=GraphicalMachine(built);game.until_input()
    assert game.text(22)[30:38]=='FALKEN-9'
    assert bytes(game.cpu.memory[0xd800+22*40+30:0xd800+22*40+38])==bytes([6])*8
    game.key('I');assert game.get('view')==1
    assert 'FALKEN-9 / MODEL INFO' in game.text(1)
    rows=[game.text(r)[5:34].rstrip() for r in range(4,22)]
    count=(built['labels']['info_line_colors']-built['labels']['info_chars'])//29
    for _ in range(count-18):
        game.key(0x11);rows.append(game.text(21)[5:34].rstrip())
    text=''.join(rows)
    assert 'FALKEN-9 1.0' in text and 'FALCON' not in text
    assert 'HTTPS://GITHUB.COM/LEWISMOTEN/FALKEN-9' in text
    assert 'HTTPS://HUGGINGFACE.CO/LEWISMOTEN/FALKEN-9' in text
    assert 'ARTIFACT SLUG: FALKEN-9' in text
    game.key('Q');assert game.text(22)[30:38]=='FALKEN-9'
    assert game.immutable_intact()

def test_replay_pixels_exist_only_for_terminal_human_games(built):
    machine=AppMachine(built)
    footer=built['game_footer']
    for mode in (0,1,2):
        for terminal in (0,1,2,3):
            machine.put('mode',mode,1);machine.put('terminal',terminal,1)
            # Poison stale replay pixels to catch a merely skipped redraw.
            for cell in footer['replay_cells']:
                machine.cpu.memory[0x2000+cell*8:0x2000+cell*8+8]=bytes([0xff])*8
            machine.call('paint_footer')
            for cell,hexglyph in zip(footer['replay_cells'],footer['glyphs']):
                expected=bytes.fromhex(hexglyph) if mode and terminal else bytes(8)
                assert bytes(machine.cpu.memory[0x2000+cell*8:0x2000+cell*8+8])==expected,(mode,terminal,cell)

def test_quit_is_gray_q_and_dark_blue_uit_in_all_modes(built):
    machine=AppMachine(built)
    footer=built['game_footer']
    for mode in (0,1,2):
        for terminal in (0,1,2,3):
            machine.put('mode',mode,1);machine.put('terminal',terminal,1)
            machine.call('paint_footer')
            assert [machine.cpu.memory[0x400+c]>>4 for c in footer['quit_cells']]==[12,6,6,6]

def test_real_terminal_and_replay_remove_stale_replay_without_blankout(built):
    game=GraphicalMachine(built);game.until_input();game.key('2')
    def visible():
        return any(game.cpu.memory[0x2000+c*8+i] for c in built['game_footer']['replay_cells'] for i in range(8))
    assert not visible()
    for key in '14253':game.key(key)
    assert game.get('terminal')==1 and visible()
    game.key('R');assert not visible() and game.get('terminal')==0
    assert game.immutable_intact()
