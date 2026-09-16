import json
import unittest
from pathlib import Path

from tools import event_context_gate as gate
from tools import run_frontier_council as council


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

    def test_unchanged_low_risk_context_skips_frontier(self):
        packet = gate.build_packet([self.obs()], self.policy, now=200.0)
        self.assertFalse(packet["material"])
        self.assertFalse(packet["frontier_call_eligible"])
        self.assertEqual(packet["packet_status"], "NOT_MATERIAL")
        ok, reason = council.eligible(packet, self.policy)
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
        self.assertTrue(packet["frontier_call_eligible"])
        self.assertEqual({x["observation_id"] for x in packet["observations"]}, {"left", "right"})
        self.assertIn("CONTRADICTION", packet["materiality_reasons"]["left"])
        ok, reason = council.eligible(packet, self.policy)
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

    def test_frontier_policy_is_selective_astra_not_universal_relay(self):
        cfg = self.policy["frontier_council"]
        self.assertEqual(cfg["primary_model"], "openai/gpt-6-astra")
        self.assertEqual(cfg["purpose"], "MATERIAL_CHANGE_SYNTHESIS_ONLY")
        self.assertEqual(cfg["max_calls_per_material_event"], 1)
        self.assertTrue(cfg["requires_materiality_receipt"])
        self.assertTrue(cfg["cannot_replace_independent_family_quorum"])
        self.assertTrue(cfg["cannot_admit_semantic_delta"])
        self.assertTrue(cfg["cannot_grant_authority"])
        self.assertLessEqual(cfg["max_call_cost_usd"], 0.20)

    def test_context_packet_preserves_backpointers_and_no_authority(self):
        packet = gate.build_packet([
            self.obs(risk="HIGH", event_kind="TEST_FAILURE", source_refs=["run:1"], evidence_refs=["log:1"])
        ], self.policy, now=200.0)
        row = packet["observations"][0]
        self.assertEqual(row["source_refs"], ["run:1"])
        self.assertEqual(row["evidence_refs"], ["log:1"])
        self.assertFalse(packet["semantic_delta_admitted"])
        self.assertFalse(packet["authority_granted"])


if __name__ == "__main__":
    unittest.main()
