import inspect
import json
import unittest
from pathlib import Path

from tools import event_context_gate as gate
from tools import run_frontier_council as frontier


class EventDrivenContextRoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = json.loads(Path("agents/event-driven-context-policy.json").read_text(encoding="utf-8"))

    def obs(self, **updates):
        row = {
            "observation_id": "o1",
            "observed_at_unix": 100.0,
            "subject": "repo:target",
            "event_kind": "ROUTINE_CHANGE",
            "fingerprint": "fp-1",
            "changed_fields": ["README"],
            "risk": "LOW",
            "uncertainty": "LOW",
            "source_refs": ["commit:abc"],
            "evidence_refs": ["diff:abc"],
            "summary": "Routine bounded change",
            "public_only": True,
            "expires_at_unix": 1000.0,
        }
        row.update(updates)
        return row

    def test_unchanged_low_risk_context_skips_frontier_handoff(self):
        packet = gate.build_packet([self.obs()], self.policy, now=200.0)
        self.assertFalse(packet["material"])
        self.assertFalse(packet["frontier_handoff_eligible"])
        self.assertEqual(packet["packet_status"], "NOT_MATERIAL")
        ok, reason = frontier.eligible(packet, self.policy)
        self.assertFalse(ok)
        self.assertEqual(reason, "NOT_MATERIAL")

    def test_exact_replay_deduplicates_before_context(self):
        first = self.obs(observation_id="o1", observed_at_unix=100.0)
        second = self.obs(observation_id="o2", observed_at_unix=101.0)
        packet = gate.build_packet([first, second], self.policy, now=200.0)
        self.assertEqual(packet["raw_observation_count"], 2)
        self.assertEqual(packet["deduplicated_observation_count"], 1)
        self.assertEqual(packet["active_observation_count"], 1)
        self.assertEqual(packet["observations"][0]["observation_id"], "o2")
        self.assertIn(
            {"observation_id": "o1", "reason": "DUPLICATE_REPLAY_SUPERSEDED"},
            packet["omitted_observations"],
        )

    def test_high_risk_contradiction_is_material_and_preserves_both_sides(self):
        left = self.obs(
            observation_id="left", fingerprint="fp-left", event_kind="SECURITY_FINDING",
            risk="HIGH", contradiction=True, summary="Evidence says gate can fail open",
        )
        right = self.obs(
            observation_id="right", fingerprint="fp-right", event_kind="SECURITY_FINDING",
            risk="HIGH", contradiction=True, summary="Counterevidence says gate fails closed",
        )
        packet = gate.build_packet([left, right], self.policy, now=200.0)
        self.assertTrue(packet["material"])
        self.assertTrue(packet["frontier_handoff_eligible"])
        self.assertEqual({x["observation_id"] for x in packet["observations"]}, {"left", "right"})
        self.assertIn("CONTRADICTION", packet["materiality_reasons"]["left"])
        ok, reason = frontier.eligible(packet, self.policy)
        self.assertTrue(ok)
        self.assertEqual(reason, "MATERIAL_CONTEXT_ELIGIBLE")

    def test_stale_observation_cannot_support_current_frontier_packet(self):
        stale = self.obs(expires_at_unix=150.0, risk="CRITICAL", event_kind="AUTHORITY_CHANGE")
        packet = gate.build_packet([stale], self.policy, now=200.0)
        self.assertEqual(packet["active_observation_count"], 0)
        self.assertEqual(packet["stale_observation_count"], 1)
        self.assertFalse(packet["material"])
        self.assertIn(
            {"observation_id": "o1", "reason": "STALE_REQUIRES_REVALIDATION"},
            packet["omitted_observations"],
        )

    def test_frontier_is_external_chatgpt_not_openrouter_or_hardcoded_model(self):
        cfg = self.policy["frontier_handoff"]
        self.assertEqual(cfg["lane"], "EXTERNAL_CHATGPT_FRONTIER_REVIEW")
        self.assertEqual(cfg["provider_boundary"], "NOT_OPENROUTER")
        self.assertEqual(cfg["model_identity"], "USER_SELECTED_CHATGPT_MODEL_NOT_HARDCODED_BY_REPOSITORY")
        self.assertNotIn("primary_model", cfg)
        self.assertNotIn("provider_policy", cfg)
        self.assertTrue(cfg["requires_materiality_receipt"])
        self.assertTrue(cfg["cannot_replace_independent_family_quorum"])
        self.assertTrue(cfg["cannot_admit_semantic_delta"])
        self.assertTrue(cfg["cannot_grant_authority"])

    def test_material_packet_builds_provider_neutral_chatgpt_request(self):
        packet = gate.build_packet([
            self.obs(risk="HIGH", event_kind="TEST_FAILURE", source_refs=["run:1"], evidence_refs=["log:1"])
        ], self.policy, now=200.0)
        request = frontier.build_request(packet, self.policy, now=201.0)
        self.assertEqual(request["schema"], "GardenFrontierReviewRequest/v1")
        self.assertEqual(request["lane"], "EXTERNAL_CHATGPT_FRONTIER_REVIEW")
        self.assertEqual(request["provider_boundary"], "NOT_OPENROUTER")
        self.assertEqual(request["model_selection"], "USER_PRODUCT_CONTEXT")
        self.assertFalse(request["contains_provider_credentials"])
        self.assertFalse(request["contains_openrouter_model_route"])
        self.assertEqual(request["context_packet"]["observations"][0]["source_refs"], ["run:1"])
        self.assertEqual(request["context_packet"]["observations"][0]["evidence_refs"], ["log:1"])
        self.assertFalse(request["semantic_delta_admitted"])
        self.assertFalse(request["authority_granted"])

    def test_frontier_builder_has_no_network_or_provider_credential_path(self):
        source = inspect.getsource(frontier)
        self.assertNotIn("urlopen", source)
        self.assertNotIn("OPENROUTER_API_KEY", source)
        self.assertNotIn("chat/completions", source)
        self.assertNotIn("openai/gpt-6-astra", source)

    def test_full_context_fallback_is_explicit(self):
        required = self.policy["full_context_fallback"]["required_when"]
        self.assertGreaterEqual(len(required), 5)
        text = " ".join(required).lower()
        self.assertIn("dependency closure", text)
        self.assertIn("designepoch", text)
        self.assertIn("whole-source", text)


if __name__ == "__main__":
    unittest.main()
