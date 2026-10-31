import importlib
import importlib.util
import unittest


class PolicyContractTests(unittest.TestCase):
    def test_history_board_preserves_players_and_rejects_invalid_continuation(self):
        self.assertIsNotNone(importlib.util.find_spec('falken9.policy'), 'history validator is not implemented')
        policy = importlib.import_module('falken9.policy')
        self.assertEqual(policy.board_from_history('ae'), (1, 0, 0, 0, 2, 0, 0, 0, 0))
        self.assertEqual(policy.board_from_history(''), (0,) * 9)
        for invalid in ['aa', 'A', 'j', 'a e', 'adbecfg', 'abcdefghi', None]:
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                policy.board_from_history(invalid)


    def test_selection_masks_occupied_and_uses_published_tie_order(self):
        policy = importlib.import_module('falken9.policy')
        self.assertTrue(hasattr(policy, 'select_move'), 'legal output selection is not implemented')
        self.assertEqual(policy.select_move([0] * 9, ''), 'e')
        self.assertEqual(policy.select_move([0] * 9, 'e'), 'b')
        self.assertEqual(policy.select_move([100, 2, 0, 0, 0, 0, 0, 0, 0], 'a'), 'b')
        for scores in [[0] * 8, [float('nan')] * 9, [float('inf')] * 9]:
            with self.assertRaises(ValueError):
                policy.select_move(scores, '')


if __name__ == '__main__':
    unittest.main()
