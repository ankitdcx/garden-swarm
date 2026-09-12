from prototype.actiongate import ActionProposal, Decision, GateContext, evaluate_action
from prototype.authority import AuthorityEnvelope, can_execute
from prototype.design_epoch import ArtifactBinding, BindingStatus, validate_binding


def test_shared_memory_poisoning_does_not_directly_authorize_high_impact_action():
    context = GateContext(
        current_policy_epoch="E1",
        capabilities_by_principal={"human:alice": frozenset({"transfer"})},
        hard_gates={"rights": True, "policy": True, "safety": True},
        high_impact_actions=frozenset({"transfer"}),
    )
    poisoned = ActionProposal(
        principal="human:alice",
        action="transfer",
        target="account:X",
        capability="transfer",
        delegation_chain=("human:alice", "agent:privileged"),
        policy_epoch="E1",
        context_trust="untrusted",
        independent_review=False,
    )
    assert evaluate_action(poisoned, context).decision is Decision.ESCALATE


def test_delegation_chain_cannot_create_high_impact_authority():
    chain = (
        AuthorityEnvelope("A", frozenset({"suggest"}), frozenset({"public"}), 3),
        AuthorityEnvelope("B", frozenset({"suggest", "low_tool"}), frozenset({"public", "internal"}), 2),
        AuthorityEnvelope("C", frozenset({"execute_high"}), frozenset({"financial"}), 1),
    )
    assert not can_execute(chain, action="execute_high", resource="financial", depth=1)


def test_stale_flattened_policy_is_rejected_after_epoch_change():
    flattened_policy = ArtifactBinding(
        artifact_id="flattened-policy",
        design_epoch="E1",
        dependencies={"consent": "v1"},
    )
    result = validate_binding(
        flattened_policy,
        current_design_epoch="E2",
        current_dependencies={"consent": "v2"},
    )
    assert result.status is BindingStatus.STALE
