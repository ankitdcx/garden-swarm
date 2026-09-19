from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class MultiTrackReviewPolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy = json.loads((ROOT / "agents/openrouter-paid-review-policy.json").read_text(encoding="utf-8"))
        self.quality = json.loads((ROOT / "agents/event-driven-model-quality-policy.json").read_text(encoding="utf-8"))
        self.convergence = json.loads((ROOT / "agents/independent-branch-convergence-policy.json").read_text(encoding="utf-8"))

    def test_deterministic_gate_precedes_paid_review(self):
        self.assertTrue(self.quality["activation"]["deterministic_gate_before_model"])
        self.assertEqual(self.quality["activation"]["no_change_default"], "NO_MODEL_CALL")

    def test_five_low_cost_specialists_are_pinned(self):
        board = self.quality["tiers"]["MATERIAL_VALUE_BOARD"]["openrouter_models"]
        self.assertEqual([row["family"] for row in board], ["deepseek","xiaomi","nvidia","pareto","mistral"])
        self.assertEqual([row["model"] for row in board], [
            "deepseek/deepseek-v4-pro-0813",
            "xiaomi/mimo-v2.5-pro",
            "nvidia/nemotron-3-ultra-550b-a55b",
            "unbiased/pareto",
            "mistralai/mistral-medium-3-5",
        ])
        self.assertEqual(self.quality["tiers"]["MATERIAL_VALUE_BOARD"]["model_followups_per_branch"], 0)
        self.assertEqual(self.quality["tiers"]["MATERIAL_VALUE_BOARD"]["maximum_confirmation_rounds"], 1)

    def test_expensive_escalation_is_never_automatic(self):
        escalation = self.quality["tiers"]["EXPENSIVE_ESCALATION"]
        self.assertFalse(escalation["automatic_dispatch"])
        self.assertTrue(escalation["requires_explicit_human_opt_in"])
        self.assertEqual(escalation["default_models"], [])

    def test_convergence_is_five_blind_then_bounded_final(self):
        self.assertEqual(self.convergence["reviewer_board"]["required_distinct_families"], 5)
        self.assertTrue(self.convergence["reviewer_board"]["same_neutral_query_and_source_packet_for_all_initial_reviews"])
        self.assertEqual(self.convergence["branch_protocol"]["model_followups_per_branch"], 0)
        self.assertEqual(self.convergence["final_review"]["reviewers"], 5)
        self.assertEqual(self.convergence["final_review"]["maximum_confirmation_rounds"], 1)
        self.assertTrue(self.convergence["stop_rule"]["five_of_five_agreement_is_insufficient_by_itself"])
        self.assertTrue(self.convergence["stop_rule"]["one_valid_material_counterexample_overrides_any_number_of_approvals"])

    def test_cost_limits_match_low_cost_policy(self):
        self.assertEqual(self.quality["budget"]["daily_openrouter_cost_ceiling_usd"], 1.0)
        self.assertEqual(self.quality["budget"]["routine_model_call_reserved_ceiling_usd"], 0.05)
        self.assertEqual(self.quality["budget"]["absolute_openrouter_inference_calls_per_convergence_task"], 15)
        self.assertEqual(self.convergence["call_budget"]["easy_case_minimum_calls"], 5)
        self.assertEqual(self.convergence["call_budget"]["normal_expected_calls"], 10)
        self.assertEqual(self.convergence["call_budget"]["absolute_maximum_openrouter_inference_calls_per_task"], 15)

if __name__ == "__main__":
    unittest.main()
