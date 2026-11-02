"""Offline diagnostics never enter the shipped inference path."""
import importlib.util


def test_tactical_labels_have_independent_board_semantics():
    assert importlib.util.find_spec('falken9.strategy_diagnostics'), 'missing offline tactical labels'
    from falken9.strategy_diagnostics import tactical, enumerate_boards
    # X to move, immediate winning square c; O also threatens f.
    labels=tactical((1,1,0,2,2,0,0,0,0))
    assert labels['wins']==[2] and labels['opponent_wins']==[5]
    assert not labels['must_block']  # winning now has priority in this definition
    labels=tactical((1,0,0,2,2,0,1,0,0))
    assert labels['wins']==[] and labels['block_squares']==[5] and labels['must_block']
    labels=tactical((1,0,0,0,2,0,0,0,1))  # O to move; opponent has fork opportunities
    assert labels['opponent_forks'] and labels['fork_prevention_squares']
    boards=enumerate_boards()
    assert len(boards)==4520
    from falken9.symmetry import canonicalize
    assert len({canonicalize(b)[0] for b in boards})==627


def test_instrumented_integer_oracle_matches_all_frozen_logits_and_copy_interventions():
    from falken9 import strategy_diagnostics as diag
    assert hasattr(diag,'DiagnosticPolicy'), 'missing exact intervention oracle'
    import torch
    from scripts.verify_app import fixture_records
    from scripts.build_runtime import FOUR_MODEL
    from falken9.flexible_integer_export import load
    torch.set_num_threads(1)
    rows=sorted(fixture_records()[0].values(),key=lambda r:r['canonical_index'])
    boards=torch.tensor([r['board'] for r in rows],dtype=torch.int64)
    candidate=load(FOUR_MODEL)
    policy=diag.DiagnosticPolicy(candidate)
    logits=policy(boards)
    assert logits.tolist()==[r['stages']['logits'] for r in rows]
    assert policy.stages['routes'].tolist()==[r['stages']['routes'] for r in rows]
    for name in ['readout_pre','readout_gelu','norm2_output','router_scores','gates','merged']:
        assert policy.stages[name].tolist()==[r['stages'][name] for r in rows], name
    experiment=diag.DiagnosticPolicy(candidate,[dict(stage='expert_outputs',expert=0,mode='zero')])
    changed=experiment(boards)
    assert torch.equal(experiment.stages['routes'],policy.stages['routes'])
    assert bool((changed!=logits).any())
    copy=diag.parameter_copy(candidate,'output.bias',(0,),17,add=True)
    shifted=diag.DiagnosticPolicy(copy)(boards)
    assert torch.equal(shifted[:,0],logits[:,0]+17)
    assert torch.equal(shifted[:,1:],logits[:,1:])
    assert candidate['tensors']['output.bias']['codes'][0]!=copy['tensors']['output.bias']['codes'][0]


def test_probe_controls_and_permutation_roundtrips():
    from falken9 import strategy_diagnostics as diag
    assert hasattr(diag,'ridge_scores'), 'missing held-out probe'
    import numpy as np
    x=np.arange(60,dtype=float).reshape(30,2);y=(x[:,0]>30).astype(int)
    scores=diag.ridge_scores(x[:20],y[:20],x[20:])
    assert scores.shape==(10,) and np.isfinite(scores).all()
    assert diag.binary_metrics(np.array([0,1,0,1]),np.array([0.,1.,.2,.8]))['auc']==1.0
    from falken9.symmetry import TRANSFORMS,transform_board,inverse,canonicalize
    for board in diag.enumerate_boards():
        target=diag.offline_optimal_set(board)
        for transform in TRANSFORMS:
            moved=transform_board(board,transform)
            assert transform_board(moved,inverse(transform))==board
            assert diag.offline_optimal_set(moved)=={transform[i] for i in target}


def test_annotated_maps_bind_real_parameters_and_dynamic_activations(tmp_path):
    assert importlib.util.find_spec('scripts.render_strategy_maps'), 'missing actual annotated map renderer'
    import json
    import struct
    import xml.etree.ElementTree as ET
    from pathlib import Path
    from PIL import Image
    from scripts.render_strategy_maps import render
    from scripts.model_strategy_study import run
    from scripts.build_runtime import FOUR_MODEL
    study=tmp_path/'study';summary=run(study)
    assert summary['canonical_boards']==627 and summary['raw_boards']==4520
    assert summary['interventions']==55
    maps=tmp_path/'maps';metadata=render(study,maps)
    assert metadata['weights_are_static'] and metadata['activations_and_gates_are_input_dependent']
    assert set(metadata['callout_ids'])=={'A','B','C','A1','B1','C1','P1','T1'}
    raw=FOUR_MODEL.read_bytes()
    for choice in json.loads((study/'callouts.json').read_text()):
        parameter=choice['parameter']
        assert struct.unpack_from('<h',raw,parameter['packet_byte_offset'])[0]==parameter['stored_value']
    for image in metadata['figures']:
        assert Image.open(maps/(image['name']+'.png')).size==tuple(image['size'])
        assert ET.parse(maps/(image['name']+'.svg')).getroot().tag.endswith('svg')
        assert all(0<=b[0]<=b[2]<=image['size'][0] and 0<=b[1]<=b[3]<=image['size'][1] for b in image['text_bounds'])
