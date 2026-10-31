import importlib
import importlib.util
import unittest


class SymmetryContractTests(unittest.TestCase):
    def test_eight_square_transforms_are_invertible(self):
        self.assertIsNotNone(importlib.util.find_spec('falken9.symmetry'), 'symmetry mappings are not implemented')
        symmetry = importlib.import_module('falken9.symmetry')
        self.assertEqual(len(set(symmetry.TRANSFORMS)), 8)
        board = tuple(range(9))
        for transform in symmetry.TRANSFORMS:
            self.assertEqual(sorted(transform), list(range(9)))
            moved = symmetry.transform_board(board, transform)
            self.assertEqual(symmetry.transform_board(moved, symmetry.inverse(transform)), board)
            for square in 'abcdefghi':
                result = symmetry.transform_move(square, transform)
                self.assertEqual(symmetry.transform_move(result, symmetry.inverse(transform)), square)
        with self.assertRaises(ValueError):
            symmetry.transform_board(board, (0,) * 9)


    def test_canonical_move_sets_preserve_original_ties_but_single_moves_do_not(self):
        from falken9.dataset import oracle_moves
        from falken9.policy import board_from_history
        symmetry = importlib.import_module('falken9.symmetry')
        self.assertTrue(hasattr(symmetry, 'canonicalize'), 'canonical board wrapper is not implemented')
        board = board_from_history('ae')
        canonical, transform = symmetry.canonicalize(board)
        restored = symmetry.restore_moves(oracle_moves(canonical), transform)
        self.assertEqual(restored, oracle_moves(board))
        center = board_from_history('e')
        turn = symmetry.TRANSFORMS[1]
        self.assertEqual(symmetry.transform_board(center, turn), center)
        selected = oracle_moves(center)[0]
        self.assertNotEqual(symmetry.transform_move(selected, turn), selected)


    def test_symmetry_audit_cli_is_available(self):
        from pathlib import Path
        import subprocess
        import sys
        script = Path(__file__).resolve().parents[1] / 'scripts' / 'audit_symmetry.py'
        self.assertTrue(script.exists(), 'reproducible symmetry audit CLI is not implemented')
        result = subprocess.run([sys.executable, str(script), '--help'], capture_output=True, text=True, check=True)
        self.assertIn('--data', result.stdout)


if __name__ == '__main__':
    unittest.main()
