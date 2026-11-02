import torch
from pathlib import Path


def test_frozen_study_runner_contract():
    import json
    root=Path(__file__).resolve().parent
    m=json.loads((root/'experiment-study009.json').read_text())
    assert len(m['components'])*len(m['variants'])==24
    assert (root/'study009_run.py').exists(), 'missing bounded study runner'
    import study009_run as r
    assert callable(r.run) and callable(r.scalar_audit) and callable(r.raw_wrapper)


def test_measured_evidence_and_renderer_contract():
    assert (Path(__file__).resolve().parent/'study009_render.py').exists(), 'missing measured renderer'
    import study009_render as r
    out=Path(__file__).resolve().parent/'artifacts/interpretability/study-009-final'
    cases=r.case_records(out)
    assert cases[0]['scope']=='value' and cases[0]['canonical_id']==109
    assert cases[0]['variants']['plain']['empty']
    assert not cases[0]['variants']['restore-baseline-router-scores']['empty']
    harm=next(c for c in cases if c['label']=='restoration-introduced-damage')
    assert harm['variants']['plain']['correct'] and not harm['variants']['restore-baseline-router-scores']['correct']
    robust=next(c for c in cases if c['label']=='robust-negative')
    assert robust['variants']['plain']['members']==robust['variants']['baseline']['members']


def test_diagram_caption_and_pairing_truth():
    out=Path(__file__).resolve().parent/'artifacts/interpretability/study-009-final'
    svg=(out/'overview009.svg').read_text()
    assert '0 legal-set changes' in svg, 'zero changes must not be captioned zero legal sets'
    raw=(out/'raw-alignment009.svg').read_text()
    assert 'M540,249 L625,249' not in raw, 'do not connect coarse canonical to baseline raw board'


def test_independent_audit_contract():
    root=Path(__file__).resolve().parent
    assert (root/'study009_verify.py').exists(), 'missing independent artifact audit'
    import study009_verify as v
    assert v.independent_round(-3,2)==-2
    assert v.independent_round(3,2)==2
    assert v.independent_round(-1,4)==0
    report=v.audit(root/'artifacts/interpretability/study-009-final')
    assert report['specifications']==24 and report['prior_files_unchanged']==1114
    assert report['raw_public_wrapper_calls']==108480
    assert report['all_self_controls_exact'] and report['all_clean_restorations_exact']
    assert report['final_affine_scalar_checks']==135432


def test_report_generator_contract():
    root=Path(__file__).resolve().parent
    assert (root/'study009_report.py').exists(), 'missing data-bound report generator'
    import study009_report as r
    text=r.report_text(root/'artifacts/interpretability/study-009-final')
    assert 'NOT historical INT8 reproduction' in text
    assert '34 rescued / 8 introduced' in text
    assert 'same 627 receiver boards' in text
    assert 'mechanism009.png' in text and 'raw-alignment009.png' in text


def test_final_artifact_byte_reproduction_and_logical_bytes():
    root=Path(__file__).resolve().parent
    assert (root/'study009_finalize.py').exists(), 'missing final artifact gate'
    from study009_finalize import check_artifacts
    report=check_artifacts()
    assert report['artifact_count']==50 and report['logical_code_scalars']==736
    assert report['figure_pairs']==5 and report['artifacts_byte_identical']

def test_signed8_exact_row_scaling():
    import study009_core as c
    assert hasattr(c,'coarsen_row'), 'missing signed8 row conversion'
    q,e,k,clipped=c.coarsen_row([32700,-32700,128,-128,0],-14)
    assert (q,e,k,clipped)==([64,-64,0,0,0],-5,9,0)
    assert c.coarsen_row([254,-254,127,-127,1,-1],-12)==([127,-127,64,-64,1,-1],-11,1,0)
    assert c.coarsen_row([0,0],-15)==([0,0],-15,0,0)


def test_packet_conversion_and_real_cutpoints():
    import copy,numpy as np
    import study009_core as c
    assert hasattr(c,'approximate') and hasattr(c,'CutPolicy'), 'missing packet conversion and cutpoints'
    from study005_run import baseline
    b,bt,packet,y,st,*_=baseline()
    low,meta=c.approximate(packet,'query.weight')
    assert low['tensors']['query.weight']['bits']==8
    assert meta['clipped']==0 and meta['shape']==[8,8]
    for n in packet['tensors']:
        if n!='query.weight':
            assert torch.equal(low['tensors'][n]['codes'],packet['tensors'][n]['codes'])
            assert low['tensors'][n]['exponents']==packet['tensors'][n]['exponents']
    p=c.CutPolicy(copy.deepcopy(low));yp=p(bt).numpy().copy()
    for stage in ('router_scores','merged'):
        q=c.CutPolicy(copy.deepcopy(low),stage,p.stages[stage]);yq=q(bt).numpy()
        assert np.array_equal(yq,yp)
        assert all(torch.equal(q.stages[k],p.stages[k]) for k in p.stages)
    q=c.CutPolicy(copy.deepcopy(low),'router_scores',torch.tensor(st['router_scores']));q(bt)
    assert np.array_equal(q.stages['routes'],st['routes'])
    assert np.array_equal(q.stages['gates'],st['gates'])
    q=c.CutPolicy(copy.deepcopy(low),'merged',torch.tensor(st['merged']))
    assert np.array_equal(q(bt).numpy(),y)
    for i in range(627):
        changed_route=set(p.stages['routes'][i].tolist())!=set(st['routes'][i].tolist())
        if changed_route:
            # Observations on unselected experts are placeholders, not measured zeros.
            for e in range(4):
                if e not in q.stages['routes'][i].tolist():assert not bool(q.stages['expert_outputs'][i,e].any())
