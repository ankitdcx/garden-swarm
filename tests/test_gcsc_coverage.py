import unittest
from tools import gcsc_coverage as g
class GCSCTests(unittest.TestCase):
 def test_raw_spaces(self):
  self.assertEqual(g.RAW_L0,2400); self.assertEqual(g.RAW_L1,21168000)
 def test_counts_close(self):
  c,_=g.l1_counts(); self.assertEqual(sum(c.values()),g.RAW_L1)
 def test_macro_gate(self): self.assertEqual(g.structural_l1("STATE","Function","THING","dependsOn","CONTEXT"),"INVALID_MACRO_FORM")
 def test_unknown_not_pass(self): self.assertTrue(all(x["classification"]=="TYPE_SIGNATURE_REQUIRED" for x in g.l0()))
if __name__=="__main__": unittest.main()
