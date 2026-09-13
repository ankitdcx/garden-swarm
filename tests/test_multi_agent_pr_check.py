import json
import unittest

from tools.check_multi_agent_pr import (
    INTENT_MARKER,
    RECEIPT_MARKER,
    evaluate_pr,
    extract_json_block,
)

BASE = "a" * 40


def body(intent_id="A", paths=None, domains=None, receipt=None):
    intent = {
        "schema": "AgentWorkIntent/v1",
        "intent_id": intent_id,
        "agent_id": f"agent:{intent_id}",
        "task_id": "TASK-TEST",
        "base_sha": BASE,
        "target_paths": paths or ["swarm/a.py"],
        "target_symbols": [],
        "semantic_domains": domains or ["alpha"],
        "affected_invariants": [],
        "affected_contracts": [],
        "intended_effect": "test",
        "parallel_mode": "INDEPENDENT_COMPARISON",
    }
    text = f"{INTENT_MARKER}\n```json\n{json.dumps(intent)}\n```"
    if receipt is not None:
        text += f"\n{RECEIPT_MARKER}\n```json\n{json.dumps(receipt)}\n```"
    return text


class MultiAgentPRCheckTests(unittest.TestCase):
    def test_extract_requires_marker(self):
        self.assertIsNone(extract_json_block("{}", INTENT_MARKER))

    def test_undeclared_actual_change_blocks(self):
        result = evaluate_pr(
            current_pr_number=1,
            current_body=body(paths=["swarm/a.py"]),
            current_changed_paths=["swarm/a.py", "server/app.py"],
            concurrent_prs=[],
        )
        self.assertEqual(result["disposition"], "BLOCKED")
        self.assertTrue(any(x.startswith("UNDECLARED_CHANGED_PATHS") for x in result["failures"]))

    def test_legacy_pr_direct_path_overlap_blocks(self):
        result = evaluate_pr(
            current_pr_number=1,
            current_body=body(paths=["swarm/a.py"]),
            current_changed_paths=["swarm/a.py"],
            concurrent_prs=[{"number": 2, "body": "legacy", "changed_paths": ["swarm/a.py"]}],
        )
        self.assertEqual(result["disposition"], "BLOCKED")
        self.assertTrue(any("UNKNOWN_CONCURRENT_INTENT_DIRECT_PATH_OVERLAP" in x for x in result["failures"]))

    def test_legacy_pr_different_path_is_warning_not_proof(self):
        result = evaluate_pr(
            current_pr_number=1,
            current_body=body(paths=["swarm/a.py"]),
            current_changed_paths=["swarm/a.py"],
            concurrent_prs=[{"number": 2, "body": "legacy", "changed_paths": ["docs/x.md"]}],
        )
        self.assertEqual(result["disposition"], "PASS")
        self.assertTrue(result["warnings"])
        self.assertIn("semantic overlap", result["uncertainty"].lower())

    def test_semantic_overlap_between_declared_prs_requires_receipt(self):
        result = evaluate_pr(
            current_pr_number=1,
            current_body=body(paths=["swarm/a.py"], domains=["error-recovery"]),
            current_changed_paths=["swarm/a.py"],
            concurrent_prs=[{
                "number": 2,
                "body": body("B", paths=["swarm/b.py"], domains=["error-recovery"]),
                "changed_paths": ["swarm/b.py"],
            }],
        )
        self.assertEqual(result["disposition"], "BLOCKED")
        self.assertIn("INTEGRATION_GUARD:REQUIRES_INTEGRATION_RECEIPT", result["failures"])

    def test_semantic_overlap_with_complete_receipt_passes(self):
        receipt = {
            "schema": "IntegrationReceipt/v1",
            "current_intent_id": "A",
            "base_sha": BASE,
            "concurrent_intent_ids": ["B"],
            "semantic_compare": "COMPATIBLE",
            "composition_evidence": ["expected vs observed semantic delta compared"],
            "tests_after_integration": ["test_combined_behavior"],
        }
        result = evaluate_pr(
            current_pr_number=1,
            current_body=body(paths=["swarm/a.py"], domains=["error-recovery"], receipt=receipt),
            current_changed_paths=["swarm/a.py"],
            concurrent_prs=[{
                "number": 2,
                "body": body("B", paths=["swarm/b.py"], domains=["error-recovery"]),
                "changed_paths": ["swarm/b.py"],
            }],
        )
        self.assertEqual(result["disposition"], "PASS")


if __name__ == "__main__":
    unittest.main()
