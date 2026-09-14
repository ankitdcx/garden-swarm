from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from tools import matrix_design_review as review
from tools import run_matrix_review_execution_budget as budget


class MatrixReviewExecutionBudgetTests(unittest.TestCase):
    def test_single_family_outage_emits_insufficient_bundle_and_returns_zero(self):
        matrix = {
            "schema": "GardenDesignReviewMatrix/v1",
            "design_epoch": "v15.5",
            "canonical_source_root_sha256": "root",
            "minimum_independent_reviewer_families": 3,
            "semantic_compliance_proved": False,
        }
        target = {
            "target_id": "T1",
            "review_question": "q",
        }
        trace = {"source": "public.txt", "source_sha256": "abc"}
        selected = [{"family": "example", "model": "example/model:free", "role": "critic"}]

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            selection_path = tmp_path / "selection.json"
            out_dir = tmp_path / "out"
            bundle_path = tmp_path / "bundle.json"
            selection_path.write_text(json.dumps({"selected": selected}), encoding="utf-8")

            with mock.patch.object(review, "SELECTION", selection_path), \
                 mock.patch.object(review, "OUT_DIR", out_dir), \
                 mock.patch.object(review, "BUNDLE", bundle_path), \
                 mock.patch.object(review, "load_matrix", return_value=(matrix, target)), \
                 mock.patch.object(review, "extract_target", return_value=("bounded", trace)), \
                 mock.patch.object(
                     review,
                     "call_openrouter",
                     return_value=(None, {"status": "HTTP_429", "model": "example/model:free", "cost": None}),
                 ) as provider:
                self.assertEqual(budget.main(), 0)

            payload = json.loads(bundle_path.read_text(encoding="utf-8"))

        provider.assert_called_once()
        self.assertEqual(payload["minimum_independent_reviewer_families"], 3)
        self.assertEqual(payload["independent_reviewer_family_count"], 0)
        self.assertEqual(payload["final_disposition_family_count"], 0)
        self.assertEqual(payload["status"], "INSUFFICIENT_INDEPENDENT_REVIEW")
        self.assertFalse(payload["semantic_delta_admitted"])
        self.assertEqual(payload["provider_attempts"][0]["status"], "HTTP_429")

    def test_non_free_route_is_refused_before_provider_call(self):
        matrix = {
            "schema": "GardenDesignReviewMatrix/v1",
            "design_epoch": "v15.5",
            "canonical_source_root_sha256": "root",
            "minimum_independent_reviewer_families": 3,
            "semantic_compliance_proved": False,
        }
        target = {"target_id": "T1", "review_question": "q"}

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            selection_path = tmp_path / "selection.json"
            selection_path.write_text(
                json.dumps({"selected": [{"family": "bad", "model": "paid/model", "role": "critic"}]}),
                encoding="utf-8",
            )
            with mock.patch.object(review, "SELECTION", selection_path), \
                 mock.patch.object(review, "load_matrix", return_value=(matrix, target)), \
                 mock.patch.object(review, "extract_target", return_value=("bounded", {})), \
                 mock.patch.object(review, "call_openrouter") as provider:
                with self.assertRaises(SystemExit):
                    budget.main()
            provider.assert_not_called()


if __name__ == "__main__":
    unittest.main()
