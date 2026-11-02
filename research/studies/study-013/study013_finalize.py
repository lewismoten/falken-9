"""Finalize verified local evidence; deterministic model-free archive."""
import hashlib,json,re,zipfile
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def finalize():
    r=ROOT;out=r/'results013';repro=r/'reproduced013'
    m=json.loads((r/'manifest013.json').read_text())
    for n,h in dict(m['source_sha256'],**m['input_sha256']).items():assert sha(r/n)==h,n
    assert (r/'manifest013.json').stat().st_mode&0o777==0o444
    files={str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file()}
    other={str(p.relative_to(repro)):sha(p) for p in sorted(repro.rglob('*')) if p.is_file()};assert files==other
    results=json.loads((out/'results013.json').read_text());certs=json.loads((out/'certificates013.json').read_text());runs=json.loads((out/'validations013.json').read_text());audit=json.loads((out/'independent-audit013.json').read_text())
    assert len(certs)==18 and len({v['id'] for v in certs})==18
    assert results['executed_full_forward_validations']==72 and results['restored_full_forward_validations']==72
    assert audit['pass_all'] and audit['all_representable_codes_enumerated']
    for p in out.glob('*.png'):
        im=Image.open(p);im.verify();assert p.with_suffix('.svg').is_file()
    report=(out/'REPORT013.md').read_text()
    for image in re.findall(r'!\[[^\]]*\]\(([^)]+)\)',report):assert (out/image).is_file()
    preserved={}
    for label,path in [('prior','/home/ai/falken9-strategy-study-003'),('main-protected','/home/ai/falken-9')]:
        vals=json.loads((r/f'preservation-{label}.json').read_text())
        for n,h in vals.items():assert sha(Path(path)/n)==h,(label,n)
        preserved[label]=len(vals)
    assert 'Ran 5 tests' in (r/'tests-final013.txt').read_text() and (r/'tests-final013.txt').read_text().rstrip().endswith('OK')
    assert json.loads((r/'independent-verification013.log').read_text())==audit
    fail=[v for v in runs if v['role']=='nearest-failure' and v['status']=='executed'];end=[v for v in runs if v['role']=='endpoint' and v['status']=='executed']
    counts={k:{field:sum(v[k][field] for v in fail) for field in ('set_changes','empty','nonoptimal_nonempty','optimal_tie_changes')} for k in ('canonical','raw')}
    summary=dict(study='013',complete=True,workspace=str(r),report='results013/REPORT013.md',manifest_sha256=sha(r/'manifest013.json'),model_sha256=results['model_sha256'],certificates=18,endpoint_forwards=len(end),nearest_failure_forwards=len(fail),restoration_forwards=72,censored_sides=results['censored_sides'],independent_code_board_sign_checks=audit['independent_signed16_code_board_sign_evaluations'],independent_scalar_head_checks=audit['independent_scalar_full_head_checks'],byte_identical_regenerated_files=len(files),all_output_sha256=files,source_preservation_verified=preserved,endpoint_occupied_sign_crossings=sum(v['occupied_sign_crossings'] for v in end),nearest_failure_observation_counts=counts,warning='Counts sum coordinate-side observations, not unique boards. Exact finite627-canonical/4520-raw domain; one coordinate at a time; no joint/universal/heldout or target timing claims.',no_further_study=True)
    # Explicit allowlist; no model/ROM/env/cache/secret files can enter.
    names=set(m['source_sha256'])|set(m['input_sha256'])
    names.discard('artifacts/flexible-integer/q11-w16-a32-early-interp/model.f9j')
    names.update(str(p.relative_to(r)) for p in out.rglob('*') if p.is_file())
    names.update(p.name for p in r.glob('*.py'))
    names.update(p.name for p in r.glob('*.txt'))
    names.update(p.name for p in r.glob('*.log'))
    names.update(['README-REPRODUCTION013.md','manifest013.json','verification013.json'])
    # Exclude arbitrary executables, packet/ROM suffixes and sensitive components.
    for n in names:
        p=Path(n);assert not p.is_absolute() and '..' not in p.parts
        assert p.suffix.lower() not in ('.f9j','.rom','.prg','.d64','.pt','.pth','.bin','.key','.pem')
        assert not any(part.lower() in ('.git','.venv','__pycache__','.env','secrets') for part in p.parts)
        if p.suffix in ('.py','.md','.json','.txt','.log','.svg'):
            text=(r/p).read_text()
            assert not re.search(r'(?i)(?:https?://)(?:localhost|127\.|10\.|192\.168\.|[a-z0-9.-]+\.(?:local|internal))',text),n
            assert not re.search(r'(?:sk-[A-Za-z0-9]{24,}|-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----)',text),n
    archive=r/'study013-source-evidence.zip'
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for n in sorted(names):
            info=zipfile.ZipInfo(n,(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16;z.writestr(info,(r/n).read_bytes(),compresslevel=9)
    with zipfile.ZipFile(archive) as z:
        assert z.namelist()==sorted(names) and z.testzip() is None
        for n in names:assert hashlib.sha256(z.read(n)).hexdigest()==sha(r/n)
    summary['source_evidence_zip']=dict(path=archive.name,files=len(names),bytes=archive.stat().st_size,sha256=sha(archive),model_rom_secrets_private_hosts_excluded=True)
    (r/'FINAL-STUDY-013.json').write_text(json.dumps(summary,sort_keys=True,indent=2)+'\n')
    print(json.dumps(summary,sort_keys=True,indent=2))
if __name__=='__main__':finalize()
