#!/usr/bin/env python3
"""Independently reload a canonical checkpoint and exhaust every history."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import json
import torch
from falken9.model import ModelConfig
from falken9.canonical_model import CanonicalPolicy, CanonicalConfig
from falken9.canonical_training import load_data, evaluate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('checkpoint')
    parser.add_argument('--data',default='data/nonterminal-legal-histories.jsonl')
    parser.add_argument('--output',default='artifacts/canonical/reload-evaluation')
    args=parser.parse_args()
    torch.set_num_threads(1)
    checkpoint=torch.load(args.checkpoint,map_location='cpu',weights_only=False)
    model=CanonicalPolicy(CanonicalConfig(**checkpoint['config']))
    model.load_state_dict(checkpoint['state_dict'])
    result=evaluate(model,load_data(args.data),args.output)
    print(json.dumps(result,indent=2))


if __name__ == '__main__': main()
