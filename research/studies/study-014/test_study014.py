import unittest,importlib.util,itertools
import numpy as np

class CoreTests(unittest.TestCase):
    def test_exact_extrema_include_negative_activation_and_half_ties(self):
        spec=importlib.util.find_spec('study014_core')
        self.assertIsNotNone(spec,'joint certificate implementation missing')
        from study014_core import extrema
        def r(a,d):return (1 if a>=0 else -1)*((abs(a)+d//2)//d)
        for d in (1,2,4,8):
            for other,a in itertools.product(range(-7,8),range(-3,4)):
                low,high=extrema(np.array([other]),np.array([a]),d,[-3,2],[-2,3])
                values=[r(other+a*w,d)+b for w in range(-3,3) for b in range(-2,4)]
                self.assertEqual((int(low[0]),int(high[0])),(min(values),max(values)))

    def test_bands_match_all_small_joint_codes(self):
        import study014_core as c
        self.assertTrue(hasattr(c,'bias_bands'),'exact joint bands missing')
        other=np.array([-7,0,5,9]);a=np.array([-2,0,3,-1]);members=np.array([False,True,True,False]);weights=np.arange(-5,6)
        lo,hi=c.bias_bands(other,a,4,members,weights,-8,7)
        for j,w in enumerate(weights):
            good=[]
            for b in range(-8,8):
                yy=np.array([(1 if v>=0 else -1)*((abs(int(v))+2)//4)+b for v in other+a*w])
                if np.array_equal(yy>=0,members):good.append(b)
            predicted=list(range(int(lo[j]),int(hi[j])+1))
            self.assertEqual(predicted,good)

    def test_shrink_rounds_negative_deltas_toward_zero_and_is_nested(self):
        import study014_core as c
        self.assertTrue(hasattr(c,'shrink'),'predeclared shrink missing')
        bounds=[-12,17];old=3
        last=[old,old]
        for k in range(17):
            cur=c.shrink(bounds,old,k)
            self.assertEqual(cur,[old-(15*k//16),old+(14*k//16)])
            self.assertLessEqual(cur[0],last[0]);self.assertGreaterEqual(cur[1],last[1]);last=cur
        self.assertEqual(last,bounds)

    @unittest.skipUnless(__import__('os').environ.get('STUDY014_INTEGRATION')=='1','explicit full frozen study only')
    def test_real_frozen_study_and_independent_proof(self):
        spec=importlib.util.find_spec('study014_run')
        self.assertIsNotNone(spec,'full study runner missing')
        from study014_run import run
        out=__import__('os').environ['STUDY014_OUT']
        run(out)
        import json
        from pathlib import Path
        result=json.loads((Path(out)/'results014.json').read_text())
        audit=json.loads((Path(out)/'independent-audit014.json').read_text())
        self.assertEqual(result['original_row_corner_batches'],36)
        self.assertEqual(result['restoration_batches'],result['candidate_batches'])
        self.assertTrue(audit['pass_all'])
        self.assertEqual(audit['independently_verified_weight_codes'],9*65536)
        self.assertTrue(result['accepted_box_all_combinations_certified'])
        for name in ('joint014.png','joint014.svg','witness014.png','witness014.svg','REPORT014.md'):
            self.assertTrue((Path(out)/name).is_file(),name)

if __name__=='__main__':unittest.main()
