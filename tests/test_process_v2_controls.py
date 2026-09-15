import copy
import hashlib
import json
import unittest

from tools.validate_evidence_class import validate_evidence
from tools.validate_review_packet import canonical_hash, validate_packet


class ProcessV2ControlTests(unittest.TestCase):
    def base_packet(self):
        packet = {
            "schema": "GardenReviewPacket/v1",
            "cycle_id": "cycle-1",
            "public_repo": {"status": "BOUND", "commit": "a" * 40},
            "private_repo": {"status": "PRIVATE_REPO_INACCESSIBLE", "reason": "not mounted"},
            "canonical_version": "v15.5",
            "design_epoch": "v15.5",
            "canonical_source_root_sha256": "b" * 64,
            "process_version": "GardenProcess-v2.0-candidate",
            "target": {"target_id": "T", "source_hash": "c" * 64},
            "diffs": [{"repo": "garden-swarm", "mode": "NO_CHANGE", "base": "a" * 40, "head": "a" * 40, "digest": "d" * 64}],
            "changed_files": [],
            "changed_symbols": [],
            "closure": {"declared_objects": ["T", "S1"], "included_objects": ["T", "S1"], "algorithm": "test"},
            "affected_objects": {"schemas": [], "function_contracts": [], "invariants": [], "tests": [], "registries": [], "implementation_bindings": []},
            "ci_test_evidence": [],
            "linked_findings": [],
            "active_freezes": [],
            "exclusions": [],
            "closure_frontier": {"status": "CLOSED_UNDER_DECLARED_ALGORITHM", "unresolved_candidates": []},
            "packet_construction_version": "1"
        }
        packet["packet_hash"] = canonical_hash(packet)
        return packet

    def test_valid_packet_passes(self):
        packet = self.base_packet()
        receipt = {"schema": "PacketCompletenessReceipt/v1", "criterion": "COHERENT_COMPLETE", "cycle_id": "cycle-1", "packet_hash": packet["packet_hash"], "status": "PASS", "manual_unexplained_exclusions": 0}
        self.assertEqual(validate_packet(packet, receipt)["status"], "PASS")

    def test_missing_required_field_fails(self):
        packet = self.base_packet()
        del packet["changed_symbols"]
        with self.assertRaises(ValueError):
            validate_packet(packet)

    def test_unexplained_closure_gap_fails(self):
        packet = self.base_packet()
        packet["closure"]["included_objects"] = ["T"]
        packet["packet_hash"] = canonical_hash({k: v for k, v in packet.items() if k != "packet_hash"})
        with self.assertRaises(ValueError):
            validate_packet(packet)

    def test_wrong_hash_fails(self):
        packet = self.base_packet()
        packet["packet_hash"] = "0" * 64
        with self.assertRaises(ValueError):
            validate_packet(packet)

    def test_e4_requires_full_trace_binding(self):
        finding = {"claimed_evidence_class": "E4", "evidence": {"kind": "executable_trace", "repo_commit": "a" * 40}}
        with self.assertRaises(ValueError):
            validate_evidence(finding)

    def test_e2_requires_source_hash(self):
        finding = {"claimed_evidence_class": "E2", "evidence": {"kind": "exact_code", "source_ref": "x.py"}}
        with self.assertRaises(ValueError):
            validate_evidence(finding)

    def test_valid_e4_passes(self):
        finding = {
            "claimed_evidence_class": "E4",
            "evidence": {
                "kind": "executable_trace",
                "repo_commit": "a" * 40,
                "design_epoch": "v15.5",
                "environment": "python-3.12",
                "command": "python -m unittest",
                "exit_code": 0,
                "output_hash": hashlib.sha256(b"ok").hexdigest()
            }
        }
        self.assertEqual(validate_evidence(finding)["validated_evidence_class"], "E4")


if __name__ == "__main__":
    unittest.main()
