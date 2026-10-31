#!/usr/bin/env python3
"""Independently reload a F9F1 packet and exhaust all canonical/board/history gates."""
import argparse
from pathlib import Path
import json
import sys
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from falken9.canonical_training import load_data, evaluate
from falken9.flexible_export import decode_model
from falken9.flexible_training import route_inventory


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('packet')
    p.add_argument('--dataset',default='data/nonterminal-legal-histories.jsonl')
    p.add_argument('--output',default='artifacts/flexible/independent-evaluation')
    args=p.parse_args(); torch.set_num_threads(1)
    data=load_data(args.dataset)
    model=decode_model(Path(args.packet).read_bytes())
    result=evaluate(model,data,args.output,benchmark=False)
    result['routes']=route_inventory(model,data['canonical_boards'])
    Path(args.output,'independent-result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__': main()
