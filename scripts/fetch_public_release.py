"""Fetch and verify one public immutable HF release; never fall back to main."""
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen
import argparse
import importlib.util
import json
import re
import shutil
import tempfile

spec = importlib.util.spec_from_file_location('public_pages_builder', Path(__file__).with_name('build_public_pages.py'))
assert spec is not None and spec.loader is not None
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)
REPOSITORY = 'lewismoten/falken-9'
MAX_FILE_BYTES = 128 * 1024 * 1024


def download_bytes(url):
    request = Request(url, headers={'User-Agent': 'falken9-public-pages/1', 'Accept-Encoding': 'identity'})
    with urlopen(request, timeout=60) as response:
        if not response.geturl().startswith('https://'):
            raise ValueError('Refusing non-HTTPS download redirect')
        data = response.read(MAX_FILE_BYTES + 1)
    if len(data) > MAX_FILE_BYTES:
        raise ValueError('Release file exceeds download limit')
    return data


def fetch_release(revision, output, download=download_bytes):
    if not isinstance(revision, str) or not re.fullmatch('[0-9a-fA-F]{40}', revision):
        raise ValueError('hf_revision must be an explicit immutable 40-hex commit, never a branch or tag')
    output = Path(output).resolve()
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError('Fetch output must be fresh or empty')
    # Hardcoded repository, caller-selected immutable commit; no token needed.
    base = f'https://huggingface.co/{REPOSITORY}/resolve/{revision}/'
    manifest_data = download(base + 'manifest.json')
    try:
        manifest = json.loads(manifest_data)
        records = builder.manifest_records(manifest)
    except (ValueError, TypeError) as error:
        raise ValueError(f'Invalid remote manifest: {error}') from error
    if len(records) > 2000 or sum(r['bytes'] for r in records.values()) > 512 * 1024 * 1024:
        raise ValueError('Release inventory exceeds package limit')
    for name, record in records.items():
        if name in {'manifest.json', 'SHA256SUMS'} or record['bytes'] > MAX_FILE_BYTES:
            raise ValueError('Invalid remote payload inventory')
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='.hf-release-', dir=output.parent))
    try:
        (staging / 'manifest.json').write_bytes(manifest_data)
        for name, record in records.items():
            data = download(base + quote(name, safe='/'))
            if len(data) != record['bytes'] or builder.sha(data) != record['sha256']:
                raise ValueError(f'Download size/SHA-256 mismatch: {name}')
            target = staging / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        (staging / 'SHA256SUMS').write_bytes(download(base + 'SHA256SUMS'))
        builder.validate_package(staging)
        if output.exists():
            output.rmdir()
        staging.rename(output)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return dict(repository=REPOSITORY, revision=revision, payload_files=len(records))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hf-revision', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = fetch_release(args.hf_revision, args.output)
    except (ValueError, OSError) as error:
        parser.exit(1, f'Fetch rejected: {error}\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
