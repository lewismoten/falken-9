"""Actual assembled graphical views, not host-render substitutes."""
import hashlib
from pathlib import Path
import importlib.util


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
    assert game.text(20)[30:38] == 'falken-9'
    assert game.text(21)[30:34] == 'v1.0'
    assert all(c == 6 for c in game.cpu.memory[0xd800+20*40+30:0xd800+20*40+38])
    game.key('I')
    assert game.get('view') == 1
    assert 'FALKEN-9' in game.text(3)
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
    assert result['carry']==0 and result['cycles']<300
    assert bytes(m.cpu.memory[0x20:0x80])==zp
    assert bytes(m.cpu.memory[0x2000:0x4000])==bitmap
    allowed={built['labels']['activity_phase'],built['labels']['packet_value'],*range(0x400+18*40+21,0x400+18*40+25),*range(0x100,0x200)}
    assert m.cpu.memory.addresses<=allowed


def test_every_status_renders_exact_native_bitmap_font(tmp_path):
    from scripts.build_graphical_app import build, CODE
    from scripts.verify_app import AppMachine
    built=build(tmp_path/'build');m=AppMachine(built,audit=True)
    font=Path(built['path']).parent.joinpath('bitmap-font.bin').read_bytes()
    m.cpu.memory.allowed[1]=1
    m.cpu.memory.allowed[0xf7:0xff]=bytes([1])*8
    m.cpu.memory[1]=0x37
    for i,text in enumerate(built['statuses']):
        m.cpu.a=i;m.call('draw_status')
        expected=b''.join(font[CODE[c]*8:CODE[c]*8+8] for c in text.ljust(32))
        at=0x2000+17*320+4*8
        assert bytes(m.cpu.memory[at:at+256])==expected, (i,text)


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
