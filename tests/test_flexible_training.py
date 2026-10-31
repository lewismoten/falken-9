"""Bounded real training, checkpoint reload, and expert pruning lineage."""
from dataclasses import asdict
from pathlib import Path
import subprocess
import sys
import torch
from falken9.flexible_model import FlexiblePolicy, FlexibleConfig


def test_bounded_training_and_encoded_reload(tmp_path):
    from falken9.flexible_training import train_candidate, packed_gate, route_inventory
    from falken9.canonical_training import evaluate
    boards = torch.zeros(1,9,dtype=torch.long)
    data = dict(canonical_boards=boards,targets=torch.ones(1,9),boards=[tuple([0]*9)],
                board_canonical_indices=[0],transforms=[tuple(range(9))],labels=['e'],sets=[set('abcdefghi')],
                histories=[''],history_indices=torch.tensor([0]),dataset_sha256='smoke',restoration_errors=0,
                transform_errors=0,transformations_checked=8)
    model = FlexiblePolicy(FlexibleConfig(experts=3))
    result = train_candidate(model,data,tmp_path,steps=2,seconds=10,eval_every=1)
    assert result['steps_completed'] <= 2
    assert (tmp_path/'best.pt').is_file()
    checkpoint = torch.load(tmp_path/'best.pt',weights_only=False)
    assert checkpoint['config']['experts'] == 3
    gate = packed_gate(model,data,tmp_path/'packed')
    assert gate['max_abs_logit_error'] == 0
    assert gate['routes_equal']
    assert gate['byte_ledger']['fp32_vector_islands'] == sum(x['bytes'] for x in gate['inventory'] if x['bits']==32 and len(x['shape'])==1)
    inv = route_inventory(model,boards)
    assert sum(inv['canonical_selection_counts']) == 2
    assert inv['expert_macs_per_board'] == 2*2*8*4
    assert len(inv['per_expert_weights']) == 3


def test_selected_bank_warmstart_is_explicit(tmp_path):
    from falken9.flexible_training import initialize_from_checkpoint
    teacher = FlexiblePolicy(FlexibleConfig(experts=4))
    path = tmp_path/'teacher.pt'
    torch.save(dict(config=asdict(teacher.config),state_dict=teacher.state_dict()),path)
    model = FlexiblePolicy(FlexibleConfig(experts=2))
    lineage = initialize_from_checkpoint(model,path,[3,1])
    assert lineage['selected_experts'] == [3,1]
    assert lineage['source_sha256']
    assert torch.equal(model.expert_w1,teacher.expert_w1[[3,1]])
    assert torch.equal(model.router.weight,teacher.router.weight[[3,1]])
    assert torch.equal(model.readout.weight,teacher.readout.weight)


def test_hard_mining_loss_preserves_all_legal_bits():
    from falken9.flexible_training import policy_loss
    logits=torch.zeros(2,9,requires_grad=True)
    targets=torch.ones(2,9)
    legal=torch.ones(2,9,dtype=torch.bool); legal[0,0]=False
    base=policy_loss(logits,targets,legal)
    focused=policy_loss(logits,targets,legal,hard_mining=.5)
    assert torch.allclose(focused,base*1.5)
    focused.backward()
    assert logits.grad[0,0]==0
    assert bool((logits.grad[legal]!=0).all())


def test_cli_entry_points_help():
    for name in ('train_flexible','evaluate_flexible'):
        result = subprocess.run([sys.executable, 'scripts/'+name+'.py','--help'],capture_output=True,text=True)
        assert result.returncode == 0, result.stderr
