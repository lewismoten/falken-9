from pathlib import Path
import unittest
import torch
from falken9.model import CompactPolicy,ModelConfig

class ExportTests(unittest.TestCase):
    def test_packed_decoder_matches_mixed_forward(self):
        from falken9.export import export_model,load_packed
        root=Path('artifacts/training/test-fixture');root.mkdir(parents=True,exist_ok=True)
        for precision in ('binary','ternary'):
            torch.manual_seed(29)
            model=CompactPolicy(ModelConfig(8,8,precision)).eval()
            path=root/f'{precision}.f9q'
            metadata=export_model(model,path)
            decoded=load_packed(path)
            boards=torch.randint(0,3,(11,9))
            self.assertTrue(torch.equal(model(boards),decoded(boards)))
            self.assertEqual(metadata['encoded_bytes'],path.stat().st_size)
            self.assertLess(path.stat().st_size,sum(p.numel()*4 for p in model.parameters())+5000)
            self.assertFalse(metadata['integer_runtime'])

if __name__=='__main__':unittest.main()
