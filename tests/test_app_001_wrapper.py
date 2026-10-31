"""Assembled wrapper gates; neural fixtures are TEST ONLY, never deployed."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def app():
    path = ROOT/'scripts/build_app.py'
    assert path.exists(), 'missing assembled application builder'
    spec = importlib.util.spec_from_file_location('build_app', path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    from scripts.verify_runtime import Machine
    return Machine(mod.build())


def history(m, text):
    m.put('history_length', len(text), 1)
    for i, ch in enumerate(text): m.put(m.labels['history']+i, ord(ch), 1)
    return m.call('validate_history')


def test_assembled_canonical_all_eight_and_original_fullset_tie():
    from falken9.symmetry import canonicalize
    m = app()
    assert 'canonicalize_board' in m.labels, 'missing assembled eight-way canonicalization'
    assert 'restore_set' in m.labels, 'missing assembled full-set inverse/legal/tie selection'
    for text in ['', 'a', 'ae', 'aeb', 'acbe', 'ideb', 'abcdef']:
        assert not history(m,text)['carry']
        original = tuple(m.get(m.labels['original_board']+i,1,False) for i in range(9))
        expected, transform = canonicalize(original)
        assert not m.call('canonicalize_board')['carry']
        assert tuple(m.get(m.labels['board']+i,1,False) for i in range(9)) == expected
        assert tuple(m.get(m.labels['selected_transform']+i,1,False) for i in range(9)) == transform
        # All-zero logits include every legal cell, not just one canonical winner.
        for i in range(9): m.put(m.labels['logits']+4*i,0,4)
        assert not m.call('restore_set')['carry']
        legal = [i for i,v in enumerate(original) if not v]
        assert [i for i in range(9) if m.get(m.labels['original_set']+i,1,False)] == legal
        assert m.get('selected_move',1,False) == next(ord(c)-97 for c in 'ebdfhcgia' if ord(c)-97 in legal)
        for i in range(9): m.put(m.labels['logits']+4*i,-1,4)
        assert m.call('restore_set')['carry'] == 1  # no heuristic fallback


def test_all_4520_wrappers_against_executed_target_fixture_logits():
    path = ROOT/'scripts/verify_app.py'
    assert path.exists(), 'missing exhaustive assembled-wrapper verification'
    spec = importlib.util.spec_from_file_location('verify_app', path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    result = mod.verify_wrapper()
    assert result['boards'] == 4520
    assert result['canonical_boards'] == 627
    assert result['set_errors'] == result['move_errors'] == 0
    assert result['stack_low_water'] == 0x1fc


def test_assembled_history_validation_and_terminal_state():
    m = app()
    for text, board, terminal in [('',[0]*9,0),('A',[1]+[0]*8,0),('aeb',[1,1,0,0,2,0,0,0,0],0),('adbec',[1,1,1,2,2,0,0,0,0],1),('abcdegfih',[1,2,1,2,1,1,2,1,2],3)]:
        result = history(m,text)
        assert result['carry'] == 0, text
        assert [m.get(m.labels['original_board']+i,1,False) for i in range(9)] == board
        assert m.get('terminal',1,False) == terminal
        assert m.get('side',1,False) == 1+len(text)%2
    for text in ['aa','j','!','adbecf','abcdefghia']:
        assert history(m,text)['carry'] == 1, text
