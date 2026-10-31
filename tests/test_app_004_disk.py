"""D64 packaging is gated by a passed exact-PRG lifecycle report."""
from scripts import build_app
from scripts.verify_app import verify_games, GameMachine


def test_release_manifest_binds_composed_wrapper_games_and_disk():
    from scripts import verify_app
    assert hasattr(verify_app,'verify_release'), 'missing application release gate'
    summary=verify_app.verify_release()
    assert summary['wrapper']['boards']==4520
    assert summary['games']['executed_neural_calls']==7
    assert summary['disk']['extracted_identical']
    assert summary['browser_tested'] is False


def test_d64_extracts_same_passed_prg_and_runs_packaged_input_loop():
    assert hasattr(build_app,'package_disk'), 'missing gated D64 builder'
    built=build_app.build()
    gate=verify_games()
    packaged=build_app.package_disk(built,gate)
    raw=build_app.extract_disk(packaged['path'])
    assert raw==open(built['prg_path'],'rb').read()
    game=GameMachine(built,prg=raw);game.until_input()
    game.key('A');assert game.get('history_length')==2
    assert game.neural_calls==1
    import pytest
    with pytest.raises(AssertionError):build_app.package_disk(built,dict(gate,prg_sha256='wrong'))
