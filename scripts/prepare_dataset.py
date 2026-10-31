#!/usr/bin/env python3
"""Prepare and independently audit the pinned published corpus."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from falken9.dataset import prepare_dataset, audit_history_rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=Path('data'))
    parser.add_argument('--output', type=Path, default=Path('results/dataset-audit.json'))
    parser.add_argument('--offline', action='store_true', help='verify existing files without any downloads')
    args = parser.parse_args()
    report = prepare_dataset(args.data, download=not args.offline)
    with (args.data / 'nonterminal-legal-histories.jsonl').open() as source:
        report['audit'] = audit_history_rows(json.loads(line) for line in source)
    if report['audit']['histories'] != 294778 or report['audit']['unique_nonterminal_boards'] != 4520:
        raise ValueError('unexpected published corpus totals')
    report['status'] = 'passed'
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'status': report['status'], 'revision': report['revision'], **report['audit']}, indent=2))


if __name__ == '__main__':
    main()
