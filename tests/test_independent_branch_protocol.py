from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from tools import context_capsule
from tools import independent_branch_protocol as p

ROOT = Path(__file__).resolve().parents[1]


class IndependentBranchProtocolTests(unittest.TestCase):
    def setUp(self):
        self.policy = p.load_policy(json.loads((ROOT / "agents/independent-branch-convergence-policy.json").read_text(encoding="utf-8")))
        self.families = ["deepseek", "xiaomi", "nvidia", "pareto", "mistral"]
        self.source_hash = "a" * 64
        self.capsule = {
            "schema": context_capsule.CAPSULE_SCHEMA,
            "public_only": True,
            "target_id": "T",
            "context_expansion_level": "L0_CAPSULE",
            "source_identity": {
                "DesignEpoch": "v15.5",
                "canonical_source_root_sha256": "d" * 64,
                "candidate_source_root_sha256": None,
                "target_source": "x",
                "target_source_sha256": "1" * 64,
            },
            "whole_garden_orientation": {"purpose": "Garden architecture orientation"},
            "dependency_closure": {"upstream": ["A"], "downstream": ["B"]},
            "cross_cutting_obligations": {"authority": "APPLICABLE"},
            "relevant_history": {"open_findings": []},
            "omission_and_uncertainty_ledger": {"omitted": ["unrelated modules"], "risk": "LOW"},
        }
        self.baseline = {
            "schema": p.BASELINE_SCHEMA,
            "baseline_sha256": "b" * 64,
            "neutral_query_sha256": "c" * 64,
            "source_packet_sha256": self.source_hash,
            "created_before_openrouter_calls": True,
            "baseline_content_embedded": False,
        }

    def base_directive(self, phase: str) -> dict:
        return {
            "schema": p.DIRECTIVE_SCHEMA,
            "protocol": p.PROTOCOL_ID,
            "public_only": True,
            "phase": phase,
            "target_id": "T",
            "source_packet_sha256": self.source_hash,
            "reviewer_families": self.families,
            "architecture_context_capsule": copy.deepcopy(self.capsule),
            "architecture_context_capsule_sha256": context_capsule.sha256_value(self.capsule),
            "private_baseline_commitment": copy.deepcopy(self.baseline),
        }

    def test_private_baseline_is_commitment_only(self):
        p.validate_baseline_commitment(self.baseline)
        bad = copy.deepcopy(self.baseline)
        bad["baseline_content_embedded"] = True
        with self.assertRaisesRegex(ValueError, "may not be embedded"):
            p.validate_baseline_commitment(bad)

    def test_blind_directive_forbids_branch_or_peer_content_and_binds_capsule(self):
        d = self.base_directive("BLIND")
        d["same_neutral_query_for_all_reviewers"] = True
        d["same_context_capsule_for_all_reviewers"] = True
        p.validate_directive(d, families=self.families, target_id="T", source_packet_sha256=self.source_hash)
        bad = copy.deepcopy(d)
        bad["architecture_context_capsule"]["whole_garden_orientation"]["purpose"] = "mutated"
        with self.assertRaisesRegex(ValueError, "capsule hash mismatch"):
            p.validate_directive(bad, families=self.families, target_id="T", source_packet_sha256=self.source_hash)
        for key in ("branch_candidate", "merged_candidate", "peer_findings"):
            bad = copy.deepcopy(d)
            bad[key] = "leak"
            with self.subTest(key=key), self.assertRaises(ValueError):
                p.validate_directive(bad, families=self.families, target_id="T", source_packet_sha256=self.source_hash)

    def test_model_reconciliation_phase_is_disabled_in_v2(self):
        d = self.base_directive("RECONCILE")
        with self.assertRaisesRegex(ValueError, "unsupported branch protocol phase"):
            p.validate_directive(d, families=self.families, target_id="T", source_packet_sha256=self.source_hash)

    def test_final_review_candidate_is_bit_identical_and_hash_bound(self):
        candidate = "merged candidate v1"
        d = self.base_directive("FINAL")
        d.update({
            "merged_candidate": candidate,
            "merged_candidate_sha256": p.sha256_text(candidate),
            "exact_same_candidate_for_all_reviewers": True,
            "reviewers_receive_other_final_reviews": False,
        })
        p.validate_directive(d, families=self.families, target_id="T", source_packet_sha256=self.source_hash)
        bad = copy.deepcopy(d)
        bad["merged_candidate"] += " mutation"
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            p.validate_directive(bad, families=self.families, target_id="T", source_packet_sha256=self.source_hash)

    def test_confirmation_is_single_round_only(self):
        candidate = "revised candidate"
        d = self.base_directive("CONFIRM")
        d.update({
            "merged_candidate": candidate,
            "merged_candidate_sha256": p.sha256_text(candidate),
            "exact_same_candidate_for_all_reviewers": True,
            "reviewers_receive_other_final_reviews": False,
            "confirmation_round": 1,
        })
        p.validate_directive(d, families=self.families, target_id="T", source_packet_sha256=self.source_hash)
        bad = copy.deepcopy(d)
        bad["confirmation_round"] = 2
        with self.assertRaisesRegex(ValueError, "one confirmation"):
            p.validate_directive(bad, families=self.families, target_id="T", source_packet_sha256=self.source_hash)

    def test_blind_prompt_is_model_identity_independent_and_requests_context_verdict(self):
        target = {"target_id": "T", "review_question": "Q?"}
        trace = {"source": "x", "source_sha256": "1" * 64}
        first = p.blind_prompt(target=target, source="public source plus capsule", trace=trace)
        second = p.blind_prompt(target=target, source="public source plus capsule", trace=trace)
        self.assertEqual(first, second)
        self.assertIn("context_sufficiency", first)
        self.assertIn("FULL_CONTEXT_REQUIRED", first)
        self.assertNotIn("deepseek", first.lower())
        self.assertNotIn("qwen", first.lower())
        self.assertNotIn("glm", first.lower())
        self.assertNotIn("xiaomi", first.lower())

    def test_final_review_validation_does_not_make_agreement_proof(self):
        review = {
            "verdict": "APPROVE",
            "material_findings": [],
            "missing_evidence": [],
            "surviving_counterexamples": [],
            "affected_invariants": [],
            "proposed_patch": "",
            "uncertainty": "none found in bounded packet",
            "overturn_conditions": "new counterexample",
            "context_sufficiency": "SUFFICIENT",
            "missing_context_reason": "",
            "requested_dependency_or_source_refs": [],
        }
        out = p.validate_final_review(review, family="deepseek", model_id="deepseek/x", candidate_sha256="e" * 64, phase="FINAL")
        self.assertTrue(out["independent"])
        self.assertFalse(out["peer_reviews_seen"])
        self.assertNotIn("proof", out)

    def test_final_review_cannot_approve_with_insufficient_context(self):
        review = {
            "verdict": "APPROVE",
            "material_findings": [],
            "missing_evidence": [],
            "surviving_counterexamples": [],
            "affected_invariants": [],
            "proposed_patch": "",
            "uncertainty": "context missing",
            "overturn_conditions": "provide source",
            "context_sufficiency": "EXPAND_REQUIRED",
            "missing_context_reason": "need upstream authority owner",
            "requested_dependency_or_source_refs": ["AuthorityOwner"],
        }
        with self.assertRaisesRegex(ValueError, "must BLOCK"):
            p.validate_final_review(review, family="qwen", model_id="qwen/x", candidate_sha256="e" * 64, phase="FINAL")

    def test_absolute_call_ceiling_is_fifteen(self):
        cycle = {"attempts": [{"inference_reserved": True} for _ in range(14)]}
        p.assert_call_budget(cycle, self.policy)
        cycle["attempts"].append({"inference_reserved": True})
        with self.assertRaisesRegex(ValueError, "ceiling"):
            p.assert_call_budget(cycle, self.policy)


if __name__ == "__main__":
    unittest.main()
