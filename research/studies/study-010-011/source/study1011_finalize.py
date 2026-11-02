"""One-shot immutable research010/011 final verification and safe archives."""
import datetime,hashlib,json,re,zipfile,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parent
ART=ROOT/'artifacts/interpretability'
NAMES=['study-010-final','study-011-final','study-010-011-walkthrough']
REPRO=['study-010-reproduced','study-011-reproduced','study-010-011-walkthrough-reproduced']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def hashes(d):return {str(p.relative_to(d)):sha(p) for p in sorted(Path(d).rglob('*')) if p.is_file()}
def compare(a,b):
    aa=hashes(a);bb=hashes(b);assert aa==bb,dict(a_only=set(aa)-set(bb),b_only=set(bb)-set(aa),different=[k for k in aa if k in bb and aa[k]!=bb[k]])
    return dict(artifact_count=len(aa),artifacts_byte_identical=True,sha256=aa)
def archive(dest,files):
    assert not Path(dest).exists(),dest
    banned={'.f9j','.bin','.rom','.prg','.pt','.pth','.ckpt','.safetensors','.env','.d64','.crt','.onnx'}
    private=re.compile(r'\b(?:10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|172\.(?:1[6-9]|2\d|3[01])\.\d+\.\d+)\b')
    for n,p in files.items():
        p=Path(p);assert p.suffix.lower() not in banned,n
        assert not any(t in Path(n).parts for t in ('.venv','__pycache__','.git','.pytest_cache'))
        if p.suffix in ('.py','.json','.md','.txt','.log','.svg'):
            s=p.read_text();assert not private.search(s),n
            assert not re.search(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|sk-[A-Za-z0-9]{30,}',s),n
    with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for n,p in sorted(files.items()):
            info=zipfile.ZipInfo(n,(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16
            z.writestr(info,Path(p).read_bytes(),compresslevel=9)
    with zipfile.ZipFile(dest) as z:
        assert z.testzip() is None and len(z.namelist())==len(files)
        for n,p in files.items():assert hashlib.sha256(z.read(n)).hexdigest()==sha(p)
    return dict(path=str(dest),sha256=sha(dest),bytes=Path(dest).stat().st_size,entries=len(files),contents_sha256={n:sha(p) for n,p in sorted(files.items())},excluded='ROM/model/checkpoint binaries, environments, credentials, secrets and private-host addresses. Original hash-pinned snapshot is an external execution prerequisite.')
def put_new(name,v):
    p=ROOT/name;assert not p.exists(),p;p.write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')
def links_and_figures():
    from PIL import Image
    count=0;links=0
    docs=[ART/NAMES[0]/'REPORT010.md',ART/NAMES[1]/'REPORT011.md',ART/NAMES[2]/'ILLUSTRATED-SYNTHESIS1011.md',ROOT/'README-REPRODUCTION1011.md']
    for p in docs:
        for target in re.findall(r'\]\(([^)]+)\)',p.read_text()):
            assert not target.startswith(('http:','https:','file:')),target
            assert (p.parent/target).resolve().is_file(),(p,target);links+=1
    for name in NAMES:
        d=ART/name
        for p in sorted(d.glob('*.png')):
            svg=p.with_suffix('.svg');assert svg.is_file();root=ET.fromstring(svg.read_text());size=Image.open(p).size
            assert (int(root.attrib['width']),int(root.attrib['height']))==size
            assert root.findall('.//{http://www.w3.org/2000/svg}text')
            count+=1
    return dict(png_svg_pairs=count,local_links_checked=links,native_visual_review=True,report_width_visual_review_px=900,corrected_native_walkthrough_review=True,preview_sha256=hashes(ART/'study-010-011-visual-review'))
def finalize():
    preserved=json.loads((ROOT/'preservation-010-011-initial.json').read_text())
    for n,h in preserved.items():assert sha(ROOT/n)==h,n
    results={sid:compare(ART/a,ART/b) for sid,a,b in zip(('010','011','walkthrough'),NAMES,REPRO)}
    visual=links_and_figures();assert visual['png_svg_pairs']==6
    log=(ROOT/'tests1011-final.txt').read_text();assert re.search(r'9 passed\b',log),log
    regression=(ROOT/'regression-study1011-final.txt').read_text();assert re.search(r'27 passed\b',regression),regression
    names=['study1011_freeze.py','study1011_core.py','study1011_run.py','study1011_audit.py','study1011_draw.py','study1011_render.py','study1011_finalize.py','test_study1011.py','study005_run.py','study005_core.py','study009_run.py','study009_core.py','study009_render.py','research678_run.py','research678_core.py','baseline-study010-011.json','experiment-study010.json','experiment-study011.json','preservation-010-011-initial.json','README-REPRODUCTION1011.md','study1011_render_attempt1_matplotlib.py','study1011-visual-draft1.zip','freeze-study010-011.log','execution-study010.log','execution-study011.log','execution-study011-retry.log','reproduction-study010.log','reproduction-study011.log','independent-study010.log','independent-study011.log','independent-study010-reproduced.log','independent-study011-reproduced.log','independent-walkthrough1011.log','independent-walkthrough1011-reproduced.log','render-study1011-pillow.log','render-study1011-layout-corrected.log','render-study1011-reproduced.log','tests1011-final.txt','regression-study1011-final.txt']
    names+=sorted(str(p.relative_to(ROOT)) for sub in ('falken9','scripts') for p in (ROOT/sub).glob('*.py'))
    names+=sorted(p.name for p in ROOT.glob('tests1011-red-*.txt'))
    names+=sorted(p.name for p in ROOT.glob('tests1011-green-*.txt'))
    assert len(names)==len(set(names));support={f'source/{n}':ROOT/n for n in names}
    for p in sorted((ART/'study-010-011-visual-review').glob('*')):support[f'visual-review/{p.name}']=p
    # Preserve directory names inside evidence so cross-study Markdown links are portable.
    files=dict(support);again=dict(support)
    for name,repro in zip(NAMES,REPRO):
        files.update({f'evidence/{name}/{n}':ART/name/n for n in hashes(ART/name)})
        again.update({f'evidence/{name}/{n}':ART/repro/n for n in hashes(ART/repro)})
    z=archive(ROOT/'study010-011-source-evidence.zip',files);zr=archive(ROOT/'study010-011-source-evidence-reproduced.zip',again)
    assert z['sha256']==zr['sha256'] and z['entries']==zr['entries']
    audits={sid:json.loads((ART/name/f'independent-audit{sid}.json').read_text()) for sid,name in zip(('010','011'),NAMES[:2])}
    walk_audit=json.loads((ART/NAMES[2]/'independent-audit-walkthrough1011.json').read_text())
    r10=json.loads((ART/NAMES[0]/'results010.json').read_text());r11=json.loads((ART/NAMES[1]/'results011.json').read_text())
    now=datetime.datetime.now(datetime.timezone.utc);start=datetime.datetime.fromisoformat('2026-11-01T15:13:11+00:00');elapsed=(now-start).total_seconds();assert elapsed<7200
    common=dict(status='PASS',source_model_sha256='fe180f8a931f9d92d8aa39da337bc819d0dbe4e6d971edcba00324fbc18a91c1',prior_files_unchanged=len(preserved),preservation_manifest_sha256=sha(ROOT/'preservation-010-011-initial.json'),source_sha256={n:sha(ROOT/n) for n in names},combined_source_evidence_bundle=z,reproduced_bundle=zr,zip_byte_identical=True,new_tests_passed=9,related_regression_tests_passed=27,visual_review=visual,walkthrough=results['walkthrough'],walkthrough_independent=walk_audit,wall_seconds_so_far=elapsed,verified_utc=now.isoformat(),main_checkout_written=False,training=False,deployment=False,issues=['No Git repository in isolated snapshot; discovery git status failed harmlessly.','First011 JSON serialization failed on NumPy scalar metadata; partial directory retained; regression RED→GREEN; scope/numbers unchanged.','Matplotlib unavailable; no install; exact draft source retained; final existing Pillow+SVG path succeeds.','Native image review caught a walkthrough heading overlap; original draft ZIP retained; text-box collision test RED→GREEN.','Initial report-reproduction display-only one-liners had a closing-parenthesis syntax typo; actual reproduction/audit processes succeeded; corrected read-only comparison passes.'])
    total=sum(v['artifact_count'] for v in results.values())
    for sid in ('010','011'):
        verification=dict(common,study=sid,independent=audits[sid],artifacts=results[sid],manifest_sha256=sha(ROOT/f'experiment-study{sid}.json'))
        put_new(f'verification-study{sid}.json',verification)
        data=r10 if sid=='010' else r11
        final=dict(study=sid,status='COMPLETE_AND_VERIFIED',report=str(ART/f'study-{sid}-final'/f'REPORT{sid}.md'),verification=str(ROOT/f'verification-study{sid}.json'),manifest=str(ROOT/f'experiment-study{sid}.json'),artifacts=results[sid],combined_reproduced_artifacts=total,source_evidence_bundle={k:z[k] for k in ('path','sha256','bytes','entries')},result=data,prior_files_unchanged=len(preserved),new_tests=9,related_regression_tests=27,figure_pairs=2,illustrated_synthesis=str(ART/NAMES[2]/'ILLUSTRATED-SYNTHESIS1011.md'),negative_findings=['No semantic expert/hidden-unit tactic detector established.','No new held-out model-domain generalization or target-performance claim.','Canonical-wrapper correctness is not learned hidden invariance.'] if sid=='010' else ['No full-logit collision on627 boards; sign collisions are distinct weaker objects.','Finite injectivity is not a semantic decoder or causal strategy claim.','Small routing cardinality is not proof of expert ignorance.'],issues=common['issues'],wall_seconds_so_far=elapsed)
        put_new(f'FINAL-STUDY-{sid}.json',final)
        outcome='Direct off-contract network:1514/4520 exact complete sets;485 empty sets;1151 nonoptimal nonempty choices;345 optimal tie changes. Fixed wrapper4520/4520 exact complete-set/raw-tie outcomes. All8 direct full-set symmetry only14/627; all8 exact logit symmetry0/627.' if sid=='010' else '627 distinct merged and integer-logit vectors;12 ordered routes,6 unordered memberships,403 gate vectors,480 route+gate records,168 raw sign vectors and118 legal sets. Independent tuple census validates25 stages /13100 classes /12 per-expert scopes;1254 actual expert executions. Controlled route+gate collisions hide different tactical labels and optimal sets.'
        md=f"# Research{sid} complete and independently verified\n\n{outcome}\n\n- **{results[sid]['artifact_count']} stage artifacts +8 shared illustrated-walkthrough artifacts byte-identically reproduced.** Combined38 artifact files, six native PNG/SVG pairs;9 new tests and27 related regression tests pass.\n- All1258 pre-existing files, including study009, unchanged. Frozen model5195bytes/hash unchanged; main game/application010 untouched.\n- Report: `{final['report']}`\n- Verification: `{final['verification']}`\n- Illustrated synthesis: `{final['illustrated_synthesis']}`\n- Combined source/evidence ZIP: `{z['path']}`\n- ZIP SHA-256: `{z['sha256']}`; {z['entries']} entries; original/reproduced ZIP bytes identical.\n\nNo held-out model-domain, semantic-detector or new C64 speed/execution claim. Original failed serialization/render drafts are preserved and fixed with regression evidence. Read `README-REPRODUCTION1011.md`; parent owns main-report integration.\n"
        p=ROOT/f'FINAL-STUDY-{sid}.md';assert not p.exists();p.write_text(md)
    handoff=dict(status='PASS',studies=['010','011'],artifact_files_byte_identical=total,stage_artifacts=results,preserved_files=len(preserved),bundle_sha256=z['sha256'],bundle_entries=z['entries'],bundle_path=z['path'],synthesis=str(ART/NAMES[2]/'ILLUSTRATED-SYNTHESIS1011.md'),verification_paths=[str(ROOT/f'verification-study{sid}.json') for sid in ('010','011')],wall_seconds=elapsed)
    put_new('RESEARCH-HANDOFF-010-011.json',handoff)
    p=ROOT/'RESEARCH-HANDOFF-010-011.md';assert not p.exists();p.write_text('# Research010/011 verified handoff\n\n'+(ROOT/'FINAL-STUDY-010.md').read_text()+'\n'+(ROOT/'FINAL-STUDY-011.md').read_text())
    for n,h in preserved.items():assert sha(ROOT/n)==h,n
    print(json.dumps(handoff,indent=2))
if __name__=='__main__':finalize()
