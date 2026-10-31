from scripts import verify_runtime


def test_verification_report_comes_from_executed_target(tmp_path):
    assert hasattr(verify_runtime,'verify'), 'durable target verification missing'
    summary=verify_runtime.verify(canonical_limit=1,output=tmp_path)
    assert summary['canonical_boards_checked']==1
    assert summary['stage_mismatches']==0
    assert summary['full_forward_accepted'] is False
    assert summary['cycles']['minimum']>0
    assert (tmp_path/'checkpoints.json').exists()
