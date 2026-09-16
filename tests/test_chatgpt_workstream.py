import unittest

from tools import chatgpt_workstream as w


POLICY = {
    "schema": "GardenChatGPTWorkstreamPolicy/v1",
    "workstream_intent_required_fields": ["workstream_id", "work_package_id", "branch", "base_sha", "dependency_intent_ids", "integration_strategy", "draft_pr_created_before_substantial_edit", "status"],
    "allowed_status": ["ACTIVE", "INTEGRATING", "SUPERSEDED", "CLOSED"],
    "allowed_integration_strategy": ["DIRECT_IF_NO_COLLISION", "INTEGRATION_BRANCH_IF_COLLISION"],
    "rules": {"future_chatgpt_branch_prefix": "chatgpt/"},
    "collision_rule": {"integration_branch_prefix": "integration/"},
}
BASE = "a" * 40


def record(name, path, domain, deps=None, strategy="INTEGRATION_BRANCH_IF_COLLISION"):
    intent_id = f"chatgpt:{name}"
    return {
        "workstream": {
            "schema": w.SCHEMA,
            "workstream_id": f"ws:{name}",
            "work_package_id": f"pkg:{name}",
            "branch": f"chatgpt/{name}",
            "base_sha": BASE,
            "dependency_intent_ids": deps or [],
            "integration_strategy": strategy,
            "draft_pr_created_before_substantial_edit": True,
            "status": "ACTIVE",
        },
        "agent_intent": {
            "schema": "AgentWorkIntent/v1",
            "intent_id": intent_id,
            "agent_id": "ChatGPT-test-lane",
            "task_id": f"task:{name}",
            "base_sha": BASE,
            "target_paths": [path],
            "target_symbols": [],
            "semantic_domains": [domain],
            "affected_invariants": [],
            "affected_contracts": [],
            "intended_effect": name,
            "parallel_mode": "COORDINATED",
        },
    }


class ChatGPTWorkstreamTests(unittest.TestCase):
    def test_early_draft_and_unique_branch_are_required(self):
        row = record("a", "a.txt", "A")
        row["workstream"]["draft_pr_created_before_substantial_edit"] = False
        with self.assertRaisesRegex(ValueError, "early draft PR"):
            w.validate_workstream(row["workstream"], POLICY)
        row = record("a", "a.txt", "A")
        row["workstream"]["branch"] = "feature/a"
        with self.assertRaisesRegex(ValueError, "chatgpt/"):
            w.validate_workstream(row["workstream"], POLICY)

    def test_different_files_same_semantic_domain_require_integration_branch(self):
        a = record("a", "agents/a.json", "MODEL_ROUTING")
        b = record("b", "tools/b.py", "MODEL_ROUTING")
        plan = w.plan([a, b], POLICY)
        self.assertEqual(len(plan["integration_groups"]), 1)
        group = plan["integration_groups"][0]
        self.assertEqual(group["status"], "INTEGRATION_BRANCH_REQUIRED")
        self.assertTrue(group["recommended_branch"].startswith("integration/"))
        self.assertEqual(plan["merge_train"], [])

    def test_noncolliding_dependency_builds_merge_train(self):
        a = record("a", "a.txt", "A")
        b = record("b", "b.txt", "B", deps=["chatgpt:a"])
        plan = w.plan([b, a], POLICY)
        self.assertEqual(plan["integration_groups"], [])
        self.assertEqual(plan["merge_train"], ["ws:a", "ws:b"])
        self.assertTrue(plan["ready_for_direct_merge_train"])

    def test_shared_branch_is_rejected(self):
        a = record("a", "a.txt", "A")
        b = record("b", "b.txt", "B")
        b["workstream"]["branch"] = a["workstream"]["branch"]
        with self.assertRaisesRegex(ValueError, "share a branch"):
            w.plan([a, b], POLICY)

    def test_collision_strategy_cannot_claim_direct_merge(self):
        a = record("a", "a.txt", "SAME", strategy="DIRECT_IF_NO_COLLISION")
        b = record("b", "b.txt", "SAME")
        plan = w.plan([a, b], POLICY)
        self.assertEqual(plan["integration_groups"][0]["status"], "BLOCKED_POLICY")

    def test_merge_emits_dependency_invalidation_for_semantic_overlap(self):
        merged = record("a", "a.txt", "MODEL_ROUTING")["agent_intent"]
        b = record("b", "different.txt", "MODEL_ROUTING")
        c = record("c", "c.txt", "UNRELATED")
        events = w.dependency_invalidations(merged, [b, c])
        self.assertEqual([e["workstream_id"] for e in events], ["ws:b"])
        self.assertEqual(events[0]["event"], "DEPENDENCY_INVALIDATION")


if __name__ == "__main__":
    unittest.main()
