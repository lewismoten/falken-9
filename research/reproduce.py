#!/usr/bin/env python3
"""Materialize original retained members into disposable copies; run only allowlisted method tests."""
from pathlib import Path
import argparse
import json
import os
import subprocess
import sys
import tempfile
from validate import ROOT, digest, inside, safe_relative, validate

# Exact node IDs: no historical full-study/finalizer invocation or model access.
SAFE_TESTS = {
 '003': ['tests/test_strategy_study003.py::test_donor_alignment_reversed_batch_and_inactive_rejection'],
 '004': ['tests/test_strategy_study004.py::test_independent_signed_rounding', 'tests/test_strategy_study004.py::test_new_square_geometry_and_mask_separation'],
 '005': ['test_study005.py::test_apportion_zero_and_leftovers005', 'test_study005.py::test_edges_inactive_identity_query_key_and_mass005'],
 '006': ['test_research678.py'],
 '007': ['test_research678.py'],
 '008': ['test_research678.py', 'test_research678_descriptor.py'],
 '009': ['test_study009.py::test_signed8_exact_row_scaling'],
 '010-011': ['test_study1011.py::Test1011::test_alignment_and_inverse', 'test_study1011.py::Test1011::test_census_equality_and_inactive_nulls'],
 '012': ['test_study012.py::Test012::test_exact_mean_sign_and_fixed_aggregators'],
 '013': ['test_study013.py::ExactArithmetic::test_rounding_threshold_exact_including_zero_and_halves', 'test_study013.py::ExactArithmetic::test_integer_constraint_interval_matches_exhaustive_signed_codes', 'test_study013.py::ExactArithmetic::test_coordinate_certificate_matches_full_code_census', 'test_study013.py::ExactArithmetic::test_source_code_bounds_are_enforced'],
 '014': ['test_study014.py::CoreTests::test_exact_extrema_include_negative_activation_and_half_ties', 'test_study014.py::CoreTests::test_bands_match_all_small_joint_codes', 'test_study014.py::CoreTests::test_shrink_rounds_negative_deltas_toward_zero_and_is_nested'],
 '015': ['test_study015.py::Contract'],
 '016': ['test_study016.py::PolicyTests', 'test_study016.py::DagTests', 'test_study016.py::AuditTests'],
}


def materialize(group, dest, inventory):
    """Retain original archive layout, including a historical source/ prefix."""
    if dest.exists():
        raise ValueError('destination must not exist')
    dest.mkdir(parents=True)
    for r in inventory['files']:
        if r['source_group'] != group or r['status'] == 'excluded':
            continue
        target = inside(dest, r['original_archive_path'])
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(inside(ROOT, r['path']).read_bytes())
    return dest / 'source' if (dest / 'source/falken9').is_dir() else dest


def run(groups):
    before = validate()
    inv = json.loads((ROOT / 'research/inventory.json').read_text())
    results = []
    for group in groups:
        with tempfile.TemporaryDirectory(prefix='falken9-method-') as tmp:
            scratch = Path(tmp)
            work = materialize(group, scratch / 'snapshot', inv)
            env = dict(os.environ, PYTHONPATH=str(work), PYTHONDONTWRITEBYTECODE='1', OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1', TMPDIR=str(scratch))
            env.pop('STUDY014_INTEGRATION', None)
            # Demonstrate local project import origin before executing original tests.
            origin = subprocess.run([sys.executable, '-B', '-c', 'import pathlib,falken9; assert pathlib.Path(falken9.__file__).resolve().is_relative_to(pathlib.Path.cwd()); print("isolated import verified")'], cwd=work, env=env, text=True, capture_output=True, timeout=60)
            if origin.returncode:
                raise RuntimeError(origin.stderr)
            command = [sys.executable, '-B', '-m', 'pytest', '-q', '-p', 'no:cacheprovider', '--basetemp=' + str(scratch / 'pytest'), *SAFE_TESTS[group]]
            p = subprocess.run(command, cwd=work, env=env, text=True, capture_output=True, timeout=180)
            output = p.stdout + p.stderr
            # Public report contains test output only, no local workspace or ephemeral paths.
            output = output.replace(str(scratch), '[SCRATCH]').replace(str(ROOT), '[REPOSITORY]')
            results.append(dict(group=group, node_ids=SAFE_TESTS[group], returncode=p.returncode, output=output, isolated_project_import=True))
            print(json.dumps(dict(group=group, returncode=p.returncode, output=output)), flush=True)
    after = validate()
    if before != after:
        raise ValueError('curated sources or references changed')
    return dict(schema='falken9-research-method-tests-v1', passed=all(r['returncode'] == 0 for r in results), inventory_sha256=before['inventory_sha256'], scope='Allowlisted original model-free unit/method tests in disposable copies; not full historical reproduction, model inference, emulator/game or hardware acceptance.', interpreter=sys.version.split()[0], original_and_curated_sources_unchanged=True, results=results)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--group', choices=list(SAFE_TESTS), action='append')
    ap.add_argument('--report', type=Path, help='new output path outside preserved study directories')
    ap.add_argument('--materialize', choices=list(SAFE_TESTS), help='copy a retained source subset without executing it')
    ap.add_argument('--destination', type=Path, help='nonexistent scratch directory, outside this repository')
    args = ap.parse_args()
    if args.materialize:
        if not args.destination or args.destination.resolve().is_relative_to(ROOT):
            ap.error('--materialize requires --destination outside this repository')
        validate()
        inv = json.loads((ROOT / 'research/inventory.json').read_text())
        work = materialize(args.materialize, args.destination.resolve(), inv)
        print(json.dumps(dict(materialized=True, group=args.materialize, source_root=str(work), scope='curated retained subset only; not complete historical archive')))
        sys.exit(0)
    if args.destination:
        ap.error('--destination requires --materialize')
    if args.report and args.report.exists():
        ap.error('report must not exist')
    if args.report and args.report.resolve().is_relative_to(ROOT / 'research/studies'):
        ap.error('never write in preserved studies')
    result = run(args.group or list(SAFE_TESTS))
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, indent=2) + '\n')
    sys.exit(0 if result['passed'] else 1)
