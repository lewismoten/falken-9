"""Build GitHub-only static launcher from one exact local release candidate."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
from scripts.build_app import extract_disk

ROOT=Path(__file__).resolve().parents[1]


def build_pages(candidate,output,screenshot):
    candidate,output,screenshot=map(lambda p:Path(p).resolve(),(candidate,output,screenshot))
    if output.exists() and any(output.iterdir()):raise ValueError('Pages output must be empty')
    if output==candidate or output.is_relative_to(candidate) or candidate.is_relative_to(output):raise ValueError('Pages output and candidate must be disjoint')
    if output.is_relative_to(ROOT/'distribution'):raise ValueError('Pages must not enter the Hub package')
    prgs=sorted(candidate.glob('*.prg'));disks=sorted(candidate.glob('*.d64'))
    if len(prgs)!=1 or len(disks)!=1:raise ValueError('Expected exactly one PRG and D64')
    prg,disk=prgs[0],disks[0];meta=json.loads((candidate/'build.json').read_text())
    if hashlib.sha256(prg.read_bytes()).hexdigest()!=meta['prg_sha256']:raise ValueError('PRG build SHA mismatch')
    if extract_disk(disk)!=prg.read_bytes():raise ValueError('D64 PRG mismatch')
    if not screenshot.read_bytes().startswith(b'\x89PNG\r\n\x1a\n'):raise ValueError('Expected actual PNG input')
    output.mkdir(parents=True,exist_ok=True);(output/'downloads').mkdir()
    manifest=dict(schema='falken9-pages-v1',release_id=prg.stem,model_sha256=meta['core']['model_sha256'],public_publication=False)
    for kind,path in [('prg',prg),('d64',disk)]:
        dest=output/'downloads'/path.name;shutil.copyfile(path,dest);raw=dest.read_bytes()
        manifest[kind]=dict(path='downloads/'+path.name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
    shutil.copyfile(screenshot,output/'screen.png')
    manifest['screenshot']=dict(path='screen.png',sha256=hashlib.sha256(screenshot.read_bytes()).hexdigest())
    for name in ('index.html','style.css','index.mjs','launcher.mjs'):shutil.copyfile(ROOT/'pages'/name,output/name)
    (output/'release.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (output/'.nojekyll').write_bytes(b'')
    return manifest

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,default=ROOT/'build/pages');p.add_argument('--screenshot',type=Path,required=True)
    args=p.parse_args();print(json.dumps(build_pages(args.candidate,args.output,args.screenshot),indent=2))
