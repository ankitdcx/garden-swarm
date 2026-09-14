from __future__ import annotations

import unittest

from tools.pr_repo_quorum import validate_blind, validate_final


def model():
    return {"family": "test-family", "model": "example/test:free", "role": "adversary"}


def target():
    return {"full_diff_sha256": "a" * 64}


class PRRepoQuorumTests(unittest.TestCase):
    def test_blind_review_requires_compact_typed_fields(self):
        value = {
            "disposition": "NO_CHANGE",
            "claim": "bounded claim",
            "falsification": "counterexample attempt",
            "proposed_delta": "NO_CHANGE",
            "do_nothing": "prefer current design",
            "evidence_ancestry": "supplied diff only",
            "uncertainty": "bounded evidence",
        }
        row = validate_blind(value, model(), target())
        self.assertEqual(row["target_hash"], "a" * 64)
        self.assertEqual(row["reviewer_family"], "test-family")

    def test_final_review_requires_cross_exam_terminal(self):
        value = {
            "final_disposition": "REJECT_PROPOSAL",
            "surviving_claim": "none",
            "peer_challenges": ["counterexample"],
            "correlated_evidence": ["common diff"],
            "recommended_delta": "NO_CHANGE",
            "required_tests": [],
            "uncertainty": "low",
        }
        row = validate_final(value, model(), target())
        self.assertEqual(row["final_disposition"], "REJECT_PROPOSAL")

    def test_invalid_terminal_fails_closed(self):
        value = {
            "disposition": "ALLOW",
            "claim": "x",
            "falsification": "x",
            "proposed_delta": "x",
            "do_nothing": "x",
            "evidence_ancestry": "x",
            "uncertainty": "x",
        }
        with self.assertRaises(ValueError):
            validate_blind(value, model(), target())


if __name__ == "__main__":
    unittest.main()
