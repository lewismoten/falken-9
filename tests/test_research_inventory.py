"""Portable research inventory/security tests; no models or sibling archives."""
import copy
import importlib.util
import io
import json
from pathlib import Path
import stat
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('research_inventory_validator', ROOT / 'research/validate.py')
assert spec is not None and spec.loader is not None
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)


class ResearchInventory(unittest.TestCase):
    def test_all_hashes_paths_source_and_study_coverage(self):
        result = v.validate()
        self.assertTrue(result['passed'])
        self.assertEqual(result['studies'], list(range(3, 17)))

    def test_manifest_member_and_source_closure(self):
        d = json.loads((ROOT / 'research/inventory.json').read_text())
        for g in d['groups']:
            rows = [r for r in d['files'] if r['source_group'] == g['id']]
            self.assertEqual(len(rows), g['archive_members'])
            if g['archive']:
                self.assertRegex(g['archive_sha256'], '^[0-9a-f]{64}$')
            else:
                self.assertEqual(g['source_kind'], 'filesystem-recovery')
                self.assertIsNone(g['archive_sha256'])
        self.assertTrue(all('/home/' not in str(g) for g in d['groups']))
        self.assertTrue(any(r['status'] == 'reference' and r['path'].startswith('docs/research/') for r in d['files']))

    def test_traversal_and_absolute_paths_rejected(self):
        for p in ['../x', '/x', 'a/../b', 'a/./b', 'C:/x', 'a\\b', 'a//b', '', 'a\x00b']:
            with self.subTest(path=p), self.assertRaises(ValueError):
                v.safe_relative(p)
        self.assertEqual(str(v.safe_relative('source/test_015.py')), 'source/test_015.py')

    def test_symlink_path_rejected(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / 'real').write_text('x')
            (root / 'alias').symlink_to(root / 'real')
            with self.assertRaises(ValueError):
                v.inside(root, 'alias')

    def test_zip_symlink_traversal_duplicate_and_ratio_rejected(self):
        fixtures = [('traversal', '../bad', 0), ('absolute', '/bad', 0), ('symlink', 'alias', (stat.S_IFLNK | 0o777) << 16)]
        for label, name, attr in fixtures:
            with self.subTest(label=label):
                stream = io.BytesIO()
                with zipfile.ZipFile(stream, 'w') as z:
                    i = zipfile.ZipInfo(name)
                    i.external_attr = attr
                    z.writestr(i, 'payload')
                stream.seek(0)
                with zipfile.ZipFile(stream) as z, self.assertRaises(ValueError):
                    v.audit_zip(z)
        stream = io.BytesIO()
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            with zipfile.ZipFile(stream, 'w') as z:
                z.writestr('a', '1')
                z.writestr('a', '2')
        stream.seek(0)
        with zipfile.ZipFile(stream) as z, self.assertRaises(ValueError):
            v.audit_zip(z)
        # Controlled fake metadata exercises limits without allocating a ZIP bomb.
        i = zipfile.ZipInfo('huge'); i.file_size = v.MAX_MEMBER + 1
        class Fake:
            def infolist(self): return [i]
        with self.assertRaises(ValueError): v.audit_zip(Fake())
        i.file_size = 2001; i.compress_size = 1
        with self.assertRaises(ValueError): v.audit_zip(Fake())

    def test_hash_change_and_missing_coverage_detected(self):
        d = json.loads((ROOT / 'research/inventory.json').read_text())
        broken = copy.deepcopy(d)
        next(r for r in broken['files'] if r['status'] == 'included')['sha256'] = '0' * 64
        with self.assertRaises(ValueError): v.validate(ROOT, broken)
        broken = copy.deepcopy(d)
        broken['groups'] = [g for g in broken['groups'] if g['id'] != '016']
        with self.assertRaises(ValueError): v.validate(ROOT, broken)

    def test_no_model_rom_archive_environment_or_secret_paths(self):
        for p in (ROOT / 'research/studies').rglob('*'):
            self.assertFalse(p.is_symlink())
            if p.is_file():
                self.assertNotIn(p.suffix.lower(), v.FORBIDDEN)
                self.assertFalse(set(p.parts) & {'.git', '.venv', '__pycache__', '.ssh', '.env'})

    def test_machine_sampler_harness_and_actual_binary_boundary(self):
        p = ROOT / 'docs/research/study-015/machine-sampler-parity.py'
        self.assertTrue(p.is_file())
        source = p.read_text()
        self.assertIn('c571353a61c8a663050c33809b6ca880d29aebc969c545a717da2644eed3143a', source)
        self.assertIn('2570b642780ea6dd2e64c1b915e4bf3143fd8d86e1f9e2224f483f53d9bdb21d', source)
        self.assertIn('from py65.devices.mpu6502 import MPU', source)


if __name__ == '__main__':
    unittest.main()
