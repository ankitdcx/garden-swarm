import unittest
from tools import gcsc_epoch1_domains as g
class T(unittest.TestCase):
 def test_domains(self): self.assertEqual(len(g.DOMAINS),14)
 def test_pairs(self): self.assertEqual(len(g.l2()),91)
 def test_cross(self): self.assertIn("REQUIRE_AUTHORITY_INTERSECTION",dict(((frozenset((a,b))),d) for a,b,d in g.l2())[frozenset(("authority_consent_rights","collective_multiagent"))])
if __name__=="__main__":unittest.main()
