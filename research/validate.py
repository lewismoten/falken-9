#!/usr/bin/env python3
"""Dependency-free integrity/path checks; never extract untrusted ZIP paths."""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import json
import stat
import zipfile

ROOT = Path(__file__).resolve().parents[1]
MAX_MEMBER = 32 * 1024 * 1024
MAX_TOTAL = 200 * 1024 * 1024
FORBIDDEN = {'.f9j', '.f9f', '.pt', '.pth', '.prg', '.d64', '.rom', '.bin', '.safetensors', '.onnx', '.gguf', '.zip'}
REQUIRED_SOURCES = {
    '003': {'experiment-study003.json', 'scripts/model_strategy_study003.py', 'tests/test_strategy_study003.py'},
    '004': {'experiment-study004.json', 'scripts/model_strategy_study004.py', 'tests/test_strategy_study004.py'},
    '005': {'experiment-study005.json', 'study005_run.py', 'study005_audit.py', 'study005_render.py', 'test_study005.py'},
    '006': {'source/experiment-study006.json', 'source/research678_run.py', 'source/research678_audit.py', 'source/test_research678.py'},
    '007': {'source/experiment-study007.json', 'source/research678_run.py', 'source/research678_audit.py', 'source/test_research678.py'},
    '008': {'source/experiment-study008.json', 'source/research678_stage008.py', 'source/test_research678_descriptor.py'},
    '009': {'source/experiment-study009.json', 'source/study009_run.py', 'source/study009_verify.py', 'source/study009_render.py', 'source/test_study009.py'},
    '010-011': {'source/experiment-study010.json', 'source/experiment-study011.json', 'source/study1011_run.py', 'source/study1011_audit.py', 'source/test_study1011.py'},
    '012': {'source/experiment-study012.json', 'source/study012.py', 'source/study012_audit.py', 'source/test_study012.py'},
    '013': {'manifest013.json', 'study013_run.py', 'study013_verify.py', 'study013_render.py', 'test_study013.py'},
    '014': {'manifest014.json', 'study014_run.py', 'study014_verify.py', 'study014_render.py', 'test_study014.py'},
    '015': {'manifest015.json', 'study015_run.py', 'study015_audit.py', 'study015_render.py', 'test_study015.py'},
    '016': {'manifest016.json', 'study016.py', 'audit016.py', 'render016.py', 'test_study016.py'},
    '007-supplement': {'research678_handoff.py', 'common-support007.json'},
}



def digest(data):
    return hashlib.sha256(data).hexdigest()


def safe_relative(name):
    if not isinstance(name, str) or not name or '\\' in name or ':' in name or '\x00' in name:
        raise ValueError('invalid relative path')
    p = PurePosixPath(name)
    if p.is_absolute() or any(x in ('', '.', '..') for x in name.split('/')):
        raise ValueError('unsafe relative path')
    return p


def inside(root, name):
    safe_relative(name)
    root = root.resolve()
    p = root / name
    # Reject symlinks even when their target is inside the root.
    for parent in [p, *p.parents]:
        if parent == root:
            break
        if parent.is_symlink():
            raise ValueError('symlink in inventory path')
    if not p.resolve().is_relative_to(root):
        raise ValueError('path escaped root')
    return p


def audit_zip(z):
    infos = z.infolist()
    if len(infos) > 3000 or sum(i.file_size for i in infos) > MAX_TOTAL:
        raise ValueError('archive size limit')
    seen = set()
    for i in infos:
        name = i.filename[:-1] if i.is_dir() else i.filename
        safe_relative(name)
        if name in seen:
            raise ValueError('duplicate archive path')
        seen.add(name)
        mode = i.external_attr >> 16
        if stat.S_ISLNK(mode) or stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR):
            raise ValueError('symlink or special member')
        if i.flag_bits & 1:
            raise ValueError('encrypted member')
        if i.file_size > MAX_MEMBER or i.file_size / max(1, i.compress_size) >= 2000:
            raise ValueError('member size or expansion ratio')
    if z.testzip() is not None:
        raise ValueError('CRC failure')
    return infos


def validate(root=ROOT, inventory=None):
    d = inventory if inventory is not None else json.loads((root / 'research/inventory.json').read_text())
    groups = {g['id']: g for g in d['groups']}
    if len(groups) != len(d['groups']):
        raise ValueError('duplicate source group')
    if {s for g in groups.values() for s in g['studies']} != set(range(3, 17)):
        raise ValueError('incomplete studies coverage')
    seen = set()
    retained = []
    for r in d['files']:
        safe_relative(r['original_archive_path'])
        key = (r['source_group'], r['original_archive_path'])
        if key in seen or r['source_group'] not in groups:
            raise ValueError('duplicate member or unknown group')
        seen.add(key)
        if len(r['sha256']) != 64 or any(c not in '0123456789abcdef' for c in r['sha256']) or r['size'] < 0:
            raise ValueError('invalid member digest or size')
        if r['status'] == 'excluded':
            if not r.get('reason'):
                raise ValueError('exclusion without reason')
            if r.get('reference_path'):
                b = inside(root, r['reference_path']).read_bytes()
                if len(b) != r['size'] or digest(b) != r['sha256']:
                    raise ValueError('excluded presentation reference changed')
            continue
        if r['status'] not in ('included', 'reference'):
            raise ValueError('invalid status')
        p = inside(root, r['path'])
        if p.suffix.lower() in FORBIDDEN:
            raise ValueError('forbidden payload')
        b = p.read_bytes()
        if len(b) != r['size'] or digest(b) != r['sha256']:
            raise ValueError('retained file hash mismatch: ' + r['path'])
        retained.append(r)
    for g in groups.values():
        rows = [r for r in d['files'] if r['source_group'] == g['id']]
        if len(rows) != g['archive_members']:
            raise ValueError('archive inventory member closure')
        selected = [r for r in retained if r['source_group'] == g['id']]
        if not REQUIRED_SOURCES.get(g['id'], set()) <= {r['original_archive_path'] for r in selected}:
            raise ValueError('missing required experiment/probe/audit/test source')
        if not any(r['original_archive_path'].endswith('.py') for r in selected):
            raise ValueError('missing scientific source')
        if g['id'] != '007-supplement' and not any('test' in PurePosixPath(r['original_archive_path']).name and r['original_archive_path'].endswith('.py') for r in selected):
            raise ValueError('missing original tests')
    indexed = {r['path'] for r in retained if r['status'] == 'included'}
    actual = {str(p.relative_to(root)) for p in (root / 'research/studies').rglob('*') if p.is_file()}
    if indexed != actual:
        raise ValueError('unindexed or missing curated file')
    return dict(passed=True, studies=list(range(3, 17)), groups=len(groups), members=len(d['files']), retained_member_records=len(retained), unique_curated_files=len(indexed), curated_bytes=sum((root / p).stat().st_size for p in indexed), inventory_sha256=digest((root / 'research/inventory.json').read_bytes()))


def verify_archives(directory, root=ROOT):
    """Optional full original ZIP check. ZIPs are not shipped or required for core validation."""
    d = json.loads((root / 'research/inventory.json').read_text())
    count = 0
    for g in d['groups']:
        if g['archive'] is None:
            continue
        p = inside(directory, g['archive'])
        if digest(p.read_bytes()) != g['archive_sha256']:
            raise ValueError('archive digest mismatch')
        with zipfile.ZipFile(p) as z:
            infos = audit_zip(z)
            rows = {r['original_archive_path']: r for r in d['files'] if r['source_group'] == g['id']}
            if {i.filename for i in infos} != set(rows):
                raise ValueError('original member-set mismatch')
            for i in infos:
                r = rows[i.filename]
                if i.file_size != r['size'] or digest(z.read(i)) != r['sha256']:
                    raise ValueError('original member hash mismatch')
        count += 1
    return count


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--archives', type=Path, help='directory of privately retained original ZIPs (read-only)')
    args = ap.parse_args()
    result = validate()
    if args.archives:
        result['original_archives_verified'] = verify_archives(args.archives)
    print(json.dumps(result, sort_keys=True))
