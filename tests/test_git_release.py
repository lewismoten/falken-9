"""Committed release inputs make Pages independent of Hub and ignored artifacts."""
from pathlib import Path
import json
import shutil
import subprocess

import pytest
from scripts import prepare_publication as pub

ROOT = Path(__file__).resolve().parents[1]
RELEASE = 'releases/falken-9-v1.0.0'
DESTINATIONS = {'model': 'model.f9j', 'prg': 'falken-9-c64.prg',
                'd64': 'falken-9-c64.d64', 'validation': 'application-validation.json'}


def git_only_inputs(tmp_path):
    descriptor = json.loads((ROOT/pub.DESCRIPTOR).read_text())
    def copy(source, destination):
        target = tmp_path/destination
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(pub.source_file(ROOT, source), target)
    copy(pub.DESCRIPTOR, pub.DESCRIPTOR)
    for kind, name in DESTINATIONS.items():
        copy(descriptor[kind]['path'], RELEASE+'/'+name)
    for entry in descriptor['screenshots']+[descriptor['screenshot_provenance']]:
        copy(entry['path'], entry['path'])
    return descriptor


def test_application_loads_from_committed_release_without_ignored_artifacts(tmp_path):
    descriptor = git_only_inputs(tmp_path)
    assert not (tmp_path/'artifacts').exists()
    assert pub.load_application_release(tmp_path) == descriptor
    for kind, name in DESTINATIONS.items():
        assert pub.source_file(tmp_path, descriptor[kind]['path']) == tmp_path/RELEASE/name


def test_stage_complete_package_from_git_inputs_only(tmp_path):
    root = tmp_path/'checkout'
    git_only_inputs(root)
    for name in ('assets', 'docs', 'publication'):
        shutil.copytree(ROOT/name, root/name, dirs_exist_ok=True)
    for name in ('README.md', 'report.md', 'LICENSE', 'NOTICE'):
        shutil.copyfile(ROOT/name, root/name)
    output = tmp_path/'package'
    pub.stage_release(root, output)
    assert pub.verify_package(output, root)['passed']
    assert not (root/'artifacts').exists()
    for kind in ('model', 'prg', 'd64'):
        assert (output/pub.DESTINATIONS[kind]).read_bytes() == (root/RELEASE/DESTINATIONS[kind]).read_bytes()
    guide = (output/'c64/README.md').read_text()
    for name in ('falken-9-c64.prg', 'falken-9-c64.d64'):
        assert ']('+name+')' in guide


@pytest.mark.parametrize('kind', ['model', 'prg', 'd64', 'validation', 'symlink'])
def test_committed_input_corruption_and_symlinks_are_rejected(tmp_path, kind):
    root = tmp_path/'checkout'
    git_only_inputs(root)
    name = DESTINATIONS['prg' if kind == 'symlink' else kind]
    target = root/RELEASE/name
    if kind == 'symlink':
        outside = tmp_path/'outside.prg'
        outside.write_bytes(target.read_bytes())
        target.unlink()
        target.symlink_to(outside)
    else:
        target.write_bytes(target.read_bytes()+b'changed')
    with pytest.raises(ValueError):
        pub.load_application_release(root)


def test_existing_corrupt_original_does_not_fall_back_to_good_git_copy(tmp_path):
    root = tmp_path/'checkout'
    descriptor = git_only_inputs(root)
    original = root/descriptor['model']['path']
    original.parent.mkdir(parents=True)
    original.write_bytes(b'corrupt original')
    with pytest.raises(ValueError, match='mismatch'):
        pub.load_application_release(root)


def test_pages_workflow_stages_from_git_without_required_hub_revision():
    workflow = (ROOT/'.github/workflows/pages.yml').read_text()
    assert 'scripts/prepare_publication.py' in workflow
    assert 'build/git-public-package' in workflow
    assert 'hf_revision' not in workflow
    assert 'scripts/fetch_public_release.py' not in workflow


def test_release_d64_is_allowed_but_historical_disks_remain_ignored():
    release = subprocess.run(['git', 'check-ignore', '--no-index', RELEASE+'/falken-9-c64.d64'], cwd=ROOT, capture_output=True)
    historical = subprocess.run(['git', 'check-ignore', '--no-index', 'artifacts/app/test.d64'], cwd=ROOT, capture_output=True)
    assert release.returncode == 1
    assert historical.returncode == 0
