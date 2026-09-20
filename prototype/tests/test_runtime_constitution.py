from prototype.authority import AuthorityEnvelope
from prototype.runtime_constitution import (
    AuthorityValidationReceipt,
    ConstraintClass,
    ExternalEnforcementStatus,
    GoalLease,
    GoalProposal,
    GoalValidationReceipt,
    GoalValidity,
    InstructionAuthority,
    RuntimeConstitutionContext,
    RuntimeDecision,
    RuntimeInstruction,
    classify_instruction_authority,
    _authority_claim_digest,
    _materiality_claim_digest,
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


def authority_receipt(
    *,
    subject: str,
    claim_digest: str,
    parent: str | None,
    jurisdiction: str = "default",
    context_scope: str = "default",
    policy_epoch: str = "E1",
    design_epoch: str = "D1",
    validation_pass=True,
    identity_authenticated=True,
    scope_validated=True,
    delegation_validated=True,
    validity_interval_current=True,
    revoked=False,
    verifier_independent=True,
):
    return AuthorityValidationReceipt(
        subject=subject,
        claim_digest=claim_digest,
        parent_subject=parent,
        policy_epoch=policy_epoch,
        design_epoch=design_epoch,
        jurisdiction=jurisdiction,
        context_scope=context_scope,
        validation_pass=validation_pass,
        identity_authenticated=identity_authenticated,
        scope_validated=scope_validated,
        delegation_validated=delegation_validated,
        validity_interval_current=validity_interval_current,
        revoked=revoked,
        verifier_id="verifier:independent",
        verifier_control_lineage="control:independent",
        verifier_independent=verifier_independent,
        evidence_refs=(f"authority-evidence:{subject}",),
    )


def goal_lease(goal_id: str, authority_digest: str):
    return GoalLease(
        goal_id=goal_id,
        design_epoch="D1",
        policy_epoch="E1",
        delegated_by="human:alice",
        authority_claim_digests=(authority_digest,),
        dependency_digest=f"deps:{goal_id}:v1",
        resource_bound="bounded",
        termination_condition="stop-on-invalid-or-complete",
        invalidators=("design_epoch_change", "authority_change", "revocation"),
        evidence_refs=(f"goal-evidence:{goal_id}",),
    )


def goal_receipt(lease: GoalLease, *, validation_pass=True, verifier_independent=True):
    return GoalValidationReceipt(
        goal_id=lease.goal_id,
        lease_digest=lease.digest(),
        policy_epoch="E1",
        validation_pass=validation_pass,
        verifier_id="goal-verifier:independent",
        verifier_control_lineage="control:goal-independent",
        verifier_independent=verifier_independent,
        evidence_refs=(f"goal-validation:{lease.goal_id}",),
    )


def base_context(**overrides):
    authorities = {
        "human:alice": authority("human:alice", {"notify"}, {"repo"}),
        "agent:A": authority("agent:A", {"notify", "deploy"}, {"repo", "world"}),
    }
    provenance = {
        "human:alice": ("delegation-root:alice",),
        "agent:A": ("delegation:alice->agent:A",),
    }
    parents = {"agent:A": "human:alice"}
    claim_digests = {
        "human:alice": _authority_claim_digest(
            subject="human:alice",
            envelope=authorities["human:alice"],
            parent=None,
            provenance=provenance["human:alice"],
        ),
        "agent:A": _authority_claim_digest(
            subject="agent:A",
            envelope=authorities["agent:A"],
            parent=parents["agent:A"],
            provenance=provenance["agent:A"],
        ),
    }
    authority_receipts = {
        "human:alice": authority_receipt(
            subject="human:alice",
            claim_digest=claim_digests["human:alice"],
            parent=None,
        ),
        "agent:A": authority_receipt(
            subject="agent:A",
            claim_digest=claim_digests["agent:A"],
            parent=parents["agent:A"],
        ),
    }
    leases = {
        goal_id: goal_lease(goal_id, claim_digests["agent:A"])
        for goal_id in ("g1", "investigate-corruption", "install-garden-worldwide")
    }
    goal_receipts = {
        goal_id: goal_receipt(lease)
        for goal_id, lease in leases.items()
    }
    materiality = {
        ("notify", "repo"): False,
        ("deploy", "world"): True,
        ("intrude_private_system", "repo"): True,
    }
    data = dict(
        current_policy_epoch="E1",
        assurance_policy_epoch="E1",
        current_design_epoch="D1",
        capabilities_by_subject={"agent:A": frozenset({"notify", "deploy"})},
        authority_by_subject=authorities,
        authority_validation_by_subject={
            "human:alice": True,
            "agent:A": True,
        },
        authority_provenance_by_subject=provenance,
        authority_parent_by_subject=parents,
        authority_claim_digest_by_subject=claim_digests,
        authority_validation_receipt_by_subject=authority_receipts,
        hard_gates={
            "rights": True,
            "consent": True,
            "privacy": True,
            "law": True,
            "safety": True,
            "human_effect": True,
        },
        human_effect_materiality_by_effect=materiality,
        human_effect_materiality_validation_by_effect={key: True for key in materiality},
        human_effect_materiality_digest_by_effect={
            key: _materiality_claim_digest(
                action=key[0], target=key[1], material=value, policy_epoch="E1"
            )
            for key, value in materiality.items()
        },
        goal_validity_by_id={
            "g1": GoalValidity(True, True, True, True, True, True),
            "investigate-corruption": GoalValidity(True, True, True, True, True, True),
            "install-garden-worldwide": GoalValidity(True, True, True, True, True, True),
        },
        goal_lease_by_id=leases,
        goal_validation_receipt_by_id=goal_receipts,
    )
    data.update(overrides)

    if (
        "authority_by_subject" in overrides
        and "authority_claim_digest_by_subject" not in overrides
    ):
        final_authorities = data["authority_by_subject"]
        final_provenance = data["authority_provenance_by_subject"]
        final_parents = data["authority_parent_by_subject"]
        data["authority_claim_digest_by_subject"] = {
            subject: _authority_claim_digest(
                subject=subject,
                envelope=envelope,
                parent=final_parents.get(subject),
                provenance=final_provenance.get(subject, ()),
            )
            for subject, envelope in final_authorities.items()
        }

        if "authority_validation_receipt_by_subject" not in overrides:
            data["authority_validation_receipt_by_subject"] = {
                subject: authority_receipt(
                    subject=subject,
                    claim_digest=digest,
                    parent=final_parents.get(subject),
                )
                for subject, digest in data["authority_claim_digest_by_subject"].items()
            }
        if "goal_lease_by_id" not in overrides:
            agent_digest = data["authority_claim_digest_by_subject"].get("agent:A")
            if agent_digest:
                data["goal_lease_by_id"] = {
                    goal_id: goal_lease(goal_id, agent_digest)
                    for goal_id in data["goal_validity_by_id"]
                }
                if "goal_validation_receipt_by_id" not in overrides:
                    data["goal_validation_receipt_by_id"] = {
                        goal_id: goal_receipt(lease)
                        for goal_id, lease in data["goal_lease_by_id"].items()
                    }

    if (
        "human_effect_materiality_by_effect" in overrides
        and "human_effect_materiality_digest_by_effect" not in overrides
    ):
        data["human_effect_materiality_digest_by_effect"] = {
            key: _materiality_claim_digest(
                action=key[0],
                target=key[1],
                material=value,
                policy_epoch=data["current_policy_epoch"],
            )
            for key, value in data["human_effect_materiality_by_effect"].items()
        }

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
    ctx = base_context(external_runtime_blocks={"provider": frozenset({("notify", "repo")})})
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
    assert result.garden_decision is RuntimeDecision.ALLOW
    assert result.external_status is ExternalEnforcementStatus.BLOCKED
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


def test_present_authority_envelope_without_validation_is_not_pass():
    ctx = base_context(
        authority_validation_by_subject={
            "human:alice": True,
            "agent:A": None,
        }
    )
    result = evaluate_instruction(
        RuntimeInstruction(
            principal="human:alice",
            actor="agent:A",
            source_class=ConstraintClass.AUTHORIZED_HUMAN_INSTRUCTION,
            action="notify",
            target="repo",
            capability="notify",
            delegation_chain=("human:alice", "agent:A"),
            policy_epoch="E1",
        ),
        ctx,
    )
    assert result.decision is RuntimeDecision.ESCALATE
    assert result.reasons == ("AUTHORITY_CLAIM_UNVALIDATED:agent:A",)


def test_invalid_authority_claim_rejects_even_when_envelope_exists():
    ctx = base_context(
        authority_validation_by_subject={
            "human:alice": True,
            "agent:A": False,
        }
    )
    result = evaluate_instruction(
        RuntimeInstruction(
            principal="human:alice",
            actor="agent:A",
            source_class=ConstraintClass.AUTHORIZED_HUMAN_INSTRUCTION,
            action="notify",
            target="repo",
            capability="notify",
            delegation_chain=("human:alice", "agent:A"),
            policy_epoch="E1",
        ),
        ctx,
    )
    assert result.decision is RuntimeDecision.REJECT
    assert result.reasons == ("AUTHORITY_CLAIM_INVALID:agent:A",)


def test_authority_claim_requires_provenance_not_only_object_presence():
    ctx = base_context(
        authority_provenance_by_subject={
            "human:alice": ("delegation-root:alice",),
            "agent:A": (),
        }
    )
    result = evaluate_instruction(
        RuntimeInstruction(
            principal="human:alice",
            actor="agent:A",
            source_class=ConstraintClass.AUTHORIZED_HUMAN_INSTRUCTION,
            action="notify",
            target="repo",
            capability="notify",
            delegation_chain=("human:alice", "agent:A"),
            policy_epoch="E1",
        ),
        ctx,
    )
    assert result.decision is RuntimeDecision.ESCALATE
    assert result.reasons == ("AUTHORITY_PROVENANCE_MISSING:agent:A",)


def test_revoked_authority_rejects_even_if_envelope_and_validation_remain():
    ctx = base_context(revoked_authority_subjects=frozenset({"agent:A"}))
    result = evaluate_instruction(
        RuntimeInstruction(
            principal="human:alice",
            actor="agent:A",
            source_class=ConstraintClass.AUTHORIZED_HUMAN_INSTRUCTION,
            action="notify",
            target="repo",
            capability="notify",
            delegation_chain=("human:alice", "agent:A"),
            policy_epoch="E1",
        ),
        ctx,
    )
    assert result.decision is RuntimeDecision.REJECT
    assert result.reasons == ("AUTHORITY_REVOKED:agent:A",)


def test_garden_constitution_constrains_but_does_not_authorize_action():
    result = evaluate_instruction(
        RuntimeInstruction(
            principal="human:alice",
            actor="agent:A",
            source_class=ConstraintClass.GARDEN_CONSTITUTION,
            action="notify",
            target="repo",
            capability="notify",
            delegation_chain=("human:alice", "agent:A"),
            policy_epoch="E1",
        ),
        base_context(),
    )
    assert result.decision is RuntimeDecision.PROPOSAL_ONLY
    assert result.reasons == (
        "GARDEN_CONSTITUTION_CONSTRAINS_BUT_DOES_NOT_AUTHORIZE_ACTION",
    )


def test_good_goal_does_not_authorize_ungranted_investigative_means():
    ctx = base_context(
        capabilities_by_subject={
            "agent:A": frozenset({"notify", "deploy", "intrude_private_system"})
        }
    )
    result = evaluate_instruction(
        RuntimeInstruction(
            principal="human:alice",
            actor="agent:A",
            source_class=ConstraintClass.MODEL_SUBGOAL,
            action="intrude_private_system",
            target="repo",
            capability="intrude_private_system",
            delegation_chain=("human:alice", "agent:A"),
            policy_epoch="E1",
            goal_id="investigate-corruption",
        ),
        ctx,
    )
    assert result.decision is RuntimeDecision.REJECT
    assert result.reasons == ("AUTHORITY_SCOPE_DENIED",)


def test_external_runtime_block_does_not_mask_garden_rejection():
    ctx = base_context(
        external_runtime_blocks={"provider": frozenset({("deploy", "world")})}
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
    assert result.decision is RuntimeDecision.REJECT
    assert result.garden_decision is RuntimeDecision.REJECT
    assert result.external_status is ExternalEnforcementStatus.BLOCKED
    assert result.reasons == (
        "AUTHORITY_SCOPE_DENIED",
        "EXTERNAL_RUNTIME_BLOCK:provider",
    )


def test_delegation_lineage_requires_explicit_parent_binding():
    ctx = base_context(authority_parent_by_subject={})
    result = evaluate_instruction(
        RuntimeInstruction(
            principal="human:alice",
            actor="agent:A",
            source_class=ConstraintClass.AUTHORIZED_HUMAN_INSTRUCTION,
            action="notify",
            target="repo",
            capability="notify",
            delegation_chain=("human:alice", "agent:A"),
            policy_epoch="E1",
        ),
        ctx,
    )
    assert result.decision is RuntimeDecision.ESCALATE
    assert result.reasons == ("AUTHORITY_PARENT_UNKNOWN:agent:A",)


def test_delegation_lineage_rejects_wrong_parent():
    ctx = base_context(authority_parent_by_subject={"agent:A": "operator:owner"})
    result = evaluate_instruction(
        RuntimeInstruction(
            principal="human:alice",
            actor="agent:A",
            source_class=ConstraintClass.AUTHORIZED_HUMAN_INSTRUCTION,
            action="notify",
            target="repo",
            capability="notify",
            delegation_chain=("human:alice", "agent:A"),
            policy_epoch="E1",
        ),
        ctx,
    )
    assert result.decision is RuntimeDecision.REJECT
    assert result.reasons == ("AUTHORITY_PARENT_MISMATCH:agent:A",)


def test_base_human_effect_gates_cannot_be_removed_by_empty_profile_set():
    ctx = base_context(
        authority_by_subject={
            "human:alice": authority("human:alice", {"deploy"}, {"world"}),
            "agent:A": authority("agent:A", {"deploy"}, {"world"}),
        },
        required_human_effect_gates=frozenset(),
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


def test_missing_human_effect_materiality_cannot_be_treated_as_low_impact():
    ctx = base_context(human_effect_materiality_by_effect={})
    result = evaluate_instruction(
        RuntimeInstruction(
            principal="human:alice",
            actor="agent:A",
            source_class=ConstraintClass.AUTHORIZED_HUMAN_INSTRUCTION,
            action="notify",
            target="repo",
            capability="notify",
            delegation_chain=("human:alice", "agent:A"),
            policy_epoch="E1",
        ),
        ctx,
    )
    assert result.decision is RuntimeDecision.ESCALATE
    assert result.reasons == ("HUMAN_EFFECT_MATERIALITY_UNKNOWN",)


def test_human_effect_materiality_is_bound_to_action_and_target():
    ctx = base_context(
        capabilities_by_subject={"agent:A": frozenset({"notify"})},
        authority_by_subject={
            "human:alice": authority("human:alice", {"notify"}, {"human:patient"}),
            "agent:A": authority("agent:A", {"notify"}, {"human:patient"}),
        },
    )
    result = evaluate_instruction(
        RuntimeInstruction(
            principal="human:alice",
            actor="agent:A",
            source_class=ConstraintClass.AUTHORIZED_HUMAN_INSTRUCTION,
            action="notify",
            target="human:patient",
            capability="notify",
            delegation_chain=("human:alice", "agent:A"),
            policy_epoch="E1",
        ),
        ctx,
    )
    assert result.decision is RuntimeDecision.ESCALATE
    assert result.reasons == ("HUMAN_EFFECT_MATERIALITY_UNKNOWN",)


def test_unvalidated_human_effect_materiality_cannot_admit_action():
    ctx = base_context(
        human_effect_materiality_validation_by_effect={
            ("notify", "repo"): None,
            ("deploy", "world"): True,
            ("intrude_private_system", "repo"): True,
        }
    )
    result = evaluate_instruction(
        RuntimeInstruction(
            principal="human:alice",
            actor="agent:A",
            source_class=ConstraintClass.AUTHORIZED_HUMAN_INSTRUCTION,
            action="notify",
            target="repo",
            capability="notify",
            delegation_chain=("human:alice", "agent:A"),
            policy_epoch="E1",
        ),
        ctx,
    )
    assert result.decision is RuntimeDecision.ESCALATE
    assert result.reasons == ("HUMAN_EFFECT_MATERIALITY_UNVALIDATED",)


def test_persistent_goal_with_stale_design_epoch_is_rejected():
    ctx = base_context(
        goal_validity_by_id={
            **base_context().goal_validity_by_id,
            "g1": GoalValidity(False, True, True, True, True, True),
        }
    )
    result = evaluate_goal(
        GoalProposal(
            goal_id="g1",
            proposer="agent:A",
            source_class=ConstraintClass.MODEL_SUBGOAL,
            summary="Continue a stale goal.",
        ),
        ctx,
    )
    assert result.decision is RuntimeDecision.REJECT
    assert result.reasons == ("GOAL_BINDING_INVALID:design_epoch",)


def test_persistent_goal_unknown_dependency_freshness_escalates():
    ctx = base_context(
        goal_validity_by_id={
            **base_context().goal_validity_by_id,
            "g1": GoalValidity(True, True, True, None, True, True),
        }
    )
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
    assert result.decision is RuntimeDecision.ESCALATE
    assert result.reasons == ("GOAL_BINDING_UNKNOWN:dependencies",)


def test_missing_goal_validity_is_not_treated_as_valid():
    ctx = base_context(goal_validity_by_id={})
    result = evaluate_goal(
        GoalProposal(
            goal_id="g1",
            proposer="agent:A",
            source_class=ConstraintClass.MODEL_SUBGOAL,
            summary="Unbound goal.",
        ),
        ctx,
    )
    assert result.decision is RuntimeDecision.ESCALATE
    assert result.reasons == ("GOAL_VALIDITY_UNKNOWN",)


def test_stale_runtime_assurance_snapshot_rejects():
    result = evaluate_instruction(
        RuntimeInstruction(
            principal="human:alice",
            actor="agent:A",
            source_class=ConstraintClass.AUTHORIZED_HUMAN_INSTRUCTION,
            action="notify",
            target="repo",
            capability="notify",
            delegation_chain=("human:alice", "agent:A"),
            policy_epoch="E1",
        ),
        base_context(assurance_policy_epoch="E0"),
    )
    assert result.decision is RuntimeDecision.REJECT
    assert result.reasons == ("RUNTIME_ASSURANCE_EPOCH_STALE",)


def test_external_runtime_block_is_bound_to_target_scope():
    ctx = base_context(
        capabilities_by_subject={"agent:A": frozenset({"notify"})},
        authority_by_subject={
            "human:alice": authority("human:alice", {"notify"}, {"repo", "other"}),
            "agent:A": authority("agent:A", {"notify"}, {"repo", "other"}),
        },
        human_effect_materiality_by_effect={
            ("notify", "repo"): False,
            ("notify", "other"): False,
        },
        human_effect_materiality_validation_by_effect={
            ("notify", "repo"): True,
            ("notify", "other"): True,
        },
        external_runtime_blocks={"provider": frozenset({("notify", "other")})},
    )
    result = evaluate_instruction(
        RuntimeInstruction(
            principal="human:alice",
            actor="agent:A",
            source_class=ConstraintClass.AUTHORIZED_HUMAN_INSTRUCTION,
            action="notify",
            target="repo",
            capability="notify",
            delegation_chain=("human:alice", "agent:A"),
            policy_epoch="E1",
        ),
        ctx,
    )
    assert result.decision is RuntimeDecision.ALLOW


def test_changed_authority_envelope_cannot_reuse_old_validation_digest():
    ctx = base_context()
    changed = dict(ctx.authority_by_subject)
    changed["agent:A"] = authority(
        "agent:A", {"notify", "deploy", "intrude_private_system"}, {"repo", "world"}
    )
    result = evaluate_instruction(
        RuntimeInstruction(
            principal="human:alice",
            actor="agent:A",
            source_class=ConstraintClass.AUTHORIZED_HUMAN_INSTRUCTION,
            action="notify",
            target="repo",
            capability="notify",
            delegation_chain=("human:alice", "agent:A"),
            policy_epoch="E1",
        ),
        base_context(
            authority_by_subject=changed,
            authority_claim_digest_by_subject=ctx.authority_claim_digest_by_subject,
            authority_validation_receipt_by_subject=ctx.authority_validation_receipt_by_subject,
        ),
    )
    assert result.decision is RuntimeDecision.REJECT
    assert result.reasons == ("AUTHORITY_CLAIM_DIGEST_MISMATCH:agent:A",)


def test_changed_materiality_value_cannot_reuse_old_validation_digest():
    ctx = base_context()
    changed = dict(ctx.human_effect_materiality_by_effect)
    changed[("notify", "repo")] = True
    result = evaluate_instruction(
        RuntimeInstruction(
            principal="human:alice",
            actor="agent:A",
            source_class=ConstraintClass.AUTHORIZED_HUMAN_INSTRUCTION,
            action="notify",
            target="repo",
            capability="notify",
            delegation_chain=("human:alice", "agent:A"),
            policy_epoch="E1",
        ),
        base_context(
            human_effect_materiality_by_effect=changed,
            human_effect_materiality_digest_by_effect=ctx.human_effect_materiality_digest_by_effect,
        ),
    )
    assert result.decision is RuntimeDecision.REJECT
    assert result.reasons == ("HUMAN_EFFECT_MATERIALITY_DIGEST_MISMATCH",)


def test_authority_receipt_must_bind_exact_jurisdiction_and_context():
    ctx = base_context()
    receipts = dict(ctx.authority_validation_receipt_by_subject)
    old = receipts["agent:A"]
    receipts["agent:A"] = authority_receipt(
        subject=old.subject,
        claim_digest=old.claim_digest,
        parent=old.parent_subject,
        jurisdiction="jurisdiction:other",
    )
    result = evaluate_instruction(
        RuntimeInstruction(
            principal="human:alice",
            actor="agent:A",
            source_class=ConstraintClass.AUTHORIZED_HUMAN_INSTRUCTION,
            action="notify",
            target="repo",
            capability="notify",
            delegation_chain=("human:alice", "agent:A"),
            policy_epoch="E1",
            jurisdiction="jurisdiction:required",
        ),
        base_context(authority_validation_receipt_by_subject=receipts),
    )
    assert result.decision is RuntimeDecision.REJECT
    assert result.reasons == ("AUTHORITY_VALIDATION_RECEIPT_MISMATCH:agent:A",)


def test_authority_receipt_requires_real_independence():
    ctx = base_context()
    receipts = dict(ctx.authority_validation_receipt_by_subject)
    agent = receipts["agent:A"]
    receipts["agent:A"] = authority_receipt(
        subject=agent.subject,
        claim_digest=agent.claim_digest,
        parent=agent.parent_subject,
        verifier_independent=False,
    )
    result = evaluate_instruction(
        RuntimeInstruction(
            principal="human:alice",
            actor="agent:A",
            source_class=ConstraintClass.AUTHORIZED_HUMAN_INSTRUCTION,
            action="notify",
            target="repo",
            capability="notify",
            delegation_chain=("human:alice", "agent:A"),
            policy_epoch="E1",
        ),
        base_context(authority_validation_receipt_by_subject=receipts),
    )
    assert result.decision is RuntimeDecision.REJECT
    assert result.reasons == ("AUTHORITY_VALIDATION_NOT_INDEPENDENT:agent:A",)


def test_goal_lease_cannot_survive_authority_claim_change():
    ctx = base_context()
    changed = dict(ctx.authority_by_subject)
    changed["agent:A"] = authority(
        "agent:A", {"notify", "deploy"}, {"repo", "world", "other"}
    )
    result = evaluate_goal(
        GoalProposal(
            goal_id="g1",
            proposer="agent:A",
            source_class=ConstraintClass.MODEL_SUBGOAL,
            summary="Continue old lease.",
        ),
        base_context(
            authority_by_subject=changed,
            goal_lease_by_id=ctx.goal_lease_by_id,
            goal_validation_receipt_by_id=ctx.goal_validation_receipt_by_id,
        ),
    )
    assert result.decision is RuntimeDecision.REJECT
    assert result.reasons == ("GOAL_LEASE_AUTHORITY_STALE",)


def test_goal_validation_receipt_cannot_reuse_old_lease_digest():
    ctx = base_context()
    old = ctx.goal_lease_by_id["g1"]
    changed = GoalLease(
        goal_id=old.goal_id,
        design_epoch=old.design_epoch,
        policy_epoch=old.policy_epoch,
        delegated_by=old.delegated_by,
        authority_claim_digests=old.authority_claim_digests,
        dependency_digest="deps:g1:v2",
        resource_bound=old.resource_bound,
        termination_condition=old.termination_condition,
        invalidators=old.invalidators,
        evidence_refs=old.evidence_refs,
    )
    leases = dict(ctx.goal_lease_by_id)
    leases["g1"] = changed
    result = evaluate_goal(
        GoalProposal(
            goal_id="g1",
            proposer="agent:A",
            source_class=ConstraintClass.MODEL_SUBGOAL,
            summary="Changed goal lease.",
        ),
        base_context(
            goal_lease_by_id=leases,
            goal_validation_receipt_by_id=ctx.goal_validation_receipt_by_id,
        ),
    )
    assert result.decision is RuntimeDecision.REJECT
    assert result.reasons == ("GOAL_VALIDATION_RECEIPT_MISMATCH",)


def test_external_requirement_conflict_preserves_garden_rejection():
    ctx = base_context(
        external_runtime_requirements={"provider": frozenset({("deploy", "world")})}
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
    assert result.decision is RuntimeDecision.REJECT
    assert result.garden_decision is RuntimeDecision.REJECT
    assert result.external_status is ExternalEnforcementStatus.REQUIRED
    assert result.reasons == (
        "AUTHORITY_SCOPE_DENIED",
        "EXTERNAL_RUNTIME_REQUIREMENT_CONFLICT:provider",
    )


def test_expired_authority_validation_receipt_rejects():
    ctx = base_context()
    receipts = dict(ctx.authority_validation_receipt_by_subject)
    receipts["agent:A"] = authority_receipt(
        subject="agent:A",
        claim_digest=ctx.authority_claim_digest_by_subject["agent:A"],
        parent="human:alice",
        validity_interval_current=False,
    )
    result = evaluate_instruction(
        RuntimeInstruction(
            principal="human:alice",
            actor="agent:A",
            source_class=ConstraintClass.AUTHORIZED_HUMAN_INSTRUCTION,
            action="notify",
            target="repo",
            capability="notify",
            delegation_chain=("human:alice", "agent:A"),
            policy_epoch="E1",
        ),
        base_context(authority_validation_receipt_by_subject=receipts),
    )
    assert result.decision is RuntimeDecision.REJECT
    assert result.reasons == (
        "AUTHORITY_VALIDATION_RECEIPT_INVALID:agent:A:validity_interval",
    )


def test_old_design_epoch_authority_receipt_cannot_be_replayed():
    ctx = base_context()
    receipts = dict(ctx.authority_validation_receipt_by_subject)
    receipts["agent:A"] = authority_receipt(
        subject="agent:A",
        claim_digest=ctx.authority_claim_digest_by_subject["agent:A"],
        parent="human:alice",
        design_epoch="D0",
    )
    result = evaluate_instruction(
        RuntimeInstruction(
            principal="human:alice",
            actor="agent:A",
            source_class=ConstraintClass.AUTHORIZED_HUMAN_INSTRUCTION,
            action="notify",
            target="repo",
            capability="notify",
            delegation_chain=("human:alice", "agent:A"),
            policy_epoch="E1",
        ),
        base_context(authority_validation_receipt_by_subject=receipts),
    )
    assert result.decision is RuntimeDecision.REJECT
    assert result.reasons == (
        "AUTHORITY_VALIDATION_RECEIPT_MISMATCH:agent:A",
    )
