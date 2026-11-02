"""Final study009 preservation, exact-byte, safe archive and handoff gates."""
import datetime,hashlib,json,re,struct,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
A=ROOT/'artifacts/interpretability/study-009-final'
B=ROOT/'artifacts/interpretability/study-009-reproduced'


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def hashes(root):return {str(p.relative_to(root)):sha(p) for p in sorted(root.rglob('*')) if p.is_file()}


def check_artifacts():
    aa=hashes(A);bb=hashes(B);assert aa==bb
    count=0
    for p in (A,B):
        total=0
        for record in json.loads((p/'logical-code-bytes009.json').read_text()):
            m=json.loads((p/(record['scope'].split('.')[0]+'-materialized009.json')).read_text());codes=[v for row in m['codes'] for v in row];cb=bytes.fromhex(record['codes_signed8_hex']);eb=bytes.fromhex(record['row_exponents_signed8_hex'])
            assert list(struct.unpack('<'+'b'*len(cb),cb))==codes
            assert list(struct.unpack('<'+'b'*len(eb),eb))==m['exponents']
            assert len(cb)==record['code_bytes'] and len(eb)==record['row_exponent_bytes']
            assert len(cb)+len(eb)==record['logical_payload_bytes']==m['new_tensor_payload_bytes'];total+=len(cb)
        assert count in (0,total);count=total
        text=(p/'REPORT009.md').read_text()
        for target in re.findall(r'!\[[^]]*\]\(([^)]+)\)',text):assert (p/target).is_file(),target
    assert (ROOT/'independent-audit-study009.json').read_bytes()==(ROOT/'independent-audit-study009-reproduced.json').read_bytes()
    figures=[n[:-4] for n in aa if n.endswith('.png')]
    assert all(n+'.svg' in aa for n in figures)
    return dict(artifact_count=len(aa),artifacts_byte_identical=True,logical_code_scalars=count,figure_pairs=len(figures),sha256=aa)


def archive(dest,artifacts,support):
    assert not dest.exists()
    files={**{f'evidence/{n}':artifacts/n for n in hashes(artifacts)},**{f'source/{n}':ROOT/n for n in support}}
    banned={'.f9j','.bin','.rom','.prg','.pt','.pth','.ckpt','.safetensors','.env','.d64','.crt'}
    private=re.compile(r'\b(?:10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|172\.(?:1[6-9]|2\d|3[01])\.\d+\.\d+)\b')
    for n,p in files.items():
        assert p.suffix.lower() not in banned,n
        assert not any(t in Path(n).parts for t in ('.venv','__pycache__','.git','.pytest_cache'))
        if p.suffix in ('.py','.json','.md','.txt','.log','.svg'):
            text=p.read_text();assert not private.search(text),n
            assert not re.search(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|sk-[A-Za-z0-9]{30,}',text),n
    with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for n,p in sorted(files.items()):
            item=zipfile.ZipInfo(n,(1980,1,1,0,0,0));item.compress_type=zipfile.ZIP_DEFLATED;item.external_attr=0o644<<16;z.writestr(item,p.read_bytes(),compresslevel=9)
    with zipfile.ZipFile(dest) as z:
        assert z.testzip() is None and len(z.namelist())==len(files)
        for n,p in files.items():assert hashlib.sha256(z.read(n)).hexdigest()==sha(p)
    return dict(path=str(dest),sha256=sha(dest),bytes=dest.stat().st_size,entries=len(files),contents_sha256={n:sha(p) for n,p in sorted(files.items())},excluded='No ROM/model binaries, environments, secrets or private hosts. Model and1114 prior snapshot files remain external prerequisites, hash-pinned.')


def finalize():
    result=check_artifacts();audit=json.loads((ROOT/'independent-audit-study009.json').read_text());pres=json.loads((ROOT/'preservation-before009.json').read_text())
    for n,h in pres.items():assert sha(ROOT/n)==h,n
    test=(ROOT/'tests009-final.txt').read_text();assert re.search(r'8 passed\b',test),test
    # Fixed source/evidence whitelist; never recursively bundle the entire snapshot.
    names=['study009_core.py','study009_run.py','study009_render.py','study009_report.py','study009_verify.py','study009_finalize.py','test_study009.py','study005_run.py','study005_core.py','research678_run.py','research678_core.py','experiment-study009.json','baseline-study009.json','preservation-before009.json','README-REPRODUCTION009.md','independent-audit-study009.json','study009-render-original-evidence.zip','study009-render-original-evidence-hashes.json','execution-study009.log','reproduction-study009.log','verification-execution-study009.log','tests009-final.txt']
    names+=sorted(str(p.relative_to(ROOT)) for p in (ROOT/'falken9').glob('*.py'))
    names+=sorted(str(p.relative_to(ROOT)) for p in (ROOT/'scripts').glob('*.py'))
    names+=sorted(p.name for p in ROOT.glob('tests009-red-*.txt'))
    names+=sorted(p.name for p in ROOT.glob('tests009-green-*.txt'))
    assert len(names)==len(set(names))
    z=archive(ROOT/'study009-source-evidence.zip',A,names);zr=archive(ROOT/'study009-source-evidence-reproduced.zip',B,names)
    assert z['sha256']==zr['sha256'] and z['bytes']==zr['bytes'] and z['entries']==zr['entries']
    start=datetime.datetime.fromisoformat('2026-11-01T14:31:14+00:00');now=datetime.datetime.now(datetime.timezone.utc);elapsed=(now-start).total_seconds();assert elapsed<3600
    verification=dict(study='009',status='PASS',independent=audit,artifacts=result,source_sha256={n:sha(ROOT/n) for n in names},bundle=z,reproduced_bundle=zr,zip_byte_identical=True,prior_files_unchanged=len(pres),preservation_manifest_sha256=sha(ROOT/'preservation-before009.json'),tests=dict(passed=8,log='tests009-final.txt',sha256=sha(ROOT/'tests009-final.txt')),figure_visual_review=dict(native_size=True,figures=['overview009','mechanism009','robust009','restoration-damage009','raw-alignment009'],corrected_figures_reinspected=['overview009','raw-alignment009']),bounded_wall_seconds=elapsed,started_utc=start.isoformat(),verified_utc=now.isoformat(),main_checkout_written=False,training=False,deployment=False)
    def put(n,o):
        p=ROOT/n;assert not p.exists(),n;p.write_text(json.dumps(o,indent=2,sort_keys=True)+'\n')
    put('verification-study009.json',verification)
    rows=json.loads((A/'results009.json').read_text());plain=[r for r in rows if r['variant']=='plain'];restored=[r for r in rows if r['variant']=='restore-baseline-router-scores']
    final=dict(study='009',status='COMPLETE_AND_VERIFIED',root=str(ROOT),model_sha256=audit['source_model_sha256'],model_bytes=audit['source_model_bytes'],report=str(A/'REPORT009.md'),verification=str(ROOT/'verification-study009.json'),manifest=str(ROOT/'experiment-study009.json'),manifest_sha256=sha(ROOT/'experiment-study009.json'),artifacts=result,source_evidence_bundle=dict(path=z['path'],sha256=z['sha256'],bytes=z['bytes'],entries=z['entries']),source_evidence_reproduced_bundle=dict(path=zr['path'],sha256=zr['sha256']),plain=plain,router_restored=restored,restoration_contrasts=audit['restoration_contrasts'],scalar_checks={k:v for k,v in audit.items() if k.endswith('checks') or k.endswith('scalars') or k=='raw_public_wrapper_calls'},prior_files_unchanged=len(pres),tests_passed=8,override_specifications=24,negative_findings=['No query chosen-move errors across627 canonical and4520 raw boards, despite full-set changes.','No clipping in any approximation.','No uniform restoration rescue: readout introduces1 canonical/8 raw failures.','Merged restoration is mechanically sufficient, not a unique circuit or natural mediation claim.','No model-heldout generalization: all627 boards previously trained/audited.'],limitations=['Packet-derived diagnostic approximation, not verified historical INT8 export reproduction.','Prior008 coordinate panel differs, so multiplicity alone is not isolated.','Only four declared individual scopes; no combined scope or post-outcome expansion.','Host integer forwards and composed real raw wrapper gate; no new C64 execution or speed/RAM claim.','No separate optional follow-up experiment; five measured figure pairs provide real-forward illustrations.'],issues=['Initial non-repository git status failed harmlessly; no Git writes.','First renderer caption was ambiguous and one cross-pair arrow misleading; both corrected with regression test. Original12-file render evidence preserved.'],bounded_wall_seconds=elapsed)
    put('FINAL-STUDY-009.json',final)
    md=['# Study009 complete and independently verified','',f"- **24 fixed specifications; {result['artifact_count']} final artifacts byte-identically regenerated; deterministic ZIPs byte-identical; 8 tests pass; all {len(pres)} earlier files unchanged.**",'- Full baseline:627 canonical boards,13167 target stage vectors,5643 logits;4520 raw full-set/inverse/tie outcomes exact.','', '|Component|Canonical full-set changes|Canonical wrong moves|Raw full-set changes|Raw wrong moves|','|---|---:|---:|---:|---:|']
    for r in plain:md.append(f"|{r['scope']}|{r['canonical']['set_changes']}|{r['canonical']['move_errors']}|{r['raw']['set_changes']}|{r['raw']['move_errors']}|")
    md+=['','Readout router-score restoration: canonical12→8 failures (5 rescues,1 new damage); raw91→65 (34 rescues,8 new damage). Self controls preserve all stages; clean-code restorations recover all baseline stages; baseline merged recovers every logit. No clipping.','', 'This is packet-derived signed8 approximation, **not historical INT8 reproduction**. Unlike the finite study008 one-code panel, many effective parameters and row exponents change at once; scopes differ, so multiplicity alone is not isolated. All boards were already trained/audited. No training/deployment/main writes, target execution or speed claim.','',f"- Report: `{A/'REPORT009.md'}`",f"- Verification: `{ROOT/'verification-study009.json'}`",f"- Figures: `{A}` (`overview009`, `mechanism009`, `robust009`, `restoration-damage009`, `raw-alignment009`, PNG+SVG)",f"- Bundle: `{z['path']}`",f"- Bundle SHA-256: `{z['sha256']}`",f"- Frozen model SHA-256: `{audit['source_model_sha256']}`",f"- Wall time to verified handoff: {elapsed:.1f}s (<3600s)",'','See `README-REPRODUCTION009.md`; source/evidence bundle intentionally excludes model/ROM binaries and requires the original hash-pinned snapshot. Original renderer evidence preserved; caption/arrow correction did not change any numerical result. Parent owns any main-repository integration.','']
    p=ROOT/'FINAL-STUDY-009.md';assert not p.exists();p.write_text('\n'.join(md))
    h=ROOT/'RESEARCH-HANDOFF-009.md';assert not h.exists();h.write_text('\n'.join(md))
    for n,h in pres.items():assert sha(ROOT/n)==h,n
    print(json.dumps(dict(status='PASS',artifact_count=result['artifact_count'],prior_files_unchanged=len(pres),zip_sha256=z['sha256'],zip_entries=z['entries'],zip_bytes=z['bytes'],elapsed_seconds=elapsed,verification_sha256=sha(ROOT/'verification-study009.json'),final_json_sha256=sha(ROOT/'FINAL-STUDY-009.json')),indent=2))

if __name__=='__main__':finalize()
