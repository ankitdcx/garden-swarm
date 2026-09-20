from prototype.upgrade_process import (
    FindingClass,
    FindingDisposition,
    FindingRecord,
    UpgradeContext,
    UpgradeDecision,
    evaluate_upgrade_closure,
)


def complete_context(**overrides):
    candidate_hash = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    values = dict(
        candidate_sha256=candidate_hash,
        audited_scope_sha256="cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
        search_coverage_scope_sha256="cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
        gate_candidate_bindings={
            "SEARCH_COVERAGE": candidate_hash,
            "PROPAGATION_CLOSURE": candidate_hash,
            "TESTS": candidate_hash,
            "RETENTION_NO_LOSS": candidate_hash,
            "VERIFICATION_INDEPENDENCE": candidate_hash,
            "INDEPENDENT_REVIEW": candidate_hash,
            "PROTECTED_AUTHORIZATION": candidate_hash,
            "FINAL_REAUDIT": candidate_hash,
            "FINDING_CLASSIFICATION": candidate_hash,
            "PROTECTED_SURFACE_SCAN": candidate_hash,
        },
        audited_scope_declared=True,
        search_coverage_complete=True,
        findings={
            "F-1": FindingRecord(FindingClass.MATERIAL, FindingDisposition.FIXED, evidence_refs=("test:F-1",)),
            "F-2": FindingRecord(FindingClass.ROUTINE, FindingDisposition.REJECTED_WITH_EVIDENCE, evidence_refs=("analysis:F-2",)),
        },
        bounded_cycle_declared=True,
        upgrade_methods_authorized=True,
        propagation_complete=True,
        tests_pass=True,
        retention_no_loss_pass=True,
        independent_review_required=True,
        independent_review_pass=True,
        verification_independence_pass=True,
        protected_change=False,
        protected_authorization_pass=None,
        final_reaudit_complete=True,
        finding_classification_validated=True,
        protected_surface_scan_pass=True,
        max_iterations=8,
        max_work_items=256,
        residual_debt_recorded=True,
    )
    values.update(overrides)
    return UpgradeContext(**values)


def test_complete_upgrade_can_close_candidate_without_creating_authority():
    result = evaluate_upgrade_closure(complete_context())
    assert result.decision is UpgradeDecision.CLOSE_CANDIDATE
    assert result.authority_created is False


def test_open_material_finding_keeps_work_loop_running():
    result = evaluate_upgrade_closure(
        complete_context(
            findings={"F-1": FindingRecord(FindingClass.MATERIAL, FindingDisposition.OPEN)},
        )
    )
    assert result.decision is UpgradeDecision.CONTINUE_WORK
    assert result.reasons == ("MATERIAL_FINDING_OPEN:F-1",)


def test_failed_tests_cannot_be_waived_by_protected_authorization():
    result = evaluate_upgrade_closure(
        complete_context(
            tests_pass=False,
            protected_change=True,
            protected_authorization_pass=True,
        )
    )
    assert result.decision is UpgradeDecision.CONTINUE_WORK
    assert result.reasons == ("TESTS_FAILED",)


def test_missing_required_independent_review_blocks_closure():
    result = evaluate_upgrade_closure(
        complete_context(independent_review_pass=False)
    )
    assert result.decision is UpgradeDecision.HOLD
    assert result.reasons == ("INDEPENDENT_REVIEW_FAILED",)


def test_unknown_independent_review_does_not_become_pass():
    result = evaluate_upgrade_closure(
        complete_context(independent_review_pass=None)
    )
    assert result.decision is UpgradeDecision.ESCALATE
    assert result.reasons == ("INDEPENDENT_REVIEW_UNKNOWN",)


def test_unvalidated_upgrade_method_authority_blocks_closure():
    result = evaluate_upgrade_closure(
        complete_context(upgrade_methods_authorized=None)
    )
    assert result.decision is UpgradeDecision.ESCALATE
    assert result.reasons == ("UPGRADE_METHOD_AUTHORITY_UNKNOWN",)


def test_protected_change_requires_separate_protected_authorization():
    result = evaluate_upgrade_closure(
        complete_context(
            protected_change=True,
            protected_authorization_pass=None,
        )
    )
    assert result.decision is UpgradeDecision.ESCALATE
    assert result.reasons == ("PROTECTED_AUTHORIZATION_UNKNOWN",)


def test_missing_final_reaudit_keeps_work_open():
    result = evaluate_upgrade_closure(
        complete_context(final_reaudit_complete=False)
    )
    assert result.decision is UpgradeDecision.CONTINUE_WORK
    assert result.reasons == ("FINAL_REAUDIT_FAILED",)


def test_unbounded_recursive_cycle_cannot_close():
    result = evaluate_upgrade_closure(
        complete_context(bounded_cycle_declared=False)
    )
    assert result.decision is UpgradeDecision.HOLD
    assert result.reasons == ("BOUNDED_UPGRADE_CYCLE_NOT_DECLARED",)


def test_empty_finding_list_without_search_coverage_cannot_close():
    result = evaluate_upgrade_closure(
        complete_context(
            findings={},
            search_coverage_complete=False,
        )
    )
    assert result.decision is UpgradeDecision.CONTINUE_WORK
    assert result.reasons == ("SEARCH_COVERAGE_FAILED",)


def test_undeclared_audit_scope_cannot_close_candidate():
    result = evaluate_upgrade_closure(
        complete_context(audited_scope_declared=False)
    )
    assert result.decision is UpgradeDecision.HOLD
    assert result.reasons == ("AUDITED_SCOPE_NOT_DECLARED",)


def test_old_test_pass_cannot_be_replayed_after_candidate_changes():
    old_hash = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    ctx = complete_context(candidate_sha256=old_hash)
    result = evaluate_upgrade_closure(ctx)
    assert result.decision is UpgradeDecision.HOLD
    assert result.reasons == ("SEARCH_COVERAGE_BINDING_MISMATCH",)


def test_missing_final_reaudit_candidate_binding_blocks_closure():
    ctx = complete_context()
    bindings = dict(ctx.gate_candidate_bindings)
    bindings.pop("FINAL_REAUDIT")
    result = evaluate_upgrade_closure(
        complete_context(gate_candidate_bindings=bindings)
    )
    assert result.decision is UpgradeDecision.ESCALATE
    assert result.reasons == ("FINAL_REAUDIT_BINDING_UNKNOWN",)


def test_rejected_finding_without_evidence_cannot_close():
    result = evaluate_upgrade_closure(
        complete_context(
            findings={
                "F-1": FindingRecord(FindingClass.MATERIAL, FindingDisposition.REJECTED_WITH_EVIDENCE)
            }
        )
    )
    assert result.decision is UpgradeDecision.HOLD
    assert result.reasons == ("FINDING_EVIDENCE_MISSING:F-1",)


def test_deferred_finding_requires_owner_and_reopen_condition():
    result = evaluate_upgrade_closure(
        complete_context(
            findings={
                "F-1": FindingRecord(
                    FindingClass.MATERIAL,
                    FindingDisposition.DEFERRED_WITH_OWNER_CONDITION,
                    owner="Engine.Proof",
                )
            }
        )
    )
    assert result.decision is UpgradeDecision.HOLD
    assert result.reasons == ("FINDING_REOPEN_CONDITION_MISSING:F-1",)


def test_escalated_finding_requires_explicit_target():
    result = evaluate_upgrade_closure(
        complete_context(
            findings={"F-1": FindingRecord(FindingClass.MATERIAL, FindingDisposition.ESCALATED)}
        )
    )
    assert result.decision is UpgradeDecision.HOLD
    assert result.reasons == ("FINDING_ESCALATION_TARGET_MISSING:F-1",)


def test_narrow_search_scope_cannot_close_broader_audit_scope():
    result = evaluate_upgrade_closure(
        complete_context(search_coverage_scope_sha256="dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd")
    )
    assert result.decision is UpgradeDecision.HOLD
    assert result.reasons == ("SEARCH_COVERAGE_SCOPE_MISMATCH",)


def test_candidate_hash_must_be_real_sha256_shape():
    result = evaluate_upgrade_closure(
        complete_context(candidate_sha256="not-a-hash")
    )
    assert result.decision is UpgradeDecision.HOLD
    assert result.reasons == ("CANDIDATE_HASH_INVALID",)


def test_hard_gate_finding_cannot_be_deferred_and_still_close():
    result = evaluate_upgrade_closure(
        complete_context(
            findings={
                "F-HARD": FindingRecord(
                    FindingClass.HARD_GATE,
                    FindingDisposition.DEFERRED_WITH_OWNER_CONDITION,
                    owner="Engine.Rights",
                    reopen_condition="rights proof becomes available",
                )
            }
        )
    )
    assert result.decision is UpgradeDecision.HOLD
    assert result.reasons == ("HARD_GATE_FINDING_UNRESOLVED:F-HARD",)


def test_hard_gate_finding_cannot_be_escalated_and_still_close():
    result = evaluate_upgrade_closure(
        complete_context(
            findings={
                "F-HARD": FindingRecord(
                    FindingClass.HARD_GATE,
                    FindingDisposition.ESCALATED,
                    escalation_target="human-constitutional-process",
                )
            }
        )
    )
    assert result.decision is UpgradeDecision.HOLD
    assert result.reasons == ("HARD_GATE_FINDING_UNRESOLVED:F-HARD",)


def test_unvalidated_finding_classification_blocks_closure():
    result = evaluate_upgrade_closure(
        complete_context(finding_classification_validated=None)
    )
    assert result.decision is UpgradeDecision.ESCALATE
    assert result.reasons == ("FINDING_CLASSIFICATION_UNKNOWN",)


def test_protected_surface_scan_is_candidate_bound():
    ctx = complete_context()
    bindings = dict(ctx.gate_candidate_bindings)
    bindings["PROTECTED_SURFACE_SCAN"] = "b" * 64
    result = evaluate_upgrade_closure(
        complete_context(gate_candidate_bindings=bindings)
    )
    assert result.decision is UpgradeDecision.HOLD
    assert result.reasons == ("PROTECTED_SURFACE_SCAN_BINDING_MISMATCH",)


def test_upgrade_cycle_requires_real_resource_bounds_and_residual_debt_record():
    result = evaluate_upgrade_closure(
        complete_context(max_iterations=0)
    )
    assert result.decision is UpgradeDecision.HOLD
    assert result.reasons == ("UPGRADE_ITERATION_BOUND_MISSING",)
