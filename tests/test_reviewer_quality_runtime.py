import copy
import unittest

from tools import independent_branch_protocol as protocol
from tools import reviewer_quality_runtime as runtime


REGISTRY = {
    "schema": "GardenReviewerSlotRegistry/v1",
    "slots": [
        {"slot_id": "SLOT-REASONING", "family": "deepseek", "model": "deepseek/deepseek-v4.1-flash"},
        {"slot_id": "SLOT-ARCHITECTURE", "family": "qwen", "model": "qwen/qwen3.8-flash"},
        {"slot_id": "SLOT-FORMAL", "family": "glm", "model": "z-ai/glm-5.3-flash"},
        {"slot_id": "SLOT-EXECUTION", "family": "xiaomi", "model": "xiaomi/mimo-v2.5"},
    ],
}


def state():
    finding = {"context_sufficiency": "SUFFICIENT", "disposition": "NO_CHANGE"}
    finding_hash = protocol.sha256_value(finding)
    record = {
        "family": "deepseek",
        "model": "deepseek/deepseek-v4.1-flash",
        "phase": "BLIND",
        "finding": finding,
        "finding_sha256": finding_hash,
        "peer_content_seen": False,
    }
    attempt = {
        "status": "REVIEW_RECORDED",
        "protocol": protocol.PROTOCOL_ID,
        "task_key": "task",
        "cycle": "cycle",
        "slot": "blind:deepseek",
        "family": "deepseek",
        "model": "deepseek/deepseek-v4.1-flash",
        "phase": "BLIND",
        "source_packet_sha256": "a" * 64,
        "finding_sha256": finding_hash,
        "response_text": '{"disposition":"NO_CHANGE"}',
        "response_id": "generation-1",
        "run_id": "run-1",
        "cost": "0.01",
    }
    return {
        "attempts": [attempt],
        "convergence_cycles": {
            "cycle": {"blind": {"deepseek": record}, "reconcile": {}, "final": {}, "confirm": {}}
        },
    }


class ReviewerQualityRuntimeTests(unittest.TestCase):
    def test_recorded_response_queues_one_assessment(self):
        value = state()
        self.assertEqual(runtime.queue_pending_assessments(value, REGISTRY, now=123.0), 1)
        self.assertEqual(len(value["reviewer_quality_queue"]), 1)
        queued = value["reviewer_quality_queue"][0]
        self.assertEqual(queued["schema"], runtime.ASSESSMENT_SCHEMA)
        self.assertEqual(queued["slot_id"], "SLOT-REASONING")
        self.assertEqual(queued["status"], runtime.QUALITY_STATUS)
        self.assertEqual(queued["context_sufficiency"], "SUFFICIENT")
        self.assertFalse(queued["peer_content_seen"])
        self.assertFalse(queued["semantic_delta_admitted"])
        self.assertTrue(queued["quality_assessment_is_not_proof_or_authority"])
        self.assertEqual(value["attempts"][0]["reviewer_quality_status"], runtime.QUALITY_STATUS)

    def test_queue_is_idempotent_by_response_hash(self):
        value = state()
        self.assertEqual(runtime.queue_pending_assessments(value, REGISTRY, now=123.0), 1)
        first = copy.deepcopy(value["reviewer_quality_queue"])
        self.assertEqual(runtime.queue_pending_assessments(value, REGISTRY, now=456.0), 0)
        self.assertEqual(value["reviewer_quality_queue"], first)

    def test_legacy_or_incomplete_attempt_is_not_queued(self):
        value = state()
        value["attempts"][0]["protocol"] = "LegacyReview/v0"
        self.assertEqual(runtime.queue_pending_assessments(value, REGISTRY, now=123.0), 0)
        self.assertEqual(value["reviewer_quality_queue"], [])
        value = state()
        value["attempts"][0]["status"] = "INCOMPLETE"
        self.assertEqual(runtime.queue_pending_assessments(value, REGISTRY, now=123.0), 0)

    def test_peer_content_exposure_fails_closed(self):
        value = state()
        value["convergence_cycles"]["cycle"]["blind"]["deepseek"]["peer_content_seen"] = True
        with self.assertRaisesRegex(ValueError, "peer-content"):
            runtime.queue_pending_assessments(value, REGISTRY, now=123.0)

    def test_unknown_slot_fails_closed(self):
        value = state()
        value["attempts"][0]["model"] = "deepseek/other-model"
        with self.assertRaisesRegex(ValueError, "governed slot"):
            runtime.queue_pending_assessments(value, REGISTRY, now=123.0)

    def test_missing_branch_record_fails_closed(self):
        value = state()
        value["convergence_cycles"]["cycle"]["blind"] = {}
        with self.assertRaisesRegex(ValueError, "branch record"):
            runtime.queue_pending_assessments(value, REGISTRY, now=123.0)

    def test_scan_limit_is_bounded(self):
        with self.assertRaisesRegex(ValueError, "scan limit"):
            runtime.queue_pending_assessments(state(), REGISTRY, limit=0)
        with self.assertRaisesRegex(ValueError, "scan limit"):
            runtime.queue_pending_assessments(state(), REGISTRY, limit=101)


if __name__ == "__main__":
    unittest.main()
