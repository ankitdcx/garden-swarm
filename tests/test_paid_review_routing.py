import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import run_paid_matrix_review as paid


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class PaidReviewRoutingTests(unittest.TestCase):
    def setUp(self):
        self.policy = json.loads(Path("agents/openrouter-paid-review-policy.json").read_text(encoding="utf-8"))

    def test_budget_pools_are_bounded_to_twenty_dollars(self):
        self.assertEqual(sum(self.policy["budget_pools_usd"].values()), 20.0)
        self.assertLessEqual(self.policy["routine_hourly_cost_ceiling_usd"], 0.05)
        self.assertLessEqual(self.policy["routine_model_call_cost_ceiling_usd"], 0.025)

    def test_model_catalog_reference_is_explicit(self):
        self.assertEqual(self.policy["catalog_reference_date"], "2026-09-14")

    def test_routine_family_set_is_exactly_deepseek_and_qwen(self):
        reviewers = self.policy["routine_reviewers"]
        self.assertEqual([row["family"] for row in reviewers], ["deepseek", "qwen"])
        self.assertEqual(len({row["family"] for row in reviewers}), 2)
        self.assertTrue(all(not row["model"].endswith(":free") for row in reviewers))

    def test_provider_policy_denies_collection_and_has_price_ceiling(self):
        provider = self.policy["provider_policy"]
        self.assertEqual(provider["data_collection"], "deny")
        self.assertTrue(provider["allow_fallbacks"])
        self.assertLessEqual(provider["max_price_usd_per_million_tokens"]["prompt"], 0.25)
        self.assertLessEqual(provider["max_price_usd_per_million_tokens"]["completion"], 0.75)

    def test_paid_call_transmits_hard_provider_price_ceiling(self):
        selection = {
            "max_prompt_characters": 10000,
            "max_output_tokens": 100,
            "routine_model_call_cost_ceiling_usd": 0.025,
            "provider_policy": self.policy["provider_policy"],
        }
        model = self.policy["routine_reviewers"][0]
        response = {
            "choices": [{"message": {"content": "{\"ok\": true}"}}],
            "usage": {"cost": 0.001},
        }
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}), patch(
            "tools.run_paid_matrix_review.request.urlopen", return_value=_Response(response)
        ) as mocked:
            raw, attempt = paid._call(model=model, prompt="bounded public target", selection=selection)
        self.assertEqual(raw, {"ok": True})
        self.assertEqual(attempt["status"], "CALLED")
        req = mocked.call_args.args[0]
        body = json.loads(req.data.decode("utf-8"))
        self.assertEqual(body["provider"]["data_collection"], "deny")
        self.assertEqual(body["provider"]["max_price"], {"prompt": 0.25, "completion": 0.75})
        self.assertTrue(body["provider"]["allow_fallbacks"])

    def test_gemini_wrapper_uses_module_execution(self):
        source = Path("tools/run_gemini_free_review.py").read_text(encoding="utf-8")
        self.assertIn('"-m", "tools.gemini_free_review"', source)
        self.assertNotIn('"tools/gemini_free_review.py"', source)


if __name__ == "__main__":
    unittest.main()
