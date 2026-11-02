"""Research012 final exact-byte, preservation, source and safe archive gate."""
import datetime,json,re,hashlib,xml.etree.ElementTree as ET
from pathlib import Path
from study1011_finalize import compare,archive,hashes
ROOT=Path(__file__).resolve().parent
ART=ROOT/'artifacts/interpretability'
A=ART/'study-012-final';B=ART/'study-012-reproduced-clean'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def new(n,v):
    p=ROOT/n;assert not p.exists();p.write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')
def finalize():
    from PIL import Image
    preserved=json.loads((ROOT/'preservation-before012.json').read_text())
    for n,h in preserved.items():assert sha(ROOT/n)==h,n
    result=compare(A,B);audit=json.loads((A/'independent-audit012.json').read_text());assert audit['passed']
    assert re.search(r'4 passed\b',(ROOT/'tests012-final.txt').read_text())
    assert re.search(r'31 passed\b',(ROOT/'regression-study012-final.txt').read_text())
    for sid in ('010','011'):
        v=json.loads((ROOT/f'verification-study{sid}.json').read_text())
        for n,h in v['source_sha256'].items():assert sha(ROOT/n)==h,n
        for n,h in v['artifacts']['sha256'].items():assert sha(ART/f'study-{sid}-final'/n)==h,n
    links=0
    for p in [A/'REPORT012.md',A/'SYNTHESIS010-012.md',ROOT/'README-REPRODUCTION012.md']:
        for target in re.findall(r'\]\(([^)]+)\)',p.read_text()):assert (p.parent/target).resolve().is_file(),(p,target);links+=1
    for p in A.glob('*.png'):
        r=ET.fromstring(p.with_suffix('.svg').read_text());assert (int(r.attrib['width']),int(r.attrib['height']))==Image.open(p).size
        assert r.findall('.//{http://www.w3.org/2000/svg}text')
    m=json.loads((ROOT/'experiment-study012.json').read_text());now=datetime.datetime.now(datetime.timezone.utc);elapsed=(now-datetime.datetime.fromisoformat(m['started_utc'])).total_seconds();assert elapsed<1800
    old=json.loads((ROOT/'verification-study010.json').read_text());names=list(old['source_sha256'])
    names+=['study012_freeze.py','study012.py','study012_audit.py','study012_finalize.py','test_study012.py','NOVELTY-STUDY-012.md','experiment-study012.json','preservation-before012.json','README-REPRODUCTION012.md','freeze-study012.log','freeze-study012-completed.log','execution-study012.log','execution-study012-retry.log','reproduction-study012-clean.log','independent-study012.log','independent-study012-clean.log','tests012-final.txt','regression-study012-final.txt','render-study012-corrected.log','study012-original-visual.zip','RESEARCH-HANDOFF-010-011.json']
    names+=sorted(p.name for p in ROOT.glob('tests012-red-*.txt'))+sorted(p.name for p in ROOT.glob('tests012-green-*.txt'))
    assert len(names)==len(set(names));files={f'source/{n}':ROOT/n for n in names};again=dict(files)
    for name in ('study-010-final','study-011-final','study-010-011-walkthrough'):
        for n in hashes(ART/name):files[f'evidence/{name}/{n}']=ART/name/n;again[f'evidence/{name}/{n}']=ART/name/n
    files.update({f'evidence/study-012-final/{n}':A/n for n in hashes(A)});again.update({f'evidence/study-012-final/{n}':B/n for n in hashes(B)})
    review=ART/'study-012-visual-review'
    for p in review.glob('*'):files[f'visual-review012/{p.name}']=p;again[f'visual-review012/{p.name}']=p
    z=archive(ROOT/'study012-source-evidence.zip',files);zr=archive(ROOT/'study012-source-evidence-reproduced.zip',again);assert z['sha256']==zr['sha256']
    verification=dict(status='PASS',study='012',manifest_sha256=sha(ROOT/'experiment-study012.json'),artifacts=result,independent=audit,source_sha256={n:sha(ROOT/n) for n in names},bundle=z,reproduced_bundle=zr,zip_byte_identical=True,prior_files_unchanged=len(preserved),preservation_manifest_sha256=sha(ROOT/'preservation-before012.json'),tests_passed=4,related_regression_tests_passed=31,figure_pairs=2,visual_review=dict(native=True,report_width_px=900,caption_correction_only=True,previews_sha256=hashes(review)),links_checked=links,elapsed_seconds=elapsed,verified_utc=now.isoformat(),new_neural_calls=0,main_checkout_written=False,training=False,deployment=False,source_model_sha256=m['source_model_sha256'],issues=['Self-inventory captured empty in-flight freeze log. Completion preserved separately, original empty log restored; first execution correctly refused mismatched preservation hash.','First color legend omitted red false members; failing test, preserved original visuals, wording correction and clean full reproduction retained.'],stop='The only optional follow-up; no013 or expanded panel.')
    new('verification-study012.json',verification)
    rows=json.loads((A/'results012.json').read_text());final=dict(study='012',status='COMPLETE_AND_VERIFIED',report=str(A/'REPORT012.md'),combined_illustrated_synthesis=str(A/'SYNTHESIS010-012.md'),verification=str(ROOT/'verification-study012.json'),manifest=str(ROOT/'experiment-study012.json'),results=rows,artifacts=result,source_evidence_bundle={k:z[k] for k in ('path','sha256','bytes','entries')},prior_files_unchanged=len(preserved),elapsed_seconds=elapsed,new_neural_calls=0,tests=4,related_regression_tests=31,negative_finding='All four external policies are perfectly full-set D4 equivariant, but none matches complete optimal sets on4520/4520. Enforced symmetry is not correctness or learned invariance.',stop='No further studies.',issues=verification['issues'])
    new('FINAL-STUDY-012.json',final)
    md=['# Research012 complete and independently verified','', '**Perfect full-set equivariance does not restore correctness.** Four fixed off-contract group aggregations all pass36,160 board/transform checks each, but exact full sets are mean1576, intersection312, union1388, votes1976 /4520; canonicalizing wrapper4520/4520. No new neural forward, training or deployment.','',f"{result['artifact_count']} files byte-identically reproduced;2 measured PNG/SVG pairs, native/900px reviewed;4 new tests and31 related tests pass. All1414 prior files—including010/011 source, reports and bundles—remain unchanged. Independent audit checks162720 membership scalars and144640 full-set board/transform equalities.",'',f"- Report: `{A/'REPORT012.md'}`",f"- Combined illustrated synthesis: `{A/'SYNTHESIS010-012.md'}`",f"- Verification: `{ROOT/'verification-study012.json'}`",f"- Source/evidence ZIP: `{z['path']}`",f"- ZIP SHA-256: `{z['sha256']}`; {z['entries']} entries; deterministic reproduced ZIP identical.",f"- Optional study wall time: {elapsed:.1f}s (<1800s).",'', 'Original self-log/legend issues preserved and corrected; no scope expansion. This is the only optional study: stop, no013. Parent owns main-report integration.','']
    p=ROOT/'FINAL-STUDY-012.md';assert not p.exists();p.write_text('\n'.join(md))
    handoff=dict(status='PASS',studies=['010','011','012'],root=str(ROOT),main_checkout_written=False,initial1258files_preserved=True,pre012files_preserved=len(preserved),all_reproduced_artifact_files=38+result['artifact_count'],native_png_svg_pairs=8,combined_synthesis=str(A/'SYNTHESIS010-012.md'),finals=[str(ROOT/f'FINAL-STUDY-{s}.json') for s in ('010','011','012')],verification=[str(ROOT/f'verification-study{s}.json') for s in ('010','011','012')],bundles=[dict(path=str(ROOT/'study010-011-source-evidence.zip'),sha256=old['combined_source_evidence_bundle']['sha256']),dict(path=z['path'],sha256=z['sha256'])],stop='Done: two requested +one bounded justified optional study; no013.')
    new('RESEARCH-HANDOFF-010-012.json',handoff)
    p=ROOT/'RESEARCH-HANDOFF-010-012.md';assert not p.exists();p.write_text('# Research010–012 verified integration handoff\n\n'+(ROOT/'RESEARCH-HANDOFF-010-011.md').read_text()+'\n'+(ROOT/'FINAL-STUDY-012.md').read_text()+'\nStart with the new combined illustrated synthesis; original010/011 synthesis is preserved. All8 figure pairs have native selectable SVG and actual board/gate/mask/logit values. Parent should retain off-contract, full-set/raw-tie, finite-domain and no-semantic-detector caveats.\n')
    for n,h in preserved.items():assert sha(ROOT/n)==h,n
    print(json.dumps(dict(handoff=handoff,optional_artifact_count=result['artifact_count'],optional_bundle_entries=z['entries'],optional_elapsed_seconds=elapsed),indent=2))
if __name__=='__main__':finalize()
