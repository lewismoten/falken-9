import importlib.util,unittest

class FinalEvidenceTests(unittest.TestCase):
    def test_actual_two_runs_and_observed_extrema_are_verified(self):
        self.assertIsNotNone(importlib.util.find_spec('finish014'),'post-run evidence verification missing')
        from finish014 import audit_existing
        from unittest.mock import patch
        from PIL import Image
        opened=[];real_open=Image.open
        def tracked_open(*args,**kwargs):
            im=real_open(*args,**kwargs);opened.append(im);return im
        with patch('PIL.Image.open',side_effect=tracked_open):
            checked=audit_existing()
        self.assertTrue(all(im.fp is None for im in opened),'figure audit must close actual image handles')
        self.assertTrue(checked['byte_identical'])
        self.assertEqual(checked['observed_original_extrema'],18)
        self.assertEqual(checked['observed_accepted_extrema'],18)
        self.assertEqual(checked['prior_file_counts'],{'study013':86,'study003':1492,'main-protected':51})

if __name__=='__main__':unittest.main()
