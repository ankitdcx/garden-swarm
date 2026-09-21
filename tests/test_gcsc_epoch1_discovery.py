import unittest
from tools import gcsc_epoch1_discovery as g
class T(unittest.TestCase):
 def test_l0(self): self.assertEqual(len(g.l0_classes()),2400)
 def test_l2(self): self.assertEqual(len(g.l2_relation_motifs()),576)
 def test_unknown_not_no_obligation(self): self.assertGreater(g.obligation_signature_counts()[()],0)
 def test_delegation(self):
  x=[x for x in g.l0_classes() if x.source=="AGENCY" and x.relation=="delegates" and x.target=="AGENCY"][0]
  self.assertIn("PROHIBIT_AUTHORITY_AMPLIFICATION",x.obligations)
if __name__=="__main__": unittest.main()
