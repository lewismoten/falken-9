"""Release packaging tests; synthetic disks are not acceptance evidence."""
import importlib.util
import json
import hashlib
import os
import sys
from typing import Any
import shutil
import subprocess
import zipfile
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def module(name) -> Any:
    path = ROOT / 'scripts' / f'{name}.py'
    if not path.exists():
        return None
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


class DiskTests(unittest.TestCase):
    def test_disk_recipe_roundtrip_and_rejects_hidden_data(self):
        release = module('reproduce_graphical_release')
        self.assertIsNotNone(release, 'self-contained release reproducer is missing')
        prg = bytes([1, 8]) + bytes(range(256)) * 4
        recipe = dict(disk_name=b'FALKEN9 GRAPHICS'.ljust(16, b'\xa0').hex(),
                      file_name=b'FALKEN9'.ljust(16, b'\xa0').hex(),
                      disk_id=b'\xa0\xa0F9\xa02A\xa0\xa0\xa0\xa0'.hex())
        disk = release.make_disk(prg, recipe)
        self.assertEqual(len(disk), 174848)
        self.assertEqual(release.disk_recipe(disk, prg), recipe)
        damaged = bytearray(disk)
        damaged[-1] = 12
        with self.assertRaisesRegex(ValueError, 'canonical'):
            release.disk_recipe(bytes(damaged), prg)


    def test_verifier_rejects_unlisted_checksum_files_and_broken_links(self):
        release = module('reproduce_graphical_release')
        self.assertTrue(hasattr(release, 'check_markdown_links'), 'local link validator is missing')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'README.md').write_text('[guide](DEPLOYMENT.md)')
            with self.assertRaisesRegex(ValueError, 'local link'):
                release.check_markdown_links(root)
            (root/'DEPLOYMENT.md').write_text('complete')
            release.check_markdown_links(root)
            (root/'README.md').write_text('[escape](../outside.md)')
            with self.assertRaisesRegex(ValueError, 'local link'):
                release.check_markdown_links(root)


class InventoryTests(unittest.TestCase):
    def test_allowlist_includes_local_import_closure_and_graphics_only(self):
        staging = module('stage_graphical_release')
        self.assertIsNotNone(staging, 'release staging script is missing')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = {
                'scripts/build_graphical_app.py': 'from scripts.build_runtime import build\nfrom scripts.compile_graphics import compile\n',
                'scripts/build_runtime.py': 'import struct\n',
                'scripts/compile_graphics.py': 'from PIL import Image\n',
                'scripts/bootstrap_64tass.sh': '# assembler\n',
                'scripts/train_secret.py': 'do not ship',
                'assets/game-art/title.png': 'image fixture',
                'assets/game-art/provenance.json': '{}',
                'assets/game-art/ignored.tmp': 'do not ship',
                'src/runtime/runtime.asm': '; core',
                'src/app/graphical.asm': '; application',
            }
            for name, data in files.items():
                p = root/name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(data)
            found = staging.source_inventory(root)
            self.assertIn('scripts/compile_graphics.py', found)
            self.assertIn('assets/game-art/provenance.json', found)
            self.assertIn('src/app/graphical.asm', found)
            self.assertNotIn('scripts/train_secret.py', found)
            self.assertNotIn('assets/game-art/ignored.tmp', found)
            (root/'assets/game-art/leak.png').symlink_to(root/'scripts/train_secret.py')
            with self.assertRaisesRegex(ValueError, 'symlink'):
                staging.source_inventory(root)


class StageTests(unittest.TestCase):
    def test_staged_and_extracted_fixture_rebuild_and_hash_gate(self):
        staging = module('stage_graphical_release')
        self.assertTrue(hasattr(staging, 'stage'), 'staging pipeline is missing')
        model = Path(os.environ.get('F9_RELEASE_TEST_MODEL', ROOT/'artifacts/flexible-integer/q11-w16-a32-early-interp/model.f9j'))
        if not model.is_file():
            self.skipTest('set F9_RELEASE_TEST_MODEL to exercise the accepted packet')
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = base/'source'
            inputs = staging.FIXED + [
                'scripts/build_runtime.py', 'scripts/bootstrap_64tass.sh',
                'scripts/reproduce_graphical_release.py', 'scripts/render_tensor_workflow.py',
            ]
            inputs += [str(p.relative_to(ROOT)) for directory in ('src/runtime', 'src/app')
                       for p in (ROOT/directory).rglob('*') if p.suffix in {'.asm', '.inc'}]
            for name in inputs:
                target = source/name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT/name, target)
            # This deterministic fixture exercises packaging, NOT graphical acceptance.
            (source/'assets/game-art').mkdir(parents=True)
            shutil.copyfile(ROOT/'assets/model-v1.0.0-tensor-workflow.png', source/'assets/game-art/title.png')
            (source/'scripts/compile_graphics.py').write_text('from PIL import Image\n')
            (source/'scripts/build_graphical_app.py').write_text('''from pathlib import Path
import hashlib
from scripts.build_runtime import FOUR_MODEL, build as build_runtime

def build(output=None):
    output = Path(output)
    core = build_runtime(FOUR_MODEL, output/'core')
    raw = bytes([0, 8]) + (output/'core/runtime.bin').read_bytes()
    path = output/'fixture.prg'
    path.write_bytes(raw)
    return dict(prg_path=str(path), prg_sha256=hashlib.sha256(raw).hexdigest(), core=core)
''')
            candidate = base/'candidate'
            candidate.mkdir()
            packet = model.read_bytes()
            assembler = os.environ.get('TASS64')
            if not assembler:
                self.skipTest('set TASS64 for clean-build integration')
            process = subprocess.run([sys.executable, '-c', 'from scripts.build_runtime import build; import sys; build(sys.argv[1],sys.argv[2])', str(model), str(candidate/'core')], cwd=source, env=os.environ, capture_output=True, text=True)
            self.assertEqual(process.returncode, 0, process.stderr)
            prg = bytes([0, 8])+(candidate/'core/runtime.bin').read_bytes()
            (candidate/'fixture.prg').write_bytes(prg)
            release = module('reproduce_graphical_release')
            recipe = dict(disk_name=b'FIXTURE NOT GAME'.ljust(16,b'\xa0').hex(), file_name=b'FALKEN9'.ljust(16,b'\xa0').hex(), disk_id=b'\xa0\xa0F9\xa02A\xa0\xa0\xa0\xa0'.hex())
            disk = release.make_disk(prg, recipe)
            (candidate/'fixture.d64').write_bytes(disk)
            sha = lambda b: hashlib.sha256(b).hexdigest()
            evidence = base/'evidence.json'
            evidence.write_text(json.dumps(dict(status='passed', artifact=dict(prg_sha256=sha(prg), d64_sha256=sha(disk)), scope='PACKAGING FIXTURE ONLY, NOT ACCEPTANCE')))
            (candidate/'build.json').write_text(json.dumps(dict(prg_sha256=sha(prg), core=dict(model_sha256=sha(packet), image_sha256=staging.CORE_SHA))))
            shot = ROOT/'assets/screenshots/falken9-model-v1.0.0-draw.png'
            metadata = dict(release_id='fixture-only', source_revision='0'*40, screenshots=[dict(name=shot.name, sha256=sha(shot.read_bytes()), caption='Unit-test input; not graphical acceptance')])
            out, archive = base/'upload', base/'transport.zip'
            result = staging.stage(candidate=candidate, model=model, evidence=evidence, screenshots=[shot], output=out, archive=archive, metadata=metadata, source_root=source)
            self.assertEqual(result['repo_id'], 'lewismoten/falcon-9')
            guide=(out/'DEPLOYMENT.md').read_text()
            self.assertIn('Title: `1` human/model, `2` two humans, `0` model/model',guide)
            self.assertIn('Wait for the ready/terminal status',guide)
            self.assertIn('ChatGPT-assisted',guide)
            self.assertTrue((out/'model.f9j').is_file())
            self.assertFalse((out/'source/artifacts').exists())
            self.assertFalse((out/'source/tests').exists())
            self.assertFalse((out/'source/scripts/train_flexible.py').exists())
            release.verify(out)
            with zipfile.ZipFile(archive) as z:
                self.assertEqual(set(z.namelist()), {p.relative_to(out).as_posix() for p in out.rglob('*') if p.is_file()})
                z.extractall(base/'extracted')
            release.verify(base/'extracted')
            for tree in (out, base/'extracted'):
                command = [sys.executable, str(tree/'reproduce.py'), '--output', str(base/('rebuilt-'+tree.name))]
                process = subprocess.run(command, cwd=base, env={**os.environ, 'PYTHONPATH': ''}, capture_output=True, text=True)
                self.assertEqual(process.returncode, 0, process.stderr)
                self.assertEqual((base/('rebuilt-'+tree.name)/result['disk']['path']).read_bytes(), disk)
            render_output = base/'decoded/workflow'
            process = subprocess.run([sys.executable, str(base/'extracted/reproduce.py'), '--render-tensors', str(render_output)], cwd=base, env={**os.environ, 'PYTHONPATH': ''}, capture_output=True, text=True)
            self.assertEqual(process.returncode, 0, process.stderr)
            self.assertTrue(render_output.with_suffix('.png').is_file())
            release.verify(base/'extracted')
            (out/'source/SHA256SUMS').write_text('unlisted nested checksum file')
            with self.assertRaisesRegex(ValueError, 'checksum inventory'):
                release.verify(out)
            (out/'source/SHA256SUMS').unlink()
            (out/'model.f9j').write_bytes(b'tampered')
            with self.assertRaisesRegex(ValueError, 'checksum'):
                release.verify(out)
            evidence.write_text(json.dumps(dict(status='passed', artifact=dict(prg_sha256='0'*64, d64_sha256=sha(disk)))))
            with self.assertRaisesRegex(ValueError, 'evidence'):
                staging.stage(candidate=candidate, model=model, evidence=evidence, screenshots=[shot], output=base/'rejected', archive=base/'reject.zip', metadata=metadata, source_root=source)
            self.assertFalse((base/'rejected').exists())


if __name__ == '__main__':
    unittest.main()
