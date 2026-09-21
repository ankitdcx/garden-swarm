import unittest
from tools import gcsc_epoch1_l5 as g
class T(unittest.TestCase):
 def test_finite(self): self.assertEqual(g.report()["bounded_cases"],243)
 def test_deadlock(self): self.assertIn("DEADLOCK_TERMINAL_SEMANTICS_REQUIRED",g.violations({"authority":"VALID","context":"VALID","epistemic":"SUPPORTED","human_effect":"NONE","execution":"DEADLOCK"}))
if __name__=="__main__":unittest.main()
