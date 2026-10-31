"""Bounded sequential width/precision search, one CUDA process."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import torch
from falken9.model import CompactPolicy, ModelConfig
from falken9.training import load_dataset, train_candidate, evaluate


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--dataset',default='data/nonterminal-legal-histories.jsonl')
    p.add_argument('--output',default='artifacts/training/search-initial')
    p.add_argument('--candidates',default='8:8:float,12:12:float,16:16:float')
    p.add_argument('--steps',type=int,default=20000)
    p.add_argument('--seconds',type=float,default=180)
    p.add_argument('--lr',type=float,default=.003)
    p.add_argument('--seed',type=int,default=1101)
    p.add_argument('--device',default='cuda')
    p.add_argument('--eval-every',type=int,default=100)
    p.add_argument('--initialize',help='checkpoint of same widths; explicit new candidate, optimizer reset')
    args=p.parse_args()
    torch.set_num_threads(1)
    torch.backends.cuda.matmul.allow_tf32=False
    torch.backends.cudnn.allow_tf32=False
    data=load_dataset(args.dataset)
    print(json.dumps(dict(histories=data['history_count'],boards=len(data['boards']),sha256=data['dataset_sha256'])),flush=True)
    if data['history_count']!=294778 or len(data['boards'])!=4520: raise ValueError('published dataset count mismatch')
    root=Path(args.output); root.mkdir(parents=True,exist_ok=True)
    results=[]
    for spec in args.candidates.split(','):
        width,hidden,precision=spec.split(':')
        torch.manual_seed(args.seed)
        model=CompactPolicy(ModelConfig(int(width),int(hidden),precision))
        directory=root/f'w{width}-h{hidden}-{precision}'
        predecessor=None
        if args.initialize:
            checkpoint=torch.load(args.initialize,map_location='cpu',weights_only=False)
            model.load_state_dict(checkpoint['state_dict'])
            predecessor=dict(path=args.initialize,sha256=hashlib.sha256(Path(args.initialize).read_bytes()).hexdigest(),config=checkpoint['config'])
            initial=evaluate(model.to(args.device),data,directory/'initial',args.device)
            if initial['accepted']:
                raise ValueError('initialized candidate already exact: preserve direct gate; training not needed')
        result=train_candidate(model,data,directory,steps=args.steps,seconds=args.seconds,lr=args.lr,seed=args.seed,device=args.device,eval_every=args.eval_every)
        if predecessor:
            result['predecessor']=predecessor
            (directory/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        results.append(result)
        (root/'summary.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps([dict(config=r['config'],gate=r['gate'],seconds=r['seconds']) for r in results]),flush=True)

if __name__=='__main__': main()
