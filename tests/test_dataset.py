import importlib
import importlib.util
import unittest


class DatasetContractTests(unittest.TestCase):
    def test_independent_oracle_matches_published_tie_examples(self):
        self.assertIsNotNone(importlib.util.find_spec('falken9.dataset'), 'dataset verification is not implemented')
        dataset = importlib.import_module('falken9.dataset')
        self.assertEqual(dataset.oracle_moves((0,) * 9), list('ebdfhcgia'))
        self.assertEqual(dataset.oracle_moves((1, 0, 0, 0, 0, 0, 0, 0, 0)), ['e'])
        self.assertEqual(dataset.oracle_moves((1, 2, 0, 0, 0, 0, 0, 0, 0)), list('edg'))
        with self.assertRaises(ValueError):
            dataset.oracle_moves((1, 1, 1, 2, 2, 0, 0, 0, 0))


    def test_file_verification_rejects_hash_and_count_changes(self):
        import hashlib
        import tempfile
        from pathlib import Path
        dataset = importlib.import_module('falken9.dataset')
        self.assertTrue(hasattr(dataset, 'verify_jsonl'), 'digest/row verifier is not implemented')
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'fixture.jsonl'
            path.write_bytes(b'{"history":""}\n')
            record = {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'rows': 1}
            self.assertEqual(dataset.verify_jsonl(path, record)['rows'], 1)
            with self.assertRaises(ValueError):
                dataset.verify_jsonl(path, dict(record, rows=2))
            path.write_bytes(b'{"history":"a"}\n')
            with self.assertRaises(ValueError):
                dataset.verify_jsonl(path, record)


    def test_history_audit_checks_labels_and_board_consistency(self):
        dataset = importlib.import_module('falken9.dataset')
        self.assertTrue(hasattr(dataset, 'audit_history_rows'), 'history audit is not implemented')
        rows = [
            {'history': '', 'board': '.../.../...', 'next_player': 'X', 'optimal_move': 'e', 'optimal_moves': list('ebdfhcgia')},
            {'history': 'a', 'board': 'X../.../...', 'next_player': 'O', 'optimal_move': 'e', 'optimal_moves': ['e']},
        ]
        summary = dataset.audit_history_rows(iter(rows))
        self.assertEqual(summary['histories'], 2)
        self.assertEqual(summary['unique_nonterminal_boards'], 2)
        with self.assertRaises(ValueError):
            dataset.audit_history_rows(iter([dict(rows[1], optimal_move='a')]))
        with self.assertRaises(ValueError):
            dataset.audit_history_rows(iter([dict(rows[1], board='.../.../...')]))
        with self.assertRaises(ValueError):
            dataset.audit_history_rows(iter([rows[0], rows[0]]))


    def test_prepare_rejects_unpinned_manifest_before_network(self):
        import tempfile
        from pathlib import Path
        dataset = importlib.import_module('falken9.dataset')
        self.assertTrue(hasattr(dataset, 'prepare_dataset'), 'pinned dataset preparation is not implemented')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'manifest.json').write_text('{}')
            with self.assertRaisesRegex(ValueError, 'pinned manifest'):
                dataset.prepare_dataset(root, download=False)


    def test_dataset_cli_exposes_offline_verification(self):
        from pathlib import Path
        import subprocess
        import sys
        script = Path(__file__).resolve().parents[1] / 'scripts' / 'prepare_dataset.py'
        self.assertTrue(script.exists(), 'dataset preparation CLI is not implemented')
        completed = subprocess.run([sys.executable, str(script), '--help'], capture_output=True, text=True, check=True)
        self.assertIn('--offline', completed.stdout)


if __name__ == '__main__':
    unittest.main()
