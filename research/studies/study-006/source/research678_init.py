from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from study005_run import baseline

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,v):Path(p).write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
if __name__=='__main__':
    # Snapshot excludes only new678 scaffolding and mutable interpreter/test caches.
    skip={'research678_core.py','research678_init.py','test_research678.py','tests678-red006.txt'}
    files={str(p.relative_to(ROOT)):sha(p) for p in sorted(ROOT.rglob('*')) if p.is_file() and p.name not in skip and not any(s in p.parts for s in ('__pycache__','.pytest_cache','.git'))}
    put(ROOT/'preservation-before006-008.json',files)
    *_,gate,pres=baseline();assert gate['model_sha256']=='fe180f8a931f9d92d8aa39da337bc819d0dbe4e6d971edcba00324fbc18a91c1'
    put(ROOT/'baseline-study006-008.json',gate)
    print(json.dumps(dict(preserved_files=len(files),baseline=gate),indent=2))
