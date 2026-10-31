"""Full materialized/scalar/wrapper gates for both handoff configurations."""
import importlib.util
from pathlib import Path
import pytest
import torch
from falken9.canonical_training import load_data


@pytest.fixture(scope='module')
def data():
    torch.set_num_threads(1)
    return load_data('data/nonterminal-legal-histories.jsonl')


@pytest.mark.parametrize('frac,components,digest,usage',[
    (11,(), 'fe180f8a931f9d92d8aa39da337bc819d0dbe4e6d971edcba00324fbc18a91c1',[301,258,355,340]),
    (10,('expert_w2','output.weight','projection.weight'),
     '94b46bcae2476a63716fb05c8820883e4e24b85960de7ea0d34c449bcd4f8faa',[300,259,355,340]),
])
def test_exhaustive_handoff(frac,components,digest,usage,data,tmp_path):
    spec=importlib.util.spec_from_file_location('flexible_evaluator',Path('scripts/evaluate_flexible_integer.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    result=module.evaluate_candidate(data,tmp_path,frac=frac,component_int8=components)
    assert result['accepted']
    assert (result['canonical_count'],result['board_count'],result['history_count'])==(627,4520,294778)
    assert result['artifact_sha256']==digest
    assert result['route_usage']==usage
    for field in ('canonical_set_errors','board_set_errors','history_set_errors','board_move_errors',
                  'history_move_errors','scalar_logit_mismatches','scalar_route_mismatches',
                  'materialized_logit_mismatches','materialized_route_mismatches','public_wrapper_mismatches'):
        assert result[field]==0
    assert result['statistics']['saturations']==0
    assert result['statistics']['expert_evaluations']==1254
    assert result['inventory_detail']['logical_macs']['total']==4408
    assert result['inventory_detail']['mixed_int8_projection_macs']==(712 if components else 0)
    assert not result['inventory_detail']['target_residency_proven']
    assert result['inventory_detail']['decoder_kernel_6502_code_bytes'] is None
