import importlib.util
from pathlib import Path
from falken9.canonical_training import load_data
from test_canonical_integer_export import SOURCE


def test_exhaustive_canonical_integer_gate(tmp_path):
    spec=importlib.util.spec_from_file_location('canonical_integer_evaluator',Path('scripts/evaluate_canonical_integer.py'))
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    data=load_data('data/nonterminal-legal-histories.jsonl')
    result=module.evaluate_candidate(SOURCE,data,tmp_path,frac=11,matrix_bits=16,activation_bits=32,attention_mode='early',interpolate=True,scalar=True,public=True)
    assert result['accepted']
    assert result['canonical_count']==627 and result['board_count']==4520 and result['history_count']==294778
    assert result['scalar_logit_mismatches']==result['scalar_route_mismatches']==result['materialized_logit_mismatches']==0
    assert result['public_wrapper_mismatches']==0
    assert result['statistics']['saturations']==0
    assert result['total_bytes']<=8192
