#!/usr/bin/env python3
"""Train bounded fewer-expert candidates; CPU-one-thread reproducible runner."""
import argparse
from dataclasses import replace
from pathlib import Path
import json
import sys
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from falken9.flexible_model import FlexibleConfig, FlexiblePolicy
from falken9.flexible_training import train_candidate, initialize_from_checkpoint
from falken9.canonical_training import load_data


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dataset',default='data/nonterminal-legal-histories.jsonl')
    p.add_argument('--output',default='artifacts/flexible')
    p.add_argument('--width',type=int,default=8)
    p.add_argument('--hidden',type=int,default=4)
    p.add_argument('--experts',type=int,default=4)
    p.add_argument('--active',type=int,default=2)
    p.add_argument('--precision',choices=['float','int8'],default='float')
    p.add_argument('--seed',type=int,default=11)
    p.add_argument('--steps',type=int,default=10000)
    p.add_argument('--seconds',type=float,default=60)
    p.add_argument('--lr',type=float,default=.003)
    p.add_argument('--hard-mining',type=float,default=0,help='additional worst-64-pattern legal-bit BCE weight')
    p.add_argument('--source')
    p.add_argument('--selected-experts',help='comma-separated source IDs; records warmstart lineage')
    p.add_argument('--sweep',action='store_true',help='W8/W6 H4 E4/E3 K2 seeds 11/23; INT8 only after accepted float capacity')
    args=p.parse_args(); torch.set_num_threads(1)
    data=load_data(args.dataset); output=Path(args.output); output.mkdir(parents=True,exist_ok=True)
    specs=[(d,e,2,s) for s in (11,23) for d in (8,6) for e in (4,3)] if args.sweep else [(args.width,args.experts,args.active,args.seed)]
    results=[]
    for width,experts,active,seed in specs:
        torch.manual_seed(seed)
        config=FlexibleConfig(width,args.hidden,experts,active,args.precision)
        model=FlexiblePolicy(config); lineage=None
        if args.source:
            selected=[int(x) for x in args.selected_experts.split(',')] if args.selected_experts else None
            lineage=initialize_from_checkpoint(model,args.source,selected)
        name=f'w{width}-h{args.hidden}-e{experts}-k{active}-{args.precision}-s{seed}'
        result=train_candidate(model,data,output/name,steps=args.steps,seconds=args.seconds,lr=args.lr,seed=seed,lineage=lineage,hard_mining=args.hard_mining)
        results.append(dict(name=name,result=str(output/name/'result.json'),**result))
        if args.sweep and result['accepted'] and args.precision=='float':
            qmodel=FlexiblePolicy(replace(config,precision='int8'))
            qlineage=initialize_from_checkpoint(qmodel,output/name/'best.pt')
            qname=name.replace('-float-','-int8-')
            quant=train_candidate(qmodel,data,output/qname,steps=args.steps,seconds=args.seconds,lr=.0005,seed=seed,lineage=qlineage)
            results.append(dict(name=qname,result=str(output/qname/'result.json'),**quant))
        (output/'sweep-results.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps([dict(name=x['name'],accepted=x['accepted'],errors=x['gate']['canonical_set_errors'],bytes=x['packed']['encoded_bytes']) for x in results],indent=2))


if __name__=='__main__': main()
