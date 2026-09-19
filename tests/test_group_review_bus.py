import copy
import unittest

from tools import group_review_bus as bus


def packet(**overrides):
    value = {
        "schema": bus.PACKET_SCHEMA,
        "problem_id": "GR-20260919-001",
        "protocol_version": "2.1",
        "prompt_version": "group-review-v2.1",
        "created_at": "2026-09-19T14:30:00+05:30",
        "public_only": True,
        "data_classification": "PUBLIC",
        "triage": "MATERIAL",
        "openrouter_requested": True,
        "problem": "Find the strongest design for a shared multi-agent review bus.",
        "scope": "Operational GROUP_REVIEW process only.",
        "assumptions": ["GitHub repository is the durable bus."],
        "source_refs": ["agents/actions/group-review.json"],
        "symmetric_worker_prompt": "Solve this frozen problem independently. Do not inspect peer outputs.",
    }
    value.update(overrides)
    value["packet_sha256"] = bus.packet_hash(value)
    return value


class GroupReviewBusTests(unittest.TestCase):
    def test_valid_packet_round_trips_through_issue_body(self):
        value = packet()
        body = bus.render_issue(bus.PACKET_MARKER, value)
        recovered = bus.extract_marked_json(body, bus.PACKET_MARKER)
        self.assertEqual(recovered, value)
        self.assertEqual(bus.validate_packet(recovered), value)

    def test_packet_tampering_is_detected(self):
        value = packet()
        value["problem"] = "mutated after freeze"
        with self.assertRaisesRegex(ValueError, "packet SHA-256 mismatch"):
            bus.validate_packet(value)

    def test_openrouter_refuses_private_or_sensitive_packet(self):
        for classification, public_only in (("PRIVATE", False), ("SENSITIVE", False)):
            value = packet(data_classification=classification, public_only=public_only)
            with self.assertRaisesRegex(ValueError, "PUBLIC-only"):
                bus.validate_packet(value)

    def test_openrouter_not_automatic_for_small_task(self):
        value = packet(triage="SMALL", openrouter_requested=True)
        with self.assertRaisesRegex(ValueError, "MATERIAL/HIGH_RISK"):
            bus.validate_packet(value)

    def test_worker_prompt_must_be_symmetric(self):
        value = packet(symmetric_worker_prompt="Worker A should be constructive.")
        with self.assertRaisesRegex(ValueError, "symmetric"):
            bus.validate_packet(value)

    def test_run_issue_must_be_owner_authored_and_title_bound(self):
        value = packet()
        issue = {
            "title": f"{bus.RUN_TITLE_PREFIX} {value['problem_id']}",
            "body": bus.render_issue(bus.PACKET_MARKER, value),
            "user": {"login": "ankitdcx"},
        }
        self.assertEqual(bus.validate_run_issue(issue, "ankitdcx"), value)
        bad = copy.deepcopy(issue)
        bad["user"]["login"] = "someone-else"
        with self.assertRaisesRegex(ValueError, "owner-authored"):
            bus.validate_run_issue(bad, "ankitdcx")

    def test_worker_result_binds_exact_packet_and_output(self):
        value = packet(openrouter_requested=False, triage="SMALL")
        output = "Independent solution."
        result = {
            "schema": bus.WORKER_RESULT_SCHEMA,
            "problem_id": value["problem_id"],
            "run_issue_number": 42,
            "role": "A",
            "packet_sha256": value["packet_sha256"],
            "created_at": "2026-09-19T14:35:00+05:30",
            "peer_exposure_before_freeze": "NONE",
            "output": output,
            "output_sha256": bus.sha256_text(output),
        }
        result["result_sha256"] = bus.worker_result_hash(result)
        self.assertEqual(bus.validate_worker_result(result, value), result)
        result["output"] = "silently edited"
        with self.assertRaises(ValueError):
            bus.validate_worker_result(result, value)

    def test_openrouter_bundle_requires_five_distinct_families(self):
        value = packet()
        records = [{"family": f"f{i}"} for i in range(5)]
        bundle = bus.make_openrouter_bundle(packet=value, run_issue_number=42, records=records)
        self.assertEqual(bundle["bundle_sha256"], bus.openrouter_bundle_hash(bundle))
        with self.assertRaisesRegex(ValueError, "five distinct"):
            bus.make_openrouter_bundle(
                packet=value,
                run_issue_number=42,
                records=[{"family": "same"} for _ in range(5)],
            )


    def test_candidate_and_verifier_are_hash_bound(self):
        value = packet(openrouter_requested=False, triage="SMALL")
        candidate_text = "Integrated candidate"
        candidate = {
            "schema": bus.CANDIDATE_SCHEMA,
            "problem_id": value["problem_id"],
            "run_issue_number": 42,
            "packet_sha256": value["packet_sha256"],
            "created_at": "2026-09-19T14:40:00+05:30",
            "candidate": candidate_text,
            "candidate_sha256": bus.sha256_text(candidate_text),
            "blind_artifact_refs": ["issue:43"],
            "decision_log": [
                {
                    "finding": "Example finding",
                    "disposition": "RETAIN",
                    "reason": "Supported by reproduction.",
                    "evidence_refs": ["test:fixture"],
                }
            ],
        }
        candidate["record_sha256"] = bus.candidate_record_hash(candidate)
        self.assertEqual(bus.validate_candidate(candidate, value), candidate)

        report = {
            "schema": bus.VERIFIER_SCHEMA,
            "problem_id": value["problem_id"],
            "run_issue_number": 42,
            "packet_sha256": value["packet_sha256"],
            "candidate_sha256": candidate["candidate_sha256"],
            "created_at": "2026-09-19T14:45:00+05:30",
            "process_integrity": "PASS",
            "verdict": "PASS_WITH_CAVEATS",
            "verified_scope": "Candidate structure and process fixture.",
            "falsifiers": ["A hash mismatch would falsify the binding."],
            "reproduction_steps": ["Recompute all hashes."],
            "blocking_findings": [],
            "caveats": ["Fixture is synthetic."],
        }
        report["record_sha256"] = bus.verifier_record_hash(report)
        self.assertEqual(bus.validate_verifier_result(report, value, candidate), report)

    def test_process_integrity_failure_cannot_pass(self):
        value = packet(openrouter_requested=False, triage="SMALL")
        text = "Candidate"
        candidate = {
            "schema": bus.CANDIDATE_SCHEMA,
            "problem_id": value["problem_id"],
            "run_issue_number": 42,
            "packet_sha256": value["packet_sha256"],
            "created_at": "now",
            "candidate": text,
            "candidate_sha256": bus.sha256_text(text),
            "blind_artifact_refs": [],
            "decision_log": [],
        }
        candidate["record_sha256"] = bus.candidate_record_hash(candidate)
        report = {
            "schema": bus.VERIFIER_SCHEMA,
            "problem_id": value["problem_id"],
            "run_issue_number": 42,
            "packet_sha256": value["packet_sha256"],
            "candidate_sha256": candidate["candidate_sha256"],
            "created_at": "now",
            "process_integrity": "FAIL",
            "verdict": "PASS",
            "verified_scope": "x",
            "falsifiers": [],
            "reproduction_steps": [],
            "blocking_findings": ["peer leakage"],
            "caveats": [],
        }
        report["record_sha256"] = bus.verifier_record_hash(report)
        with self.assertRaisesRegex(ValueError, "cannot PASS"):
            bus.validate_verifier_result(report, value, candidate)


if __name__ == "__main__":
    unittest.main()
