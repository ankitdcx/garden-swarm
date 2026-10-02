import unittest
from tools import gcsc_semantic_compare as g
class T(unittest.TestCase):
 def test_equiv(self): self.assertEqual(g.compare("authority context","valid authority in context"),"EQUIVALENT_CANDIDATE")
 def test_no_keyword_is_not_equiv(self): self.assertEqual(g.compare("authority","bananas"),"UNRESOLVED")
if __name__=="__main__":unittest.main()
