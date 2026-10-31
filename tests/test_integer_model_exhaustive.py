"""Exhaustive gates are real tests, not acceptance assumptions."""
import importlib.util
from pathlib import Path
import torch


def test_evaluator_materialized_and_scalar_gate(tmp_path):
    spec=importlib.util.spec_from_file_location('evaluate_integer','scripts/evaluate_integer.py')
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    from falken9.training import load_dataset
    data=load_dataset('data/nonterminal-legal-histories.jsonl')
    result=module.evaluate_candidate('artifacts/training/float-search/w8-h8-float/best.pt',data,tmp_path,8,8,scalar_oracle=True)
    assert result['board_count']==4520
    assert result['history_count']==294778
    assert result['materialized_logit_mismatches']==0
    assert result['scalar_oracle_logit_mismatches']==0
    assert result['scalar_oracle_route_mismatches']==0
    assert result['status'] in ('accepted','rejected')
    assert result['accepted']==(result['history_mismatches']==0)
    assert result['source_sha256_after']==result['source_sha256']
    assert result['overflow_count']==0
    assert result['bounds']['attention_scaled_absolute_bound']==99514392248320
    assert result['bounds']['int32_whole_model_safe'] is False
    assert result['bounds']['int64_whole_model_safe'] is True
    assert (tmp_path/'counterexamples.jsonl').exists()
