"""Release-facing INFO is exercised through the packaged 6502 viewer."""
from pathlib import Path
from scripts.build_graphical_app import build
from scripts.build_app import extract_disk
from scripts.verify_graphical_app import GraphicalMachine


def test_010_info_lineage_namesake_and_public_copy_across_every_scroll(tmp_path):
    built = build(tmp_path/'build')
    assert Path(built['prg_path']).name == 'falken9-010-graphical.prg'
    game = GraphicalMachine(built)
    game.until_input()
    title = game.planes()
    game.key('I')
    pages = []
    scroll = built['labels']['info_scroll']
    previous = -1
    frame = Path(built['path']).parent.joinpath('info_screen.bin').read_bytes()
    color_frame = Path(built['path']).parent.joinpath('info_color.bin').read_bytes()
    editable = {r*40+c for r in range(4,22) for c in range(5,34)} | {r*40+34 for r in range(4,22)}
    while game.cpu.memory[scroll] != previous:
        previous = game.cpu.memory[scroll]
        screen, colors = game.planes()
        assert all(screen[i] == frame[i] and colors[i] == color_frame[i] for i in range(1000) if i not in editable)
        pages.append('\n'.join(game.text(r)[5:34] for r in range(4,22)))
        game.key(0x11)
    joined = ' '.join(' '.join(pages).split())
    for phrase in ['PALACE-9', 'CRYSTAL-9', 'C64-FIRST', 'WARGAMES (1983)', 'DR. STEPHEN FALKEN', 'JOSHUA', 'WOPR', 'TIC-TAC-TOE ONLY', 'FROZEN MODEL - NOT LEARNING', 'HTTPS://GITHUB.COM/LEWISMOTEN', 'HTTPS://HUGGINGFACE.CO/']:
        assert phrase in joined, phrase
    assert 'NOT YET PUBLISHED' not in joined
    assert 'REQUESTED' not in joined
    assert previous >= 50
    game.key('Q'); assert game.planes() == title
    game.key('I'); assert game.cpu.memory[scroll] == 0
    game.key('Q'); game.key('2'); game.key('5'); game.key('R'); game.key('Q')
    game.key('I'); assert game.cpu.memory[scroll] == 0
    assert game.immutable_intact()
