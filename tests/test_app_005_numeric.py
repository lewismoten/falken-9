"""Numeric UI/result adaptation executes outside the unchanged neural core."""
from pathlib import Path
import pytest
from scripts.build_app import ROOT, build
from scripts.verify_app import AppMachine, GameMachine


@pytest.fixture(scope='module')
def numeric_build():
    return build()


@pytest.mark.parametrize('index', range(9))
def test_digits_and_legacy_letters_reach_identical_human_board(index, numeric_build):
    snapshots = []
    for key in (str(index + 1), chr(65 + index)):
        game = GameMachine(numeric_build)
        game.until_input()
        assert [game.cell(i) for i in range(9)] == list(b'123456789')
        assert '1-9: MOVE' in game.text(20)
        game.key(key, stop_at='neural_begin')
        assert game.get('history_length') == 1
        assert game.get('history') == 97 + index
        assert game.cell(index) == 24 and game.color(index) == 10
        assert game.neural_calls == 0  # acknowledged before expensive inference
        snapshots.append(bytes(game.cpu.memory[0x7800:0x781b]))
    assert snapshots[0] == snapshots[1]


def test_zero_and_invalid_keys_clear_result_without_a_model_call(numeric_build):
    game = GameMachine(numeric_build)
    game.until_input()
    assert game.get('move_result') == 0
    for key in ['0', '!', ':', '/', 'J']:
        game.cpu.memory[game.labels['move_result']] = 9  # stale-success poison
        game.key(key)
        assert game.get('move_result') == 0
        assert game.get('history_length') == game.neural_calls == 0
        assert [game.cell(i) for i in range(9)] == list(b'123456789')
        assert 'INVALID' in game.text(16) and '1-9' in game.text(16)
    game.cpu.memory[game.labels['move_result']] = 9
    game.key('R')
    assert game.get('move_result') == 0


def test_public_result_names_all_nine_squares_and_zero_only_on_failure(numeric_build):
    m = AppMachine(numeric_build)
    for index in range(9):
        for i in range(9):
            m.put(m.labels['original_board'] + i, 0, 1)
            m.put(m.labels['selected_transform'] + i, i, 1)
            m.put(m.labels['logits'] + 4*i, 0 if i == index else -1, 4)
        assert m.call('restore_set')['carry'] == 0
        assert m.get('selected_move', 1, False) == index
        assert m.get('move_result', 1, False) == index + 1
    for i in range(9):
        m.put(m.labels['logits'] + 4*i, -1, 4)
    assert m.call('restore_set')['carry'] == 1
    assert m.get('move_result', 1, False) == 0
    assert m.get('selected_move', 1, False) == 255


@pytest.mark.parametrize('text', ['aa', '!', 'adbec', '123'])
def test_invalid_or_terminal_policy_request_clears_stale_public_result(text, numeric_build):
    m = AppMachine(numeric_build)
    m.put('history_length', len(text), 1)
    for i, char in enumerate(text):
        m.put(m.labels['history'] + i, ord(char), 1)
    m.put('move_result', 9, 1)
    sentinel = b'\xa5' * 36
    m.cpu.memory[m.labels['logits']:m.labels['logits'] + 36] = sentinel
    assert m.call('policy_request')['carry'] == 1
    assert m.get('move_result', 1, False) == 0
    assert bytes(m.cpu.memory[m.labels['logits']:m.labels['logits'] + 36]) == sentinel


def test_new_artifact_number_and_frozen_001_directory_guard(numeric_build):
    assert Path(numeric_build['prg_path']).name == 'falken9-002-numeric.prg'
    from scripts.verify_app import verify_release
    with pytest.raises(AssertionError, match='001'):
        verify_release(ROOT/'artifacts/app/001-resident')
