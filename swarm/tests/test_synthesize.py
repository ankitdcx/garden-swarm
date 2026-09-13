import json
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from swarm.synthesize import synthesize


class SynthesisTests(unittest.TestCase):
    def test_preserves_candidate_and_requires_cross_reference(self):
        model_output = {
            "summary": "x",
            "verdict": "PATCH_CANDIDATE",
            "findings": [{
                "title": "Possible gap",
                "kind": "implementation gap",
                "severity": "HIGH",
                "current_claim": "claim",
                "problem_or_opportunity": "problem",
                "proposed_change": "change",
                "alternatives_considered": [],
                "affected_anchors_or_terms": ["A-1"],
                "evidence_needed": ["Technical contract"],
                "regression_test": "test",
                "uncertainty": "uncertain",
                "what_would_overturn": "full source proves coverage"
            }]
        }
        receipt = {
            "schema": "GardenSwarmRunReceipt/v0.1",
            "garden_release": "v15.5",
            "source_identity": [],
            "results": [{
                "status": "OK",
                "role_id": "R1",
                "role_name": "reviewer",
                "requested_model": "m",
                "returned_model": "m",
                "work_item": "w",
                "usage": {"cost": 0},
                "output": json.dumps(model_output)
            }]
        }
        result = synthesize(receipt)
        self.assertEqual(result["admission_status"], "CANDIDATES_ONLY_NOT_ADMITTED")
        self.assertEqual(result["candidate_count"], 1)
        self.assertEqual(result["candidates"][0]["status"], "NEEDS_CROSS_REFERENCE")
        self.assertIn("A-1", result["candidates"][0]["cross_reference_queries"])

    def test_invalid_output_is_not_admitted(self):
        receipt = {"results": [{
            "status": "OK", "role_id": "R", "role_name": "r",
            "requested_model": "m", "returned_model": "m",
            "work_item": "w", "usage": {}, "output": "not json"
        }]}
        result = synthesize(receipt)
        self.assertEqual(result["candidate_count"], 0)
        self.assertEqual(len(result["rejected_outputs"]), 1)


if __name__ == "__main__":
    unittest.main()
