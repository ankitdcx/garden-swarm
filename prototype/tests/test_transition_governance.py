from prototype.transition_governance import (
    TransitionContext,
    TransitionDecision,
    TransitionProposal,
    TransitionStage,
    evaluate_transition,
)


PLAN = (
    TransitionStage.SHADOW,
    TransitionStage.PARALLEL,
    TransitionStage.BOUNDED_ACTIVE,
    TransitionStage.EXPANDED_ACTIVE,
    TransitionStage.STABLE_OPERATION,
)


def proposal(
    current=TransitionStage.SHADOW,
    next_stage=TransitionStage.PARALLEL,
    *,
    reversible=True,
):
    return TransitionProposal(
        transition_id="t1",
        current_stage=current,
        next_stage=next_stage,
        declared_stage_plan=PLAN,
        effect_scope="institution:bounded",
        reversible_effect=reversible,
    )


def context(**overrides):
    values = dict(
        authority_validated=True,
        hard_gates={
            "rights": True,
            "consent": True,
            "privacy": True,
            "law": True,
            "safety": True,
            "human_effect": True,
        },
        independent_verification=True,
        divergence_resolved=True,
        capture_conflict_clear=True,
        operational_readiness=True,
        entry_criteria={"entry": True},
        exit_criteria={"exit": True},
        rollback_ready=True,
        compensation_recovery_ready=True,
    )
    values.update(overrides)
    return TransitionContext(**values)


def test_shadow_to_parallel_can_advance_without_minting_authority():
    result = evaluate_transition(proposal(), context())
    assert result.decision is TransitionDecision.ADVANCE
    assert result.authority_created is False


def test_declared_stage_cannot_be_skipped():
    result = evaluate_transition(
        proposal(
            current=TransitionStage.SHADOW,
            next_stage=TransitionStage.BOUNDED_ACTIVE,
        ),
        context(),
    )
    assert result.decision is TransitionDecision.REJECT
    assert result.reasons == ("DECLARED_STAGE_SKIP_OR_INVALID_NEXT_STAGE",)


def test_unknown_transition_authority_is_not_pass():
    result = evaluate_transition(proposal(), context(authority_validated=None))
    assert result.decision is TransitionDecision.ESCALATE
    assert result.reasons == ("TRANSITION_AUTHORITY_UNKNOWN",)


def test_invalid_transition_authority_rejects():
    result = evaluate_transition(proposal(), context(authority_validated=False))
    assert result.decision is TransitionDecision.REJECT
    assert result.reasons == ("TRANSITION_AUTHORITY_INVALID",)


def test_human_effect_gate_failure_rejects():
    gates = dict(context().hard_gates)
    gates["human_effect"] = False
    result = evaluate_transition(proposal(), context(hard_gates=gates))
    assert result.decision is TransitionDecision.REJECT
    assert result.reasons == ("TRANSITION_HARD_GATE_FAILED:human_effect",)


def test_parallel_divergence_blocks_bounded_activation():
    result = evaluate_transition(
        proposal(
            current=TransitionStage.PARALLEL,
            next_stage=TransitionStage.BOUNDED_ACTIVE,
        ),
        context(divergence_resolved=False),
    )
    assert result.decision is TransitionDecision.HOLD
    assert result.reasons == ("MATERIAL_DIVERGENCE_UNRESOLVED",)


def test_capture_conflict_blocks_advancement():
    result = evaluate_transition(proposal(), context(capture_conflict_clear=False))
    assert result.decision is TransitionDecision.HOLD
    assert result.reasons == ("CAPTURE_OR_CONFLICT_CHECK_FAILED",)


def test_required_independence_unknown_escalates():
    result = evaluate_transition(proposal(), context(independent_verification=None))
    assert result.decision is TransitionDecision.ESCALATE
    assert result.reasons == ("INDEPENDENT_VERIFICATION_UNKNOWN",)


def test_irreversible_effect_requires_prior_recovery_or_compensation():
    result = evaluate_transition(
        proposal(reversible=False),
        context(compensation_recovery_ready=False),
    )
    assert result.decision is TransitionDecision.HOLD
    assert result.reasons == ("IRREVERSIBLE_EFFECT_RECOVERY_NOT_READY",)


def test_reversible_effect_requires_rollback_readiness():
    result = evaluate_transition(proposal(), context(rollback_ready=False))
    assert result.decision is TransitionDecision.HOLD
    assert result.reasons == ("ROLLBACK_NOT_READY",)


def test_material_nonseparable_dispute_holds_affected_scope():
    result = evaluate_transition(
        proposal(),
        context(
            material_dispute_open=True,
            dispute_path_ready=True,
            dispute_separable_from_effect_scope=False,
        ),
    )
    assert result.decision is TransitionDecision.HOLD
    assert result.reasons == ("MATERIAL_DISPUTE_BLOCKS_EFFECT_SCOPE",)


def test_material_separable_dispute_can_continue_with_ready_path():
    result = evaluate_transition(
        proposal(),
        context(
            material_dispute_open=True,
            dispute_path_ready=True,
            dispute_separable_from_effect_scope=True,
        ),
    )
    assert result.decision is TransitionDecision.ADVANCE
