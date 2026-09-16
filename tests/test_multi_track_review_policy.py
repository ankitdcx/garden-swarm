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

    def test_matrix_spans_design_and_operational_work(self) -> None:
        kinds = {row["target_kind"] for row in self.matrix["targets"]}
        required = {"canonical_design","operations_and_budget","test_and_verification","integration_and_provenance","security_and_privacy","authority_and_actiongate"}
        self.assertTrue(required.issubset(kinds))
        self.assertGreaterEqual(len(self.matrix["targets"]), 10)
        self.assertTrue(all(row["public_only"] is True for row in self.matrix["targets"]))

    def test_specialist_sweep_is_free_only_and_broad(self) -> None:
        cfg = self.policy["specialist_free_sweep"]
        self.assertTrue(cfg["enabled"])
        self.assertGreaterEqual(cfg["preferred_families_per_hour"], 6)
        self.assertGreaterEqual(cfg["minimum_families_per_hour"], 3)
        self.assertTrue(cfg["cross_examination"])
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
        self.assertEqual(self.quality["budget"]["daily_openrouter_cost_ceiling_usd"], 1.0)
        board = self.quality["tiers"]["MATERIAL_STRONG_BOARD"]["openrouter_models"]
        self.assertEqual([row["family"] for row in board], ["deepseek", "qwen", "glm"])
        self.assertEqual(self.quality["tiers"]["MATERIAL_STRONG_BOARD"]["separate_google_lane"]["model"], "gemini-3.8-flash")

if __name__ == "__main__":
    unittest.main()
