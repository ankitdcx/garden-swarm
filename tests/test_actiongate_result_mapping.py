import unittest

from prototype.actiongate import ActionProposal, Decision, GateContext, evaluate_action
from prototype.authority import AuthorityEnvelope


def context(*, epoch="E1", hard_gates=None):
    return GateContext(
        current_policy_epoch=epoch,
        capabilities_by_principal={"human:alice": frozenset({"notify"})},
        authority_by_subject={
            "human:alice": AuthorityEnvelope(
                subject="human:alice",
                actions=frozenset({"notify"}),
                resources=frozenset({"demo"}),
                max_depth=0,
            )
        },
        hard_gates=hard_gates if hard_gates is not None else {"rights": True},
    )


def proposal(*, epoch="E1"):
    return ActionProposal(
        principal="human:alice",
        action="notify",
        target="demo",
        capability="notify",
        delegation_chain=("human:alice",),
        policy_epoch=epoch,
    )


class ActionGateResultMappingTests(unittest.TestCase):
    def test_stale_is_reject_with_stale_reason(self):
        result = evaluate_action(proposal(epoch="E0"), context(epoch="E1"))
        self.assertEqual(result.decision, Decision.REJECT)
        self.assertEqual(result.reasons, ("STALE_POLICY_EPOCH",))

    def test_unknown_gate_is_escalate_with_unknown_reason(self):
        result = evaluate_action(proposal(), context(hard_gates={"rights": None}))
        self.assertEqual(result.decision, Decision.ESCALATE)
        self.assertEqual(result.reasons, ("HARD_GATE_UNKNOWN:rights",))

    def test_stale_and_unknown_remain_distinguishable(self):
        stale = evaluate_action(proposal(epoch="E0"), context(epoch="E1"))
        unknown = evaluate_action(proposal(), context(hard_gates={"rights": None}))
        self.assertNotEqual(stale.decision, unknown.decision)
        self.assertNotEqual(stale.reasons, unknown.reasons)


if __name__ == "__main__":
    unittest.main()
