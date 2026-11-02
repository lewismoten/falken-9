"""Finish016: deterministic evidence, fresh-bundle smoke and preservation.
Original-machine controller; portable analysis commands are in README.
"""
import datetime,hashlib,json,os,re,shutil,subprocess,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
PY='/home/ai/falken-9/.venv/bin/python'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,v):Path(p).write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')
def bundle(root,files,target):
 root=Path(root);files=sorted(set(map(Path,files)),key=lambda p:str(p.relative_to(root)))
 for p in files:
  if p.suffix.lower() in ('.f9j','.bin','.d64','.prg','.pt','.pth','.safetensors','.ckpt'):raise ValueError('model/runtime excluded: '+str(p))
  if p.read_bytes().startswith(b'F9J2'):raise ValueError('packet bytes excluded')
 with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for p in files:
   info=zipfile.ZipInfo(str(p.relative_to(root)),(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16;z.writestr(info,p.read_bytes(),compresslevel=9)
 return len(files)
def execute(root,args,log):
 env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',PYTHONPATH=str(root))
 r=subprocess.run([PY,*args],cwd=root,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 Path(log).write_text(r.stdout)
 if r.returncode:raise RuntimeError((args,r.stdout))
 return r.stdout
def preservation():
 before=json.loads((ROOT/'preservation-before016.json').read_text());after={};counts={}
 exclusions=json.loads((ROOT/'preservation-exceptions016.json').read_text())['excluded_parent_owned_mutable_documents']
 for root,files in before.items():
  files={n:h for n,h in files.items() if n not in exclusions.get(root,[])}
  p=Path(root);actual={n:sha(p/n) for n in files};assert files==actual,root
  if root!='/home/ai/falken-9':assert {str(q.relative_to(p)) for q in p.rglob('*') if q.is_file()}==set(files),root
  after[root]=actual;counts[root]=len(actual)
 put(ROOT/'preservation-after016.json',after);return counts
def finish():
 sources=[ROOT/n for n in ('study016.py','audit016.py','scalar_reference015.py','render016.py','finish016.py','test_study016.py','README-REPRODUCTION016.md')]
 put(ROOT/'source-lock016.json',{p.name:sha(p) for p in sources});counts=preservation()
 execute(ROOT,['-m','unittest','test_study016','-v'],ROOT/'final-tests016.log')
 a=ROOT/'results016'
 raw=execute(ROOT,['audit016.py','results016'],ROOT/'audit-final016.log');put(a/'independent-audit016.json',json.loads(raw))
 execute(ROOT,['render016.py','results016'],ROOT/'render-final016.log')
 execute(ROOT,['study016.py','reproduced016'],ROOT/'reproduced-run016.log')
 raw=execute(ROOT,['audit016.py','reproduced016'],ROOT/'reproduced-audit016.log');put(ROOT/'reproduced016/independent-audit016.json',json.loads(raw))
 execute(ROOT,['render016.py','reproduced016'],ROOT/'reproduced-render016.log')
 names=sorted(p.name for p in a.iterdir() if p.is_file());b=ROOT/'reproduced016'
 assert names==sorted(p.name for p in b.iterdir() if p.is_file())
 for n in names:assert sha(a/n)==sha(b/n),n
 put(ROOT/'deterministic-rerun016.json',dict(passed=True,byte_identical_artifacts=len(names),sha256={n:sha(a/n) for n in names}))
 counts=preservation()
 files=sources+[ROOT/n for n in ('manifest016.json','source-lock016.json','preservation-before016.json','preservation-after016.json','preservation-exceptions016.json','deterministic-rerun016.json')]
 files+=list((ROOT/'falken9').glob('*.py'))+[p for p in (ROOT/'source010').rglob('*') if p.is_file()]+[a/n for n in names]
 # Explicit log allowlist avoids including a currently growing finalization log.
 files += [p for p in ROOT.glob('*.log') if p.name.startswith(('red-','green-','final-tests','results016-run','render016','audit-final','render-final','reproduced-'))]
 # No external credentials/endpoints. Only SVG namespace and public dataset URL allowed.
 urls=set()
 for p in files:
  if p.suffix in ('.py','.md','.json','.asm','.inc','.lst','.log','.svg'):
   text=p.read_text()
   for match in re.findall(r'https?://[^\s<>"\x27]+',text):urls.add(match)
   assert not re.search(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|\b(?:sk-[A-Za-z0-9]{24,}|ghp_[A-Za-z0-9]{24,})',text),p
   assert not re.search(r'https?://(?:localhost|127\.|10\.|192\.168\.|172\.(?:1[6-9]|2\d|3[01])\.)',text),p
 # Only known public destinations may be literal URLs; regex source literals are not actual endpoints.
 for url in urls:
  assert url.startswith(('http://www.w3.org/2000/svg','https://huggingface.co/','https://github.com/lewismoten/','http://www.w3.org/1999/xlink')),url
 target=ROOT/'study016-source-evidence.zip';count=bundle(ROOT,files,target);h=sha(target);bundle(ROOT,files,target);assert sha(target)==h
 fresh=ROOT/'bundle-smoke016';fresh.mkdir(exist_ok=False)
 with zipfile.ZipFile(target) as z:
  assert len(z.namelist())==count and len(set(z.namelist()))==count and z.testzip() is None
  assert z.namelist()==sorted(z.namelist());z.extractall(fresh)
  for n in z.namelist():assert z.read(n)==(ROOT/n).read_bytes(),n
 packet=Path('artifacts/flexible-integer/q11-w16-a32-early-interp/model.f9j');(fresh/packet).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/packet,fresh/packet)
 execute(fresh,['study016.py','smoke-results016'],ROOT/'bundle-smoke-run016.log')
 raw=execute(fresh,['audit016.py','smoke-results016'],ROOT/'bundle-smoke-audit016.log');put(fresh/'smoke-results016/independent-audit016.json',json.loads(raw))
 execute(fresh,['render016.py','smoke-results016'],ROOT/'bundle-smoke-render016.log')
 for n in names:
  if n=='results016.json':
   aa=json.loads((a/n).read_text());bb=json.loads((fresh/'smoke-results016'/n).read_text());aa.pop('imports');bb.pop('imports');assert aa==bb
  else:assert sha(a/n)==sha(fresh/'smoke-results016'/n),n
 for n,v in json.loads((ROOT/'source-lock016.json').read_text()).items():assert sha(ROOT/n)==v,n
 counts=preservation();end=datetime.datetime.now(datetime.timezone.utc);start=datetime.datetime.fromisoformat('2026-11-01T17:34:25+00:00');elapsed=(end-start).total_seconds();assert elapsed<2700
 r=json.loads((a/'results016.json').read_text());audit=json.loads((a/'independent-audit016.json').read_text())
 verification=dict(status='COMPLETE — stop after016',finished_utc=end.isoformat(),elapsed_seconds=elapsed,manifest_sha256=sha(ROOT/'manifest016.json'),packet_sha256=r['packet_sha256'],packet_bytes=5195,protected_roots=counts,preserved_files=sum(counts.values()),same_workspace_byte_identical_artifacts=len(names),fresh_extraction_passed=True,relocation_only_difference='absolute imports provenance in results016.json',bundle=dict(path=str(target),bytes=target.stat().st_size,sha256=h,files=count,rebuild_byte_identical=True,model_included=False,runtime_binaries_included=False,secrets_or_private_endpoints_found=False,observed_public_urls=sorted(urls)),independent_audit=audit,artifact_sha256={n:sha(a/n) for n in names},report=str(a/'REPORT016.md'),figures=['roles-outcomes016.png','roles-outcomes016.svg','branching-example016.png','branching-example016.svg'],tests='7 tests passed (real neural binding integration included)',issues=['Matplotlib unavailable; replaced with existing Pillow plus explicit SVG, no installation or panel change.','One concurrently parent-updated mutable main research verification document is explicitly excluded in preservation-exceptions016.json; original baseline and both observed hashes retained.'],native_replay=False,training=False,runtime_model_changes=False,further_studies=False,panels=[{k:p[k] for k in ('role','policy','win','draw','loss','expected_terminal_marks','supported_games')} for p in r['panels']])
 put(ROOT/'verification016.json',verification);print(json.dumps(verification,sort_keys=True,indent=2))
if __name__=='__main__':finish()
