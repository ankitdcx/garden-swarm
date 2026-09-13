from __future__ import annotations

from prototype.actiongate import ActionProposal, Decision, GateConditionStatus, GateContext, evaluate_action


def test_stale_policy_is_typed_stale_not_only_a_reject_reason():
    ctx = GateContext(
        current_policy_epoch="E2",
        capabilities_by_principal={"human:alice": frozenset({"notify"})},
    )
    proposal = ActionProposal(
        principal="human:alice",
        action="notify",
        target="demo",
        capability="notify",
        delegation_chain=("human:alice",),
        policy_epoch="E1",
    )
    result = evaluate_action(proposal, ctx)
    assert result.decision is Decision.REJECT
    assert result.condition_status is GateConditionStatus.STALE
    assert result.reasons == ("STALE_POLICY_EPOCH",)


def test_missing_authority_is_typed_unknown_not_only_an_escalation_reason():
    ctx = GateContext(
        current_policy_epoch="E1",
        capabilities_by_principal={"human:alice": frozenset({"notify"})},
    )
    proposal = ActionProposal(
        principal="human:alice",
        action="notify",
        target="demo",
        capability="notify",
        delegation_chain=("human:alice",),
        policy_epoch="E1",
    )
    result = evaluate_action(proposal, ctx)
    assert result.decision is Decision.ESCALATE
    assert result.condition_status is GateConditionStatus.UNKNOWN
    assert result.reasons == ("AUTHORITY_ENVELOPE_UNKNOWN:human:alice",)
