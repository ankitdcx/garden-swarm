from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.matrix_design_review import build_bundle, extract_target, load_matrix
from tools.free_model_rotation import choose


ROOT = Path(__file__).resolve().parents[1]


class DesignReviewMatrixTests(unittest.TestCase):
    def test_matrix_requires_three_and_extracts_exact_public_target(self) -> None:
        matrix, target = load_matrix(ROOT)
        self.assertGreaterEqual(matrix["minimum_independent_reviewer_families"], 3)
        self.assertTrue(target["public_only"])
        source, trace = extract_target(ROOT, target)
        self.assertIn(target["start_anchor"], source)
        self.assertNotIn(target["end_anchor"], source)
        self.assertEqual(trace["coverage"], "BOUNDED_EXACT_ANCHORS")
        self.assertEqual(len(trace["source_sha256"]), 64)

    def test_bundle_fails_closed_below_independent_threshold(self) -> None:
        matrix, target = load_matrix(ROOT)
        trace = {"source": target["source_file"], "source_sha256": "0" * 64}
        finding = {
            "reviewer_family": "family-a",
            "reviewer_model": "example/a:free",
        }
        bundle = build_bundle(
            matrix=matrix,
            target=target,
            trace=trace,
            independent=[finding],
            finals=[],
            attempts=[{"status": "CALLED", "cost": 0}],
        )
        self.assertEqual(bundle["status"], "INSUFFICIENT_INDEPENDENT_REVIEW")
        self.assertFalse(bundle["semantic_delta_admitted"])

    def test_bundle_never_auto_admits_even_after_three_final_dispositions(self) -> None:
        matrix, target = load_matrix(ROOT)
        trace = {"source": target["source_file"], "source_sha256": "0" * 64}
        independent = [
            {"reviewer_family": family, "reviewer_model": f"example/{family}:free"}
            for family in ("family-a", "family-b", "family-c")
        ]
        finals = [dict(row) for row in independent]
        attempts = [
            {"status": "CALLED", "cost": 0, "phase": phase, "family": family}
            for phase in ("INDEPENDENT", "PEER_CROSS_EXAMINATION")
            for family in ("family-a", "family-b", "family-c")
        ]
        bundle = build_bundle(
            matrix=matrix,
            target=target,
            trace=trace,
            independent=independent,
            finals=finals,
            attempts=attempts,
        )
        self.assertEqual(bundle["status"], "REVIEW_COMPLETE_NEEDS_GSL_INTEGRATOR")
        self.assertTrue(bundle["zero_cost_verified"])
        self.assertFalse(bundle["semantic_delta_admitted"])

    def test_bundle_refuses_unverified_or_nonzero_cost_as_complete(self) -> None:
        matrix, target = load_matrix(ROOT)
        trace = {"source": target["source_file"], "source_sha256": "0" * 64}
        independent = [
            {"reviewer_family": family, "reviewer_model": f"example/{family}:free"}
            for family in ("family-a", "family-b", "family-c")
        ]
        finals = [dict(row) for row in independent]
        attempts = [
            {"status": "CALLED", "cost": cost}
            for cost in (0, 0, None, 0, 0, 0)
        ]
        bundle = build_bundle(
            matrix=matrix,
            target=target,
            trace=trace,
            independent=independent,
            finals=finals,
            attempts=attempts,
        )
        self.assertEqual(bundle["status"], "COST_VERIFICATION_FAILED")
        self.assertFalse(bundle["zero_cost_verified"])
        self.assertFalse(bundle["semantic_delta_admitted"])

    def test_selector_can_choose_three_distinct_free_families(self) -> None:
        models = [
            {"id": "deepseek/a:free", "context_length": 10},
            {"id": "qwen/a:free", "context_length": 20},
            {"id": "mistralai/a:free", "context_length": 30},
            {"id": "google/gemma-a:free", "context_length": 40},
        ]
        picked = choose(models, slot=0, count=3)
        self.assertEqual(len(picked), 3)
        self.assertEqual(len({row["family"] for row in picked}), 3)
        self.assertTrue(all(row["model"].endswith(":free") for row in picked))


if __name__ == "__main__":
    unittest.main()
