import unittest
from tools.challenger_review_contract import validate_challenger_admission

class ChallengerReviewContractTests(unittest.TestCase):
    def good(self, **kw):
        args=dict(explicit_human_authorization=True,required_slot_transport_state="QUALIFIED_BUT_UNAVAILABLE",public_source_bound=True,peer_answers_hidden=True,cost_ceiling_usd=0.01)
        args.update(kw)
        return validate_challenger_admission(**args)

    def test_challenger_never_completes_required_review(self):
        r=self.good()
        self.assertEqual(r["evidence_class"],"CHALLENGER_ONLY")
        self.assertFalse(r["satisfies_required_slot"])
        self.assertFalse(r["satisfies_independent_convergence"])
        self.assertFalse(r["semantic_delta_admitted"])

    def test_requires_explicit_authorization(self):
        with self.assertRaises(ValueError): self.good(explicit_human_authorization=False)

    def test_requires_actual_transport_block(self):
        with self.assertRaises(ValueError): self.good(required_slot_transport_state="QUALIFIED_AND_AVAILABLE")

    def test_keeps_budget_gate(self):
        with self.assertRaises(ValueError): self.good(cost_ceiling_usd=0.011)

if __name__=="__main__": unittest.main()
