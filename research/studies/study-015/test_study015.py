import unittest,importlib
class Contract(unittest.TestCase):
 def test_geometry_and_sampler_contract(self):
  self.assertIsNotNone(importlib.util.find_spec('study015_core'),'missing bounded policy emulator')
  from study015_core import canonical,restore,choose,sample,PERMS,trajectory_key
  self.assertEqual(choose(list(range(9))),4)
  b=(1,0,0,0,2,0,0,0,0); cb,p=canonical(b)
  self.assertEqual(cb,(0,0,0,0,2,0,0,0,1))
  self.assertEqual(restore([0]*9,b,p),[i for i in range(9) if b[i]==0])
  self.assertEqual(sample([4],4,167),(4,167,0))
  for mask in ([0,8],[1,4,6],[0,1,2,3,4,5,6],[0,1,2,3,4,5,6,7,8]):
   for prev in mask:
    for seed in range(1,256):
     move,state,attempts=sample(mask,prev,seed)
     self.assertIn(move,mask);self.assertNotEqual(move,prev)
  self.assertEqual(sample([0,8],0,0)[0],8)
  for prev in range(9):
   for seed in range(1,256):
    s,state,attempts=sample(list(range(9)),prev,seed)
    self.assertNotEqual(s,prev);self.assertIn(state,range(1,256));self.assertLessEqual(attempts,9)
  self.assertEqual(len(set(PERMS)),8)
  seq=[4,1,3,5,7,2,6,8,0]
  for p in PERMS:self.assertEqual(trajectory_key(seq),trajectory_key([p[s] for s in seq]))
class Execution(unittest.TestCase):
 def test_real_forwards_provenance_and_complete_games(self):
  self.assertIsNotNone(importlib.util.find_spec('study015_run'),'missing real-forward runner')
  from study015_run import run
  import tempfile,pathlib,json,shutil
  root=pathlib.Path(__file__).resolve().parent
  out=root/'test-output015'
  if out.exists():shutil.rmtree(out)
  r=run(out)
  self.assertEqual(r['opening_count'],9)
  self.assertEqual(r['complete_games'],9)
  self.assertEqual(r['game_forward_calls'],sum(r['lengths']))
  self.assertEqual(r['minimax_wrong_sets'],0)
  self.assertEqual(r['domain_canonical'],627)
  self.assertEqual(len(json.loads((out/'games015.json').read_text())),9)
class Independent(unittest.TestCase):
 def test_independent_full_stages(self):
  self.assertIsNotNone(importlib.util.find_spec('study015_audit'),'missing independent audit')
  from study015_audit import audit
  from pathlib import Path
  r=audit(Path(__file__).resolve().parent/'test-output015')
  self.assertTrue(r['passed']);self.assertEqual(r['game_forward_audits'],81)
class NegativeControls(unittest.TestCase):
 def test_auditor_rejects_corrupted_game_coordinate(self):
  from study015_audit import audit
  from pathlib import Path
  import tempfile,json
  root=Path(__file__).resolve().parent;source=root/'test-output015'
  with tempfile.TemporaryDirectory(dir=root,prefix='audit-negative015-') as d:
   out=Path(d)
   for p in source.iterdir():
    if p.is_file() and p.name!='games015.json':(out/p.name).symlink_to(p)
   g=json.loads((source/'games015.json').read_text());g[0]['steps'][0]['selected_move']=99
   (out/'games015.json').write_text(json.dumps(g))
   with self.assertRaises(AssertionError):audit(out)
class Visuals(unittest.TestCase):
 def test_evidence_figures_and_report(self):
  self.assertIsNotNone(importlib.util.find_spec('study015_render'),'missing evidence renderer')
  from study015_render import render
  from pathlib import Path
  from PIL import Image
  out=Path(__file__).resolve().parent/'test-output015';render(out)
  for name in ['paths015','routes015','sampler015']:
   self.assertTrue((out/(name+'.svg')).read_text().startswith('<svg'))
   with Image.open(out/(name+'.png')) as im:self.assertGreaterEqual(im.width,1400)
  report=(out/'REPORT015.md').read_text()
  for term in ['37/627','64/4520','not learning','host','248','1/8','1/9']:
   self.assertIn(term,report)
if __name__=='__main__':unittest.main()
