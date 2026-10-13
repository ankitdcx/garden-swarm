import unittest
from tools import gcsc_closure_lint as g
class T(unittest.TestCase):
 def test_missing(self):
  x=g.ClosureBinding("X")
  self.assertEqual(set(g.lint(x)),{"MISSING_SCHEMA_BINDING","MISSING_INVARIANT_BINDING","MISSING_VERIFICATION_BINDING","MISSING_FUNCTION_BINDING","MISSING_OWNER_BINDING"})
 def test_full(self):
  x=g.ClosureBinding("X",("S",),("I",),("T",),(),("F",),("O",))
  self.assertEqual(g.lint(x),())
if __name__=="__main__":unittest.main()
