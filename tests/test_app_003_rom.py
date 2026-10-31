"""Optional genuine-ROM acceptance, never the GETIN shim."""
import os
import pytest
from scripts import verify_app
from scripts.build_app import ROOT


@pytest.mark.skipif(not os.environ.get('F9_RUN_VICE'),reason='set F9_RUN_VICE=1 and F9_VICE_ROOT for local stock ROMs')
def test_packaged_prg_stock_rom_complete_games():
    assert hasattr(verify_app,'verify_stock_rom'), 'missing stock-ROM application verifier'
    result=verify_app.verify_stock_rom(ROOT/'artifacts/app/002-numeric/vice',os.environ.get('F9_VICE_ROOT'))
    assert result['draws']==1 and result['model_wins']==1
    assert result['requests']==7
    assert result['prg_autostart']


@pytest.mark.skipif(not os.environ.get('F9_RUN_VICE'),reason='set F9_RUN_VICE=1 for stock true-drive D64 route')
def test_packaged_d64_stock_rom_complete_games():
    from scripts.build_app import build, package_disk
    from scripts.verify_app import verify_games
    built=build();disk=package_disk(built,verify_games())
    result=verify_app.verify_stock_rom(ROOT/'artifacts/app/002-numeric/vice-d64',os.environ.get('F9_VICE_ROOT'),image=disk['path'])
    assert result['d64_true_drive_autostart']
    assert result['draws']==1 and result['model_wins']==1 and result['requests']==7
