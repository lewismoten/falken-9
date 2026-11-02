import unittest
try:
    import study013_core as core
except ImportError:
    core=None

class ExactArithmetic(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(core,'Exact interval arithmetic is not implemented')
    def test_rounding_threshold_exact_including_zero_and_halves(self):
        for d in (1,2,4,8,32):
            for target in range(-8,9):
                got=core.threshold(target,d)
                expected=next(a for a in range(-400,401) if core.rounded(a,d)>=target)
                self.assertEqual(got,expected)
    def test_integer_constraint_interval_matches_exhaustive_signed_codes(self):
        for a in range(-5,6):
            for c in range(-20,21):
                for positive in (False,True):
                    expected=[x for x in range(-32,32) if ((a*x>=c) if positive else (a*x<c))]
                    got=core.constrain(-32,31,a,c,positive)
                    observed=list(range(got[0],got[1]+1)) if got else []
                    self.assertEqual(observed,expected)

    def test_coordinate_certificate_matches_full_code_census(self):
        self.assertTrue(hasattr(core,'certificate'),'Coordinate certificate is missing')
        for kind in ('bias','weight'):
            rows=[dict(dot=13,activation=-3,bias=2,member=True),dict(dot=-19,activation=5,bias=-1,member=False)]
            old=1
            for row in rows:
                row['member']=core.rounded(row['dot'],4)+row['bias']>=0
            got=core.certificate(rows,kind,old,4,-32,31)
            good=[]
            for x in range(-32,32):
                signs=[(core.rounded(r['dot']+(x-old)*r['activation'],4)+r['bias']>=0) if kind=='weight' else (core.rounded(r['dot'],4)+x>=0) for r in rows]
                if signs==[r['member'] for r in rows]:good.append(x)
            self.assertEqual(got['code_interval'],[min(good),max(good)])

    def test_source_code_bounds_are_enforced(self):
        import copy
        import torch
        from falken9.strategy_diagnostics import parameter_copy
        candidate={'tensors':{'output.bias':{'codes':torch.tensor([0]),'bits':16,'exponents':[-11]}}}
        for legal in (-32768,32767):
            got=parameter_copy(candidate,'output.bias',(0,),legal)
            self.assertEqual(int(got['tensors']['output.bias']['codes'][0]),legal)
            self.assertEqual(int(candidate['tensors']['output.bias']['codes'][0]),0)
        for illegal in (-32769,32768):
            with self.assertRaises(ValueError):parameter_copy(candidate,'output.bias',(0,),illegal)

    def test_runner_and_independent_verifier_exist(self):
        from pathlib import Path
        for name in ('study013_run.py','study013_verify.py','study013_render.py'):
            self.assertTrue(Path(name).is_file(),name+' not implemented')

if __name__=='__main__':unittest.main()
