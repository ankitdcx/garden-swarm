import copy
import unittest
from unittest import mock

from tools import reviewer_quality as q
from tools import select_paid_matrix_reviewers as selector


POLICY = {
    "schema": "GardenReviewerQualityPolicy/v1",
    "quality_dimensions": {
        "source_grounding": .22,
        "defect_precision": .16,
        "defect_recall_after_closure": .18,
        "context_handling": .16,
        "instruction_schema_compliance": .12,
        "unique_material_contribution": .10,
        "counterexample_quality": .06,
    },
    "hard_failures": ["FABRICATED_SOURCE_OR_EVIDENCE", "PEER_ANSWER_LEAKAGE_OR_USE"],
    "lifecycle": {
        "ordinary_window_minimum_receipts": 8,
        "degrade_when_weighted_quality_below": .58,
        "quarantine_when_weighted_quality_below": .48,
    },
    "shadow_replacement": {
        "minimum_shadow_packets": 6,
        "minimum_weighted_quality_improvement": .08,
        "candidate_unique_contribution_floor_relative_to_incumbent": -.05,
    },
}


def receipt(i=0, score=.8, hard=None):
    return {
        "schema": q.RECEIPT_SCHEMA,
        "receipt_id": f"r{i}",
        "task_id": f"t{i}",
        "slot_id": "SLOT-REASONING",
        "family": "deepseek",
        "model": "deepseek/deepseek-v4.1-flash",
        "source_packet_sha256": "a" * 64,
        "response_sha256": f"{i:064x}"[-64:],
        "phase": "INITIAL",
        "context_sufficiency": "SUFFICIENT",
        "adjudicator": "EXTERNAL_CHATGPT_FRONTIER",
        "scores": {k: score for k in POLICY["quality_dimensions"]},
        "evidence_refs": [f"task:{i}:closure"],
        "hard_failures": hard or [],
    }


class ReviewerQualityTests(unittest.TestCase):
    def test_weighted_score_uses_declared_quality_dimensions(self):
        self.assertEqual(q.weighted_score(receipt(score=.8), POLICY), .8)

    def test_agreement_is_not_an_admissible_quality_signal(self):
        r = receipt()
        r["agreement_with_peers"] = 1.0
        with self.assertRaisesRegex(ValueError, "agreement"):
            q.validate_receipt(r, POLICY)

    def test_hard_failure_rejects_score_and_quarantines(self):
        r = receipt(hard=["FABRICATED_SOURCE_OR_EVIDENCE"])
        self.assertEqual(q.weighted_score(r, POLICY), 0.0)
        summary = q.summarize([r], slot_id=r["slot_id"], family=r["family"], model=r["model"], policy=POLICY)
        self.assertEqual(summary["recommended_state"], "QUARANTINED")

    def test_ordinary_degradation_requires_evidence_window(self):
        few = [receipt(i, .5) for i in range(3)]
        s = q.summarize(few, slot_id="SLOT-REASONING", family="deepseek", model="deepseek/deepseek-v4.1-flash", policy=POLICY)
        self.assertEqual(s["recommended_state"], "ACTIVE")
        enough = [receipt(i, .5) for i in range(8)]
        s = q.summarize(enough, slot_id="SLOT-REASONING", family="deepseek", model="deepseek/deepseek-v4.1-flash", policy=POLICY)
        self.assertEqual(s["recommended_state"], "DEGRADED")

    def test_low_quality_window_quarantines(self):
        rows = [receipt(i, .4) for i in range(8)]
        s = q.summarize(rows, slot_id="SLOT-REASONING", family="deepseek", model="deepseek/deepseek-v4.1-flash", policy=POLICY)
        self.assertEqual(s["recommended_state"], "QUARANTINED")

    def test_shadow_replacement_requires_material_improvement(self):
        incumbent = {"weighted_quality": .62, "unique_material_contribution": .40, "hard_failure_count": 0}
        candidate = {"weighted_quality": .72, "unique_material_contribution": .38, "hard_failure_count": 0}
        result = q.shadow_benchmark(incumbent, candidate, packet_count=6, policy=POLICY)
        self.assertTrue(result["qualified"])
        candidate["weighted_quality"] = .67
        result = q.shadow_benchmark(incumbent, candidate, packet_count=6, policy=POLICY)
        self.assertFalse(result["qualified"])
        self.assertIn("QUALITY_IMPROVEMENT_TOO_SMALL", result["blocking_reasons"])

    def test_selector_blocks_non_active_slot(self):
        policy = {
            "routine_reviewers": [
                {"family": "deepseek", "role": "r1", "model": "deepseek/deepseek-v4-pro-0813"},
                {"family": "xiaomi", "role": "r2", "model": "xiaomi/mimo-v2.5-pro"},
                {"family": "nvidia", "role": "r3", "model": "nvidia/nemotron-3-ultra-550b-a55b"},
                {"family": "pareto", "role": "r4", "model": "unbiased/pareto"},
                {"family": "mistral", "role": "r5", "model": "mistralai/mistral-medium-3-5"},
            ]
        }
        registry = {"schema": "GardenReviewerSlotRegistry/v1", "required_active_slots": 5, "slots": [
            {"slot_id": "1", "state": "ACTIVE", "family": "deepseek", "role": "r1", "model": "deepseek/deepseek-v4-pro-0813"},
            {"slot_id": "2", "state": "ACTIVE", "family": "xiaomi", "role": "r2", "model": "xiaomi/mimo-v2.5-pro"},
            {"slot_id": "3", "state": "ACTIVE", "family": "nvidia", "role": "r3", "model": "nvidia/nemotron-3-ultra-550b-a55b"},
            {"slot_id": "4", "state": "ACTIVE", "family": "pareto", "role": "r4", "model": "unbiased/pareto"},
            {"slot_id": "5", "state": "ACTIVE", "family": "mistral", "role": "r5", "model": "mistralai/mistral-medium-3-5"},
        ]}
        exclusion = {"schema": "GardenProviderExclusionPolicy/v1", "excluded": []}
        with mock.patch.object(selector, "require_allowed_model", return_value=None):
            self.assertEqual(len(selector.active_reviewers(policy, registry, exclusion)), 5)
            registry = copy.deepcopy(registry)
            registry["slots"][1]["state"] = "QUARANTINED"
            with self.assertRaisesRegex(ValueError, "not ACTIVE"):
                selector.active_reviewers(policy, registry, exclusion)


if __name__ == "__main__":
    unittest.main()
