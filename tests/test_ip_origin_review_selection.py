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

    def test_four_family_routine_policy_scopes_ip_review_to_deepseek_qwen(self):
        self.assertGreaterEqual(len(self.policy["routine_reviewers"]), 4)
        payload = build_selection(self.policy)
        self.assertEqual(
            [row["family"] for row in payload["selected"]],
            ["deepseek", "qwen"],
        )
        self.assertEqual(payload["approved_families"], ["deepseek", "qwen"])
        self.assertEqual(payload["purpose"], "PUBLIC_IP_ORIGIN_REVIEW")
        self.assertLessEqual(payload["daily_openrouter_cost_ceiling_usd"], 1.0)
        self.assertEqual(payload["provider_policy"]["data_collection"], "deny")
        self.assertFalse(payload["semantic_delta_admitted"])

    def test_missing_required_family_fails_closed(self):
        policy = copy.deepcopy(self.policy)
        policy["routine_reviewers"] = [
            row for row in policy["routine_reviewers"] if row["family"] != "qwen"
        ]
        with self.assertRaisesRegex(ValueError, "missing required IP-origin reviewer families"):
            build_selection(policy)


if __name__ == "__main__":
    unittest.main()
