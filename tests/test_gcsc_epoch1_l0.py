import unittest
from tools import gcsc_epoch1_l0 as g
class T(unittest.TestCase):
 def test_counts(self): self.assertEqual(g.counts(),{"TYPED_ADMISSIBLE_SOURCE_SUPPORTED":2,"UNKNOWN_PAIR_PREDICATE":2398})
 def test_no_guess(self): self.assertEqual(g.classify("RULE","governs","ACTION"),"UNKNOWN_PAIR_PREDICATE")
 def test_acts(self): self.assertEqual(g.classify("AGENCY","acts","ACTION"),"TYPED_ADMISSIBLE_SOURCE_SUPPORTED")
if __name__=="__main__": unittest.main()
