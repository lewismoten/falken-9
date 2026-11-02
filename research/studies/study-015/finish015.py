"""Finish bounded015: two real reruns, scalar audit, safe ZIP, preservation."""
import datetime,hashlib,json,os,shutil,subprocess,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
PY='/home/ai/falken-9/.venv/bin/python'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,v):Path(p).write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')
def env(root):return dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',PYTHONPATH=str(root))
def execute(root,args,log):
 r=subprocess.run([PY,*args],cwd=root,env=env(root),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 Path(log).write_text(r.stdout);assert r.returncode==0,(args,r.stdout);return r.stdout

def preserve():
 before=json.loads((ROOT/'preservation-before015.json').read_text());after={};counts={}
 for label,item in before.items():
  p=Path(item['root']);expected=item['sha256'];actual={n:sha(p/n) for n in expected};assert expected==actual,label
  if label!='main-protected':assert {str(q.relative_to(p)) for q in p.rglob('*') if q.is_file()}==set(expected),label
  after[label]=dict(root=str(p),sha256=actual);counts[label]=len(actual)
 put(ROOT/'preservation-after015.json',after);return counts

def finish():
 source_files=sorted(list(ROOT.glob('study015*.py'))+[ROOT/'test_study015.py',ROOT/'finish015.py',ROOT/'README-REPRODUCTION015.md'])
 put(ROOT/'source-lock015.json',{p.name:sha(p) for p in source_files})
 # Read-only input inventories first; never rerun old study audit generators.
 counts=preserve()
 for name in ('results015','reproduced015'):
  output=ROOT/name
  execute(ROOT,['study015_run.py',name],ROOT/(name+'-run.log'))
  raw=execute(ROOT,['study015_audit.py',name],ROOT/(name+'-audit.log'));put(output/'independent-audit015.json',json.loads(raw))
  execute(ROOT,['study015_render.py',name],ROOT/(name+'-render.log'))
 a=ROOT/'results015';b=ROOT/'reproduced015';files=sorted(p.name for p in a.iterdir() if p.is_file())
 assert files==sorted(p.name for p in b.iterdir() if p.is_file())
 for name in files:assert sha(a/name)==sha(b/name),name
 put(ROOT/'deterministic-rerun015.json',dict(passed=True,byte_identical_artifacts=len(files),sha256={name:sha(a/name) for name in files}))
 # Whitelist only sources, evidence and input activations; never model/runtime.
 archive_files=source_files+[ROOT/'manifest015.json',ROOT/'source-lock015.json',ROOT/'preservation-before015.json',ROOT/'preservation-after015.json',ROOT/'deterministic-rerun015.json']
 archive_files+=list((ROOT/'falken9').glob('*.py'))+[p for p in (ROOT/'source010').rglob('*') if p.is_file()]+[p for p in a.iterdir() if p.is_file()]
 archive_files+=[ROOT/'artifacts/interpretability/study-010-final/baseline010.npz',ROOT/'artifacts/interpretability/study-010-final/measurements010.npz']
 archive_files+=[p for p in ROOT.glob('*.log') if p.name.startswith(('red','green','final-tests','results015','reproduced015'))]
 archive_files=sorted(set(archive_files))
 assert all(p.suffix not in ('.f9j','.bin','.d64','.prg','.pt','.pth') for p in archive_files)
 assert all(not p.read_bytes().startswith(b'F9J2') for p in archive_files)
 bundle=ROOT/'study015-source-evidence.zip'
 def package():
  with zipfile.ZipFile(bundle,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
   for p in archive_files:
    info=zipfile.ZipInfo(str(p.relative_to(ROOT)),(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16;z.writestr(info,p.read_bytes(),compresslevel=9)
 package();bundle_hash=sha(bundle);package();assert sha(bundle)==bundle_hash
 # Fresh extraction execution with explicit external model provision.
 fresh=ROOT/'bundle-smoke015';fresh.mkdir(exist_ok=False)
 with zipfile.ZipFile(bundle) as z:
  assert len(z.namelist())==len(archive_files);assert z.testzip() is None;z.extractall(fresh)
 packet=fresh/'artifacts/flexible-integer/q11-w16-a32-early-interp/model.f9j';packet.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/'artifacts/flexible-integer/q11-w16-a32-early-interp/model.f9j',packet)
 execute(fresh,['study015_run.py','smoke-results015'],ROOT/'bundle-smoke-run015.log')
 raw=execute(fresh,['study015_audit.py','smoke-results015'],ROOT/'bundle-smoke-audit015.log');put(fresh/'smoke-results015/independent-audit015.json',json.loads(raw))
 execute(fresh,['study015_render.py','smoke-results015'],ROOT/'bundle-smoke-render015.log')
 for name in files:
  if name=='results015.json':
   aa=json.loads((a/name).read_text());bb=json.loads((fresh/'smoke-results015'/name).read_text());aa.pop('imports');bb.pop('imports');assert aa==bb
  else:assert sha(a/name)==sha(fresh/'smoke-results015'/name),name
 for p,h in json.loads((ROOT/'source-lock015.json').read_text()).items():assert sha(ROOT/p)==h,p
 counts=preserve();assert sha(bundle)==bundle_hash
 end=datetime.datetime.now(datetime.timezone.utc);elapsed=(end-datetime.datetime.fromisoformat('2026-11-01T17:08:07+00:00')).total_seconds();assert elapsed<2700
 r=json.loads((a/'results015.json').read_text());audit=json.loads((a/'independent-audit015.json').read_text())
 verified=dict(status='COMPLETE; stopped after015',root=str(ROOT),finished_utc=end.isoformat(),elapsed_seconds_from_first_tool=elapsed,manifest_sha256=sha(ROOT/'manifest015.json'),model_sha256=r['packet_sha256'],accepted_model_bytes=5195,protected_file_counts=counts,preserved_files_total=sum(counts.values()),deterministic_output_artifacts=len(files),independent_audit=audit,bundle=dict(path=str(bundle),sha256=bundle_hash,bytes=bundle.stat().st_size,files=len(archive_files),model_included=False,archive_rebuild_byte_identical=True,extracted_source_smoke_test_passed=True,smoke_comparison='Every artifact exact except absolute import path provenance in results015.json'),reader_report=str(a/'REPORT015.md'),artifact_sha256={name:sha(a/name) for name in files},findings={k:r[k] for k in ('opening_count','raw_distinct_sequences','d4_trajectory_classes','outcomes','game_forward_calls','unique_raw_nonterminal_boards','unique_canonical_nonterminal_boards','first_game_sequence_one_based')},no_native_replay=True,no_release_changes=True)
 put(ROOT/'verification015.json',verified);print(json.dumps(verified,sort_keys=True,indent=2))
if __name__=='__main__':finish()
