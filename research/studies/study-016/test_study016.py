import unittest
from fractions import Fraction
import study016

class PolicyTests(unittest.TestCase):
 def test_three_frozen_ties(self):
  b=(0,)*9; logits=[2,3,-1,4,1,-1,-1,-1,9]
  self.assertEqual(study016.pick(b,logits,'accepted'),4)
  self.assertEqual(study016.pick(b,logits,'reversed'),0)
  self.assertEqual(study016.pick(b,logits,'largest_score'),8)
  b=(0,0,0,0,0,0,0,0,1)
  self.assertEqual(study016.pick(b,logits,'largest_score'),3)

class DagTests(unittest.TestCase):
 def test_exact_uniform_terminal_and_length(self):
  # O can win at f now; with uniformly random O, terminal lengths differ.
  b=(1,1,0,2,2,0,1,2,1)
  dp=study016.make_dp('accepted',2,lambda b,p:5)
  self.assertEqual(dp(b),((Fraction(1),Fraction(0),Fraction(0)),Fraction(1),(1,0,0)))
  dp=study016.make_dp('accepted',1,lambda b,p:5)
  self.assertEqual(dp(b),((Fraction(0),Fraction(1,2),Fraction(1,2)),Fraction(3,2),(0,1,1)))
 def test_domain_geometry(self):
  raw=study016.domain()
  self.assertEqual(len(raw),4520)
  self.assertEqual(len({study016.canonical(b)[0] for b in raw}),627)
  self.assertEqual(study016.canonical((0,)*9)[1],tuple(range(9)))

class IntegrationTests(unittest.TestCase):
 def test_real_binding_six_panels(self):
  import tempfile
  from pathlib import Path
  with tempfile.TemporaryDirectory(dir='/home/ai/.hermes/cache/scratch') as d:
   out=Path(d)/'result'
   r=study016.run(out)
   self.assertEqual(r['neural_binding_boards'],627)
   self.assertEqual(len(r['panels']),6)
   for p in r['panels']:
    self.assertEqual(sum(Fraction(p[k]) for k in ('win','draw','loss')),1)
    self.assertEqual(p['loss'],'0')
    self.assertEqual(p['supported_games'],sum(p['supported_by_outcome']))
   self.assertTrue((out/'domain016.npz').exists())

class AuditTests(unittest.TestCase):
 def test_inverse_negative_control(self):
  import audit016
  b=(1,0,0,0,0,0,0,0,0);p=(2,5,8,1,4,7,0,3,6);y=[-7]*9;y[p[1]]=9
  self.assertEqual(audit016.restore(b,y,p),[1])
  corrupted=p[1:]+p[:1]
  self.assertNotEqual(audit016.restore(b,y,corrupted),[1])

class VisualTests(unittest.TestCase):
 def test_two_annotated_pairs(self):
  import render016
  from pathlib import Path
  import tempfile,json
  with tempfile.TemporaryDirectory(dir='/home/ai/.hermes/cache/scratch') as d:
   out=Path(d)
   render016.render(Path(__file__).parent/'results016',out)
   for name in ('roles-outcomes016','branching-example016'):
    self.assertGreater((out/(name+'.png')).stat().st_size,10000)
    self.assertIn('<svg',(out/(name+'.svg')).read_text())
   m=json.loads((out/'figure-metadata016.json').read_text())
   self.assertEqual(m['panels'],6)
   self.assertTrue(m['offline_only'])

class BundleTests(unittest.TestCase):
 def test_bundle_rejects_packet_and_repeats(self):
  from pathlib import Path
  import tempfile,hashlib,zipfile
  from finish016 import bundle
  with tempfile.TemporaryDirectory(dir='/home/ai/.hermes/cache/scratch') as d:
   root=Path(d);(root/'example.txt').write_text('evidence')
   (root/'model.f9j').write_bytes(b'F9J2secret-model')
   with self.assertRaises(ValueError):bundle(root,[root/'model.f9j'],root/'bad.zip')
   bundle(root,[root/'example.txt'],root/'good.zip');a=hashlib.sha256((root/'good.zip').read_bytes()).hexdigest()
   bundle(root,[root/'example.txt'],root/'good.zip');self.assertEqual(a,hashlib.sha256((root/'good.zip').read_bytes()).hexdigest())
   with zipfile.ZipFile(root/'good.zip') as z:self.assertEqual(z.namelist(),['example.txt']);self.assertIsNone(z.testzip())

if __name__=='__main__': unittest.main()
