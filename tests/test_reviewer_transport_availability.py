import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class ReviewerTransportAvailabilityTests(unittest.TestCase):
    def setUp(self):
        self.registry = json.loads((ROOT / "agents/reviewer-slot-registry.json").read_text())
        self.proposal = json.loads((ROOT / "agents/reviewer-transport-availability-proposal.json").read_text())

    def test_quality_and_transport_are_distinct(self):
        rules = self.registry["transport_availability_semantics"]
        self.assertTrue(rules["qualification_is_distinct_from_transport"])

    def test_unavailable_required_slot_does_not_complete(self):
        rules = self.registry["transport_availability_semantics"]
        self.assertTrue(rules["qualified_but_unavailable_does_not_complete_required_slot"])
        slot = next(x for x in self.registry["slots"] if x["slot_id"] == "SLOT-DETERMINISM")
        self.assertEqual(slot["state"], "ACTIVE")
        self.assertEqual(slot["transport_state"], "QUALIFIED_BUT_UNAVAILABLE")

    def test_challenger_only_cannot_satisfy_required_slot(self):
        rules = self.registry["transport_availability_semantics"]
        self.assertTrue(rules["challenger_only_may_continue_when_explicitly_authorized"])
        self.assertTrue(rules["challenger_only_never_satisfies_required_slot"])
        self.assertTrue(rules["final_high_risk_convergence_requires_all_required_slots_or_governed_replacement"])

    def test_no_gate_weakening(self):
        joined = "\n".join(self.proposal["rules"])
        self.assertIn("Provider, privacy, budget, context and fee gates are not weakened", joined)

    def test_run_277_evidence_bound(self):
        e = self.proposal["trigger_evidence"]
        self.assertEqual(e["run_issue"], 277)
        self.assertEqual(e["endpoints_discovered"], 24)
        self.assertEqual(e["eligible_endpoints"], 0)

if __name__ == "__main__":
    unittest.main()
