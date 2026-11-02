#!/usr/bin/env python3
"""Check an externally obtained packet without copying, loading or modifying it."""
import argparse
import hashlib
import json
from pathlib import Path

EXPECTED_SIZE = 5195
EXPECTED_SHA256 = 'fe180f8a931f9d92d8aa39da337bc819d0dbe4e6d971edcba00324fbc18a91c1'


def check(path):
    raw = path.read_bytes()
    if len(raw) != EXPECTED_SIZE or hashlib.sha256(raw).hexdigest() != EXPECTED_SHA256:
        raise ValueError('wrong frozen model packet')
    return dict(passed=True, size=len(raw), sha256=EXPECTED_SHA256, modified=False)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('packet', type=Path)
    args = ap.parse_args()
    print(json.dumps(check(args.packet), sort_keys=True))
