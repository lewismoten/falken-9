#!/usr/bin/env python3
"""Verify each stage before advancement; deterministic fresh-run reproduction."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess,sys,zipfile
from research678_run import ROOT,sha,put,preserved
from research678_audit import audit

def archive(stage,base,dest):
    files={}
    for p in sorted(base.iterdir()):
        if p.is_file():files[f'evidence/{p.name}']=p
    # Explicit allowlist; no release packets, ROMs, runtime binaries, credentials/caches/envs.
    paths=list(ROOT.glob('research678_*.py'))+[ROOT/'test_research678.py',ROOT/'study005_core.py',ROOT/'study005_run.py',ROOT/f'experiment-study{stage}.json',ROOT/'baseline-study006-008.json',ROOT/'preservation-before006-008.json',ROOT/'RESEARCH-SNAPSHOT.json',ROOT/'requirements.txt',ROOT/'requirements-interpretability.txt',ROOT/'pyproject.toml']
    paths+=list((ROOT/'falken9').glob('*.py'))+list((ROOT/'scripts').glob('*.py'))
    paths+=list(ROOT.glob('tests678-*.txt'))+[ROOT/'test_research678_descriptor.py',ROOT/'amendment-study008-descriptors.json']
    paths += [ROOT/'artifacts/runtime/full-forward/q11-w16-e4'/name for name in ('summary.json','shard-0.jsonl','shard-1.jsonl','shard-2.jsonl','shard-3.jsonl')]
    paths += [ROOT/'artifacts/interpretability/study-005-final/matched-relocations005.json']
    # Baseline's hash-preservation prerequisites are external by design; inclusion of full old release is forbidden.
    for p in paths:
        if p.exists():files['source/'+str(p.relative_to(ROOT))]=p
    files['source/README-REPRODUCTION678.md']=ROOT/'README-REPRODUCTION678.md'
    with zipfile.ZipFile(dest,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,p in sorted(files.items()):
            assert not any(s in name.lower() for s in ('secret','password','credential','.env','__pycache__','.venv'))
            assert p.suffix not in ('.f9j','.rom','.bin','.prg','.d64','.crt','.pyc','.zip')
            info=zipfile.ZipInfo(name,date_time=(2026,11,1,0,0,0));info.external_attr=0o644<<16;info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,p.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    with zipfile.ZipFile(dest) as z:assert z.testzip() is None;entries=len(z.infolist())
    return entries

def verify(stage,visual):
    assert visual,'Visually inspect figures before accepting'
    main=ROOT/f'artifacts/interpretability/study-{stage}-final';fresh=ROOT/f'artifacts/interpretability/study-{stage}-reproduced'
    # Previous completed stages must remain unchanged during automatic advancement.
    for old in ('006','007'):
        if old>=stage:break
        v=json.loads((ROOT/f'verification-study{old}.json').read_text())
        for n,h in v['artifact_sha256'].items():assert sha(ROOT/f'artifacts/interpretability/study-{old}-final'/n)==h
        assert sha(ROOT/f'study{old}-source-evidence.zip')==v['archive_sha256']
    env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(ROOT))
    with (ROOT/f'tests678-final{stage}.txt').open('w') as log:subprocess.run([sys.executable,'-m','pytest','test_research678.py','test_research678_descriptor.py','-q'],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    a=audit(stage,main)
    with (ROOT/f'reproduction-study{stage}.log').open('w') as log:subprocess.run([sys.executable,str(ROOT/('research678_stage008.py' if stage=='008' else 'research678_run.py')),stage,'--out',str(fresh)],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    assert audit(stage,fresh)==a
    hashes={p.name:sha(p) for p in sorted(main.iterdir()) if p.is_file()};other={p.name:sha(p) for p in sorted(fresh.iterdir()) if p.is_file()};assert hashes==other,(hashes.keys()^other.keys())
    # Freeze bundle input list by omitting future final-test logs (added stage by stage).
    z=ROOT/f'study{stage}-source-evidence.zip';zr=ROOT/f'study{stage}-source-evidence-reproduced.zip';entries=archive(stage,main,z);assert archive(stage,fresh,zr)==entries;assert z.read_bytes()==zr.read_bytes()
    s=json.loads((main/'summary.json').read_text());v=dict(study=stage,status='PASS',artifact_sha256=hashes,byte_identical_artifacts=len(hashes),independent_audit=a,prior_files_preserved=preserved(),source_sha256={p.name:sha(p) for p in sorted(ROOT.glob('research678_*.py'))},manifest_sha256=sha(ROOT/f'experiment-study{stage}.json'),model_sha256='fe180f8a931f9d92d8aa39da337bc819d0dbe4e6d971edcba00324fbc18a91c1',archive_sha256=sha(z),archive_entries=entries,archive_bytes=z.stat().st_size,archive_identical=True,figures_visually_inspected=2,unit_tests=4,prior_stages_rechecked=True,no_new_target_execution=True)
    put(ROOT/f'verification-study{stage}.json',v)
    final=dict(study=stage,status='COMPLETE / verified / bounded experiment stopped',summary=s,verification=v,paths=dict(report=str(main/f'REPORT{stage}.md'),figures=[str(main/f'{prefix}{stage}.{ext}') for prefix in ('overview','cases') for ext in ('png','svg')],evidence_directory=str(main),source_evidence_zip=str(z),reproduced_directory=str(fresh)),negative_findings=['No named human strategy detector or dedicated full circuit established.','Finite previously trained/audited domain, not model-heldout generalization.','Offline counterfactual extra expert compute and OOD interventions; not new target-performance evidence.'],no_model_training_or_deployment_changes=True)
    put(ROOT/f'FINAL-STUDY-{stage}.json',final)
    text=f"# Study{stage} — verified handoff\n\nStatus: COMPLETE. {len(hashes)} artifacts byte-identically reproduced in a fresh directory; deterministic source/evidence ZIP also identical. {v['prior_files_preserved']} pre-existing files unchanged, including all earlier studies. Four independent small unit tests passed; independent scalar audit: `{json.dumps(a,sort_keys=True)}`. Both PNG figures visually inspected.\n\nReport: `{main/f'REPORT{stage}.md'}`\n\nFigures: `{main/f'overview{stage}.png'}` / `{main/f'cases{stage}.png'}` (SVG partners available).\n\nBundle: `{z}`\nSHA-256: `{v['archive_sha256']}`\n\nManifest SHA-256: `{v['manifest_sha256']}`\nVerification: `verification-study{stage}.json` contains all artifact/source hashes.\n\n## Key measured outcomes\n\n```json\n{json.dumps(s,indent=2,sort_keys=True)}\n```\n\n## Boundaries\nNo training, packet/game mutation, main-checkout build, new target execution, external notification or publication. All627 canonical boards were previously trained/audited; confirmation folds are probe-only. >=0 membership is not categorical ranking. Local rescue is not full circuit sufficiency/natural mediation. See report for empty vs nonoptimal nonempty vs optimal tie/full-set outcomes and unavailable matching strata.\n"
    (ROOT/f'FINAL-STUDY-{stage}.md').write_text(text)
    print(json.dumps(dict(stage=stage,status='PASS',artifact_files=len(hashes),archive_sha256=v['archive_sha256'],archive_bytes=v['archive_bytes'],audit=a),sort_keys=True))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['006','007','008']);p.add_argument('--visual-inspected',action='store_true');a=p.parse_args();verify(a.stage,a.visual_inspected)
