from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping, Optional


class FindingDisposition(str, Enum):
    FIXED = "FIXED"
    REJECTED_WITH_EVIDENCE = "REJECTED_WITH_EVIDENCE"
    DEFERRED_WITH_OWNER_CONDITION = "DEFERRED_WITH_OWNER_CONDITION"
    ESCALATED = "ESCALATED"
    OPEN = "OPEN"


class UpgradeDecision(str, Enum):
    CLOSE_CANDIDATE = "CLOSE_CANDIDATE"
    CONTINUE_WORK = "CONTINUE_WORK"
    HOLD = "HOLD"
    ESCALATE = "ESCALATE"


@dataclass
class UpgradeContext:
    finding_dispositions: Mapping[str, FindingDisposition] = field(default_factory=dict)
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


@dataclass(frozen=True)
class UpgradeResult:
    decision: UpgradeDecision
    reasons: tuple[str, ...]
    authority_created: bool = False


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


def evaluate_upgrade_closure(context: UpgradeContext) -> UpgradeResult:
    """Evaluate whether an AI-led Garden upgrade may claim candidate closure.

    This checker does not merge, canonize, authorize deployment, or create
    constitutional authority. It only evaluates the declared closure conditions.
    """

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

    open_findings = sorted(
        finding_id
        for finding_id, disposition in context.finding_dispositions.items()
        if disposition is FindingDisposition.OPEN
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

    tests = _typed_gate(
        "TESTS",
        context.tests_pass,
        false_decision=UpgradeDecision.CONTINUE_WORK,
    )
    if tests is not None:
        return tests

    retention = _typed_gate(
        "RETENTION_NO_LOSS",
        context.retention_no_loss_pass,
        false_decision=UpgradeDecision.HOLD,
    )
    if retention is not None:
        return retention

    independence = _typed_gate(
        "VERIFICATION_INDEPENDENCE",
        context.verification_independence_pass,
        false_decision=UpgradeDecision.HOLD,
    )
    if independence is not None:
        return independence

    if context.independent_review_required:
        review = _typed_gate(
            "INDEPENDENT_REVIEW",
            context.independent_review_pass,
            false_decision=UpgradeDecision.HOLD,
        )
        if review is not None:
            return review

    if context.protected_change:
        protected = _typed_gate(
            "PROTECTED_AUTHORIZATION",
            context.protected_authorization_pass,
            false_decision=UpgradeDecision.HOLD,
        )
        if protected is not None:
            return protected

    reaudit = _typed_gate(
        "FINAL_REAUDIT",
        context.final_reaudit_complete,
        false_decision=UpgradeDecision.CONTINUE_WORK,
    )
    if reaudit is not None:
        return reaudit

    return UpgradeResult(
        UpgradeDecision.CLOSE_CANDIDATE,
        (
            "ALL_MATERIAL_FINDINGS_DISPOSED",
            "PROPAGATION_TEST_RETENTION_AND_REAUDIT_PASS",
            "REQUIRED_INDEPENDENCE_PASS",
            "CANDIDATE_CLOSURE_ONLY_NO_AUTHORITY_CREATED",
        ),
    )
