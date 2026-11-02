"""New isolated study helpers; caches disabled in invocation."""
import importlib.util,unittest
import numpy as np
from falken9.symmetry import TRANSFORMS,transform_board,inverse

class Test1011(unittest.TestCase):
    def test_alignment_and_inverse(self):
        spec=importlib.util.find_spec('study1011_core')
        self.assertIsNotNone(spec,'missing orientation-alignment implementation')
        from study1011_core import align_stage
        for t in TRANSFORMS:
            inv=inverse(t)
            self.assertEqual(transform_board(transform_board(tuple(range(9)),t),inv),tuple(range(9)))
            v=np.arange(18).reshape(9,2);rot=np.empty_like(v);rot[list(t)]=v
            self.assertTrue(np.array_equal(align_stage('board_query',rot,t),v))
            p=np.arange(81).reshape(9,9);rp=np.empty_like(p);rp[np.ix_(t,t)]=p
            self.assertTrue(np.array_equal(align_stage('attention_probs',rp,t),p))
            y=np.arange(9);ry=np.empty_like(y);ry[list(t)]=y
            self.assertTrue(np.array_equal(align_stage('logits',ry,t),y))
            self.assertTrue(np.array_equal(align_stage('merged',np.arange(8),t),np.arange(8)))
    def test_census_equality_and_inactive_nulls(self):
        import study1011_core as c
        self.assertTrue(hasattr(c,'collision_census'),'missing exact collision census')
        vals=[np.array([1,2]),np.array([1,2]),np.array([3,4])]
        labels=[(True,False),(False,False),(False,False)];optimal=[(1,),(2,),(2,)]
        r,groups=c.collision_census(vals,labels,optimal,[(0,),(0,),(1,)])
        self.assertEqual(r['distinct_classes'],2)
        self.assertEqual(r['duplicate_boards'],2)
        self.assertEqual(r['colliding_pairs'],1)
        self.assertEqual(r['mixed_tactic_classes'],1)
        self.assertEqual(r['mixed_optimal_classes'],1)
        self.assertEqual(r['conditioned']['mixed_tactic_classes'],1)
        # Hash bucket collisions must never merge unequal bytes.
        rr,_=c.collision_census(vals,labels,optimal,[(0,)]*3,hash_fn=lambda b:'forced')
        self.assertEqual(rr['distinct_classes'],2)
        rr,_=c.collision_census([np.array([9]),np.array([8]),np.array([8]),np.array([9])],[(0,),(0,),(1,),(1,)],[(0,)]*4,[(0,)]*4)
        self.assertEqual(rr['first_tactic_pair'],[0,3])
        rr,_=c.collision_census([np.array([9]),np.array([8]),np.array([8]),np.array([9]),np.array([9])],[(0,),(0,),(1,),(0,),(1,)],[(0,)]*5,[(1,),(0,),(0,),(0,),(0,)])
        self.assertEqual(rr['conditioned']['first_tactic_pair'],[1,2])
        self.assertNotEqual(c.serialize(np.array([[1,2]])),c.serialize(np.array([1,2])))
        routes=np.array([3,1]);v=np.arange(8).reshape(4,2)
        record=c.expert_record(routes,v)
        self.assertIsNone(record[0]['value']);self.assertIsNone(record[2]['value'])
        self.assertEqual(record[1]['value'],[2,3]);self.assertEqual(record[3]['value'],[6,7])
        z=v.copy();z[0]=999;z[2]=888
        self.assertTrue(np.array_equal(c.executed_vector(routes,v),c.executed_vector(routes,z)))
        self.assertFalse(np.array_equal(c.executed_vector(routes,v),c.executed_vector(np.array([3,0]),v)))
    def test_measurement_runners_and_metric_partition(self):
        spec=importlib.util.find_spec('study1011_run')
        self.assertIsNotNone(spec,'missing executable finite-study runners')
        from study1011_run import measure_sets,run010,run011
        gold=np.array([[1,1,0],[0,1,0],[1,0,0],[0,0,1]],bool)
        pred=np.array([[0,1,0],[0,0,0],[0,0,1],[0,0,1]],bool)
        # Priority index1 then0 then2; distinguishes correct alternative from loss.
        r=measure_sets(pred,gold,[1,0,2])
        self.assertEqual(r['empty_sets'],1)
        self.assertEqual(r['nonoptimal_nonempty'],1)
        self.assertEqual(r['full_set_changes'],3)
        self.assertEqual(r['chosen_optimal'],2)
        self.assertEqual(r['optimal_tie_changes'],0)
        self.assertTrue(callable(run010) and callable(run011))
    def test_json_integer_metadata(self):
        import tempfile,json
        from pathlib import Path
        from study1011_run import put
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'record.json'
            put(p,dict(control=[np.int64(4)],active=np.bool_(True)))
            self.assertEqual(json.loads(p.read_text()),dict(control=[4],active=True))
    def test_independent_audit_entrypoints(self):
        spec=importlib.util.find_spec('study1011_audit')
        self.assertIsNotNone(spec,'missing independent audits')
        from study1011_audit import independent_transforms,oracle,label_board,audit010,audit011
        self.assertEqual(independent_transforms(),TRANSFORMS)
        self.assertEqual(oracle((1,1,0,2,2,0,0,0,0)),(2,))
        self.assertTrue(label_board((1,1,0,2,2,0,0,0,0))['has_win'])
        self.assertTrue(callable(audit010) and callable(audit011))
    def test_render_report_contract(self):
        spec=importlib.util.find_spec('study1011_render')
        self.assertIsNotNone(spec,'missing measured figures and report generator')
        from study1011_render import render010,render011,walkthrough,make_reports
        self.assertTrue(all(callable(f) for f in (render010,render011,walkthrough,make_reports)))
    def test_rendered_text_boxes_do_not_overlap(self):
        import json
        from pathlib import Path
        root=Path(__file__).resolve().parent/'artifacts/interpretability'
        for p in [root/'study-010-final/figure-metadata010.json',root/'study-011-final/figure-metadata011.json',root/'study-010-011-walkthrough/figure-metadata-walkthrough1011.json']:
            if not p.exists():continue
            for fig in json.loads(p.read_text())['figures']:
                boxes=fig['text_boxes']
                for i,a in enumerate(boxes):
                    for b in boxes[i+1:]:
                        x1,y1,x2,y2=a['bounds'];u1,v1,u2,v2=b['bounds']
                        self.assertFalse(min(x2,u2)>max(x1,u1) and min(y2,v2)>max(y1,v1),(fig['name'],a['text'],b['text']))
    def test_walkthrough_independent_data_and_baseline_selection(self):
        import inspect
        from study1011_render import walkthrough
        self.assertIn('baseline_path',inspect.signature(walkthrough).parameters)
        import study1011_audit as audit
        self.assertTrue(hasattr(audit,'audit_walkthrough'),'missing independent illustrated arithmetic check')
    def test_finalizer_artifact_and_safe_archive_contract(self):
        spec=importlib.util.find_spec('study1011_finalize')
        self.assertIsNotNone(spec,'missing reproduction/source/archive final gate')
        from study1011_finalize import compare,archive
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);a=root/'a';b=root/'b';a.mkdir();b.mkdir();(a/'one.txt').write_text('x');(b/'one.txt').write_text('x')
            self.assertEqual(compare(a,b)['artifact_count'],1)
            result=archive(root/'safe.zip',{'evidence/one.txt':a/'one.txt'})
            self.assertEqual(result['entries'],1)
            (a/'bad.rom').write_bytes(b'x')
            with self.assertRaises(AssertionError):archive(root/'bad.zip',{'bad.rom':a/'bad.rom'})
if __name__=='__main__':unittest.main()
