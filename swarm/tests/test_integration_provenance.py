import unittest

from swarm.integration_provenance import AgentWorkIntent, assess_intents, compare_intents


BASE = "a" * 40


def intent(intent_id, *, paths, domains, symbols=None, invariants=None, contracts=None, base=BASE):
    return AgentWorkIntent.from_mapping({
        "schema": "AgentWorkIntent/v1",
        "intent_id": intent_id,
        "agent_id": f"agent:{intent_id}",
        "task_id": "TASK-TEST",
        "base_sha": base,
        "target_paths": paths,
        "target_symbols": symbols or [],
        "semantic_domains": domains,
        "affected_invariants": invariants or [],
        "affected_contracts": contracts or [],
        "intended_effect": "synthetic test change",
        "parallel_mode": "INDEPENDENT_COMPARISON",
    })


class IntegrationProvenanceTests(unittest.TestCase):
    def test_different_files_same_semantic_domain_collide(self):
        a = intent("A", paths=["swarm/error_handler.py"], domains=["error-recovery"])
        b = intent("B", paths=["swarm/error_manager.py"], domains=["error-recovery"])
        result = compare_intents(a, b)
        self.assertEqual(result["classification"], "POTENTIAL_COLLISION")
        self.assertIn("SEMANTIC_DOMAIN_OVERLAP", result["reasons"])

    def test_parent_directory_path_overlap_is_detected(self):
        a = intent("A", paths=["swarm"], domains=["orchestration"])
        b = intent("B", paths=["swarm/orchestrator.py"], domains=["review-routing"])
        result = compare_intents(a, b)
        self.assertIn("PATH_OVERLAP", result["reasons"])

    def test_shared_invariant_collides_even_without_path_overlap(self):
        a = intent("A", paths=["a.py"], domains=["alpha"], invariants=["AUTH-001"])
        b = intent("B", paths=["b.py"], domains=["beta"], invariants=["AUTH-001"])
        self.assertTrue(compare_intents(a, b)["requires_integration_receipt"])

    def test_no_overlap_passes_without_receipt(self):
        a = intent("A", paths=["a.py"], domains=["alpha"])
        b = intent("B", paths=["b.py"], domains=["beta"])
        result = assess_intents(a, [b])
        self.assertEqual(result["disposition"], "PASS")

    def test_collision_fails_closed_without_receipt(self):
        a = intent("A", paths=["a.py"], domains=["shared"])
        b = intent("B", paths=["b.py"], domains=["shared"])
        result = assess_intents(a, [b])
        self.assertEqual(result["disposition"], "REQUIRES_INTEGRATION_RECEIPT")

    def test_compatible_receipt_requires_post_integration_tests(self):
        a = intent("A", paths=["a.py"], domains=["shared"])
        b = intent("B", paths=["b.py"], domains=["shared"])
        receipt = {
            "schema": "IntegrationReceipt/v1",
            "current_intent_id": "A",
            "base_sha": BASE,
            "concurrent_intent_ids": ["B"],
            "semantic_compare": "COMPATIBLE",
            "composition_evidence": ["manual semantic diff"],
            "tests_after_integration": [],
        }
        result = assess_intents(a, [b], receipt)
        self.assertEqual(result["disposition"], "BLOCKED")
        self.assertIn("COMPATIBLE requires tests_after_integration evidence", result["integration_receipt_status"]["errors"])

    def test_complete_compatible_receipt_passes(self):
        a = intent("A", paths=["a.py"], domains=["shared"])
        b = intent("B", paths=["b.py"], domains=["shared"])
        receipt = {
            "schema": "IntegrationReceipt/v1",
            "current_intent_id": "A",
            "base_sha": BASE,
            "concurrent_intent_ids": ["B"],
            "semantic_compare": "COMPATIBLE",
            "composition_evidence": ["semantic diff checked"],
            "tests_after_integration": ["test_composed_behavior"],
        }
        result = assess_intents(a, [b], receipt)
        self.assertEqual(result["disposition"], "PASS")

    def test_receipt_omitting_one_collision_blocks(self):
        a = intent("A", paths=["a.py"], domains=["shared"])
        b = intent("B", paths=["b.py"], domains=["shared"])
        c = intent("C", paths=["c.py"], domains=["shared"])
        receipt = {
            "schema": "IntegrationReceipt/v1",
            "current_intent_id": "A",
            "base_sha": BASE,
            "concurrent_intent_ids": ["B"],
            "semantic_compare": "COMPATIBLE",
            "composition_evidence": ["partial compare"],
            "tests_after_integration": ["test_partial"],
        }
        result = assess_intents(a, [b, c], receipt)
        self.assertEqual(result["disposition"], "BLOCKED")
        self.assertTrue(any("C" in e for e in result["integration_receipt_status"]["errors"]))

    def test_unsafe_paths_are_rejected(self):
        with self.assertRaises(ValueError):
            intent("A", paths=["../outside.py"], domains=["x"])


if __name__ == "__main__":
    unittest.main()
