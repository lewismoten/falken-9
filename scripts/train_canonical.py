#!/usr/bin/env python3
"""Bounded canonical-set search; one process, one CPU thread by default."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import torch
from falken9.model import ModelConfig
from falken9.canonical_model import CanonicalPolicy
from falken9.canonical_training import load_data, train_candidate, run_quantized_stage


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', default='data/nonterminal-legal-histories.jsonl')
    parser.add_argument('--output', default='artifacts/canonical')
    parser.add_argument('--shapes', default='4x4,6x6,8x4,8x8')
    parser.add_argument('--seeds', default='11')
    parser.add_argument('--precision', choices=['float','binary','ternary'], default='float')
    parser.add_argument('--island-precision', choices=['float','int8','int4'], default='float')
    parser.add_argument('--teacher', help='Initialize QAT from this viable float best.pt, never low-bit scratch')
    parser.add_argument('--steps', type=int, default=4000)
    parser.add_argument('--seconds', type=float, default=75)
    parser.add_argument('--lr', type=float, default=.003)
    parser.add_argument('--device', choices=['cpu','cuda'], default='cpu')
    args = parser.parse_args()
    torch.set_num_threads(1)
    if args.device == 'cuda':
        busy = subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,process_name,used_memory','--format=csv,noheader'], text=True).strip()
        if busy: raise SystemExit('GPU owned; refusing training: '+busy)
    if (args.precision != 'float' or args.island_precision != 'float') and not args.teacher:
        raise SystemExit('Low-bit training requires an explicit viable float teacher')
    data = load_data(args.data)
    root = Path(args.output); root.mkdir(parents=True, exist_ok=True)
    teacher = torch.load(args.teacher, map_location='cpu', weights_only=False) if args.teacher else None
    if teacher and teacher['canonical_set_errors'] != 0:
        raise SystemExit('Teacher must pass canonical full-set gate')
    summary = dict(dataset_sha256=data['dataset_sha256'], canonical_count=len(data['canonical_boards']),
                   board_count=len(data['boards']), history_count=len(data['histories']),
                   transform_errors=data['transform_errors'], candidates=[])
    for shape in args.shapes.split(','):
        width, hidden = map(int, shape.split('x'))
        if teacher and (width != teacher['config']['width'] or hidden != teacher['config']['expert_width']):
            raise SystemExit('teacher dimensions differ')
        for seed in map(int,args.seeds.split(',')):
            torch.manual_seed(seed)
            model = CanonicalPolicy(ModelConfig(width,hidden,args.precision))
            if teacher: model.load_state_dict(teacher['state_dict'])
            name = f'w{width}-h{hidden}-{args.precision}-s{seed}'
            destination = root/name
            if destination.exists(): raise SystemExit(f'Refusing to overwrite candidate {destination}')
            provenance = dict(path=args.teacher, sha256=hashlib.sha256(Path(args.teacher).read_bytes()).hexdigest()) if teacher else None
            if teacher:
                if args.device != 'cpu': raise SystemExit('quantized-stage materialization currently CPU only')
                result = run_quantized_stage(args.teacher,data,destination,args.precision,args.island_precision,
                                             steps=args.steps,seconds=args.seconds,lr=args.lr,seed=seed)
            else:
                result = train_candidate(model,data,destination,steps=args.steps,seconds=args.seconds,lr=args.lr,
                                         seed=seed,device=args.device,teacher=provenance)
            summary['candidates'].append(dict(name=name,result_path=str(destination/'result.json'),**result))
            (root/'search-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({candidate['name']: candidate['gate'] for candidate in summary['candidates']},indent=2))


if __name__ == '__main__': main()
