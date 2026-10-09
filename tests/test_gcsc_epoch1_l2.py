import unittest
from tools import gcsc_epoch1_l2 as g
class T(unittest.TestCase):
 def test_pairs(self): self.assertEqual(g.report()["raw_relation_pairs"],576)
 def test_delegation_chain(self): self.assertIn("REQUIRE_DELEGATION_SCOPE_INTERSECTION",g.emergent("delegates","delegates"))
 def test_no_fake(self): self.assertEqual(g.emergent("identifies","frames"),frozenset())
if __name__=="__main__": unittest.main()
