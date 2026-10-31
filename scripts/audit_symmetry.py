#!/usr/bin/env python3
"""Audit exact symmetry and tie semantics; this is not neural inference."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from falken9.dataset import oracle_moves, prepare_dataset
from falken9.symmetry import canonicalize, restore_moves


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=Path('data'))
    parser.add_argument('--output', type=Path, default=Path('results/symmetry-audit.json'))
    args = parser.parse_args()
    provenance = prepare_dataset(args.data, download=False)
    canonical_boards = set()
    total, set_errors, singleton_errors = 0, [], []
    with (args.data / 'nonterminal-board-states.jsonl').open() as source:
        for line in source:
            row = json.loads(line)
            board = tuple('.XO'.index(value) for value in row['board'] if value != '/')
            canonical, transform = canonicalize(board)
            canonical_boards.add(canonical)
            expected = oracle_moves(board)
            canonical_set = oracle_moves(canonical)
            if restore_moves(canonical_set, transform) != expected:
                set_errors.append(row['board'])
            if restore_moves(canonical_set[:1], transform)[0] != expected[0]:
                singleton_errors.append(row['board'])
            total += 1
    if total != 4520 or set_errors:
        raise ValueError('full-board symmetry set restoration gate failed')
    report = {
        'dataset_revision': provenance['revision'],
        'boards_checked': total,
        'dihedral_canonical_nonterminal_boards': len(canonical_boards),
        'inverse_optimal_set_mismatches': len(set_errors),
        'single_selected_canonical_move_mismatches': len(singleton_errors),
        'single_move_counterexample_boards': singleton_errors[:8],
        'scope': 'Exact coordinate/target audit only; no learned symmetry model is accepted.',
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
