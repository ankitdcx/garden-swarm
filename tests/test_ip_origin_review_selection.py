import copy
import json
import unittest
from pathlib import Path

from tools.select_ip_origin_reviewers import build_selection


class IPOriginReviewSelectionTests(unittest.TestCase):
    def setUp(self):
        self.policy = json.loads(
            Path("agents/openrouter-paid-review-policy.json").read_text(encoding="utf-8")
        )

    def test_ip_review_uses_all_current_approved_routine_families(self):
        self.assertGreaterEqual(len(self.policy["routine_reviewers"]), 4)
        payload = build_selection(self.policy)
        expected = []
        seen = set()
        for row in self.policy["routine_reviewers"]:
            family = row["family"]
            if family not in seen:
                seen.add(family)
                expected.append(family)
        self.assertEqual([row["family"] for row in payload["selected"]], expected)
        self.assertEqual(payload["approved_families"], expected)
        self.assertIn("deepseek", expected)
        self.assertIn("qwen", expected)
        self.assertEqual(payload["anchor_families"], ["deepseek", "qwen"])
        self.assertEqual(payload["purpose"], "PUBLIC_IP_ORIGIN_REVIEW")
        self.assertLessEqual(payload["daily_openrouter_cost_ceiling_usd"], 2.0)
        self.assertEqual(payload["provider_policy"]["data_collection"], "deny")
        self.assertFalse(payload["semantic_delta_admitted"])

    def test_missing_required_anchor_family_fails_closed(self):
        policy = copy.deepcopy(self.policy)
        policy["routine_reviewers"] = [
            row for row in policy["routine_reviewers"] if row["family"] != "qwen"
        ]
        with self.assertRaisesRegex(ValueError, "missing required IP-origin anchor families"):
            build_selection(policy)

    def test_duplicate_family_is_deduplicated_without_reordering(self):
        policy = copy.deepcopy(self.policy)
        policy["routine_reviewers"].append(copy.deepcopy(policy["routine_reviewers"][0]))
        payload = build_selection(policy)
        families = [row["family"] for row in payload["selected"]]
        self.assertEqual(len(families), len(set(families)))
        self.assertEqual(families[0], policy["routine_reviewers"][0]["family"])


if __name__ == "__main__":
    unittest.main()
