import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import group_review_bus as bus
from tools import group_review_openrouter_worker as worker


def write_event(payload):
    handle = tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8")
    json.dump(payload, handle)
    handle.close()
    return handle.name


class GroupReviewOpenRouterWorkerTests(unittest.TestCase):
    def base_env(self, workflow="provider"):
        name = "group-review-openrouter.yml" if workflow == "provider" else "group-review-openrouter-trigger.yml"
        return {
            "GITHUB_REPOSITORY": "ankitdcx/garden-swarm",
            "GITHUB_REF": "refs/heads/main",
            "GITHUB_WORKFLOW_REF": f"ankitdcx/garden-swarm/.github/workflows/{name}@refs/heads/main",
            "GITHUB_REPOSITORY_OWNER": "ankitdcx",
        }

    def test_issue_trigger_requires_owner_and_run_title(self):
        path = write_event(
            {
                "action": "opened",
                "issue": {
                    "number": 99,
                    "title": "[GROUP_REVIEW_RUN] GR-1",
                    "user": {"login": "ankitdcx"},
                },
            }
        )
        env = self.base_env("trigger") | {
            "GITHUB_EVENT_NAME": "issues",
            "GITHUB_ACTOR": "ankitdcx",
            "GITHUB_EVENT_PATH": path,
        }
        try:
            with patch.dict(os.environ, env, clear=True):
                self.assertEqual(worker.trigger_issue_number(), 99)
            bad = dict(env)
            bad["GITHUB_ACTOR"] = "other"
            with patch.dict(os.environ, bad, clear=True):
                with self.assertRaisesRegex(ValueError, "repository owner"):
                    worker.trigger_issue_number()
        finally:
            Path(path).unlink(missing_ok=True)

    def test_workflow_dispatch_continuation_accepts_owner_or_actions_bot(self):
        path = write_event({"inputs": {"trigger_issue_number": "101"}})
        try:
            for actor in ("ankitdcx", "github-actions[bot]"):
                env = self.base_env() | {
                    "GITHUB_EVENT_NAME": "workflow_dispatch",
                    "GITHUB_ACTOR": actor,
                    "GITHUB_EVENT_PATH": path,
                }
                with patch.dict(os.environ, env, clear=True):
                    self.assertEqual(worker.trigger_issue_number(), 101)
        finally:
            Path(path).unlink(missing_ok=True)

    def test_next_reviewer_is_sequential_and_never_exposes_peer_content(self):
        selected = [
            {"family": "deepseek", "role": "r1", "model": "m1"},
            {"family": "xiaomi", "role": "r2", "model": "m2"},
            {"family": "nvidia", "role": "r3", "model": "m3"},
            {"family": "pareto", "role": "r4", "model": "m4"},
            {"family": "mistral", "role": "r5", "model": "m5"},
        ]
        cycle = {"findings": {}}
        self.assertEqual(worker.next_reviewer(cycle, selected)["family"], "deepseek")
        cycle["findings"]["deepseek"] = {"finding": {"summary": "peer content"}}
        self.assertEqual(worker.next_reviewer(cycle, selected)["family"], "xiaomi")

    def test_cycle_id_changes_when_packet_or_policy_changes(self):
        selected = [{"family": f"f{i}", "role": "r", "model": f"m{i}"} for i in range(5)]
        packet = {"packet_sha256": "a" * 64}
        one = worker.cycle_id(packet, selected, {"x": 1})
        two = worker.cycle_id({"packet_sha256": "b" * 64}, selected, {"x": 1})
        three = worker.cycle_id(packet, selected, {"x": 2})
        self.assertNotEqual(one, two)
        self.assertNotEqual(one, three)

    def test_compact_profile_caps_output(self):
        policy = {
            "review_profiles": {
                "ROUTINE": {
                    "max_output_tokens": 8000,
                    "reasoning_effort": "medium",
                    "request_timeout_seconds": 240,
                }
            }
        }
        profile = worker._profile(policy)
        self.assertEqual(profile["max_output_tokens"], 4000)
        self.assertEqual(profile["request_timeout_seconds"], 180)

    def test_openrouter_prompt_contains_frozen_packet_but_no_peer_findings(self):
        packet = {
            "schema": bus.PACKET_SCHEMA,
            "problem_id": "GR-X",
            "protocol_version": "2.1",
            "prompt_version": "v",
            "created_at": "now",
            "public_only": True,
            "data_classification": "PUBLIC",
            "triage": "MATERIAL",
            "openrouter_requested": True,
            "problem": "P",
            "scope": "S",
            "assumptions": [],
            "source_refs": [],
            "symmetric_worker_prompt": "Solve independently.",
        }
        packet["packet_sha256"] = bus.packet_hash(packet)
        prompt = bus.openrouter_prompt(packet, family="deepseek", role="find defects", model="m")
        self.assertIn(packet["packet_sha256"], prompt)
        self.assertNotIn("peer findings", prompt.lower())
        self.assertIn("have not seen any other reviewer output", prompt)


if __name__ == "__main__":
    unittest.main()
