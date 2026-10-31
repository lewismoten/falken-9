#!/usr/bin/env python3
"""Prove local weight-derived fusion exactly; count its extra storage honestly."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import torch
from falken9.canonical_integer import CanonicalIntegerPolicy
from falken9.canonical_integer_export import load
from falken9.canonical_training import load_data, evaluate
from falken9.local_fusion import LocalNormPolicy, LocalFusionPolicy


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path('artifacts/canonical-integer/verified/q11-w16-a32-early-interp/model.f9j'))
    parser.add_argument('--dataset', default='data/nonterminal-legal-histories.jsonl')
    parser.add_argument('--artifacts', type=Path, default=Path('artifacts/local-fusion'))
    parser.add_argument('--output', type=Path, default=Path('results/local-fusion-summary.json'))
    args = parser.parse_args()
    torch.set_num_threads(1)
    source_hash = hashlib.sha256(args.source.read_bytes()).hexdigest()
    candidate = load(args.source)
    data = load_data(args.dataset)
    boards = data['canonical_boards']
    normal = CanonicalIntegerPolicy(candidate)
    expected, expected_routes = normal(boards, return_routes=True)
    results = []
    args.artifacts.mkdir(parents=True, exist_ok=True)
    for name, model, table_name in [('norm1', LocalNormPolicy(candidate), 'local_norm'),
                                     ('norm1-qkv', LocalFusionPolicy(candidate), 'local_qkv')]:
        actual, routes = model(boards, return_routes=True)
        differences = int((actual != expected).sum())
        route_differences = int((routes != expected_routes).sum())
        if differences or route_differences:
            raise ValueError(f'{name}: fused forward is not exact')
        table = getattr(model, table_name)
        if bool(((table < -32768) | (table > 32767)).any()):
            raise ValueError(f'{name}: local table does not fit declared INT16')
        values = table.flatten().tolist()
        raw = struct.pack('<' + 'h' * len(values), *values)
        path = args.artifacts / (name + '.bin')
        path.write_bytes(raw)
        restored = torch.tensor(struct.unpack('<' + 'h' * len(values), path.read_bytes()), dtype=torch.int64).reshape(table.shape)
        if not torch.equal(restored, table):
            raise ValueError('serialized local table roundtrip failed')
        setattr(model, table_name, restored)
        gate = evaluate(model, data, args.artifacts / name, benchmark=False)
        gate['arithmetic'] = 'host exact whole-integer inference with weight-derived local constant folding; NOT assembled C64 accepted'
        (args.artifacts / name / 'evaluation.json').write_text(json.dumps(gate, indent=2) + '\n')
        if not gate['accepted']:
            raise ValueError('fused policy failed exhaustive gameplay gate')
        results.append({
            'variant': name, 'table_path': str(path), 'table_shape': list(table.shape),
            'table_bytes': len(raw), 'table_sha256': hashlib.sha256(raw).hexdigest(),
            'table_min': int(table.min()), 'table_max': int(table.max()),
            'source_plus_table_bytes': args.source.stat().st_size + len(raw),
            'storage_scope': 'actual unchanged source packet plus separate raw table; unused original parameters retained, no new stripped packet/target code claimed',
            'first_norm_calls_removed_per_board': 9,
            'qkv_matrix_macs_removed_per_board': 3 * 9 * candidate['width'] ** 2 if name == 'norm1-qkv' else 0,
            'local_feature_combinations': 2 * 9 * 3,
            'logit_mismatches': differences, 'route_mismatches': route_differences,
            'gate': gate,
        })
    if hashlib.sha256(args.source.read_bytes()).hexdigest() != source_hash:
        raise ValueError('source artifact changed')
    report = {'scope': 'exact host whole-integer local constant-folding proof; no measured 6502 speed or RAM residency',
              'source': str(args.source), 'source_sha256': source_hash,
              'dataset_sha256': data['dataset_sha256'], 'variants': results,
              'lookup_boundary': 'local occupancy/position/side features only; no board index, history, target labels or moves in tables'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'scope': report['scope'], 'variants': [
        {key: value for key, value in row.items() if key != 'gate'} for row in results]}, indent=2))


if __name__ == '__main__':
    main()
