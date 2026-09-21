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

    def test_budget_pools_are_bounded_and_daily_spend_is_ten_dollars(self):
        self.assertEqual(sum(self.policy["budget_pools_usd"].values()), 20.0)
        self.assertEqual(self.policy["daily_openrouter_cost_ceiling_usd"], 10.0)
        self.assertLessEqual(self.policy["routine_hourly_cost_ceiling_usd"], 0.40)
        self.assertLessEqual(self.policy["routine_model_call_cost_ceiling_usd"], 0.10)
        self.assertEqual(self.policy["event_driven_activation"]["no_change_default"], "NO_PAID_CALL")
        self.assertTrue(self.policy["event_driven_activation"]["clock_passage_alone_never_authorizes_spend"])
        self.assertTrue(self.policy["event_driven_activation"]["private_chatgpt_baseline_commitment_required_before_first_openrouter_inference"])

    def test_model_catalog_reference_is_explicit(self): self.assertEqual(self.policy["catalog_reference_date"], "2026-09-16")

    def test_routine_family_set_is_current_value_board(self):
        reviewers = self.policy["routine_reviewers"]
        families = [row["family"] for row in reviewers]
        models = [row["model"] for row in reviewers]
        self.assertEqual(families, ["deepseek", "qwen", "glm", "xiaomi"])
        self.assertEqual(models, ["deepseek/deepseek-v4.1-flash", "qwen/qwen3.8-flash", "z-ai/glm-5.3-flash", "xiaomi/mimo-v2.5"])
        self.assertEqual(len(set(families)), 4)
        self.assertTrue(all(not row["model"].endswith(":free") for row in reviewers))

    def test_legacy_peer_cross_examination_is_disabled(self):
        swarm = self.policy["free_swarm"]
        self.assertTrue(swarm["enabled"])
        self.assertEqual(swarm["distinct_families_per_hour"], 4)
        self.assertGreaterEqual(swarm["minimum_available_families"], 3)
        self.assertFalse(swarm["cross_examination"])
        self.assertFalse(self.policy["specialist_free_sweep"]["cross_examination"])
        self.assertEqual(self.policy["independent_branch_convergence_policy"], "agents/independent-branch-convergence-policy.json")

    def test_provider_policy_denies_collection_exclusions_and_has_value_price_ceiling(self):
        provider = self.policy["provider_policy"]
        self.assertEqual(provider["data_collection"], "deny")
        self.assertTrue(provider["allow_fallbacks"])
        self.assertEqual(set(provider["ignore"]), {"anthropic", "nvidia", "mistral"})
        self.assertLessEqual(provider["max_price_usd_per_million_tokens"]["prompt"], 0.25)
        self.assertLessEqual(provider["max_price_usd_per_million_tokens"]["completion"], 1.0)

    def test_selector_is_offline_and_does_not_require_provider_key(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(selector, "OUTPUT", Path(tmp) / "selection.json"), patch.dict(os.environ, {}, clear=True):
            self.assertEqual(selector.main(), 0)
            receipt = json.loads((Path(tmp) / "selection.json").read_text(encoding="utf-8"))
        expected = [row["family"] for row in self.policy["routine_reviewers"]]
        self.assertEqual(receipt["schema"], "GardenPaidModelSelection/v2")
        self.assertEqual([row["family"] for row in receipt["selected"]], expected)
        self.assertEqual(receipt["approved_families"], expected)
        self.assertEqual(receipt["daily_openrouter_cost_ceiling_usd"], 10.0)
        self.assertEqual(set(receipt["provider_policy"]["ignore"]), {"anthropic", "nvidia", "mistral"})
        self.assertFalse(receipt["semantic_delta_admitted"])

    def _selection(self):
        return {"approved_families":[self.policy["routine_reviewers"][0]["family"]],"max_prompt_characters":60000,"max_output_tokens":3000,"routine_model_call_cost_ceiling_usd":0.05,"daily_openrouter_cost_ceiling_usd":1.0,"provider_policy":self.policy["provider_policy"]}

    def test_paid_call_transmits_hard_provider_price_ceiling_and_exclusions(self):
        selection = self._selection(); model = self.policy["routine_reviewers"][0]
        response = {"choices":[{"message":{"content":"{\"ok\": true}"}}],"usage":{"cost":0.01}}
        with patch.dict(os.environ, {"OPENROUTER_API_KEY":"test-key"}), patch("tools.run_paid_matrix_review._key_usage_daily", return_value=(0.0,{"status":"VERIFIED","usage_daily":0.0})), patch("tools.run_paid_matrix_review.request.urlopen", return_value=_Response(response)) as mocked:
            raw, attempt = paid._call(model=model, prompt="bounded public target", selection=selection)
        self.assertEqual(raw,{"ok":True}); self.assertEqual(attempt["status"],"CALLED")
        body = json.loads(mocked.call_args.args[0].data.decode("utf-8"))
        self.assertEqual(body["provider"]["data_collection"],"deny")
        self.assertEqual(body["provider"]["max_price"],{"prompt":0.25,"completion":1.0})
        self.assertEqual(set(body["provider"]["ignore"]), {"anthropic", "nvidia", "mistral"})
        self.assertTrue(body["provider"]["allow_fallbacks"]); self.assertNotIn("reasoning", body)

    def test_paid_call_can_disable_reasoning_for_structured_one_use_review(self):
        selection = self._selection(); model = self.policy["routine_reviewers"][0]
        response = {"choices":[{"message":{"content":"{\"ok\": true}"}}],"usage":{"cost":0.01}}
        with patch.dict(os.environ, {"OPENROUTER_API_KEY":"test-key"}), patch("tools.run_paid_matrix_review._key_usage_daily", return_value=(0.0,{"status":"VERIFIED","usage_daily":0.0})), patch("tools.run_paid_matrix_review.request.urlopen", return_value=_Response(response)) as mocked:
            raw, attempt = paid._call(model=model,prompt="bounded structured public target",selection=selection,reasoning={"effort":"none"})
        self.assertEqual(raw,{"ok":True}); self.assertEqual(attempt["status"],"CALLED")
        body=json.loads(mocked.call_args.args[0].data.decode("utf-8"))
        self.assertEqual(body["reasoning"],{"effort":"none"}); self.assertEqual(body["provider"]["data_collection"],"deny")

    def test_daily_key_usage_is_fail_closed_and_parsed(self):
        response={"data":{"usage_daily":0.37,"limit_remaining":19.63,"limit":20.0,"limit_reset":None}}
        with patch("tools.run_paid_matrix_review.request.urlopen", return_value=_Response(response)):
            usage, receipt = paid._key_usage_daily("test-key")
        self.assertEqual(usage,0.37); self.assertEqual(receipt["status"],"VERIFIED")

    def test_paid_call_refuses_when_daily_reserved_budget_would_exceed_cap(self):
        selection=self._selection(); model=self.policy["routine_reviewers"][0]
        with patch.dict(os.environ,{"OPENROUTER_API_KEY":"test-key"}), patch("tools.run_paid_matrix_review._key_usage_daily", return_value=(0.96,{"status":"VERIFIED","usage_daily":0.96})):
            raw, attempt = paid._call(model=model,prompt="bounded public target",selection=selection)
        self.assertIsNone(raw); self.assertEqual(attempt["status"],"DAILY_BUDGET_RESERVED_EXHAUSTED")

    def test_gemini_wrapper_uses_module_execution(self):
        source=Path("tools/run_gemini_free_review.py").read_text(encoding="utf-8")
        self.assertIn('"-m", "tools.gemini_free_review"', source)
        self.assertNotIn('"tools/gemini_free_review.py"', source)

if __name__ == "__main__": unittest.main()
