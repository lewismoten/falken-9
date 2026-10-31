"""Packaged PRG input-loop tests; KERNAL GETIN shim != real ROM proof."""
from scripts.build_app import build, ROOT


def test_complete_packaged_draw_loss_replay_and_safety():
    from scripts import verify_app
    assert hasattr(verify_app,'verify_games'), 'missing complete packaged-match gate'
    result=verify_app.verify_games()
    assert result['draws']>=1 and result['model_wins']>=1
    assert result['executed_neural_calls']>=7
    assert result['code_model_immutable']


def test_basic_prg_boots_real_input_loop_and_acknowledges_human_before_neural():
    built=build()
    assert 'prg_path' in built, 'missing BASIC auto-start PRG'
    from scripts.verify_app import GameMachine
    game=GameMachine(built)
    game.until_input()
    assert game.text(2).strip() == 'FALKEN-9 / RESIDENT NEURAL TIC-TAC-TOE'
    assert game.get('history_length')==0
    game.key('!')
    assert game.get('history_length')==0
    assert 'INVALID' in game.text(16)
    game.key('A', stop_at='neural_begin')
    assert game.get('history_length')==1
    assert game.cell(0)==24  # screen-code X, before slow forward starts
    assert game.color(0)==10
    assert 'NEURAL FORWARD' in game.text(16)
    assert game.cpu.p & game.cpu.INTERRUPT
    assert bytes(game.cpu.memory[0x800:built['labels']['code_end']]) == (ROOT/'build/app/core/runtime.bin').read_bytes()[:built['labels']['code_end']-0x800]
    game.until_input()
    assert game.get('history_length')==2
    assert game.get('terminal')==0
    assert sum(game.get('original_board',i)==2 for i in range(9))==1
    assert game.neural_calls==1
    assert game.cpu.sp==0xff
    assert game.cpu.memory[0xcc]==0xff  # no KERNAL cursor blink over fixed UI
    game.key('A')
    assert game.get('history_length')==2
    assert game.neural_calls==1
    game.key('R')
    assert game.get('history_length')==0
    assert game.neural_calls==1
    assert game.cpu.sp==0xff
