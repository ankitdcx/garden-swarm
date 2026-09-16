from __future__ import annotations

import json
import unittest
from pathlib import Path

from tools.select_matrix_reviewers import _adaptive_choose

ROOT = Path(__file__).resolve().parents[1]

class MultiTrackReviewPolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy = json.loads((ROOT / "agents/openrouter-paid-review-policy.json").read_text(encoding="utf-8"))
        self.matrix = json.loads((ROOT / "agents/design-review-matrix.json").read_text(encoding="utf-8"))
        self.quality = json.loads((ROOT / "agents/event-driven-model-quality-policy.json").read_text(encoding="utf-8"))
        self.convergence = json.loads((ROOT / "agents/independent-branch-convergence-policy.json").read_text(encoding="utf-8"))

    def test_matrix_spans_design_and_operational_work(self) -> None:
        kinds = {row["target_kind"] for row in self.matrix["targets"]}
        required = {"canonical_design","operations_and_budget","test_and_verification","integration_and_provenance","security_and_privacy","authority_and_actiongate"}
        self.assertTrue(required.issubset(kinds))
        self.assertGreaterEqual(len(self.matrix["targets"]), 10)
        self.assertTrue(all(row["public_only"] is True for row in self.matrix["targets"]))

    def test_legacy_specialist_sweep_cannot_peer_cross_examine(self) -> None:
        cfg = self.policy["specialist_free_sweep"]
        self.assertTrue(cfg["enabled"])
        self.assertGreaterEqual(cfg["preferred_families_per_hour"], 6)
        self.assertGreaterEqual(cfg["minimum_families_per_hour"], 3)
        self.assertFalse(cfg["cross_examination"])
        self.assertGreaterEqual(cfg["max_free_calls_per_hour"], cfg["preferred_families_per_hour"] * 2)
        self.assertIn("no paid fallback", cfg["cost_policy"].lower())

    def test_work_tracks_cover_build_and_governance(self) -> None:
        tracks = set(self.policy["work_tracks"])
        for required in {"canonical_design","implementation_correctness","test_and_verification","security_and_privacy","integration_and_provenance","operations_and_budget","authority_and_actiongate","adversarial_falsification"}:
            self.assertIn(required, tracks)

    def test_adaptive_free_selection_degrades_only_to_minimum(self) -> None:
        models = [
            {"id":"deepseek/a:free","context_length":10},
            {"id":"qwen/a:free","context_length":20},
            {"id":"z-ai/a:free","context_length":30},
        ]
        picked = _adaptive_choose(models, slot=7, requested=8, minimum=3)
        self.assertEqual(len(picked), 3)
        self.assertEqual(len({row["family"] for row in picked}), 3)

    def test_event_quality_policy_spends_only_on_material_work(self) -> None:
        self.assertTrue(self.quality["activation"]["clock_passage_never_authorizes_model_spend"])
        self.assertEqual(self.quality["activation"]["no_change_default"], "NO_MODEL_CALL")
        self.assertTrue(self.quality["activation"]["private_chatgpt_baseline_commitment_required_before_openrouter_inference"])
        self.assertEqual(self.quality["budget"]["daily_openrouter_cost_ceiling_usd"], 2.0)
        self.assertEqual(self.quality["budget"]["absolute_openrouter_inference_calls_per_convergence_task"], 20)
        board_cfg = self.quality["tiers"]["MATERIAL_VALUE_BOARD"]
        board = board_cfg["openrouter_models"]
        self.assertEqual([row["model"] for row in board], ["deepseek/deepseek-v4.1-flash", "qwen/qwen3.8-flash", "z-ai/glm-5.3-flash", "xiaomi/mimo-v2.5"])
        self.assertEqual(board_cfg["peer_answer_sharing"], "FORBIDDEN")
        self.assertEqual(board_cfg["maximum_followups_per_branch"], 2)
        self.assertEqual(board_cfg["maximum_confirmation_rounds"], 1)
        escalation = self.quality["tiers"]["HIGH_CRITICAL_ESCALATION"]
        self.assertEqual(escalation["execution_status"], "DECLARED_NOT_AUTOMATICALLY_DISPATCHED")
        self.assertTrue(escalation["must_still_preserve_four_isolated_branches"])
        escalation_models = [row["model"] for row in escalation["models"]]
        self.assertIn("qwen/qwen3.8-max-0902", escalation_models)
        self.assertIn("xiaomi/mimo-v2.5-pro", escalation_models)
        self.assertEqual(self.quality["tiers"]["SEPARATE_GOOGLE_LANE"]["model"], "gemini-3.8-flash")
        self.assertTrue(self.quality["activation"]["moving_latest_aliases_are_not_used_for_evidence_lineage"])

    def test_convergence_policy_keeps_four_branches_isolated(self) -> None:
        self.assertEqual(self.convergence["reviewer_board"]["required_distinct_families"], 4)
        self.assertTrue(self.convergence["reviewer_board"]["same_neutral_query_and_source_packet_for_all_initial_reviews"])
        self.assertEqual(self.convergence["branch_protocol"]["maximum_followups_per_branch"], 2)
        self.assertTrue(self.convergence["synthesis"]["model_outputs_cannot_self_synthesize_across_branches"])
        self.assertTrue(self.convergence["final_review"]["all_reviewers_receive_bit_identical_merged_candidate"])
        self.assertEqual(self.convergence["final_review"]["maximum_confirmation_rounds"], 1)
        self.assertTrue(self.convergence["stop_rule"]["four_of_four_agreement_is_insufficient_by_itself"])

if __name__ == "__main__":
    unittest.main()
