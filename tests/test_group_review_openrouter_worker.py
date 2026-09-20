import base64
import hashlib
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
        if workflow == "provider":
            name = "group-review-openrouter.yml"
        elif workflow == "push":
            name = "group-review-openrouter-push-trigger.yml"
        else:
            name = "group-review-openrouter-trigger.yml"
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

    def test_push_trigger_uses_hash_bound_request_file(self):
        path = write_event({})
        request = {
            "schema": worker.PUSH_REQUEST_SCHEMA,
            "status": "REQUESTED",
            "run_issue_number": 254,
            "packet_sha256": "a" * 64,
        }
        request_path = Path(tempfile.mkstemp()[1])
        request_path.write_text(json.dumps(request), encoding="utf-8")
        env = self.base_env("push") | {
            "GITHUB_EVENT_NAME": "push",
            "GITHUB_ACTOR": "ankitdcx",
            "GITHUB_EVENT_PATH": path,
        }
        try:
            with patch.object(worker, "PUSH_REQUEST_PATH", request_path):
                with patch.dict(os.environ, env, clear=True):
                    self.assertEqual(worker.trigger_issue_number(), 254)
        finally:
            Path(path).unlink(missing_ok=True)
            request_path.unlink(missing_ok=True)

    def test_push_dispatch_binding_rejects_packet_drift(self):
        request = {
            "schema": worker.PUSH_REQUEST_SCHEMA,
            "status": "REQUESTED",
            "run_issue_number": 254,
            "packet_sha256": "a" * 64,
        }
        worker.validate_push_dispatch_binding(
            request, 254, {"packet_sha256": "a" * 64}
        )
        with self.assertRaisesRegex(ValueError, "packet binding mismatch"):
            worker.validate_push_dispatch_binding(
                request, 254, {"packet_sha256": "b" * 64}
            )

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

    def simple_budget_policy(self):
        return {
            "routine_model_call_cost_ceiling_usd": 0.05,
            "daily_openrouter_cost_ceiling_usd": 2,
        }

    def paid_key_info(self, **overrides):
        value = {
            "is_management_key": False,
            "is_free_tier": False,
            "usage": 10,
            "usage_daily": 0,
            "limit_remaining": 10,
        }
        value.update(overrides)
        return value

    def test_group_review_budget_uses_provider_daily_usage_and_exact_call_cap(self):
        state = {"paused": False, "attempts": []}
        reserve, day, daily, rule_id = worker.group_review_budget_check(
            state,
            self.paid_key_info(usage_daily="1.50"),
            self.simple_budget_policy(),
            1_758_000_000,
            cycle_id="cycle-1",
        )
        self.assertEqual(str(reserve), "0.05")
        self.assertEqual(daily, "1.50")
        self.assertEqual(rule_id, "OPENROUTER_2_USD_DAY_0_05_CALL")
        self.assertRegex(day, r"^\d{4}-\d{2}-\d{2}$")

    def test_group_review_budget_blocks_daily_reservation_over_two_dollars(self):
        state = {"paused": False, "attempts": []}
        with self.assertRaisesRegex(ValueError, "daily reservation exhausted"):
            worker.group_review_budget_check(
                state,
                self.paid_key_info(usage_daily="1.995"),
                self.simple_budget_policy(),
                1_758_000_000,
                cycle_id="cycle-1",
            )

    def test_group_review_budget_rejects_policy_drift(self):
        state = {"paused": False, "attempts": []}
        bad = dict(self.simple_budget_policy(), routine_model_call_cost_ceiling_usd=0.02)
        with self.assertRaisesRegex(ValueError, "USD 2/day and USD 0.05/call"):
            worker.group_review_budget_check(
                state,
                self.paid_key_info(),
                bad,
                1_758_000_000,
                cycle_id="cycle-1",
            )

    def test_group_review_budget_preserves_credit_limit_gate(self):
        state = {"paused": False, "attempts": []}
        with self.assertRaisesRegex(ValueError, "key credit limit too low"):
            worker.group_review_budget_check(
                state,
                self.paid_key_info(limit_remaining="0.005"),
                self.simple_budget_policy(),
                1_758_000_000,
                cycle_id="cycle-1",
            )

    def test_group_review_budget_blocks_unresolved_reservation(self):
        state = {
            "paused": False,
            "attempts": [
                {
                    "cycle": "cycle-1",
                    "utc_day": "2025-09-15",
                    "status": "RESERVED",
                    "cost": None,
                }
            ],
        }
        with self.assertRaisesRegex(ValueError, "outstanding reservation"):
            worker.group_review_budget_check(
                state,
                self.paid_key_info(),
                self.simple_budget_policy(),
                1_758_000_000,
                cycle_id="cycle-1",
            )

    def test_budget_rejection_diagnostics_are_normalized(self):
        cases = [
            (ValueError("paid inference key required"), "KEY_TYPE_NOT_PAID"),
            (ValueError("daily reservation exhausted"), "DAILY_BUDGET_EXHAUSTED"),
            (ValueError("key credit limit too low"), "KEY_CREDIT_LIMIT_TOO_LOW"),
            (ValueError("unknown monetary value"), "KEY_USAGE_UNKNOWN"),
            (ValueError("invalid monetary value"), "KEY_USAGE_INVALID"),
            (ValueError("outstanding reservation/unknown cost; reconciliation required"), "OUTSTANDING_RESERVATION"),
        ]
        for exc, expected in cases:
            self.assertEqual(worker._budget_rejection_code(exc), expected)

    def test_unknown_budget_rejection_is_generic(self):
        self.assertEqual(
            worker._budget_rejection_code(ValueError("opaque account detail 123")),
            "BUDGET_POLICY_REJECTED",
        )

    def test_endpoint_rejection_diagnostics_are_normalized(self):
        cases = [
            (ValueError("endpoint above routing price cap"), "PRICE_CAP"),
            (ValueError("request exceeds reserved cost/context"), "RESERVE_OR_CONTEXT"),
            (ValueError("endpoint cannot fit the full review prompt"), "PROMPT_LIMIT"),
            (ValueError("excluded endpoint"), "ENDPOINT_EXCLUDED"),
            (KeyError("pricing"), "ENDPOINT_METADATA_MISSING"),
            (RuntimeError("provider problem"), "ENDPOINT_RUNTIME_REJECTED"),
        ]
        for exc, expected in cases:
            self.assertEqual(worker._endpoint_rejection_code(exc), expected)

    def test_unknown_endpoint_rejection_is_generic(self):
        self.assertEqual(
            worker._endpoint_rejection_code(ValueError("opaque provider detail 123")),
            "ENDPOINT_POLICY_REJECTED",
        )

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
            "source_refs": ["repo:ankitdcx/garden-swarm@aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa:AGENTS.md"],
            "source_hashes": {"repo:ankitdcx/garden-swarm@aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa:AGENTS.md": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"},
            "symmetric_worker_prompt": "Solve independently.",
        }
        packet["packet_sha256"] = bus.packet_hash(packet)
        prompt = bus.openrouter_prompt(packet, family="deepseek", role="find defects", model="m")
        self.assertIn(packet["packet_sha256"], prompt)
        self.assertNotIn("peer findings", prompt.lower())
        self.assertIn("have not seen any other reviewer output", prompt)


    def test_materialize_frozen_sources_fetches_exact_bytes_and_verifies_sha256(self):
        text = "alpha\nbeta\n"
        raw = text.encode("utf-8")
        digest = hashlib.sha256(raw).hexdigest()
        ref = "repo:ankitdcx/garden-swarm@" + ("a" * 40) + ":candidate.txt"
        packet = {
            "schema": bus.PACKET_SCHEMA,
            "problem_id": "GR-SRC",
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
            "source_refs": [ref],
            "source_hashes": {ref: digest},
            "symmetric_worker_prompt": "Solve independently.",
        }
        packet["packet_sha256"] = bus.packet_hash(packet)

        response = {
            "type": "file",
            "sha": "b" * 40,
            "content": base64.b64encode(raw).decode("ascii"),
        }
        with patch.object(worker.legacy, "http", return_value=response):
            bundle = worker.materialize_frozen_sources(
                packet, "gh-token", max_characters=1000
            )
        self.assertIn(text, bundle)
        self.assertIn(digest, bundle)
        self.assertIn(ref, bundle)

    def test_materialize_frozen_sources_rejects_hash_drift(self):
        text = "actual"
        ref = "repo:ankitdcx/garden-swarm@" + ("a" * 40) + ":candidate.txt"
        packet = {
            "schema": bus.PACKET_SCHEMA,
            "problem_id": "GR-SRC",
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
            "source_refs": [ref],
            "source_hashes": {ref: "c" * 64},
            "symmetric_worker_prompt": "Solve independently.",
        }
        packet["packet_sha256"] = bus.packet_hash(packet)
        response = {
            "type": "file",
            "sha": "b" * 40,
            "content": base64.b64encode(text.encode()).decode("ascii"),
        }
        with patch.object(worker.legacy, "http", return_value=response):
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                worker.materialize_frozen_sources(
                    packet, "gh-token", max_characters=1000
                )

    def test_materialize_frozen_sources_never_silently_truncates(self):
        raw = ("x" * 100).encode()
        digest = hashlib.sha256(raw).hexdigest()
        ref = "repo:ankitdcx/garden-swarm@" + ("a" * 40) + ":large.txt"
        packet = {
            "schema": bus.PACKET_SCHEMA,
            "problem_id": "GR-SRC",
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
            "source_refs": [ref],
            "source_hashes": {ref: digest},
            "symmetric_worker_prompt": "Solve independently.",
        }
        packet["packet_sha256"] = bus.packet_hash(packet)
        response = {
            "type": "file",
            "sha": "b" * 40,
            "content": base64.b64encode(raw).decode("ascii"),
        }
        with patch.object(worker.legacy, "http", return_value=response):
            with self.assertRaisesRegex(ValueError, "no truncation"):
                worker.materialize_frozen_sources(
                    packet, "gh-token", max_characters=40
                )


if __name__ == "__main__":
    unittest.main()
