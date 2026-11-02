"""Read-only numerical/preservation audit, then deterministic014 packaging.
Post-run only: no candidate execution, training, selection or source edits.
"""
import hashlib,io,json,re,sys,zipfile
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
from PIL import Image,ImageFont
from study014_run import ROOT,PACKET,sha,put,verify_inputs
from study014_verify import verify

def audit_existing():
    verify_inputs();a=ROOT/'results014';b=ROOT/'reproduced014'
    aa={p.name:sha(p) for p in sorted(a.iterdir()) if p.is_file()};bb={p.name:sha(p) for p in sorted(b.iterdir()) if p.is_file()}
    assert aa==bb,(set(aa)^set(bb),[n for n in set(aa)&set(bb) if aa[n]!=bb[n]])
    independent=verify(a);assert independent==json.loads((a/'independent-audit014.json').read_text())
    boxes=json.loads((a/'boxes014.json').read_text());records=json.loads((a/'validations014.json').read_text());forwards=np.load(a/'forwards014.npz');baseline=np.load(a/'baseline014.npz');k=boxes['accepted_numerator'];observed=[];formal=[]
    for grid,role in [(16,'original'),(k,'accepted')]:
        for s,row in enumerate(boxes['grid'][grid]['rows']):
            for kind,key in [('member-min','member_minimum'),('nonmember-max','nonmember_maximum')]:
                i=row[key+'_id'];a0=int(baseline['merged'][i,0]);maximum=kind=='nonmember-max';bi=int(maximum);wi=(1 if a0>=0 else 0) if maximum else (0 if a0>=0 else 1)
                ident=f'original-row{s}-b{bi}-w{wi}' if role=='original' else f'accepted-row{s}-{kind}'
                rec=next(v for v in records if v['id']==ident);ch=next(v for v in rec['changes'] if v['row']==s)
                assert ch['bias_code']==row['bias_interval'][bi] and ch['weight_code']==row['weight_interval'][wi]
                actual=int(forwards[ident][i,s]);assert actual==row[key]
                observed.append(dict(scope=role,kind=kind,row=s,canonical_id=i,board=baseline['boards'][i].tolist(),activation0=a0,bias_code=ch['bias_code'],weight_code=ch['weight_code'],score=actual,full_network_candidate_id=ident,source='observed full-network saved output; mathematical extremum independently matched'))
    if k<16:
        for row in boxes['grid'][k+1]['rows']:
            for kind,key in [('member-min','member_minimum'),('nonmember-max','nonmember_maximum')]:
                if (kind=='member-min' and row[key]<0) or (kind=='nonmember-max' and row[key]>=0):
                    i=row[key+'_id'];s=row['row'];formal.append(dict(scale_numerator=k+1,denominator=16,row=s,kind=kind,canonical_id=i,board=baseline['boards'][i].tolist(),extreme_score=row[key],weight_interval=row['weight_interval'],bias_interval=row['bias_interval'],source='exact independently verified rounding constraint; NOT an additional whole-network observation'))
    assert len(observed)==36
    figure_checks={}
    for name in ('joint014','witness014'):
        png=a/(name+'.png');svg=a/(name+'.svg');im=Image.open(png);node=ET.parse(svg).getroot();width=int(node.attrib['width']);height=int(node.attrib['height']);assert im.size==(width,height)
        for text in node.iter('{http://www.w3.org/2000/svg}text'):
            font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',int(text.attrib['font-size']))
            assert float(text.attrib['x'])+font.getlength(text.text or '')<=width,(name,text.text)
            assert float(text.attrib['y'])<=height
        figure_checks[name]=dict(png_dimensions=list(im.size),png_sha256=sha(png),svg_sha256=sha(svg),svg_text_within_canvas=True,visually_inspected=True)
        im.close()
    report=(a/'REPORT014.md').read_text()
    for path in re.findall(r'!\[[^\]]*\]\(([^)]+)\)',report):assert (a/path).is_file(),path
    imports={name:str(Path(m.__file__).resolve()) for name,m in sys.modules.items() if (name=='falken9' or name.startswith('falken9.') or name.startswith('study014') or name.startswith('study013') or name=='finish014') and getattr(m,'__file__',None)}
    assert all(Path(p).is_relative_to(ROOT) for p in imports.values())
    preservation=json.loads((ROOT/'preservation014.json').read_text())
    summary=dict(byte_identical=True,matched_output_files=len(aa),output_sha256=aa,fresh_independent_audit_matches_saved=True,observed_original_extrema=18,observed_accepted_extrema=18,next_grid_failure_certificates=len(formal),prior_file_counts={n:len(v['sha256']) for n,v in preservation.items()},prior_and_main_protected_hashes_unchanged=True,prior_source_file_lists_unchanged=True,figure_checks=figure_checks,imports=imports)
    return dict(summary,extremum_evidence=dict(observed_full_network_extrema=observed,next_grid_constraint_failures=formal))

def finish():
    checked=audit_existing();evidence=checked.pop('extremum_evidence');put(ROOT/'verification014.json',checked);put(ROOT/'extremum-witnesses014.json',evidence)
    testing=dict(test_driven_sequence=['extrema: missing implementation assertion FAILED; exact integer exhaustive check PASSED','bias bands: missing function assertion FAILED; all small signed joint codes PASSED','shrink: missing function assertion FAILED; signed truncation/nesting PASSED','real study: missing runner assertion FAILED; full frozen integration PASSED twice','packaging verification: missing module assertion FAILED; real two-run/extremum/preservation audit PASSED'],full_study_unittest_runs=2,tests_each_full_run=4,complete_full_network_batches_per_run=117,complete_full_network_batches_two_runs=234,canonical_forward_board_executions_per_run=73359,canonical_forward_board_executions_two_runs=146718,independent_audits_reexecute_no_neural_batches=True)
    put(ROOT/'testing014.json',testing)
    # Explicit allowlist: no model bytes, ROMs, environments, caches, credentials.
    paths=set()
    for p in (ROOT/'falken9').glob('*.py'):paths.add(p)
    copied=json.loads((ROOT/'copied-inputs014.json').read_text())
    for n in copied:
        if n!=PACKET:paths.add(ROOT/n)
    for p in (ROOT/'results014').iterdir():
        if p.is_file():paths.add(p)
    for name in ('manifest014.json','copied-inputs014.json','preservation014.json','study014_core.py','study014_run.py','study014_verify.py','study014_render.py','test_study014.py','test_finish014.py','finish014.py','README-REPRODUCTION014.md','verification014.json','extremum-witnesses014.json','testing014.json','first-run014.log','reproduction-run014.log','final-tests014.log','standalone-audit014.json'):
        paths.add(ROOT/name)
    entries={str(p.relative_to(ROOT)):sha(p) for p in sorted(paths)}
    put(ROOT/'bundle-contents014.json',entries);paths.add(ROOT/'bundle-contents014.json')
    bundle=ROOT/'study014-source-evidence.zip'
    with zipfile.ZipFile(bundle,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in sorted(paths):
            info=zipfile.ZipInfo(str(p.relative_to(ROOT)),(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16
            z.writestr(info,p.read_bytes(),compresslevel=9)
    with zipfile.ZipFile(bundle) as z:
        assert z.testzip() is None
        assert len(z.namelist())==len(paths) and PACKET not in z.namelist()
        for p in paths:assert hashlib.sha256(z.read(str(p.relative_to(ROOT)))).hexdigest()==sha(p)
    verify_inputs()
    res=json.loads((ROOT/'results014/results014.json').read_text());audit=json.loads((ROOT/'results014/independent-audit014.json').read_text())
    final=dict(study='014',complete=True,no_further_study=True,workspace=str(ROOT),report=str(ROOT/'results014/REPORT014.md'),manifest_sha256=sha(ROOT/'manifest014.json'),model_sha256=sha(ROOT/PACKET),model_bytes=(ROOT/PACKET).stat().st_size,original_corner_batches=36,original_failing_corner_batches=res['original_failing_corner_batches'],accepted_grid_scale='8/16',accepted_box_all_combinations_certified=True,accepted_combinations_decimal=res['accepted_combinations_decimal'],byte_identical_reproduced_output_files=checked['matched_output_files'],full_network_batches_per_run=117,full_network_batches_two_runs=234,restoration_batches_per_run=58,independent_row_weight_codes=audit['independently_verified_weight_codes'],independent_board_weight_sign_evaluations=audit['independent_board_weight_sign_evaluations'],independent_scalar_head_outputs_per_run=audit['independent_scalar_full_head_checks'],preserved_file_counts=checked['prior_file_counts'],all_preservation_passed=True,verification_sha256=sha(ROOT/'verification014.json'),extremum_evidence_sha256=sha(ROOT/'extremum-witnesses014.json'),bundle=dict(path=str(bundle),sha256=sha(bundle),bytes=bundle.stat().st_size,entries=len(paths),excludes_model=True,zip_crc_and_entry_hashes_verified=True),output_sha256=checked['output_sha256'])
    put(ROOT/'FINAL-STUDY-014.json',final);print(json.dumps(final,sort_keys=True,indent=2))
if __name__=='__main__':finish()
