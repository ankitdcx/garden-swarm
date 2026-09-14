import unittest

from scripts.check_constitutional_change import evaluate


class ConstitutionalChangeGuardTests(unittest.TestCase):
    def test_ordinary_change_passes(self):
        receipt = evaluate(["README.md", "prototype/actiongate.py"])
        self.assertEqual(receipt["result"], "PASS")
        self.assertEqual(receipt["constitutional_paths_touched"], [])

    def test_constitutional_change_escalates_without_external_verifier(self):
        receipt = evaluate(["README.md", "gsl/CHANGE_POLICY.json"])
        self.assertEqual(receipt["result"], "ESCALATE")
        self.assertEqual(receipt["approval_verifier_status"], "NOT_IMPLEMENTED")
        self.assertIn("gsl/CHANGE_POLICY.json", receipt["constitutional_paths_touched"])

    def test_integrity_workflow_is_constitutional(self):
        receipt = evaluate([".github/workflows/integrity.yml"])
        self.assertEqual(receipt["result"], "ESCALATE")


if __name__ == "__main__":
    unittest.main()
