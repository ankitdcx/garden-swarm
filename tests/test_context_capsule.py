from __future__ import annotations

import copy
import unittest

from tools import context_capsule as c


class ContextCapsuleTests(unittest.TestCase):
    def capsule(self):
        return {
            "schema": c.CAPSULE_SCHEMA,
            "public_only": True,
            "target_id": "T",
            "context_expansion_level": "L0_CAPSULE",
            "source_identity": {
                "DesignEpoch": "v15.5",
                "canonical_source_root_sha256": "a" * 64,
                "candidate_source_root_sha256": None,
                "target_source": "Garden_User_v15.5_FULL_2026-09-12.txt",
                "target_source_sha256": "b" * 64,
            },
            "whole_garden_orientation": {"topology": "five-document Garden plus governed deltas"},
            "dependency_closure": {"upstream": ["Authority"], "downstream": ["ActionGate"]},
            "cross_cutting_obligations": {"Proof": "APPLICABLE", "Evidence": "APPLICABLE"},
            "relevant_history": {"open_contradictions": []},
            "omission_and_uncertainty_ledger": {"omitted": ["unrelated theory details"], "could_affect_answer": False},
        }

    def trace(self):
        return {
            "source": "Garden_User_v15.5_FULL_2026-09-12.txt",
            "source_sha256": "b" * 64,
        }

    def test_capsule_binds_target_source_and_global_root(self):
        out = c.validate_capsule(self.capsule(), target_id="T", trace=self.trace())
        self.assertEqual(out["context_expansion_level"], "L0_CAPSULE")
        bad = self.capsule()
        bad["source_identity"]["target_source_sha256"] = "c" * 64
        with self.assertRaisesRegex(ValueError, "target source hash mismatch"):
            c.validate_capsule(bad, target_id="T", trace=self.trace())

    def test_directive_capsule_hash_is_fail_closed(self):
        cap = self.capsule()
        directive = {
            "architecture_context_capsule": cap,
            "architecture_context_capsule_sha256": c.sha256_value(cap),
        }
        _, digest = c.require_directive_capsule(directive, target_id="T", trace=self.trace())
        self.assertEqual(digest, c.sha256_value(cap))
        bad = copy.deepcopy(directive)
        bad["architecture_context_capsule"]["dependency_closure"]["upstream"].append("NewOwner")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            c.require_directive_capsule(bad, target_id="T", trace=self.trace())

    def test_insufficient_context_requires_reason_and_requested_refs(self):
        good = {
            "context_sufficiency": "EXPAND_REQUIRED",
            "missing_context_reason": "upstream authority composition owner is missing",
            "requested_dependency_or_source_refs": ["AuthorityProvenanceChain"],
        }
        c.validate_context_verdict(good)
        bad = dict(good, requested_dependency_or_source_refs=[])
        with self.assertRaisesRegex(ValueError, "request dependency/source refs"):
            c.validate_context_verdict(bad)

    def test_sufficient_context_can_have_empty_missing_context_fields(self):
        c.validate_context_verdict({
            "context_sufficiency": "SUFFICIENT",
            "missing_context_reason": "",
            "requested_dependency_or_source_refs": [],
        })


if __name__ == "__main__":
    unittest.main()
