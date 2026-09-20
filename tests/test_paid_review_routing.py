import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import run_paid_matrix_review as paid
from tools import select_paid_matrix_reviewers as selector

class _Response:
    def __init__(self, payload): self.payload = payload
    def __enter__(self): return self
    def __exit__(self, exc_type, exc, tb): return False
    def read(self): return json.dumps(self.payload).encode("utf-8")

class PaidReviewRoutingTests(unittest.TestCase):
    def setUp(self):
        self.policy = json.loads(Path("agents/openrouter-paid-review-policy.json").read_text(encoding="utf-8"))

    def test_budget_is_low_cost_and_fail_closed(self):
        self.assertEqual(sum(self.policy["budget_pools_usd"].values()), 20.0)
        self.assertEqual(self.policy["daily_openrouter_cost_ceiling_usd"], 2.0)
        self.assertEqual(self.policy["routine_task_cost_ceiling_usd"], 2.0)
        self.assertEqual(self.policy["routine_model_call_cost_ceiling_usd"], 0.01)
        self.assertEqual(self.policy["automatic_expensive_escalation_daily_ceiling_usd"], 0.0)
        self.assertEqual(self.policy["event_driven_activation"]["no_change_default"], "NO_PAID_CALL")
        self.assertTrue(self.policy["event_driven_activation"]["deterministic_gate_before_model"])

    def test_model_catalog_reference_is_current(self):
        self.assertEqual(self.policy["catalog_reference_date"], "2026-09-19")

    def test_routine_family_set_is_five_specialist_board(self):
        reviewers = self.policy["routine_reviewers"]
        families = [row["family"] for row in reviewers]
        models = [row["model"] for row in reviewers]
        self.assertEqual(families, ["deepseek", "xiaomi", "nvidia", "pareto", "mistral"])
        self.assertEqual(models, [
            "deepseek/deepseek-v4-pro-0813",
            "xiaomi/mimo-v2.5-pro",
            "nvidia/nemotron-3-ultra-550b-a55b",
            "unbiased/pareto",
            "mistralai/mistral-medium-3-5",
        ])
        self.assertEqual(len(set(families)), 5)

    def test_provider_policy_denies_collection_and_keeps_anthropic_excluded(self):
        provider = self.policy["provider_policy"]
        self.assertEqual(provider["data_collection"], "deny")
        self.assertTrue(provider["allow_fallbacks"])
        self.assertEqual(set(provider["ignore"]), set())
        self.assertLessEqual(provider["max_price_usd_per_million_tokens"]["prompt"], 1.0)
        self.assertLessEqual(provider["max_price_usd_per_million_tokens"]["completion"], 3.0)

    def test_selector_is_offline_and_uses_five_slots(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(selector, "OUTPUT", Path(tmp) / "selection.json"), patch.dict(os.environ, {}, clear=True):
            self.assertEqual(selector.main(), 0)
            receipt = json.loads((Path(tmp) / "selection.json").read_text(encoding="utf-8"))
        expected = [row["family"] for row in self.policy["routine_reviewers"]]
        self.assertEqual([row["family"] for row in receipt["selected"]], expected)
        self.assertEqual(receipt["approved_families"], expected)
        self.assertEqual(receipt["daily_openrouter_cost_ceiling_usd"], 1.0)
        self.assertEqual(set(receipt["provider_policy"]["ignore"]), set())

    def _selection(self):
        return {
            "approved_families":[self.policy["routine_reviewers"][0]["family"]],
            "max_prompt_characters":60000,
            "max_output_tokens":3000,
            "routine_model_call_cost_ceiling_usd":0.05,
            "daily_openrouter_cost_ceiling_usd":1.0,
            "provider_policy":self.policy["provider_policy"]
        }

    def test_paid_call_transmits_provider_policy(self):
        selection = self._selection(); model = self.policy["routine_reviewers"][0]
        response = {"choices":[{"message":{"content":"{\"ok\": true}"}}],"usage":{"cost":0.01}}
        with patch.dict(os.environ, {"OPENROUTER_API_KEY":"test-key"}), patch("tools.run_paid_matrix_review._key_usage_daily", return_value=(0.0,{"status":"VERIFIED","usage_daily":0.0})), patch("tools.run_paid_matrix_review.request.urlopen", return_value=_Response(response)) as mocked:
            raw, attempt = paid._call(model=model, prompt="bounded public target", selection=selection)
        self.assertEqual(raw,{"ok":True}); self.assertEqual(attempt["status"],"CALLED")
        body = json.loads(mocked.call_args.args[0].data.decode("utf-8"))
        self.assertEqual(body["provider"]["data_collection"],"deny")
        self.assertEqual(body["provider"]["max_price"],{"prompt":1.0,"completion":3.0})
        self.assertEqual(set(body["provider"]["ignore"]), set())

    def test_daily_budget_refuses_reserved_overrun(self):
        selection=self._selection(); model=self.policy["routine_reviewers"][0]
        with patch.dict(os.environ,{"OPENROUTER_API_KEY":"test-key"}), patch("tools.run_paid_matrix_review._key_usage_daily", return_value=(1.995,{"status":"VERIFIED","usage_daily":1.995})):
            raw, attempt = paid._call(model=model,prompt="bounded public target",selection=selection)
        self.assertIsNone(raw); self.assertEqual(attempt["status"],"DAILY_BUDGET_RESERVED_EXHAUSTED")

if __name__ == "__main__":
    unittest.main()
