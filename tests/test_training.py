import json
from pathlib import Path
import unittest
import torch
from falken9.model import CompactPolicy, ModelConfig
from falken9.training import load_dataset, evaluate, train_candidate

class TrainingTests(unittest.TestCase):
    def test_training_checkpoint_exhaustive_gate(self):
        root = Path('artifacts/training/test-fixture'); root.mkdir(parents=True, exist_ok=True)
        rows = [dict(history='',board='.../.../...',optimal_move='e'),dict(history='a',board='X../.../...',optimal_move='e')]
        path = root/'data.jsonl'; path.write_text(''.join(json.dumps(r)+'\n' for r in rows))
        data = load_dataset(path)
        self.assertEqual(data['history_count'],2)
        torch.manual_seed(3)
        model = CompactPolicy(ModelConfig(8,8))
        result = train_candidate(model,data,root/'candidate',steps=2,seconds=10,lr=.01,seed=3,device='cpu',eval_every=1)
        saved = torch.load(root/'candidate/best.pt',weights_only=False)
        model.load_state_dict(saved['state_dict'])
        gate = evaluate(model,data,root/'evaluation',device='cpu')
        self.assertEqual(gate['history_count'],2)
        self.assertEqual(gate['history_mismatches'],gate['board_mismatches'])
        self.assertEqual(result['steps_completed'],2)
        self.assertTrue((root/'evaluation/counterexamples.jsonl').exists())
        path.write_text(json.dumps(rows[0])+'\n'+json.dumps(dict(rows[0],optimal_move='a'))+'\n')
        with self.assertRaisesRegex(ValueError,'inconsistent'):
            load_dataset(path)

    def test_low_bit_training_exports_exhaustively_checked_decoder(self):
        root=Path('artifacts/training/test-fixture/lowbit');root.mkdir(parents=True,exist_ok=True)
        path=root/'data.jsonl'
        path.write_text(json.dumps(dict(history='',board='.../.../...',optimal_move='e'))+'\n')
        torch.manual_seed(3)
        result=train_candidate(CompactPolicy(ModelConfig(8,8,'ternary')),load_dataset(path),root,steps=2,seconds=10,lr=.01,seed=3,device='cpu',eval_every=1)
        self.assertTrue((root/'model.f9q').exists())
        self.assertEqual(result['packed']['parity_max_abs_logit_error'],0)
        self.assertEqual(result['packed']['decoded_gate']['history_count'],1)

    def test_reproducible_cli_entrypoints(self):
        import subprocess, sys
        for script in ('scripts/train_search.py','scripts/evaluate_model.py'):
            proc = subprocess.run([sys.executable,script,'--help'],capture_output=True,text=True)
            self.assertEqual(proc.returncode,0,proc.stderr)
            self.assertIn('--dataset',proc.stdout)
            if script.endswith('train_search.py'):
                self.assertIn('--initialize',proc.stdout)
            if script.endswith('evaluate_model.py'):
                self.assertIn('--packed',proc.stdout)

if __name__ == '__main__': unittest.main()
