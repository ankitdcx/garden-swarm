from prototype.upgrade_process import (
    FindingDisposition,
    UpgradeContext,
    UpgradeDecision,
    evaluate_upgrade_closure,
)


def complete_context(**overrides):
    candidate_hash = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    values = dict(
        candidate_sha256=candidate_hash,
        gate_candidate_bindings={
            "SEARCH_COVERAGE": candidate_hash,
            "PROPAGATION_CLOSURE": candidate_hash,
            "TESTS": candidate_hash,
            "RETENTION_NO_LOSS": candidate_hash,
            "VERIFICATION_INDEPENDENCE": candidate_hash,
            "INDEPENDENT_REVIEW": candidate_hash,
            "PROTECTED_AUTHORIZATION": candidate_hash,
            "FINAL_REAUDIT": candidate_hash,
        },
        audited_scope_declared=True,
        search_coverage_complete=True,
        finding_dispositions={
            "F-1": FindingDisposition.FIXED,
            "F-2": FindingDisposition.REJECTED_WITH_EVIDENCE,
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
            finding_dispositions={"F-1": FindingDisposition.OPEN},
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
            finding_dispositions={},
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
