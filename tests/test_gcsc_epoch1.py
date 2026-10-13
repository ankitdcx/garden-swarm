import unittest
from tools import gcsc_epoch1 as g
class T(unittest.TestCase):
 def test_l0(self): self.assertEqual(len(g.enumerate_l0()),2400)
 def test_partition(self):
  r=g.compare_families({"A","B","C"},{"B","C","D"})
  self.assertEqual(r.rediscovered,frozenset({"B","C"})); self.assertEqual(r.new_candidates,frozenset({"D"})); self.assertEqual(r.not_rediscovered,frozenset({"A"}))
 def test_gate(self):
  self.assertFalse(g.coverage_allowed(False,True,True)); self.assertTrue(g.coverage_allowed(True,True,True))
