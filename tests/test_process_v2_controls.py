import hashlib
import json
import unittest
from pathlib import Path

from tools.build_review_packet import classify_diff_relation
from tools.packet_review_common import canonical_reviewer_payload
from tools.validate_evidence_class import validate_evidence, validate_evidence_bound
from tools.validate_review_packet import canonical_hash, validate_packet

ROOT = Path(__file__).resolve().parents[1]


class ProcessV2ControlTests(unittest.TestCase):
    def base_packet(self):
        source_hash = "e" * 64
        packet = {
            "schema": "GardenReviewPacket/v1",
            "cycle_id": "cycle-1",
            "public_repo": {"status": "BOUND", "commit": "a" * 40},
            "private_repo": {"status": "PRIVATE_REPO_INACCESSIBLE", "reason": "not mounted"},
            "canonical_version": "v15.5",
            "design_epoch": "v15.5",
            "canonical_source_root_sha256": "b" * 64,
            "process_version": "GardenProcess-v2.0-candidate",
            "target": {"target_id": "T", "source_file": "x.py", "source_hash": source_hash},
            "diffs": [{
                "repo": "garden-swarm", "mode": "NO_CHANGE", "base": "a" * 40,
                "head": "a" * 40, "digest": "d" * 64,
                "semantic_role": "REPOSITORY_TIP_COMMIT_CONTEXT",
                "selected_target_relation": "NO_CHANGE",
                "claims_selected_target_delta": False,
                "claims_prior_cycle_delta": False,
            }],
            "diff_scope_policy": "TIP_COMMIT_CONTEXT_NOT_CYCLE_OR_TARGET_DELTA",
            "changed_files": [],
            "changed_files_semantics": "TIP_COMMIT_CONTEXT_ONLY",
            "changed_symbols": [],
            "changed_symbols_semantics": "TIP_COMMIT_CONTEXT_ONLY",
            "closure": {
                "declared_objects": ["file:x.py"],
                "included_objects": ["file:x.py"],
                "algorithm": "test",
                "objects": [{"object_id": "file:x.py", "path": "x.py", "sha256": source_hash, "content": "pass\n"}],
            },
            "affected_objects": {"schemas": [], "function_contracts": [], "invariants": [], "tests": [], "registries": [], "implementation_bindings": []},
            "ci_test_evidence": [],
            "linked_findings": [],
            "active_freezes": [],
            "exclusions": [],
            "closure_frontier": {"status": "CLOSED_UNDER_DECLARED_ALGORITHM", "unresolved_candidates": []},
            "packet_construction_version": "GardenReviewPacketBuilder/v1.1"
        }
        packet["packet_hash"] = canonical_hash(packet)
        return packet

    def rehash(self, packet):
        packet["packet_hash"] = canonical_hash({k: v for k, v in packet.items() if k != "packet_hash"})
        return packet

    def test_valid_packet_passes(self):
        packet = self.base_packet()
        receipt = {"schema": "PacketCompletenessReceipt/v1", "criterion": "COHERENT_COMPLETE", "cycle_id": "cycle-1", "packet_hash": packet["packet_hash"], "status": "PASS", "manual_unexplained_exclusions": 0}
        self.assertEqual(validate_packet(packet, receipt)["status"], "PASS")

    def test_missing_required_field_fails(self):
        packet = self.base_packet(); del packet["changed_symbols"]
        self.rehash(packet)
        with self.assertRaises(ValueError): validate_packet(packet)

    def test_unexplained_closure_gap_fails(self):
        packet = self.base_packet(); packet["closure"]["included_objects"] = []
        self.rehash(packet)
        with self.assertRaises(ValueError): validate_packet(packet)

    def test_wrong_hash_fails(self):
        packet = self.base_packet(); packet["packet_hash"] = "0" * 64
        with self.assertRaises(ValueError): validate_packet(packet)

    def test_untyped_tip_diff_fails(self):
        packet = self.base_packet(); del packet["diffs"][0]["semantic_role"]
        self.rehash(packet)
        with self.assertRaises(ValueError): validate_packet(packet)

    def test_tip_diff_cannot_claim_target_delta(self):
        packet = self.base_packet(); packet["diffs"][0]["claims_selected_target_delta"] = True
        self.rehash(packet)
        with self.assertRaises(ValueError): validate_packet(packet)

    def test_e4_requires_full_trace_binding_structurally(self):
        with self.assertRaises(ValueError):
            validate_evidence({"claimed_evidence_class": "E4", "evidence": {"kind": "executable_trace", "repo_commit": "a" * 40}})

    def test_e2_requires_source_hash_structurally(self):
        with self.assertRaises(ValueError):
            validate_evidence({"claimed_evidence_class": "E2", "evidence": {"kind": "exact_code", "source_ref": "x.py"}})

    def test_structural_e4_is_not_packet_bound(self):
        finding = {"claimed_evidence_class": "E4", "evidence": {"kind": "executable_trace", "repo_commit": "a" * 40, "design_epoch": "v15.5", "environment": "python-3.12", "command": "python -m unittest", "exit_code": 0, "output_hash": hashlib.sha256(b"ok").hexdigest()}}
        self.assertEqual(validate_evidence(finding)["validated_evidence_class"], "E4")
        with self.assertRaises(ValueError):
            validate_evidence_bound(finding, self.base_packet())

    def test_packet_bound_e2_exact_hash_passes(self):
        packet = self.base_packet()
        finding = {"claimed_evidence_class": "E2", "evidence": {"kind": "exact_code", "source_ref": "x.py", "source_hash": "e" * 64}}
        self.assertEqual(validate_evidence_bound(finding, packet)["evidence_binding_validation"], "PASS_PACKET_BOUND")

    def test_packet_bound_e2_forged_hash_fails(self):
        packet = self.base_packet()
        finding = {"claimed_evidence_class": "E2", "evidence": {"kind": "exact_code", "source_ref": "x.py", "source_hash": "f" * 64}}
        with self.assertRaises(ValueError): validate_evidence_bound(finding, packet)

    def test_packet_bound_e2_unknown_ref_fails(self):
        packet = self.base_packet()
        finding = {"claimed_evidence_class": "E2", "evidence": {"kind": "exact_code", "source_ref": "missing.py", "source_hash": "e" * 64}}
        with self.assertRaises(ValueError): validate_evidence_bound(finding, packet)

    def test_packet_bound_e3_forged_premise_fails(self):
        packet = self.base_packet()
        finding = {"claimed_evidence_class": "E3", "evidence": {"kind": "formal_proof", "premises": ["p"], "premise_bindings": [{"ref": "x.py", "hash": "f" * 64}]}}
        with self.assertRaises(ValueError): validate_evidence_bound(finding, packet)

    def test_packet_bound_e4_exact_trace_passes(self):
        packet = self.base_packet()
        trace = {"repo_commit": "a" * 40, "design_epoch": "v15.5", "environment": "python-3.12", "command": "python -m unittest", "exit_code": 0, "output_hash": hashlib.sha256(b"ok").hexdigest()}
        packet["ci_test_evidence"] = [{"schema": "TraceBundle/v1", "traces": [trace]}]
        self.rehash(packet)
        finding = {"claimed_evidence_class": "E4", "evidence": {"kind": "executable_trace", **trace}}
        self.assertEqual(validate_evidence_bound(finding, packet)["evidence_binding_validation"], "PASS_PACKET_BOUND")

    def test_reviewer_payload_hash_is_exact_bytes(self):
        packet = self.base_packet()
        payload = canonical_reviewer_payload(packet)
        self.assertEqual(hashlib.sha256(payload).hexdigest(), packet["packet_hash"])
        self.assertNotIn(b'"packet_hash"', payload)

    def test_diff_relation_does_not_mislabel_unrelated_tip_change(self):
        packet = self.base_packet()
        packet["changed_files"] = ["unrelated.txt"]
        self.assertEqual(classify_diff_relation(packet), "UNRELATED_TO_SELECTED_TARGET")
        packet["changed_files"] = ["x.py"]
        self.assertEqual(classify_diff_relation(packet), "TOUCHES_TARGET_SOURCE")

    def test_state_machine_is_linear_and_clock_is_not_authority(self):
        p = json.loads((ROOT / "agents/process-control-policy.json").read_text(encoding="utf-8"))
        sm = p["cycle_state_machine"]
        expected = list(zip(sm["states"], sm["states"][1:]))
        self.assertEqual([tuple(x) for x in sm["allowed_transitions"]], expected)
        self.assertEqual(sm["clock_schedule_role"], "WATCHDOG_START_OPPORTUNITY_ONLY")
        self.assertEqual(sm["adjacent_cycle_evidence_mixing"], "FORBIDDEN")

    def test_budget_and_research_boundaries(self):
        p = json.loads((ROOT / "agents/process-control-policy.json").read_text(encoding="utf-8"))
        self.assertEqual(p["budget"]["routine_openrouter_daily_ceiling_usd"], 1.0)
        self.assertEqual(p["budget"]["automatic_expensive_escalation_daily_ceiling_usd"], 0.0)
        self.assertIn("CANDIDATE_ALTERNATIVE", p["research"]["allowed_state_claims"])
        self.assertIn("BETTER_ALTERNATIVE", p["research"]["forbidden_state_claims"])

    def test_process_cannot_self_authorize(self):
        pv = json.loads((ROOT / "PROCESS_VERSION.json").read_text(encoding="utf-8"))
        policy = json.loads((ROOT / "agents/process-control-policy.json").read_text(encoding="utf-8"))
        self.assertTrue(pv["self_authorization_forbidden"])
        self.assertTrue(pv["effective_only_after_admission"])
        self.assertTrue(policy["process_change_control"]["successor_reviewed_under_predecessor"])
        self.assertTrue(policy["process_change_control"]["activation_requires_separate_admission"])

    def test_human_unavailability_is_bounded(self):
        p = json.loads((ROOT / "agents/process-control-policy.json").read_text(encoding="utf-8"))
        h = p["human_availability"]
        self.assertEqual(h["temporary_unavailability_semantic_delta_cap"], 10)
        self.assertEqual(h["permanent_unavailability_semantic_delta_cap"], 10)
        self.assertEqual(h["permanent_unavailability_continuity_review_days"], 90)
        self.assertTrue(h["silent_authority_transfer_forbidden"])


if __name__ == "__main__":
    unittest.main()
