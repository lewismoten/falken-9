"""Independent scalar geometry/arithmetic tests, no main checkout writes."""
import importlib
from fractions import Fraction

def test_independent_signed_rounding():
    spec=importlib.util.find_spec('falken9.strategy_square004')
    assert spec is not None, 'new arithmetic module is missing'
    m=importlib.import_module('falken9.strategy_square004')
    for den in (1,2,4,8,32768):
        for n in range(-39,40):
            q,r=divmod(abs(n),den)
            gold=(q+(2*r>=den))*(-1 if n<0 else 1)
            assert m.rnd(n,den)==gold
    assert m.scaled(-3,-1)==-2
    assert m.scaled(3,2)==12

def test_new_square_geometry_and_mask_separation():
    from falken9 import strategy_square004 as m
    assert hasattr(m,'square_labels'), 'new independent square labels missing'
    b=(1,1,0,2,2,0,0,0,0)
    lab=m.square_labels(b)
    assert lab[2]['win'] and not lab[5]['block'] # own win has priority
    assert lab[0]['occupied_own'] and not lab[0]['legal']
    b=(1,1,0,0,2,0,0,0,0) # O to move must block square2
    assert m.square_labels(b)[2]['block']
    b=(1,0,0,0,2,0,0,0,1)
    assert any(x['prevention'] for x in m.square_labels(b))
    for b in [(0,)*9,(1,0,0,0,2,0,0,0,1)]:
        for s,x in enumerate(m.square_labels(b)):
            assert x['legal']==(b[s]==0)
            assert x['neutral']==(x['legal'] and not any(x[t] for t in m.TASKS))

def test_exact_paths_independent_fraction_and_expert_id_index():
    from falken9 import strategy_square004 as m
    assert hasattr(m,'bookkeep'), 'new exact bookkeeping missing'
    from falken9.flexible_integer_export import load
    from falken9.strategy_diagnostics import DiagnosticPolicy
    from scripts.build_runtime import FOUR_MODEL
    import torch,copy
    torch.set_num_threads(1)
    c=load(FOUR_MODEL);before={n:t['codes'].clone() for n,t in c['tensors'].items()}
    q=DiagnosticPolicy(c);q(torch.tensor([[0,0,0,0,0,2,2,1,1]],dtype=torch.int64))
    st={k:v.tolist()[0] for k,v in q.stages.items()}
    r=m.bookkeep(c,st)
    for s in range(9):
        assert sum(r['terms'][k][s] for k in r['terms'])==st['logits'][s]*m.D
    for slot,e in enumerate(st['routes']):
        for h in range(4):
            for lane in range(8):
                for s in range(9):
                    gold=Fraction(st['expert_hidden'][e][h])*int(c['tensors']['expert_w2']['codes'][e,h,lane])*Fraction(2)**c['tensors']['expert_w2']['exponents'][e*8+lane]*Fraction(st['gates'][slot],32768)*int(c['tensors']['output.weight']['codes'][s,lane])*Fraction(2)**c['tensors']['output.weight']['exponents'][s]
                    assert Fraction(r['paths'][slot][h][lane][s],m.D)==gold
    assert r['expert_ids']==st['routes']
    assert all(torch.equal(before[n],t['codes']) for n,t in c['tensors'].items())
    assert r['reconstructed_logits']==st['logits']

def test_finite_run_acceptance(tmp_path):
    spec=importlib.util.find_spec('scripts.model_strategy_study004')
    assert spec is not None, 'new finite runner missing'
    from scripts.model_strategy_study004 import run
    out=tmp_path/'study004';summary=run(out)
    assert summary['canonical']==627 and summary['raw']==4520
    assert summary['baseline_stage_checks']==13167
    assert summary['prior69_verified']==69 and summary['prior23_verified']==23
    assert summary['exact_logits']==5643 and summary['bookkeeping_max_error']==0
    assert summary['identity_all_stages']
    assert summary['interventions']<=38
    import json,struct
    from pathlib import Path
    from fractions import Fraction
    from falken9.symmetry import canonicalize
    from falken9.strategy_diagnostics import enumerate_boards
    from scripts.build_runtime import FOUR_MODEL
    cases=json.loads((out/'cases.json').read_text())
    books=json.loads((out/'exact-paths.json').read_text());den=books['denominator']
    from falken9.strategy_square004 import square_labels,rnd
    # Independent head recomputation starts from retained merged, raw packet
    # codes and declared exponents, not the generated contribution sum.
    coords=json.loads((out/'weight-coordinates.json').read_text())['scalars']
    raw=FOUR_MODEL.read_bytes();weights={}
    for r in coords:
        assert struct.unpack_from('<h',raw,r['packet_byte_offset'])[0]==r['code']
        assert int(r['runtime_address'],16)==0x4000+r['packet_byte_offset']
        assert struct.unpack_from('<b',raw,r['exponent_byte_offset'])[0]==r['exponent']
        assert int(r['exponent_runtime_address'],16)==0x4000+r['exponent_byte_offset']
        weights[(r['tensor'],tuple(r['coordinates']))]=r
    zeroexecuted=0
    for i,bk in enumerate(books['records']):
        assert len(bk['expert_ids'])==2
        for e in range(4):assert (cases[i]['hidden'][e] is None)==(e not in bk['expert_ids'])
        for slot,e in enumerate(bk['expert_ids']):
            if not bk['gates'][slot]:
                zeroexecuted+=1
                assert cases[i]['hidden'][e] is not None
                assert all(v==0 for unit in bk['paths'][slot] for lane in unit for v in lane)
        for s in range(9):
            v=Fraction(0)
            for j in range(8):
                r=weights[('output.weight',(s,j))]
                v+=bk['merged'][j]*r['code']*Fraction(2)**r['exponent']
            gold=rnd(v.numerator,v.denominator)+weights[('output.bias',(s,))]['code']
            assert gold==cases[i]['logits'][s]
            assert sum(v[s] for v in bk['terms'].values())==gold*den
    assert zeroexecuted==summary['executed_zero_gate_observations'] and zeroexecuted>0
    legal=set(enumerate_boards())
    for r in json.loads((out/'matched-relocations.json').read_text()):
        a=tuple(r['receiver_raw']);b=tuple(r['donor_raw'])
        assert a in legal and b in legal and sum(x!=y for x,y in zip(a,b))==2
        assert sum(x!=0 for x in a)==sum(x!=0 for x in b)
        cb,tr=canonicalize(b)
        assert list(cb)==cases[r['donor']]['board'] and list(tr)==r['donor_raw_to_canonical']
        assert r['receiver_square']==next(s for s in range(9) if tr[s]==r['donor_square'])
        assert cases[r['receiver']]['fold']==cases[r['donor']]['fold']==r['fold']
        assert square_labels(a)[r['receiver_square']][r['task']]
        assert not square_labels(b)[r['receiver_square']][r['task']]
    # Geometry must commute with every frozen external permutation.
    from falken9.symmetry import TRANSFORMS
    for case in cases:
        a=case['board'];lab=square_labels(a)
        for tr in TRANSFORMS:
            b=[0]*9
            for s in range(9):b[tr[s]]=a[s]
            ll=square_labels(b)
            assert all(ll[tr[s]]==lab[s] for s in range(9))

def test_annotated004_evidence_figures(tmp_path):
    spec=importlib.util.find_spec('scripts.render_strategy_study004')
    assert spec is not None, 'new measured renderer missing'
    from scripts.model_strategy_study004 import run
    from scripts.render_strategy_study004 import render
    import json
    from PIL import Image
    out=tmp_path/'figures004';run(out);render(out)
    meta=json.loads((out/'figure-metadata.json').read_text())
    assert len(meta['figures'])==2 and meta['model_immutable']
    assert meta['callouts']['A']['canonical_id']==49
    for r in meta['figures']:
        assert Image.open(out/(r['name']+'.png')).size==tuple(r['size'])
        assert '<svg ' in (out/(r['name']+'.svg')).read_text()
    assert 'not probabilities' in (out/'REPORT.md').read_text()

def test_deterministic004_archive_refuses_payloads(tmp_path):
    spec=importlib.util.find_spec('scripts.finish_strategy_study004')
    assert spec is not None, 'new deterministic archive helper missing'
    from scripts.finish_strategy_study004 import pack
    import pytest,zipfile
    entries={'new004.py':b'print(1)\n','REPORT004.md':b'research\n'}
    a=tmp_path/'a004.zip';b=tmp_path/'b004.zip'
    pack(entries,a);pack(entries,b)
    assert a.read_bytes()==b.read_bytes()
    assert zipfile.ZipFile(a).testzip() is None
    with pytest.raises(ValueError):pack({'secret.env':b'x'},tmp_path/'bad004.zip')
    with pytest.raises(ValueError):pack({'model.f9j':b'x'},tmp_path/'model004.zip')
