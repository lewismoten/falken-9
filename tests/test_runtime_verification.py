from scripts import verify_runtime


def test_full_forward_evidence_is_real_and_partial_not_exhaustive(tmp_path):
    assert hasattr(verify_runtime,'verify_full'), 'full-forward verification missing'
    summary=verify_runtime.verify_full(canonical_limit=1,workers=1,output=tmp_path)
    assert summary['canonical_boards_checked']==1
    assert summary['full_forward_accepted'] is False
    assert summary['stage_mismatches']==0
    assert summary['cycles']['minimum']>7000000
    assert summary['memory_writes_total']>0
    assert (tmp_path/'shard-0.jsonl').exists()
    assert (tmp_path/'safety-audit.json').exists()
    assert summary['safety_audit']['mac_operand_abs_limit']==8388607



def test_verification_report_comes_from_executed_target(tmp_path):
    assert hasattr(verify_runtime,'verify'), 'durable target verification missing'
    summary=verify_runtime.verify(canonical_limit=1,output=tmp_path)
    assert summary['canonical_boards_checked']==1
    assert summary['stage_mismatches']==0
    assert summary['full_forward_accepted'] is False
    assert summary['cycles']['minimum']>0
    assert (tmp_path/'checkpoints.json').exists()
