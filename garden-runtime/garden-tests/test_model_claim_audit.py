import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "garden-console"))
from server import audit_numeric_claims


class ModelClaimAuditTests(unittest.TestCase):
    def test_observed_smol_wrong_arithmetic_cannot_be_called_verified(self):
        result = audit_numeric_claims([{"role": "representation escape", "summary": "17 * 23 = 427"}])
        self.assertEqual(result[0]["status"], "CONTRADICTED")
        self.assertEqual(result[0]["expected"], 391)

    def test_correct_small_equality_not_reported_contradicted(self):
        self.assertEqual(audit_numeric_claims([{"summary": "12+30=42"}]), [])

    def test_freeform_prose_is_not_assigned_a_pass(self):
        self.assertEqual(audit_numeric_claims([{"summary": "All consequences are safe."}]), [])


if __name__ == "__main__": unittest.main()
