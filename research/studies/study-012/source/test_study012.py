import importlib.util,unittest
import numpy as np
class Test012(unittest.TestCase):
    def test_exact_mean_sign_and_fixed_aggregators(self):
        self.assertIsNotNone(importlib.util.find_spec('study012'),'missing exact offline aggregation')
        from study012 import aggregate
        x=np.array([[-1,1,1],[0,-1,1],[0,1,1],[0,-1,1],[0,1,1],[0,-1,1],[0,1,1],[0,-1,1]])[:,None,:]
        r=aggregate(x)
        self.assertEqual(list(r),['mean-exact-sign','intersection','union','vote-at-least-half'])
        self.assertEqual(r['mean-exact-sign'].tolist(),[[False,True,True]])
        self.assertEqual(r['intersection'].tolist(),[[False,False,True]])
        self.assertEqual(r['union'].tolist(),[[True,True,True]])
        self.assertEqual(r['vote-at-least-half'].tolist(),[[True,True,True]])
        for k,v in r.items():
            self.assertTrue(np.array_equal(aggregate(x[::-1])[k],v))
            self.assertTrue(np.array_equal(aggregate(np.concatenate((x,x)))[k],v))
    def test_finite_execution_and_evidence_entrypoints(self):
        import study012
        self.assertTrue(hasattr(study012,'run'),'missing bounded measurement runner')
        self.assertTrue(hasattr(study012,'render'),'missing measured annotated figures')
        self.assertTrue(hasattr(study012,'report'),'missing complete report')
    def test_independent_audit_and_figure_bounds(self):
        self.assertIsNotNone(importlib.util.find_spec('study012_audit'),'missing independent all-raw audit')
        from study012_audit import audit
        self.assertTrue(callable(audit))
        from pathlib import Path
        import json
        p=Path(__file__).resolve().parent/'artifacts/interpretability/study-012-final/figure-metadata012.json'
        if p.exists():
            metadata=json.loads(p.read_text())
            self.assertTrue(any('red fill = false member' in box['text'] for fig in metadata['figures'] for box in fig['text_boxes']),'membership color legend must include false red members')
            for fig in metadata['figures']:
                boxes=fig['text_boxes']
                for i,a in enumerate(boxes):
                    for b in boxes[i+1:]:
                        x,y,u,v=a['bounds'];xx,yy,uu,vv=b['bounds']
                        self.assertFalse(min(u,uu)>max(x,xx) and min(v,vv)>max(y,yy),(fig['name'],a['text'],b['text']))
    def test_final_handoff_entrypoint_and_synthesis(self):
        self.assertIsNotNone(importlib.util.find_spec('study012_finalize'),'missing final preservation/archive gate')
        from study012_finalize import finalize
        self.assertTrue(callable(finalize))
if __name__=='__main__':unittest.main()
