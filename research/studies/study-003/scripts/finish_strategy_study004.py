#!/usr/bin/env python3
"""Execute final study004 gates, deterministic bundle and handoff. Fresh paths only."""
import ast,contextlib,hashlib,json,os,re,subprocess,sys,zipfile
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
PY='/home/ai/falken-9/.venv/bin/python'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,v):
    with p.open('x') as f:json.dump(v,f,indent=2,allow_nan=False);f.write('\n')

def pack(entries,output):
    allowed={'.md','.json','.py','.png','.svg','.log'}
    for n in entries:
        pp=PurePosixPath(n)
        if pp.is_absolute() or '..' in pp.parts or pp.suffix not in allowed or any(x.startswith('.') for x in pp.parts):
            raise ValueError('archive permits explicit research text/images only: '+n)
    with zipfile.ZipFile(output,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for n,data in sorted(entries.items()):
            info=zipfile.ZipInfo(n,(2026,11,1,0,0,0));info.create_system=3;info.external_attr=0o644<<16
            z.writestr(info,data,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    with zipfile.ZipFile(output) as z:
        assert z.testzip() is None
        assert z.namelist()==sorted(entries)
        assert all(z.read(n)==data for n,data in entries.items())

def dependencies(starts):
    found=set(starts);todo=[p for p in starts if p.suffix=='.py']
    # Include package source for from-package aliases; never bytecode/envs.
    for p in (ROOT/'falken9').glob('*.py'):
        if p not in found:found.add(p);todo.append(p)
    while todo:
        p=todo.pop()
        for node in ast.walk(ast.parse(p.read_text())):
            names=[]
            if isinstance(node,ast.Import):names=[n.name for n in node.names]
            elif isinstance(node,ast.ImportFrom) and node.module:names=[node.module]
            for n in names:
                if n.split('.')[0] not in ('falken9','scripts'):continue
                a=ROOT.joinpath(*n.split('.')).with_suffix('.py')
                if not a.is_file():a=ROOT.joinpath(*n.split('.'))/'__init__.py'
                if a.is_file() and a not in found:found.add(a);todo.append(a)
    return sorted(found)

def main():
    assert Path(sys.executable).resolve()==Path(PY).resolve()
    assert os.environ.get('OMP_NUM_THREADS')=='1' and os.environ.get('OPENBLAS_NUM_THREADS')=='1'
    assert os.environ.get('PYTHONDONTWRITEBYTECODE')=='1'
    from scripts.model_strategy_study004 import run,prior
    from scripts.render_strategy_study004 import render
    prior()
    final=ROOT/'artifacts/interpretability/study-004-final'
    repeated=ROOT/'artifacts/interpretability/study-004-reproduced'
    logs=[]
    for name,out in [('final',final),('reproduced',repeated)]:
        log=ROOT/f'artifacts/study004-{name}-run.log';logs.append(log)
        with log.open('x') as f,contextlib.redirect_stdout(f):run(out);render(out)
        print(name,'numeric/report/PNG/SVG complete',flush=True)
    aa={p.name:sha(p) for p in sorted(final.iterdir()) if p.is_file()}
    bb={p.name:sha(p) for p in sorted(repeated.iterdir()) if p.is_file()}
    assert aa==bb,(aa.keys()^bb.keys(),[(k,v,bb.get(k)) for k,v in aa.items() if bb.get(k)!=v])
    print('Byte-identical final/reproduced artifacts:',len(aa),flush=True)
    # Regression tests never instantiate a machine/emulator or rerun old studies.
    testlog=ROOT/'artifacts/study004-final-tests.log';logs.append(testlog)
    cmd=[PY,'-m','pytest','-q','-p','no:cacheprovider','--basetemp=artifacts/study004-final-test-output','tests/test_strategy_study004.py','tests/test_strategy_study003.py','tests/test_strategy_diagnostics.py','-k','not annotated_maps_bind_real_parameters_and_dynamic_activations']
    env=dict(os.environ,PYTEST_DISABLE_PLUGIN_AUTOLOAD='1')
    result=subprocess.run(cmd,cwd=ROOT,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    with testlog.open('x') as f:f.write(result.stdout)
    print(result.stdout,flush=True);assert result.returncode==0
    found=re.search(r'(\d+) passed',result.stdout);assert found and int(found.group(1))==12
    # Mandatory arithmetic sizes are computed, not manually asserted in prose.
    su=json.loads((final/'summary.json').read_text())
    paths=sum(len(lane) for b in json.loads((final/'exact-paths.json').read_text())['records'] for expert in b['paths'] for hidden in expert for lane in hidden)
    assert paths==627*2*4*8*9
    n69,n23=prior()
    verification=dict(study='004',byte_identical_files=len(aa),compared_directories=[str(final),str(repeated)],sha256=aa,total_artifact_bytes=sum(p.stat().st_size for p in final.iterdir() if p.is_file()),exact_pre_round_paths=paths,exact_final_logits=su['exact_logits'],prior69_unchanged=n69,prior23_unchanged=n23,tests=dict(passed=int(found.group(1)),failed=0,command=cmd,log=str(testlog),sha256=sha(testlog),scope='six new arithmetic/geometry/exact-path/index/exhaustive/figure/archive tests plus six earlier baseline/identity/patch checks; old full-study regression reruns excluded'),execution='CPU1thread, frozen packet, saved target evidence only; no GPU/training/emulator/main/game edits',visual_review='Final handoff records native visual inspection after final render')
    vpath=ROOT/'verification-study004.json';write(vpath,verification)
    starts=[ROOT/n for n in ['falken9/strategy_square004.py','scripts/model_strategy_study004.py','scripts/render_strategy_study004.py','scripts/finish_strategy_study004.py','tests/test_strategy_study004.py']]
    sourcefiles=dependencies(starts)
    sources={str(p.relative_to(ROOT)):sha(p) for p in sourcefiles}
    req=dict(model=dict(path='artifacts/flexible-integer/q11-w16-a32-early-interp/model.f9j',bytes=5195,sha256=su['model_sha256'],included_in_bundle=False),baseline_source_evidence_sha256=json.loads((ROOT/'RESEARCH-SNAPSHOT.json').read_text())['source_evidence_sha256'],study003_required_dir='artifacts/interpretability/study-003-final',study003_sha256=json.loads((ROOT/'verification-study003.json').read_text())['sha256'],python=PY,versions=json.loads((final/'provenance.json').read_text()),renderer=json.loads((final/'render-provenance.json').read_text()),source_sha256=sources,scope='Overlay kit; supply exact immutable model/69 evidence/23 prior artifacts separately. No ROM/environment/model payload included.')
    reqpath=ROOT/'requirements-study004.json';write(reqpath,req)
    include=sourcefiles+[ROOT/n for n in ['experiment-study004.json','RESEARCH-SNAPSHOT.json','verification-study003.json','verification-study004.json','requirements-study004.json','README-STUDY-004.md','LESSONS-STUDY-004.md']]+logs+sorted(p for p in final.iterdir() if p.is_file())
    entries={str(p.relative_to(ROOT)):p.read_bytes() for p in include}
    archive=ROOT/'artifacts/interpretability/study-004-research-bundle.zip'
    archive2=ROOT/'artifacts/interpretability/study-004-research-bundle-reproduced.zip'
    pack(entries,archive);pack(entries,archive2);assert archive.read_bytes()==archive2.read_bytes()
    bundle=dict(path=str(archive),sha256=sha(archive),bytes=archive.stat().st_size,entries=len(entries),deterministic_reproduction=str(archive2),deterministic_reproduction_sha256=sha(archive2),model_payload_included=False,roms_envs_secrets_included=False,integrity='all entries CRC/in-memory byte readback verified')
    handoff=dict(status='awaiting_visual_review',study='004',root=str(ROOT),model_sha256=su['model_sha256'],artifact_directory=str(final),report=str(final/'REPORT.md'),figures=[str(final/n) for n in ('square-paths.png','square-paths.svg','position-contrasts.png','position-contrasts.svg')],artifacts_sha256={str(final/n):h for n,h in aa.items()},verification=dict(path=str(vpath),sha256=sha(vpath)),requirements=dict(path=str(reqpath),sha256=sha(reqpath)),bundle=bundle,new_source_sha256={str(p):sha(p) for p in starts},manifest=dict(path=str(ROOT/'experiment-study004.json'),sha256=sha(ROOT/'experiment-study004.json')),findings=su,unsupported_claims=['dedicated strategy unit/expert','unique semantic decomposition','lesion deltas as additive contributions','probabilities/preferences','learned external legality mask','matched heldout fork confirmation','model-heldout/OOD generalization','strategy transplant/mediation','new C64 execution'],limits=['only66 strict relocation-pair records; no held-out fork matches','test fork positives7squares/6boards','matched comparisons are legal different inputs, not causal psychological proof','adjacent-lane controls are not magnitude-matched','prior model trained/audited full finite domain'],test_log=str(testlog),reproduction='All final output files and both PNG/SVG figures reproduced byte-for-byte in a fresh output directory; archive bytes also reproduced',immutability=dict(baseline69=n69,study003_artifacts23=n23,model_unchanged=True),visual_review='PENDING final native figure inspection',no_game_changes='No game/model/main files changed; no emulator/GPU/training/install/build/merge/publication. Only new004 research files inside isolated root.',issues=['No research blocker; strict matching coverage inadequate for strategy-specific confirmation','Early development RED tests intentionally failed for missing new features; final suite is green'])
    write(ROOT/'FINAL-STUDY-004.json',handoff)
    text=f'''# FINAL STUDY004 — awaiting final visual review

- Report: `{final/'REPORT.md'}`
- Figures: `{final/'square-paths.png'}` / `.svg`; `{final/'position-contrasts.png'}` / `.svg`.
- Downloadable source/evidence bundle: `{archive}` ({bundle['bytes']} bytes, SHA256 `{bundle['sha256']}`). No model payload/ROMs/envs/secrets; exact external hash requirements and read-only dependency sources included.
- Verification: `{vpath}` (SHA256 `{sha(vpath)}`). All{len(aa)} final artifacts byte-identical in `{repeated}`; all361152 exact paths and5643 logits checked. Both ZIP bundles byte-identical and integrity/readback verified.
- Tests: **12 passed**,0 failed; real log `{testlog}` (SHA256 `{sha(testlog)}`). New scalar/Fraction arithmetic, packet code/exponent/index, geometry/symmetry, exhaustive identity/immutability, actual zero-gate execution, legal relocation alignment, figure binding and deterministic archive checks; earlier safe baseline/patch tests included.
- Baseline first:13167 saved actual-target stage vectors/627 boards;4520 host composed wrapper outcomes;0 mismatches. No new C64 execution.
- Findings: same E2.h2→lane5 supports#49 square1 by+47587.29 but rejects#170 square5 by−1652.04 through different head rows; lane zero drops the former membership but not the latter. E2.h2/E3.h1 training-selected;22 bounded interventions, no confirmed strategy specificity. Strict relocation matching66 records, zero held-out fork matches.108 actually executed zero-gate expert observations are not inactive experts.1832 occupied/nonnegative scores remain externally masked. Combined downstream rounding residual max{su['max_abs_combined_rounding_residual']:.6f},0 baseline legal-sign changes under the declared pre-round comparison; residuals retained exactly, never assigned to hidden units.
- Limits: folds are not model-heldout; only6 fork-positive test boards/7 squares; matched legal alternatives are different inputs, not psychological causal proof; broad empty-set/set damage and controls defeat selective detector claims. No probability, unique decomposition, learned legality, transplant, mediation, OOD or target-speed claim.
- Immutability: all69 baseline files and all23 study003 final artifacts hash-identical before/after; frozen model SHA256 `{su['model_sha256']}` unchanged.
- **Visual review: PENDING final native figure inspection.**
- No game changes: no writes to main, no original model mutation, emulator use, GPU initialization, training, installs, jobs killed, builds, merge or publication. New004 files only in isolated research root. This finite study is finished after visual review; no follow-on search authorized by this script.

Exact file paths/hashes, measured counts, source/provenance, unsupported claims, test/reproduction evidence and limits are machine-readable in `FINAL-STUDY-004.json`. Reusable lessons are in `LESSONS-STUDY-004.md`; no shared/global skill was edited outside the authorized root.
'''
    with (ROOT/'FINAL-STUDY-004.md').open('x') as f:f.write(text)
    prior()
    print(json.dumps(dict(artifacts=len(aa),exact_paths=paths,tests=12,bundle=bundle,handoff=str(ROOT/'FINAL-STUDY-004.json'),visual_review='pending final inspection'),indent=2),flush=True)

if __name__=='__main__':main()
