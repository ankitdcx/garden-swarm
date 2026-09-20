from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping, Optional


class TransitionStage(str, Enum):
    SHADOW = "SHADOW"
    PARALLEL = "PARALLEL"
    BOUNDED_ACTIVE = "BOUNDED_ACTIVE"
    EXPANDED_ACTIVE = "EXPANDED_ACTIVE"
    STABLE_OPERATION = "STABLE_OPERATION"


class TransitionDecision(str, Enum):
    ADVANCE = "ADVANCE"
    HOLD = "HOLD"
    REJECT = "REJECT"
    ROLLBACK = "ROLLBACK"
    COMPENSATE = "COMPENSATE"
    ESCALATE = "ESCALATE"


@dataclass(frozen=True)
class TransitionProposal:
    transition_id: str
    current_stage: TransitionStage
    next_stage: TransitionStage
    declared_stage_plan: tuple[TransitionStage, ...]
    effect_scope: str
    reversible_effect: bool = True


@dataclass
class TransitionContext:
    authority_validated: Optional[bool]
    hard_gates: Mapping[str, Optional[bool]] = field(default_factory=dict)
    required_hard_gates: frozenset[str] = frozenset(
        {"rights", "consent", "privacy", "law", "safety", "human_effect"}
    )
    independent_verification: Optional[bool] = None
    divergence_resolved: Optional[bool] = None
    capture_conflict_clear: Optional[bool] = None
    operational_readiness: Optional[bool] = None
    entry_criteria: Mapping[str, Optional[bool]] = field(default_factory=dict)
    exit_criteria: Mapping[str, Optional[bool]] = field(default_factory=dict)
    rollback_ready: Optional[bool] = None
    compensation_recovery_ready: Optional[bool] = None
    material_dispute_open: bool = False
    dispute_path_ready: Optional[bool] = None
    dispute_separable_from_effect_scope: Optional[bool] = None


@dataclass(frozen=True)
class TransitionResult:
    decision: TransitionDecision
    reasons: tuple[str, ...]
    authority_created: bool = False


def _criteria_result(prefix: str, values: Mapping[str, Optional[bool]]) -> TransitionResult | None:
    failed = sorted(name for name, value in values.items() if value is False)
    if failed:
        return TransitionResult(
            TransitionDecision.HOLD,
            tuple(f"{prefix}_FAILED:{name}" for name in failed),
        )
    unknown = sorted(name for name, value in values.items() if value is not True)
    if unknown:
        return TransitionResult(
            TransitionDecision.ESCALATE,
            tuple(f"{prefix}_UNKNOWN:{name}" for name in unknown),
        )
    return None


def evaluate_transition(
    proposal: TransitionProposal, context: TransitionContext
) -> TransitionResult:
    """Evaluate one requested GTF stage advancement.

    This is a narrow executable reference for the existing Engine.Transition/GTF
    owner. It grants no authority. Stage advancement requires fresh validated
    authority plus the applicable rights, Human-Effect Closure, assurance,
    independence, divergence, capture, readiness and recovery checks.
    """

    plan = proposal.declared_stage_plan
    if not plan or len(plan) != len(set(plan)):
        return TransitionResult(
            TransitionDecision.REJECT, ("INVALID_DECLARED_STAGE_PLAN",)
        )

    try:
        current_index = plan.index(proposal.current_stage)
    except ValueError:
        return TransitionResult(
            TransitionDecision.REJECT, ("CURRENT_STAGE_NOT_IN_DECLARED_PLAN",)
        )

    if current_index + 1 >= len(plan) or plan[current_index + 1] is not proposal.next_stage:
        return TransitionResult(
            TransitionDecision.REJECT, ("DECLARED_STAGE_SKIP_OR_INVALID_NEXT_STAGE",)
        )

    if context.authority_validated is False:
        return TransitionResult(
            TransitionDecision.REJECT, ("TRANSITION_AUTHORITY_INVALID",)
        )
    if context.authority_validated is not True:
        return TransitionResult(
            TransitionDecision.ESCALATE, ("TRANSITION_AUTHORITY_UNKNOWN",)
        )

    failed_gates = sorted(
        gate
        for gate in context.required_hard_gates
        if context.hard_gates.get(gate) is False
    )
    if failed_gates:
        return TransitionResult(
            TransitionDecision.REJECT,
            tuple(f"TRANSITION_HARD_GATE_FAILED:{gate}" for gate in failed_gates),
        )

    unknown_gates = sorted(
        gate
        for gate in context.required_hard_gates
        if context.hard_gates.get(gate) is not True
        and context.hard_gates.get(gate) is not False
    )
    if unknown_gates:
        return TransitionResult(
            TransitionDecision.ESCALATE,
            tuple(f"TRANSITION_HARD_GATE_UNKNOWN:{gate}" for gate in unknown_gates),
        )

    if context.independent_verification is False:
        return TransitionResult(
            TransitionDecision.HOLD, ("INDEPENDENT_VERIFICATION_FAILED",)
        )
    if context.independent_verification is not True:
        return TransitionResult(
            TransitionDecision.ESCALATE, ("INDEPENDENT_VERIFICATION_UNKNOWN",)
        )

    if context.capture_conflict_clear is False:
        return TransitionResult(
            TransitionDecision.HOLD, ("CAPTURE_OR_CONFLICT_CHECK_FAILED",)
        )
    if context.capture_conflict_clear is not True:
        return TransitionResult(
            TransitionDecision.ESCALATE, ("CAPTURE_OR_CONFLICT_CHECK_UNKNOWN",)
        )

    if context.operational_readiness is False:
        return TransitionResult(TransitionDecision.HOLD, ("OPERATIONAL_READINESS_FAILED",))
    if context.operational_readiness is not True:
        return TransitionResult(
            TransitionDecision.ESCALATE, ("OPERATIONAL_READINESS_UNKNOWN",)
        )

    entry = _criteria_result("ENTRY_CRITERION", context.entry_criteria)
    if entry is not None:
        return entry

    exit_result = _criteria_result("EXIT_CRITERION", context.exit_criteria)
    if exit_result is not None:
        return exit_result

    divergence_required = proposal.next_stage in {
        TransitionStage.BOUNDED_ACTIVE,
        TransitionStage.EXPANDED_ACTIVE,
        TransitionStage.STABLE_OPERATION,
    }
    if divergence_required:
        if context.divergence_resolved is False:
            return TransitionResult(
                TransitionDecision.HOLD, ("MATERIAL_DIVERGENCE_UNRESOLVED",)
            )
        if context.divergence_resolved is not True:
            return TransitionResult(
                TransitionDecision.ESCALATE, ("DIVERGENCE_STATUS_UNKNOWN",)
            )

    if context.material_dispute_open:
        if context.dispute_path_ready is False:
            return TransitionResult(
                TransitionDecision.HOLD, ("MATERIAL_DISPUTE_PATH_NOT_READY",)
            )
        if context.dispute_path_ready is not True:
            return TransitionResult(
                TransitionDecision.ESCALATE, ("MATERIAL_DISPUTE_PATH_UNKNOWN",)
            )
        if context.dispute_separable_from_effect_scope is False:
            return TransitionResult(
                TransitionDecision.HOLD, ("MATERIAL_DISPUTE_BLOCKS_EFFECT_SCOPE",)
            )
        if context.dispute_separable_from_effect_scope is not True:
            return TransitionResult(
                TransitionDecision.ESCALATE, ("DISPUTE_SEPARABILITY_UNKNOWN",)
            )

    if proposal.reversible_effect:
        if context.rollback_ready is False:
            return TransitionResult(TransitionDecision.HOLD, ("ROLLBACK_NOT_READY",))
        if context.rollback_ready is not True:
            return TransitionResult(
                TransitionDecision.ESCALATE, ("ROLLBACK_READINESS_UNKNOWN",)
            )
    else:
        if context.compensation_recovery_ready is False:
            return TransitionResult(
                TransitionDecision.HOLD,
                ("IRREVERSIBLE_EFFECT_RECOVERY_NOT_READY",),
            )
        if context.compensation_recovery_ready is not True:
            return TransitionResult(
                TransitionDecision.ESCALATE,
                ("IRREVERSIBLE_EFFECT_RECOVERY_UNKNOWN",),
            )

    return TransitionResult(
        TransitionDecision.ADVANCE,
        (
            "DECLARED_NEXT_STAGE_ONLY",
            "FRESH_AUTHORITY_AND_HARD_GATES_PASS",
            "INDEPENDENT_VERIFICATION_AND_CAPTURE_CHECK_PASS",
            "NO_AUTHORITY_CREATED_BY_STAGE_ADVANCEMENT",
        ),
    )
