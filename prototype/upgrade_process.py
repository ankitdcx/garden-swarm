from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping, Optional
import re


class FindingClass(str, Enum):
    ROUTINE = "ROUTINE"
    MATERIAL = "MATERIAL"
    HARD_GATE = "HARD_GATE"
    PROTECTED = "PROTECTED"


class FindingDisposition(str, Enum):
    FIXED = "FIXED"
    REJECTED_WITH_EVIDENCE = "REJECTED_WITH_EVIDENCE"
    DEFERRED_WITH_OWNER_CONDITION = "DEFERRED_WITH_OWNER_CONDITION"
    ESCALATED = "ESCALATED"
    OPEN = "OPEN"


@dataclass(frozen=True)
class FindingRecord:
    finding_class: FindingClass
    disposition: FindingDisposition
    evidence_refs: tuple[str, ...] = ()
    owner: str | None = None
    reopen_condition: str | None = None
    escalation_target: str | None = None


class UpgradeDecision(str, Enum):
    CLOSE_CANDIDATE = "CLOSE_CANDIDATE"
    CONTINUE_WORK = "CONTINUE_WORK"
    HOLD = "HOLD"
    ESCALATE = "ESCALATE"


@dataclass
class UpgradeContext:
    candidate_sha256: str = ""
    audited_scope_sha256: str = ""
    search_coverage_scope_sha256: str = ""
    gate_candidate_bindings: Mapping[str, str] = field(default_factory=dict)
    findings: Mapping[str, FindingRecord] = field(default_factory=dict)
    audited_scope_declared: bool = False
    search_coverage_complete: Optional[bool] = None
    bounded_cycle_declared: bool = False
    upgrade_methods_authorized: Optional[bool] = None
    propagation_complete: Optional[bool] = None
    tests_pass: Optional[bool] = None
    retention_no_loss_pass: Optional[bool] = None
    independent_review_required: bool = False
    independent_review_pass: Optional[bool] = None
    verification_independence_pass: Optional[bool] = None
    protected_change: bool = False
    protected_authorization_pass: Optional[bool] = None
    final_reaudit_complete: Optional[bool] = None
    finding_classification_validated: Optional[bool] = None
    finding_classification_independent: Optional[bool] = None
    protected_surface_scan_pass: Optional[bool] = None
    protected_surface_scan_independent: Optional[bool] = None
    max_iterations: int = 0
    max_work_items: int = 0
    residual_debt_recorded: bool = False


@dataclass(frozen=True)
class UpgradeResult:
    decision: UpgradeDecision
    reasons: tuple[str, ...]
    authority_created: bool = False



def _is_sha256(value: str) -> bool:
    return re.fullmatch(r"[0-9a-f]{64}", value.strip().lower()) is not None


def _typed_gate(
    name: str,
    value: Optional[bool],
    *,
    false_decision: UpgradeDecision,
) -> UpgradeResult | None:
    if value is False:
        return UpgradeResult(false_decision, (f"{name}_FAILED",))
    if value is not True:
        return UpgradeResult(UpgradeDecision.ESCALATE, (f"{name}_UNKNOWN",))
    return None




def _candidate_binding_gate(
    gate_name: str, context: UpgradeContext
) -> UpgradeResult | None:
    expected = context.candidate_sha256.strip()
    if not expected:
        return UpgradeResult(
            UpgradeDecision.HOLD,
            ("CANDIDATE_HASH_MISSING",),
        )
    actual = context.gate_candidate_bindings.get(gate_name)
    if actual is None:
        return UpgradeResult(
            UpgradeDecision.ESCALATE,
            (f"{gate_name}_BINDING_UNKNOWN",),
        )
    if actual != expected:
        return UpgradeResult(
            UpgradeDecision.HOLD,
            (f"{gate_name}_BINDING_MISMATCH",),
        )
    return None

def evaluate_upgrade_closure(context: UpgradeContext) -> UpgradeResult:
    """Evaluate whether an AI-led Garden upgrade may claim candidate closure.

    This checker does not merge, canonize, authorize deployment, or create
    constitutional authority. It only evaluates the declared closure conditions.
    """

    if not context.audited_scope_declared:
        return UpgradeResult(
            UpgradeDecision.HOLD,
            ("AUDITED_SCOPE_NOT_DECLARED",),
        )

    if not _is_sha256(context.candidate_sha256):
        return UpgradeResult(
            UpgradeDecision.HOLD,
            ("CANDIDATE_HASH_INVALID",),
        )
    if not _is_sha256(context.audited_scope_sha256):
        return UpgradeResult(
            UpgradeDecision.HOLD,
            ("AUDITED_SCOPE_HASH_INVALID",),
        )
    if not _is_sha256(context.search_coverage_scope_sha256):
        return UpgradeResult(
            UpgradeDecision.ESCALATE,
            ("SEARCH_COVERAGE_SCOPE_HASH_UNKNOWN",),
        )
    if context.search_coverage_scope_sha256 != context.audited_scope_sha256:
        return UpgradeResult(
            UpgradeDecision.HOLD,
            ("SEARCH_COVERAGE_SCOPE_MISMATCH",),
        )

    coverage = _typed_gate(
        "SEARCH_COVERAGE",
        context.search_coverage_complete,
        false_decision=UpgradeDecision.CONTINUE_WORK,
    )
    if coverage is not None:
        return coverage

    search_coverage_binding = _candidate_binding_gate("SEARCH_COVERAGE", context)
    if search_coverage_binding is not None:
        return search_coverage_binding

    if not context.bounded_cycle_declared:
        return UpgradeResult(
            UpgradeDecision.HOLD,
            ("BOUNDED_UPGRADE_CYCLE_NOT_DECLARED",),
        )

    methods = _typed_gate(
        "UPGRADE_METHOD_AUTHORITY",
        context.upgrade_methods_authorized,
        false_decision=UpgradeDecision.HOLD,
    )
    if methods is not None:
        return methods

    classification = _typed_gate(
        "FINDING_CLASSIFICATION",
        context.finding_classification_validated,
        false_decision=UpgradeDecision.HOLD,
    )
    if classification is not None:
        return classification
    classification_binding = _candidate_binding_gate(
        "FINDING_CLASSIFICATION", context
    )
    if classification_binding is not None:
        return classification_binding

    classification_independence = _typed_gate(
        "FINDING_CLASSIFICATION_INDEPENDENCE",
        context.finding_classification_independent,
        false_decision=UpgradeDecision.HOLD,
    )
    if classification_independence is not None:
        return classification_independence
    classification_independence_binding = _candidate_binding_gate(
        "FINDING_CLASSIFICATION_INDEPENDENCE", context
    )
    if classification_independence_binding is not None:
        return classification_independence_binding

    protected_scan = _typed_gate(
        "PROTECTED_SURFACE_SCAN",
        context.protected_surface_scan_pass,
        false_decision=UpgradeDecision.HOLD,
    )
    if protected_scan is not None:
        return protected_scan
    protected_scan_binding = _candidate_binding_gate(
        "PROTECTED_SURFACE_SCAN", context
    )
    if protected_scan_binding is not None:
        return protected_scan_binding

    protected_scan_independence = _typed_gate(
        "PROTECTED_SURFACE_SCAN_INDEPENDENCE",
        context.protected_surface_scan_independent,
        false_decision=UpgradeDecision.HOLD,
    )
    if protected_scan_independence is not None:
        return protected_scan_independence
    protected_scan_independence_binding = _candidate_binding_gate(
        "PROTECTED_SURFACE_SCAN_INDEPENDENCE", context
    )
    if protected_scan_independence_binding is not None:
        return protected_scan_independence_binding

    if context.max_iterations <= 0:
        return UpgradeResult(
            UpgradeDecision.HOLD,
            ("UPGRADE_ITERATION_BOUND_MISSING",),
        )
    if context.max_work_items <= 0:
        return UpgradeResult(
            UpgradeDecision.HOLD,
            ("UPGRADE_WORK_ITEM_BOUND_MISSING",),
        )
    if not context.residual_debt_recorded:
        return UpgradeResult(
            UpgradeDecision.HOLD,
            ("RESIDUAL_DEBT_RECORD_MISSING",),
        )

    for finding_id, record in sorted(context.findings.items()):
        if (
            record.finding_class in {FindingClass.HARD_GATE, FindingClass.PROTECTED}
            and record.disposition
            in {
                FindingDisposition.DEFERRED_WITH_OWNER_CONDITION,
                FindingDisposition.ESCALATED,
                FindingDisposition.OPEN,
            }
        ):
            return UpgradeResult(
                UpgradeDecision.HOLD,
                (f"BLOCKING_FINDING_UNRESOLVED:{finding_id}",),
            )
        if record.disposition in {
            FindingDisposition.FIXED,
            FindingDisposition.REJECTED_WITH_EVIDENCE,
        } and not record.evidence_refs:
            return UpgradeResult(
                UpgradeDecision.HOLD,
                (f"FINDING_EVIDENCE_MISSING:{finding_id}",),
            )
        if record.disposition is FindingDisposition.DEFERRED_WITH_OWNER_CONDITION:
            if not (record.owner or "").strip():
                return UpgradeResult(
                    UpgradeDecision.HOLD,
                    (f"FINDING_DEFERRED_OWNER_MISSING:{finding_id}",),
                )
            if not (record.reopen_condition or "").strip():
                return UpgradeResult(
                    UpgradeDecision.HOLD,
                    (f"FINDING_REOPEN_CONDITION_MISSING:{finding_id}",),
                )
        if record.disposition is FindingDisposition.ESCALATED and not (
            record.escalation_target or ""
        ).strip():
            return UpgradeResult(
                UpgradeDecision.HOLD,
                (f"FINDING_ESCALATION_TARGET_MISSING:{finding_id}",),
            )

    open_findings = sorted(
        finding_id
        for finding_id, record in context.findings.items()
        if record.disposition is FindingDisposition.OPEN
    )
    if open_findings:
        return UpgradeResult(
            UpgradeDecision.CONTINUE_WORK,
            tuple(f"MATERIAL_FINDING_OPEN:{finding_id}" for finding_id in open_findings),
        )

    propagation = _typed_gate(
        "PROPAGATION_CLOSURE",
        context.propagation_complete,
        false_decision=UpgradeDecision.CONTINUE_WORK,
    )
    if propagation is not None:
        return propagation

    propagation_closure_binding = _candidate_binding_gate("PROPAGATION_CLOSURE", context)
    if propagation_closure_binding is not None:
        return propagation_closure_binding

    tests = _typed_gate(
        "TESTS",
        context.tests_pass,
        false_decision=UpgradeDecision.CONTINUE_WORK,
    )
    if tests is not None:
        return tests

    tests_binding = _candidate_binding_gate("TESTS", context)
    if tests_binding is not None:
        return tests_binding

    retention = _typed_gate(
        "RETENTION_NO_LOSS",
        context.retention_no_loss_pass,
        false_decision=UpgradeDecision.HOLD,
    )
    if retention is not None:
        return retention

    retention_no_loss_binding = _candidate_binding_gate("RETENTION_NO_LOSS", context)
    if retention_no_loss_binding is not None:
        return retention_no_loss_binding

    independence = _typed_gate(
        "VERIFICATION_INDEPENDENCE",
        context.verification_independence_pass,
        false_decision=UpgradeDecision.HOLD,
    )
    if independence is not None:
        return independence

    verification_independence_binding = _candidate_binding_gate("VERIFICATION_INDEPENDENCE", context)
    if verification_independence_binding is not None:
        return verification_independence_binding

    if context.independent_review_required:
        review = _typed_gate(
            "INDEPENDENT_REVIEW",
            context.independent_review_pass,
            false_decision=UpgradeDecision.HOLD,
        )
        if review is not None:
            return review
        review_binding = _candidate_binding_gate("INDEPENDENT_REVIEW", context)
        if review_binding is not None:
            return review_binding

    protected_finding_present = any(
        record.finding_class is FindingClass.PROTECTED
        for record in context.findings.values()
    )
    if context.protected_change or protected_finding_present:
        protected = _typed_gate(
            "PROTECTED_AUTHORIZATION",
            context.protected_authorization_pass,
            false_decision=UpgradeDecision.HOLD,
        )
        if protected is not None:
            return protected
        protected_binding = _candidate_binding_gate("PROTECTED_AUTHORIZATION", context)
        if protected_binding is not None:
            return protected_binding

    reaudit = _typed_gate(
        "FINAL_REAUDIT",
        context.final_reaudit_complete,
        false_decision=UpgradeDecision.CONTINUE_WORK,
    )
    if reaudit is not None:
        return reaudit

    final_reaudit_binding = _candidate_binding_gate("FINAL_REAUDIT", context)
    if final_reaudit_binding is not None:
        return final_reaudit_binding

    return UpgradeResult(
        UpgradeDecision.CLOSE_CANDIDATE,
        (
            "ALL_MATERIAL_FINDINGS_DISPOSED",
            "PROPAGATION_TEST_RETENTION_AND_REAUDIT_PASS",
            "REQUIRED_INDEPENDENCE_PASS",
            "CANDIDATE_CLOSURE_ONLY_NO_AUTHORITY_CREATED",
        ),
    )
