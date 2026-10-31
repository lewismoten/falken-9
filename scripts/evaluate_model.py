"""Reload an actual saved best checkpoint and rerun exhaustive history gate."""
import argparse
from pathlib import Path
import sys
import json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import torch
from falken9.model import CompactPolicy,ModelConfig
from falken9.training import load_dataset,evaluate


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--dataset',default='data/nonterminal-legal-histories.jsonl')
    source=p.add_mutually_exclusive_group(required=True)
    source.add_argument('--checkpoint')
    source.add_argument('--packed')
    p.add_argument('--output',required=True)
    p.add_argument('--device',default='cpu')
    args=p.parse_args(); torch.set_num_threads(1)
    if args.packed:
        from falken9.export import load_packed
        model=load_packed(args.packed).to(args.device)
    else:
        checkpoint=torch.load(args.checkpoint,map_location=args.device,weights_only=False)
        model=CompactPolicy(ModelConfig(**checkpoint['config'])).to(args.device)
        model.load_state_dict(checkpoint['state_dict'])
    print(json.dumps(evaluate(model,load_dataset(args.dataset),args.output,args.device),indent=2))

if __name__=='__main__': main()
