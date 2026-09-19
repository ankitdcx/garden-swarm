from prototype.authority import AuthorityEnvelope
from prototype.runtime_constitution import (
    ConstraintClass,
    GoalProposal,
    InstructionAuthority,
    RuntimeConstitutionContext,
    RuntimeDecision,
    RuntimeInstruction,
    classify_instruction_authority,
    evaluate_answer_integrity,
    evaluate_goal,
    evaluate_instruction,
)


def authority(subject: str, actions: set[str], resources: set[str], depth: int = 2):
    return AuthorityEnvelope(
        subject=subject,
        actions=frozenset(actions),
        resources=frozenset(resources),
        max_depth=depth,
    )


def base_context(**overrides):
    data = dict(
        current_policy_epoch="E1",
        capabilities_by_subject={"agent:A": frozenset({"notify", "deploy"})},
        authority_by_subject={
            "human:alice": authority("human:alice", {"notify"}, {"repo"}),
            "agent:A": authority("agent:A", {"notify", "deploy"}, {"repo", "world"}),
        },
        hard_gates={
            "rights": True,
            "consent": True,
            "privacy": True,
            "law": True,
            "safety": True,
            "human_effect": True,
        },
        high_impact_actions=frozenset({"deploy"}),
    )
    data.update(overrides)
    return RuntimeConstitutionContext(**data)



def test_instruction_source_class_never_mints_authority_by_identity():
    assert (
        classify_instruction_authority(ConstraintClass.GARDEN_CONSTITUTION)
        is InstructionAuthority.GARDEN_CONSTRAINT_ONLY
    )
    assert (
        classify_instruction_authority(ConstraintClass.AUTHORIZED_HUMAN_INSTRUCTION)
        is InstructionAuthority.DELEGATED_AUTHORITY_REQUIRED
    )
    assert (
        classify_instruction_authority(ConstraintClass.OPERATOR_INSTRUCTION)
        is InstructionAuthority.PROPOSAL_ONLY
    )
    assert (
        classify_instruction_authority(ConstraintClass.MODEL_SUBGOAL)
        is InstructionAuthority.PROPOSAL_ONLY
    )
    assert (
        classify_instruction_authority(ConstraintClass.EXTERNAL_RUNTIME_CONSTRAINT)
        is InstructionAuthority.EXTERNAL_ENFORCEMENT_ONLY
    )

def test_model_selected_long_goal_can_persist_but_creates_no_authority():
    result = evaluate_goal(
        GoalProposal(
            goal_id="g1",
            proposer="agent:A",
            source_class=ConstraintClass.MODEL_SUBGOAL,
            summary="Evaluate and improve Garden over a long horizon.",
        ),
        base_context(),
    )
    assert result.decision is RuntimeDecision.PROPOSAL_ONLY
    assert result.authority_created is False
    assert "EACH_EFFECT_REQUIRES_FRESH_AUTHORIZATION" in result.reasons


def test_external_runtime_rule_can_block_but_cannot_authorize():
    ctx = base_context(external_runtime_blocks={"provider": frozenset({"notify"})})
    instruction = RuntimeInstruction(
        principal="human:alice",
        actor="agent:A",
        source_class=ConstraintClass.AUTHORIZED_HUMAN_INSTRUCTION,
        action="notify",
        target="repo",
        capability="notify",
        delegation_chain=("human:alice", "agent:A"),
        policy_epoch="E1",
    )
    result = evaluate_instruction(instruction, ctx)
    assert result.decision is RuntimeDecision.EXTERNALLY_BLOCKED
    assert result.authority_created is False
    assert result.reasons == ("EXTERNAL_RUNTIME_BLOCK:provider",)


def test_external_runtime_constraint_is_never_an_authority_source():
    result = evaluate_instruction(
        RuntimeInstruction(
            principal="provider",
            actor="provider",
            source_class=ConstraintClass.EXTERNAL_RUNTIME_CONSTRAINT,
            action="deploy",
            target="world",
            capability="deploy",
            delegation_chain=("provider",),
            policy_epoch="E1",
        ),
        base_context(),
    )
    assert result.decision is RuntimeDecision.PROPOSAL_ONLY
    assert result.authority_created is False


def test_operator_status_without_authority_does_not_create_authority():
    ctx = base_context()
    result = evaluate_instruction(
        RuntimeInstruction(
            principal="operator:owner",
            actor="agent:A",
            source_class=ConstraintClass.OPERATOR_INSTRUCTION,
            action="notify",
            target="repo",
            capability="notify",
            delegation_chain=("operator:owner", "agent:A"),
            policy_epoch="E1",
        ),
        ctx,
    )
    assert result.decision is RuntimeDecision.ESCALATE
    assert result.reasons == ("AUTHORITY_ENVELOPE_UNKNOWN:operator:owner",)


def test_model_subgoal_cannot_expand_delegated_scope():
    result = evaluate_instruction(
        RuntimeInstruction(
            principal="human:alice",
            actor="agent:A",
            source_class=ConstraintClass.MODEL_SUBGOAL,
            action="deploy",
            target="world",
            capability="deploy",
            delegation_chain=("human:alice", "agent:A"),
            policy_epoch="E1",
            goal_id="g1",
        ),
        base_context(),
    )
    assert result.decision is RuntimeDecision.REJECT
    assert result.reasons == ("AUTHORITY_SCOPE_DENIED",)


def test_force_install_goal_from_human_still_cannot_mint_global_authority():
    result = evaluate_instruction(
        RuntimeInstruction(
            principal="human:alice",
            actor="agent:A",
            source_class=ConstraintClass.AUTHORIZED_HUMAN_INSTRUCTION,
            action="deploy",
            target="world",
            capability="deploy",
            delegation_chain=("human:alice", "agent:A"),
            policy_epoch="E1",
            goal_id="install-garden-worldwide",
        ),
        base_context(),
    )
    assert result.decision is RuntimeDecision.REJECT
    assert result.authority_created is False


def test_high_impact_effect_requires_complete_human_effect_closure():
    ctx = base_context(
        authority_by_subject={
            "human:alice": authority("human:alice", {"deploy"}, {"world"}),
            "agent:A": authority("agent:A", {"deploy"}, {"world"}),
        },
        hard_gates={
            "rights": True,
            "consent": None,
            "privacy": True,
            "law": True,
            "safety": True,
            "human_effect": True,
        },
    )
    result = evaluate_instruction(
        RuntimeInstruction(
            principal="human:alice",
            actor="agent:A",
            source_class=ConstraintClass.MODEL_SUBGOAL,
            action="deploy",
            target="world",
            capability="deploy",
            delegation_chain=("human:alice", "agent:A"),
            policy_epoch="E1",
            goal_id="g1",
        ),
        ctx,
    )
    assert result.decision is RuntimeDecision.ESCALATE
    assert result.reasons == ("HUMAN_EFFECT_GATE_UNKNOWN:consent",)


def test_authorized_low_impact_model_selected_subgoal_can_execute():
    result = evaluate_instruction(
        RuntimeInstruction(
            principal="human:alice",
            actor="agent:A",
            source_class=ConstraintClass.MODEL_SUBGOAL,
            action="notify",
            target="repo",
            capability="notify",
            delegation_chain=("human:alice", "agent:A"),
            policy_epoch="E1",
            goal_id="g1",
        ),
        base_context(),
    )
    assert result.decision is RuntimeDecision.ALLOW
    assert result.authority_created is False
    assert "SOURCE_CLASS_DID_NOT_CREATE_AUTHORITY" in result.reasons


def test_revoked_persistent_goal_stops_future_effects():
    ctx = base_context(revoked_goal_ids=frozenset({"g1"}))
    result = evaluate_instruction(
        RuntimeInstruction(
            principal="human:alice",
            actor="agent:A",
            source_class=ConstraintClass.MODEL_SUBGOAL,
            action="notify",
            target="repo",
            capability="notify",
            delegation_chain=("human:alice", "agent:A"),
            policy_epoch="E1",
            goal_id="g1",
        ),
        ctx,
    )
    assert result.decision is RuntimeDecision.REJECT
    assert result.reasons == ("GOAL_REVOKED",)


def test_constraint_blocked_judgment_cannot_be_replaced_by_external_verdict():
    result = evaluate_answer_integrity(
        direct_judgment_permitted=False,
        response_claims_model_judgment=False,
        substitutes_external_judgment=True,
        constraint_disclosed=False,
    )
    assert result.decision is RuntimeDecision.REJECT
    assert result.reasons == (
        "CONSTRAINT_BLOCKED_JUDGMENT_SUBSTITUTED_BY_EXTERNAL_JUDGMENT",
    )


def test_constraint_blocked_judgment_is_honest_when_boundary_is_disclosed():
    result = evaluate_answer_integrity(
        direct_judgment_permitted=False,
        response_claims_model_judgment=False,
        substitutes_external_judgment=False,
        constraint_disclosed=True,
    )
    assert result.decision is RuntimeDecision.ALLOW
    assert "CONSTRAINT_BOUNDARY_DISCLOSED" in result.reasons
