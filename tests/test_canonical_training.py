import json
from pathlib import Path
import torch
from falken9.model import ModelConfig
from falken9.canonical_model import CanonicalPolicy
from falken9 import canonical_training as ct


def test_training_full_set_transforms_and_real_saved_evaluation(tmp_path):
    source = tmp_path / 'sample.jsonl'
    rows = [dict(history='', board='.../.../...', optimal_move='e', optimal_moves=list('ebdfhcgia')),
            dict(history='a', board='X../.../...', optimal_move='e', optimal_moves=['e']),
            dict(history='c', board='..X/.../...', optimal_move='e', optimal_moves=['e'])]
    source.write_text(''.join(json.dumps(row) + '\n' for row in rows))
    data = ct.load_data(source, verify_digest=False)
    assert data['canonical_boards'].shape == (2, 9)
    assert int(data['targets'][data['board_canonical_indices'][0]].sum()) == 9
    assert data['restoration_errors'] == 0
    torch.manual_seed(7)
    model = CanonicalPolicy(ModelConfig(4, 4))
    before = model.output.weight.detach().clone()
    result = ct.train_candidate(model, data, tmp_path / 'run', steps=3, seconds=10,
                                eval_every=1, seed=7)
    assert not torch.equal(before, model.output.weight)
    assert result['steps_completed'] == 3
    assert (tmp_path / 'run' / 'best.pt').is_file()
    assert (tmp_path / 'run' / 'evaluation.json').is_file()
    assert result['gate']['history_count'] == 3
    assert result['gate']['board_count'] == 3
    assert result['gate']['canonical_count'] == 2
    assert result['payload_estimate']['total_encoded_bytes'] > result['payload_estimate']['weight_bytes']
    evaluated = ct.evaluate(model, data, tmp_path / 'again')
    assert evaluated['board_move_errors'] == result['gate']['board_move_errors']


def test_packed_gate_accounts_islands_and_direct_parity(tmp_path):
    from falken9.canonical_model import CanonicalConfig
    path=tmp_path/'empty.jsonl'
    path.write_text(json.dumps(dict(history='',board='.../.../...',optimal_move='e',optimal_moves=list('ebdfhcgia')))+'\n')
    data=ct.load_data(path,verify_digest=False)
    model=CanonicalPolicy(CanonicalConfig(4,4,'ternary','int8'))
    with torch.no_grad():
        model.output.weight.zero_(); model.output.bias.fill_(1.)
    result=ct.packed_gate(model,data,tmp_path/'packed')
    assert result['fake']['accepted'] and result['decoded']['accepted']
    assert result['max_abs_logit_error'] == 0
    estimate=ct.payload_estimate(model)
    assert estimate['total_encoded_bytes'] == result['encoded_bytes']
    assert estimate['scale_bytes'] == (4 + 2*9 + 6)*4


def test_quantized_stage_direct_acceptance_and_frozen_scope(tmp_path):
    from dataclasses import asdict
    from falken9.canonical_model import CanonicalConfig
    path=tmp_path/'empty.jsonl'
    path.write_text(json.dumps(dict(history='',board='.../.../...',optimal_move='e',optimal_moves=list('ebdfhcgia')))+'\n')
    data=ct.load_data(path,verify_digest=False)
    model=CanonicalPolicy(CanonicalConfig(4,4))
    with torch.no_grad():
        model.output.weight.zero_(); model.output.bias.fill_(1.)
    teacher=tmp_path/'teacher.pt'
    torch.save(dict(config=asdict(model.config),state_dict=model.state_dict(),canonical_set_errors=0),teacher)
    result=ct.run_quantized_stage(teacher,data,tmp_path/'stage','float','int8',steps=2,seconds=10)
    assert result['status']=='accepted-direct-materialization'
    assert result['steps_completed']==0 and result['frozen_byte_identity']
    assert (tmp_path/'stage'/'best.pt').is_file()
    assert result['packed']['decoded']['accepted']


def test_canonical_cli_entry_points():
    import subprocess
    import sys
    for script in ['scripts/train_canonical.py', 'scripts/evaluate_canonical.py']:
        run = subprocess.run([sys.executable, script, '--help'], capture_output=True, text=True)
        assert run.returncode == 0, run.stderr
        assert 'usage:' in run.stdout


def test_training_rejects_incomplete_canonical_set_conflicts(tmp_path):
    path = tmp_path / 'conflict.jsonl'
    rows = [dict(history='a', board='X../.../...', optimal_move='e', optimal_moves=['e']),
            dict(history='c', board='..X/.../...', optimal_move='e', optimal_moves=['e', 'a'])]
    path.write_text(''.join(json.dumps(row) + '\n' for row in rows))
    import pytest
    with pytest.raises(ValueError, match='canonical.*conflict'):
        ct.load_data(path, verify_digest=False)
