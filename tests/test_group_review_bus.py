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
        "source_refs": ["repo:ankitdcx/garden-swarm@aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa:agents/actions/group-review.json"],
        "source_hashes": {
            "repo:ankitdcx/garden-swarm@aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa:agents/actions/group-review.json": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
        },
        "symmetric_worker_prompt": "Solve this frozen problem independently. Do not inspect peer outputs.",
    }
    value.update(overrides)
    value["packet_sha256"] = bus.packet_hash(value)
    return value


def isolated_context(**overrides):
    value = {
        "status": "VERIFIED",
        "isolation_mode": "temporary-chat-memory-off",
        "excluded_context_detected": False,
        "project_context_present": False,
        "memory_or_personal_context_present": False,
        "prior_review_context_present": False,
        "peer_output_present": False,
        "evidence_refs": ["attestation:test-fixture"],
    }
    value.update(overrides)
    return value


class GroupReviewBusTests(unittest.TestCase):
    def test_valid_packet_round_trips_through_issue_body(self):
        value = packet()
        body = bus.render_issue(bus.PACKET_MARKER, value)
        recovered = bus.extract_marked_json(body, bus.PACKET_MARKER)
        self.assertEqual(recovered, value)
        self.assertEqual(bus.validate_packet(recovered), value)


    def test_packet_requires_hash_for_every_source(self):
        value = packet()
        value.pop("source_hashes")
        value["packet_sha256"] = bus.packet_hash(value)
        with self.assertRaisesRegex(ValueError, "source_hashes"):
            bus.validate_packet(value)

    def test_packet_rejects_mutable_pr_or_branch_source(self):
        mutable = packet(
            source_refs=["https://github.com/ankitdcx/garden-swarm/pull/237"],
            source_hashes={
                "https://github.com/ankitdcx/garden-swarm/pull/237": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
            },
        )
        with self.assertRaisesRegex(ValueError, "exact-commit"):
            bus.validate_packet(mutable)

        branch_ref = "repo:ankitdcx/garden-swarm@main:AGENTS.md"
        mutable = packet(
            source_refs=[branch_ref],
            source_hashes={branch_ref: "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"},
        )
        with self.assertRaisesRegex(ValueError, "exact-commit"):
            bus.validate_packet(mutable)

    def test_source_hash_keys_must_match_refs_exactly(self):
        value = packet()
        value["source_hashes"] = {"content:sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb:other": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"}
        value["packet_sha256"] = bus.packet_hash(value)
        with self.assertRaisesRegex(ValueError, "exactly match"):
            bus.validate_packet(value)

    def test_validate_source_text_detects_drift(self):
        text = "frozen source bytes"
        ref = "content:sha256:" + bus.sha256_text(text) + ":fixture"
        value = packet(
            source_refs=[ref],
            source_hashes={ref: bus.sha256_text(text)},
        )
        self.assertEqual(
            bus.validate_source_text(
                packet=value,
                source_ref=ref,
                source_text=text,
            ),
            bus.sha256_text(text),
        )
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            bus.validate_source_text(
                packet=value,
                source_ref=ref,
                source_text="changed later",
            )

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

    def test_worker_result_binds_exact_packet_output_and_context_isolation(self):
        value = packet(openrouter_requested=False, triage="SMALL")
        output = "Independent solution."
        result = {
            "schema": bus.WORKER_RESULT_SCHEMA,
            "problem_id": value["problem_id"],
            "run_issue_number": 42,
            "role": "A",
            "packet_sha256": value["packet_sha256"],
            "created_at": "2026-09-19T14:35:00+05:30",
            "status": "FROZEN_RESULT",
            "context_isolation": isolated_context(),
            "peer_exposure_before_freeze": "NONE",
            "output": output,
            "output_sha256": bus.sha256_text(output),
        }
        result["result_sha256"] = bus.worker_result_hash(result)
        self.assertEqual(bus.validate_worker_result(result, value), result)
        result["output"] = "silently edited"
        with self.assertRaises(ValueError):
            bus.validate_worker_result(result, value)

    def test_semantic_result_rejects_project_or_memory_context(self):
        value = packet(openrouter_requested=False, triage="SMALL")
        for field in (
            "project_context_present",
            "memory_or_personal_context_present",
            "prior_review_context_present",
            "peer_output_present",
            "excluded_context_detected",
        ):
            output = "Independent solution."
            result = {
                "schema": bus.WORKER_RESULT_SCHEMA,
                "problem_id": value["problem_id"],
                "run_issue_number": 42,
                "role": "A",
                "packet_sha256": value["packet_sha256"],
                "created_at": "2026-09-19T14:35:00+05:30",
                "status": "FROZEN_RESULT",
                "context_isolation": isolated_context(**{field: True}),
                "peer_exposure_before_freeze": "NONE",
                "output": output,
                "output_sha256": bus.sha256_text(output),
            }
            result["result_sha256"] = bus.worker_result_hash(result)
            with self.assertRaisesRegex(ValueError, "verified context isolation"):
                bus.validate_worker_result(result, value)

    def test_process_fail_is_valid_and_carries_no_semantic_output(self):
        value = packet(openrouter_requested=False, triage="SMALL")
        result = {
            "schema": bus.WORKER_RESULT_SCHEMA,
            "problem_id": value["problem_id"],
            "run_issue_number": 42,
            "role": "A",
            "packet_sha256": value["packet_sha256"],
            "created_at": "2026-09-19T14:35:00+05:30",
            "status": "PROCESS_FAIL",
            "context_isolation": isolated_context(
                status="FAILED",
                excluded_context_detected=True,
                memory_or_personal_context_present=True,
            ),
            "failure_code": "BLIND_CONTEXT_LEAKAGE",
            "failure_detail": "Prior review context was present before source retrieval.",
        }
        result["result_sha256"] = bus.worker_result_hash(result)
        self.assertEqual(bus.validate_worker_result(result, value), result)

        bad = copy.deepcopy(result)
        bad["output"] = "inadmissible semantic findings"
        bad["output_sha256"] = bus.sha256_text(bad["output"])
        bad["result_sha256"] = bus.worker_result_hash(bad)
        with self.assertRaisesRegex(ValueError, "must not publish semantic output"):
            bus.validate_worker_result(bad, value)

    def test_blocked_context_isolation_is_typed_without_rerun_claim(self):
        value = packet(openrouter_requested=False, triage="SMALL")
        result = {
            "schema": bus.WORKER_RESULT_SCHEMA,
            "problem_id": value["problem_id"],
            "run_issue_number": 42,
            "role": "B",
            "packet_sha256": value["packet_sha256"],
            "created_at": "2026-09-19T14:35:00+05:30",
            "status": "BLOCKED_BY_CONTEXT_ISOLATION",
            "context_isolation": isolated_context(
                status="UNAVAILABLE",
                isolation_mode="product-context-cannot-be-disabled",
                excluded_context_detected=True,
                memory_or_personal_context_present=True,
            ),
            "failure_code": "CONTEXT_ISOLATION_UNAVAILABLE",
            "failure_detail": "The product supplied prior Garden context automatically.",
        }
        result["result_sha256"] = bus.worker_result_hash(result)
        self.assertEqual(bus.validate_worker_result(result, value), result)

    def test_worker_status_lifecycle_requires_isolation_before_blind_review(self):
        value = packet(openrouter_requested=False, triage="SMALL")
        status = {
            "schema": bus.WORKER_STATUS_SCHEMA,
            "problem_id": value["problem_id"],
            "run_issue_number": 42,
            "role": "A",
            "packet_sha256": value["packet_sha256"],
            "created_at": "2026-09-19T14:34:00+05:30",
            "state": "BLIND_REVIEW",
            "context_isolation": isolated_context(),
        }
        status["status_sha256"] = bus.worker_status_hash(status)
        self.assertEqual(bus.validate_worker_status(status, value), status)

        contaminated = copy.deepcopy(status)
        contaminated["context_isolation"] = isolated_context(
            status="FAILED",
            project_context_present=True,
            excluded_context_detected=True,
        )
        contaminated["status_sha256"] = bus.worker_status_hash(contaminated)
        with self.assertRaisesRegex(ValueError, "verified context isolation"):
            bus.validate_worker_status(contaminated, value)

    def test_worker_status_can_record_context_isolation_block(self):
        value = packet(openrouter_requested=False, triage="SMALL")
        status = {
            "schema": bus.WORKER_STATUS_SCHEMA,
            "problem_id": value["problem_id"],
            "run_issue_number": 42,
            "role": "B",
            "packet_sha256": value["packet_sha256"],
            "created_at": "2026-09-19T14:34:00+05:30",
            "state": "BLOCKED_BY_CONTEXT_ISOLATION",
            "context_isolation": isolated_context(
                status="UNAVAILABLE",
                isolation_mode="product-context-cannot-be-disabled",
                excluded_context_detected=True,
                memory_or_personal_context_present=True,
            ),
        }
        status["status_sha256"] = bus.worker_status_hash(status)
        self.assertEqual(bus.validate_worker_status(status, value), status)

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
