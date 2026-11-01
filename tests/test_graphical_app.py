"""Actual assembled graphical views, not host-render substitutes."""
import hashlib
from pathlib import Path
import importlib.util


# Independent 3x5 digits, one logical multicolor pixel = two physical pixels.
# The complete 8x8 character footprints lie inside the source cell rectangles.
NUMBER_ROWS = ('010110010010111', '111001111100111', '111001111001111',
               '101101111001001', '111100111001111', '111100111101111',
               '111001010010010', '111101111101111', '111101111001111')
NUMBER_CELLS = tuple(row*40+col for row in (5,8,11) for col in (16,20,23))


def numbered_reference(built, board):
    packed = Path(built['path']).parent.joinpath('graphics.bin').read_bytes()
    regions = built['graphics']['regions']
    planes = {}
    for plane in ('bitmap', 'screen', 'color'):
        r = regions['board_'+plane]
        planes[plane] = bytearray(packed[r['offset']:r['offset']+r['length']])
    for i, mark in enumerate(board):
        if mark:
            for name, p in built['graphics']['cells']['abcdefghi'[i]]['planes'].items():
                r = regions[p['values']['xo'[mark-1]]]
                for j, d in enumerate(p['destination_offsets']):
                    planes[name][d] = packed[r['offset']+j]
        else:
            cell = NUMBER_CELLS[i]
            rows = NUMBER_ROWS[i]
            glyph = bytes([0]+[sum(int(rows[y*3+x]) << (6-2*x) for x in range(3)) for y in range(5)]+[0,0])
            planes['bitmap'][cell*8:cell*8+8] = glyph
            planes['screen'][cell] = 0xc0 | (planes['screen'][cell] & 15)
    return planes


def assert_numbered_board(game):
    expected = numbered_reference(game.build, [game.get('original_board', i) for i in range(9)])
    for plane, start, length in [('bitmap',0x2000,14*320),('screen',0x400,14*40),('color',0xd800,14*40)]:
        assert bytes(game.cpu.memory[start:start+length]) == expected[plane][:length], plane


def test_empty_cells_show_native_row_major_numeric_labels(tmp_path):
    from scripts.build_graphical_app import build
    from scripts.verify_graphical_app import GraphicalMachine
    game = GraphicalMachine(build(tmp_path/'build'))
    game.until_input(); game.key('2')
    assert_numbered_board(game)
    # Real dispatch: partial/full board, labels disappear, then replay restores.
    for key in '532846917':
        game.key(key)
        assert_numbered_board(game)
    assert game.get('terminal') == 3
    game.key('R'); assert_numbered_board(game)
    game.key('Q'); title = game.planes()
    game.key('I'); game.key('Q'); assert game.planes() == title
    game.key('2'); assert_numbered_board(game)
    assert game.immutable_intact()


def test_each_numeric_label_replaced_by_either_original_mark_only(tmp_path):
    from scripts.build_graphical_app import build
    from scripts.verify_app import AppMachine
    built = build(tmp_path/'build')
    m = AppMachine(built, audit=True)
    m.cpu.memory.allowed[1] = 1
    m.cpu.memory.allowed[0xf7:0xff] = bytes([1])*8
    m.cpu.memory.allowed[0xd011] = 1
    m.cpu.memory.allowed[0xd016:0xd019] = bytes([1])*3
    m.cpu.memory[1] = 0x37
    # This gate invokes the assembled renderer for both marks in every cell.
    for i in range(9):
        for mark in (1,2):
            board = [0]*9; board[i] = mark
            for j, value in enumerate(board): m.put(m.labels['original_board']+j,value,1)
            nn = bytes(m.cpu.memory[0x6000:0x7800])
            m.call('draw_board')
            expected = numbered_reference(built,board)
            for plane,start,length in [('bitmap',0x2000,14*320),('screen',0x400,14*40),('color',0xd800,1000)]:
                assert bytes(m.cpu.memory[start:start+length]) == expected[plane][:length], (i,mark,plane)
            assert bytes(m.cpu.memory[0x6000:0x7800]) == nn


def test_native_title_info_roundtrip_and_frozen_residency(tmp_path):
    assert importlib.util.find_spec('scripts.build_graphical_app'), 'missing graphical builder'
    from scripts.build_graphical_app import build
    from scripts.verify_graphical_app import GraphicalMachine
    built = build(tmp_path/'build')
    game = GraphicalMachine(built)
    game.until_input()
    assert game.get('view') == 0
    assert game.cpu.memory[0xd018] == 0x1c
    assert bytes(game.cpu.memory[0x3000:0x3800]) == Path(built['path']).parent.joinpath('charset.bin').read_bytes()
    title = game.planes()
    assert game.text(22)[30:38] == 'FALCON-9'
    assert game.text(23)[35:38] == '1.0'
    assert all(c == 6 for c in game.cpu.memory[0xd800+22*40+30:0xd800+22*40+38])
    game.key('I')
    assert game.get('view') == 1
    assert 'FALCON-9' in game.text(4)
    game.key('Q')
    assert game.get('view') == 0
    assert game.planes() == title
    for _ in range(12):
        game.key('I');game.key('Q')
    game.key('Q')
    assert game.get('view')==3 and 'SESSION ENDED' in game.text(7)
    assert 'RESET OR RELOAD TO PLAY' in game.text(10)
    assert game.cpu.sp == 255
    assert game.immutable_intact()
    assert built['core']['image_sha256'] == '838aa62a854aa58bd603c7525b52dc67c4c4b01ea0f50f58982475959ec61961'


def test_live_human_ack_neural_activity_and_recovery(tmp_path):
    from scripts.build_graphical_app import build
    from scripts.verify_graphical_app import GraphicalMachine
    built=build(tmp_path/'build')
    assert 'activity_tick' in built['labels'], 'missing bounded real-work activity'
    game=GraphicalMachine(built);game.until_input();game.key('1')
    game.key('0');assert game.get('history_length')==0 and game.neural_calls==0
    game.key('1',stop_at='neural_begin')
    assert game.get('history_length')==1 and game.expected_board_planes_match()
    assert game.status_text()=='NEURAL FORWARD - WAIT'
    game.until_input()
    assert game.get('history_length')==2 and game.neural_calls==1
    assert len(game.phases)>=18
    assert game.expected_board_planes_match()
    assert game.get('activity_phase')==0
    game.key('1');assert game.get('history_length')==2 and game.neural_calls==1
    assert game.get('move_result')==0
    game.key('2');assert game.get('history_length')==4 and game.neural_calls==2
    assert game.immutable_intact()


def test_complete_modes_continuous_lifecycle(tmp_path):
    from scripts import verify_graphical_app as verifier
    assert hasattr(verifier,'verify_games'), 'missing complete graphical lifecycle gate'
    result=verifier.verify_games(verifier.build(tmp_path/'build'),tmp_path/'evidence')
    assert result['human_model_outcomes']==[3,2]
    assert result['auto_outcome']==3
    assert result['auto_neural_calls']==9
    assert result['two_human_outcomes']==[1,2,3]
    assert result['code_model_art_immutable']


def test_activity_preserves_registers_flags_zp_and_only_reserved_cells(tmp_path):
    from scripts.build_graphical_app import build
    from scripts.verify_app import AppMachine
    built=build(tmp_path/'build');m=AppMachine(built,audit=True)
    m.put('activity_phase',0,1)
    zp=bytes(m.cpu.memory[0x20:0x80]);bitmap=bytes(m.cpu.memory[0x2000:0x4000])
    m.cpu.a=0x83;m.cpu.x=0x79;m.cpu.y=0xa7
    result=m.call('activity_tick')
    assert (m.cpu.a,m.cpu.x,m.cpu.y)==(0x83,0x79,0xa7)
    assert m.cpu.p&m.cpu.DECIMAL
    assert result['carry']==0 and result['cycles']<650
    assert bytes(m.cpu.memory[0x20:0x80])==zp
    assert bytes(m.cpu.memory[0x2000:0x4000])==bitmap
    allowed={built['labels']['activity_phase'],built['labels']['activity_prng'],built['labels']['audio_pending'],*(0x400+c for c in built['activity_cells']),*range(0x100,0x200)}
    assert m.cpu.memory.addresses<=allowed


def test_every_status_renders_native_single_cell_glyph(tmp_path):
    from scripts.build_graphical_app import build
    from scripts.verify_app import AppMachine
    built=build(tmp_path/'build');m=AppMachine(built,audit=True)

    m.cpu.memory.allowed[1]=1
    m.cpu.memory.allowed[0xf7:0xff]=bytes([1])*8
    m.cpu.memory[1]=0x37
    glyphs=['0041411414414100','0014414141411400','0054414141415400','0014440410001000','0010101010001000']
    for i in range(9):
        m.put('terminal',i-3 if 4<=i<=6 else 0,1)
        m.put('side',1,1)
        m.cpu.a=i;m.call('draw_status')
        index=3 if i==1 else 4 if i==7 else i-4 if 4<=i<=6 else 0
        assert bytes(m.cpu.memory[0x3218:0x3220])==bytes.fromhex(glyphs[index]), i
        assert all(not (0x2000+17*320 <= a < 0x2000+18*320) for a in m.cpu.memory.addresses)


def test_two_human_all_cells_terminal_and_replay(tmp_path):
    assert importlib.util.find_spec('scripts.build_graphical_app'), 'missing graphical builder'
    from scripts.build_graphical_app import build
    from scripts.verify_graphical_app import GraphicalMachine
    game = GraphicalMachine(build(tmp_path/'build')); game.until_input()
    game.key('2')
    assert game.get('view') == 2 and game.get('mode') == 2
    assert game.cpu.memory[0xd011] == 0x3b and game.cpu.memory[0xd016] == 0x18
    for key in '532846917':
        game.key(key)
    assert game.get('terminal') == 3
    assert game.get('history_length') == 9
    assert game.neural_calls == 0
    assert game.status_text() == 'DRAW - R REPLAY / Q TITLE'
    assert game.expected_board_planes_match()
    game.key('0');assert game.get('move_result') == 0
    game.key('R');assert game.get('history_length') == 0
    game.key('Q');assert game.get('view') == 0
    assert game.immutable_intact()
