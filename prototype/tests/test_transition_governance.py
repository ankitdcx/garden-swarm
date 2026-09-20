from prototype.transition_governance import (
    AuthorityDelta,
    RecoveryProposal,
    TransitionAssuranceBinding,
    TransitionContext,
    TransitionDecision,
    TransitionProposal,
    TransitionStage,
    evaluate_recovery,
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


def assurance_binding(
    *,
    purpose="ADVANCE",
    current=TransitionStage.SHADOW,
    target=TransitionStage.PARALLEL,
    effect_scope="institution:bounded",
):
    return TransitionAssuranceBinding(
        purpose=purpose,
        transition_id="t1",
        effect_scope=effect_scope,
        current_stage=current,
        target_stage=target,
        design_epoch="E1",
    )


def context(**overrides):
    values = dict(
        authority_validated=True,
        assurance_binding=assurance_binding(),
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
        criteria_profile_validated=True,
        entry_criteria={"entry": True},
        exit_criteria={"exit": True},
        rollback_ready=True,
        compensation_recovery_ready=True,
        last_qualified_stage=TransitionStage.PARALLEL,
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
        context(
            divergence_resolved=False,
            assurance_binding=assurance_binding(
                current=TransitionStage.PARALLEL,
                target=TransitionStage.BOUNDED_ACTIVE,
            ),
        ),
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


def test_mandatory_transition_hard_gates_cannot_be_removed_by_empty_profile_set():
    gates = dict(context().hard_gates)
    gates["human_effect"] = None
    result = evaluate_transition(
        proposal(),
        context(required_hard_gates=frozenset(), hard_gates=gates),
    )
    assert result.decision is TransitionDecision.ESCALATE
    assert result.reasons == ("TRANSITION_HARD_GATE_UNKNOWN:human_effect",)


def test_empty_entry_criteria_cannot_vacuously_pass():
    result = evaluate_transition(proposal(), context(entry_criteria={}))
    assert result.decision is TransitionDecision.ESCALATE
    assert result.reasons == ("ENTRY_CRITERIA_MISSING",)


def test_empty_exit_criteria_cannot_vacuously_pass():
    result = evaluate_transition(proposal(), context(exit_criteria={}))
    assert result.decision is TransitionDecision.ESCALATE
    assert result.reasons == ("EXIT_CRITERIA_MISSING",)


def test_abbreviated_stage_plan_requires_explicit_omission_justification():
    abbreviated = (
        TransitionStage.SHADOW,
        TransitionStage.BOUNDED_ACTIVE,
        TransitionStage.EXPANDED_ACTIVE,
        TransitionStage.STABLE_OPERATION,
    )
    result = evaluate_transition(
        TransitionProposal(
            transition_id="t1",
            current_stage=TransitionStage.SHADOW,
            next_stage=TransitionStage.BOUNDED_ACTIVE,
            declared_stage_plan=abbreviated,
            effect_scope="institution:bounded",
            reversible_effect=True,
        ),
        context(),
    )
    assert result.decision is TransitionDecision.REJECT
    assert result.reasons == ("STAGE_OMISSION_UNJUSTIFIED:PARALLEL",)


def test_stage_omission_requires_independent_approval_state():
    abbreviated = (
        TransitionStage.SHADOW,
        TransitionStage.BOUNDED_ACTIVE,
        TransitionStage.EXPANDED_ACTIVE,
        TransitionStage.STABLE_OPERATION,
    )
    result = evaluate_transition(
        TransitionProposal(
            transition_id="t1",
            current_stage=TransitionStage.SHADOW,
            next_stage=TransitionStage.BOUNDED_ACTIVE,
            declared_stage_plan=abbreviated,
            effect_scope="institution:bounded",
            reversible_effect=True,
            stage_omission_justifications={
                TransitionStage.PARALLEL: "Incumbent path is unavailable in the bounded synthetic profile."
            },
        ),
        context(),
    )
    assert result.decision is TransitionDecision.ESCALATE
    assert result.reasons == ("STAGE_OMISSION_APPROVAL_UNKNOWN:PARALLEL",)


def test_explicitly_approved_stage_omission_can_proceed_through_remaining_gates():
    abbreviated = (
        TransitionStage.SHADOW,
        TransitionStage.BOUNDED_ACTIVE,
        TransitionStage.EXPANDED_ACTIVE,
        TransitionStage.STABLE_OPERATION,
    )
    result = evaluate_transition(
        TransitionProposal(
            transition_id="t1",
            current_stage=TransitionStage.SHADOW,
            next_stage=TransitionStage.BOUNDED_ACTIVE,
            declared_stage_plan=abbreviated,
            effect_scope="institution:bounded",
            reversible_effect=True,
            stage_omission_justifications={
                TransitionStage.PARALLEL: "Incumbent path is unavailable in the bounded synthetic profile."
            },
        ),
        context(
            stage_omission_approval={TransitionStage.PARALLEL: True},
            assurance_binding=assurance_binding(
                current=TransitionStage.SHADOW,
                target=TransitionStage.BOUNDED_ACTIVE,
            ),
        ),
    )
    assert result.decision is TransitionDecision.ADVANCE


def test_declared_stage_plan_must_preserve_standard_order():
    reordered = (
        TransitionStage.SHADOW,
        TransitionStage.BOUNDED_ACTIVE,
        TransitionStage.PARALLEL,
        TransitionStage.EXPANDED_ACTIVE,
        TransitionStage.STABLE_OPERATION,
    )
    result = evaluate_transition(
        TransitionProposal(
            transition_id="t1",
            current_stage=TransitionStage.SHADOW,
            next_stage=TransitionStage.BOUNDED_ACTIVE,
            declared_stage_plan=reordered,
            effect_scope="institution:bounded",
            reversible_effect=True,
        ),
        context(),
    )
    assert result.decision is TransitionDecision.REJECT
    assert result.reasons == ("INVALID_DECLARED_STAGE_ORDER",)


def test_reversible_material_failure_can_rollback_only_to_earlier_stage():
    result = evaluate_recovery(
        RecoveryProposal(
            transition_id="t1",
            current_stage=TransitionStage.BOUNDED_ACTIVE,
            target_stage=TransitionStage.PARALLEL,
            effect_scope="institution:bounded",
            reversible_effect=True,
            material_failure_confirmed=True,
        ),
        context(assurance_binding=assurance_binding(purpose="RECOVERY", current=TransitionStage.BOUNDED_ACTIVE, target=TransitionStage.PARALLEL)),
    )
    assert result.decision is TransitionDecision.ROLLBACK
    assert result.authority_created is False


def test_rollback_cannot_move_forward_or_sideways():
    result = evaluate_recovery(
        RecoveryProposal(
            transition_id="t1",
            current_stage=TransitionStage.BOUNDED_ACTIVE,
            target_stage=TransitionStage.EXPANDED_ACTIVE,
            effect_scope="institution:bounded",
            reversible_effect=True,
            material_failure_confirmed=True,
        ),
        context(assurance_binding=assurance_binding(purpose="RECOVERY", current=TransitionStage.BOUNDED_ACTIVE, target=TransitionStage.EXPANDED_ACTIVE)),
    )
    assert result.decision is TransitionDecision.REJECT
    assert result.reasons == ("ROLLBACK_TARGET_NOT_EARLIER",)


def test_irreversible_material_failure_routes_to_compensation():
    result = evaluate_recovery(
        RecoveryProposal(
            transition_id="t1",
            current_stage=TransitionStage.BOUNDED_ACTIVE,
            target_stage=TransitionStage.BOUNDED_ACTIVE,
            effect_scope="institution:bounded",
            reversible_effect=False,
            material_failure_confirmed=True,
        ),
        context(assurance_binding=assurance_binding(purpose="RECOVERY", current=TransitionStage.BOUNDED_ACTIVE, target=TransitionStage.BOUNDED_ACTIVE)),
    )
    assert result.decision is TransitionDecision.COMPENSATE
    assert result.authority_created is False


def test_unknown_recovery_trigger_cannot_act():
    result = evaluate_recovery(
        RecoveryProposal(
            transition_id="t1",
            current_stage=TransitionStage.BOUNDED_ACTIVE,
            target_stage=TransitionStage.PARALLEL,
            effect_scope="institution:bounded",
            reversible_effect=True,
            material_failure_confirmed=None,
        ),
        context(),
    )
    assert result.decision is TransitionDecision.ESCALATE
    assert result.reasons == ("RECOVERY_TRIGGER_UNKNOWN",)


def test_recovery_requires_independent_verification():
    result = evaluate_recovery(
        RecoveryProposal(
            transition_id="t1",
            current_stage=TransitionStage.BOUNDED_ACTIVE,
            target_stage=TransitionStage.PARALLEL,
            effect_scope="institution:bounded",
            reversible_effect=True,
            material_failure_confirmed=True,
        ),
        context(
            independent_verification=None,
            assurance_binding=assurance_binding(
                purpose="RECOVERY",
                current=TransitionStage.BOUNDED_ACTIVE,
                target=TransitionStage.PARALLEL,
            ),
        ),
    )
    assert result.decision is TransitionDecision.ESCALATE
    assert result.reasons == ("RECOVERY_INDEPENDENT_VERIFICATION_UNKNOWN",)


def test_rollback_target_must_equal_last_qualified_stage():
    result = evaluate_recovery(
        RecoveryProposal(
            transition_id="t1",
            current_stage=TransitionStage.EXPANDED_ACTIVE,
            target_stage=TransitionStage.PARALLEL,
            effect_scope="institution:bounded",
            reversible_effect=True,
            material_failure_confirmed=True,
        ),
        context(
            last_qualified_stage=TransitionStage.BOUNDED_ACTIVE,
            assurance_binding=assurance_binding(
                purpose="RECOVERY",
                current=TransitionStage.EXPANDED_ACTIVE,
                target=TransitionStage.PARALLEL,
            ),
        ),
    )
    assert result.decision is TransitionDecision.REJECT
    assert result.reasons == ("ROLLBACK_TARGET_NOT_LAST_QUALIFIED",)


def test_unknown_last_qualified_stage_blocks_rollback():
    result = evaluate_recovery(
        RecoveryProposal(
            transition_id="t1",
            current_stage=TransitionStage.BOUNDED_ACTIVE,
            target_stage=TransitionStage.PARALLEL,
            effect_scope="institution:bounded",
            reversible_effect=True,
            material_failure_confirmed=True,
        ),
        context(
            last_qualified_stage=None,
            assurance_binding=assurance_binding(
                purpose="RECOVERY",
                current=TransitionStage.BOUNDED_ACTIVE,
                target=TransitionStage.PARALLEL,
            ),
        ),
    )
    assert result.decision is TransitionDecision.ESCALATE
    assert result.reasons == ("LAST_QUALIFIED_STAGE_UNKNOWN",)


def test_transition_assurance_from_different_effect_scope_cannot_be_replayed():
    result = evaluate_transition(
        proposal(),
        context(
            assurance_binding=assurance_binding(effect_scope="institution:other")
        ),
    )
    assert result.decision is TransitionDecision.REJECT
    assert result.reasons == ("TRANSITION_ASSURANCE_BINDING_MISMATCH",)


def test_missing_transition_assurance_binding_cannot_advance():
    result = evaluate_transition(proposal(), context(assurance_binding=None))
    assert result.decision is TransitionDecision.ESCALATE
    assert result.reasons == ("TRANSITION_ASSURANCE_BINDING_UNKNOWN",)


def test_advance_assurance_cannot_be_replayed_for_recovery():
    result = evaluate_recovery(
        RecoveryProposal(
            transition_id="t1",
            current_stage=TransitionStage.BOUNDED_ACTIVE,
            target_stage=TransitionStage.PARALLEL,
            effect_scope="institution:bounded",
            reversible_effect=True,
            material_failure_confirmed=True,
        ),
        context(
            assurance_binding=assurance_binding(
                purpose="ADVANCE",
                current=TransitionStage.BOUNDED_ACTIVE,
                target=TransitionStage.PARALLEL,
            )
        ),
    )
    assert result.decision is TransitionDecision.REJECT
    assert result.reasons == ("RECOVERY_ASSURANCE_BINDING_MISMATCH",)


def test_stale_transition_design_epoch_rejects_before_assurance_reuse():
    result = evaluate_transition(
        TransitionProposal(
            transition_id="t1",
            current_stage=TransitionStage.SHADOW,
            next_stage=TransitionStage.PARALLEL,
            declared_stage_plan=PLAN,
            effect_scope="institution:bounded",
            design_epoch="E0",
        ),
        context(),
    )
    assert result.decision is TransitionDecision.REJECT
    assert result.reasons == ("STALE_TRANSITION_DESIGN_EPOCH",)


def test_transition_assurance_from_old_design_epoch_cannot_be_replayed():
    old = TransitionAssuranceBinding(
        purpose="ADVANCE",
        transition_id="t1",
        effect_scope="institution:bounded",
        current_stage=TransitionStage.SHADOW,
        target_stage=TransitionStage.PARALLEL,
        design_epoch="E0",
    )
    result = evaluate_transition(proposal(), context(assurance_binding=old))
    assert result.decision is TransitionDecision.REJECT
    assert result.reasons == ("TRANSITION_ASSURANCE_BINDING_MISMATCH",)


def valid_authority_delta():
    return AuthorityDelta(
        delta_id="d1",
        delegator="institution:old",
        recipient="service:garden",
        actions=frozenset({"review"}),
        resources=frozenset({"permit:bounded"}),
        affected_subjects=frozenset({"community:1"}),
        jurisdiction="jurisdiction:1",
        invalidation_conditions=("revoked", "epoch_changed"),
        revocation_path="appeal-board",
        appeal_path="independent-appeal",
        evidence_refs=("authority-record:1",),
    )


def test_unvalidated_authority_delta_cannot_advance_transition():
    p = TransitionProposal(
        transition_id="t1",
        current_stage=TransitionStage.SHADOW,
        next_stage=TransitionStage.PARALLEL,
        declared_stage_plan=PLAN,
        effect_scope="institution:bounded",
        authority_deltas=(valid_authority_delta(),),
    )
    result = evaluate_transition(p, context())
    assert result.decision is TransitionDecision.ESCALATE
    assert result.reasons == ("AUTHORITY_DELTA_UNVALIDATED:d1",)


def test_authority_delta_requires_evidence_and_revocation_appeal_bindings():
    delta = AuthorityDelta(
        delta_id="d1",
        delegator="institution:old",
        recipient="service:garden",
        actions=frozenset({"review"}),
        resources=frozenset({"permit:bounded"}),
        affected_subjects=frozenset({"community:1"}),
        jurisdiction="jurisdiction:1",
        invalidation_conditions=("revoked",),
        revocation_path="",
        appeal_path="",
        evidence_refs=(),
    )
    p = TransitionProposal(
        transition_id="t1",
        current_stage=TransitionStage.SHADOW,
        next_stage=TransitionStage.PARALLEL,
        declared_stage_plan=PLAN,
        effect_scope="institution:bounded",
        authority_deltas=(delta,),
    )
    result = evaluate_transition(
        p,
        context(authority_delta_validation={"d1": True}),
    )
    assert result.decision is TransitionDecision.REJECT
    assert result.reasons == ("AUTHORITY_DELTA_BINDING_INCOMPLETE:d1",)


def test_validated_authority_delta_can_transfer_without_minting_authority():
    p = TransitionProposal(
        transition_id="t1",
        current_stage=TransitionStage.SHADOW,
        next_stage=TransitionStage.PARALLEL,
        declared_stage_plan=PLAN,
        effect_scope="institution:bounded",
        authority_deltas=(valid_authority_delta(),),
    )
    result = evaluate_transition(
        p,
        context(authority_delta_validation={"d1": True}),
    )
    assert result.decision is TransitionDecision.ADVANCE
    assert result.authority_created is False


def test_unvalidated_transition_criteria_profile_cannot_pass():
    result = evaluate_transition(
        proposal(),
        context(criteria_profile_validated=None),
    )
    assert result.decision is TransitionDecision.ESCALATE
    assert result.reasons == ("TRANSITION_CRITERIA_PROFILE_UNVALIDATED",)
