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


STANDARD_TRANSITION_PLAN = (
    TransitionStage.SHADOW,
    TransitionStage.PARALLEL,
    TransitionStage.BOUNDED_ACTIVE,
    TransitionStage.EXPANDED_ACTIVE,
    TransitionStage.STABLE_OPERATION,
)

BASE_TRANSITION_HARD_GATES = frozenset(
    {"rights", "consent", "privacy", "law", "safety", "human_effect"}
)


@dataclass(frozen=True)
class TransitionAssuranceBinding:
    purpose: str
    transition_id: str
    effect_scope: str
    current_stage: TransitionStage
    target_stage: TransitionStage
    design_epoch: str


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
    design_epoch: str = "E1"
    reversible_effect: bool = True
    stage_omission_justifications: Mapping[TransitionStage, str] = field(default_factory=dict)


@dataclass
class TransitionContext:
    authority_validated: Optional[bool]
    assurance_binding: Optional[TransitionAssuranceBinding] = None
    current_design_epoch: str = "E1"
    hard_gates: Mapping[str, Optional[bool]] = field(default_factory=dict)
    required_hard_gates: frozenset[str] = frozenset()
    stage_omission_approval: Mapping[TransitionStage, Optional[bool]] = field(default_factory=dict)
    independent_verification: Optional[bool] = None
    divergence_resolved: Optional[bool] = None
    capture_conflict_clear: Optional[bool] = None
    operational_readiness: Optional[bool] = None
    entry_criteria: Mapping[str, Optional[bool]] = field(default_factory=dict)
    exit_criteria: Mapping[str, Optional[bool]] = field(default_factory=dict)
    rollback_ready: Optional[bool] = None
    compensation_recovery_ready: Optional[bool] = None
    material_dispute_open: bool = False
    last_qualified_stage: Optional[TransitionStage] = None
    dispute_path_ready: Optional[bool] = None
    dispute_separable_from_effect_scope: Optional[bool] = None


@dataclass(frozen=True)
class TransitionResult:
    decision: TransitionDecision
    reasons: tuple[str, ...]
    authority_created: bool = False




def _assurance_binding_result(
    *,
    purpose: str,
    transition_id: str,
    effect_scope: str,
    current_stage: TransitionStage,
    target_stage: TransitionStage,
    design_epoch: str,
    context: TransitionContext,
) -> TransitionResult | None:
    binding = context.assurance_binding
    prefix = "TRANSITION" if purpose == "ADVANCE" else "RECOVERY"
    if binding is None:
        return TransitionResult(
            TransitionDecision.ESCALATE,
            (f"{prefix}_ASSURANCE_BINDING_UNKNOWN",),
        )
    if (
        binding.purpose != purpose
        or binding.transition_id != transition_id
        or binding.effect_scope != effect_scope
        or binding.current_stage is not current_stage
        or binding.target_stage is not target_stage
        or binding.design_epoch != design_epoch
    ):
        return TransitionResult(
            TransitionDecision.REJECT,
            (f"{prefix}_ASSURANCE_BINDING_MISMATCH",),
        )
    return None

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

    ordered_projection = tuple(stage for stage in STANDARD_TRANSITION_PLAN if stage in plan)
    if ordered_projection != plan:
        return TransitionResult(
            TransitionDecision.REJECT, ("INVALID_DECLARED_STAGE_ORDER",)
        )

    omitted_stages = tuple(stage for stage in STANDARD_TRANSITION_PLAN if stage not in plan)
    for stage in omitted_stages:
        justification = proposal.stage_omission_justifications.get(stage, "").strip()
        if not justification:
            return TransitionResult(
                TransitionDecision.REJECT,
                (f"STAGE_OMISSION_UNJUSTIFIED:{stage.value}",),
            )
        approval = context.stage_omission_approval.get(stage)
        if approval is False:
            return TransitionResult(
                TransitionDecision.HOLD,
                (f"STAGE_OMISSION_NOT_APPROVED:{stage.value}",),
            )
        if approval is not True:
            return TransitionResult(
                TransitionDecision.ESCALATE,
                (f"STAGE_OMISSION_APPROVAL_UNKNOWN:{stage.value}",),
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

    if proposal.design_epoch != context.current_design_epoch:
        return TransitionResult(
            TransitionDecision.REJECT, ("STALE_TRANSITION_DESIGN_EPOCH",)
        )

    assurance_binding = _assurance_binding_result(
        purpose="ADVANCE",
        transition_id=proposal.transition_id,
        effect_scope=proposal.effect_scope,
        current_stage=proposal.current_stage,
        target_stage=proposal.next_stage,
        design_epoch=proposal.design_epoch,
        context=context,
    )
    if assurance_binding is not None:
        return assurance_binding

    if context.authority_validated is False:
        return TransitionResult(
            TransitionDecision.REJECT, ("TRANSITION_AUTHORITY_INVALID",)
        )
    if context.authority_validated is not True:
        return TransitionResult(
            TransitionDecision.ESCALATE, ("TRANSITION_AUTHORITY_UNKNOWN",)
        )

    required_hard_gates = BASE_TRANSITION_HARD_GATES | context.required_hard_gates
    failed_gates = sorted(
        gate
        for gate in required_hard_gates
        if context.hard_gates.get(gate) is False
    )
    if failed_gates:
        return TransitionResult(
            TransitionDecision.REJECT,
            tuple(f"TRANSITION_HARD_GATE_FAILED:{gate}" for gate in failed_gates),
        )

    unknown_gates = sorted(
        gate
        for gate in required_hard_gates
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

    if not context.entry_criteria:
        return TransitionResult(
            TransitionDecision.ESCALATE, ("ENTRY_CRITERIA_MISSING",)
        )
    if not context.exit_criteria:
        return TransitionResult(
            TransitionDecision.ESCALATE, ("EXIT_CRITERIA_MISSING",)
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



@dataclass(frozen=True)
class RecoveryProposal:
    transition_id: str
    current_stage: TransitionStage
    target_stage: TransitionStage
    effect_scope: str
    reversible_effect: bool
    material_failure_confirmed: Optional[bool]
    design_epoch: str = "E1"


def evaluate_recovery(
    proposal: RecoveryProposal, context: TransitionContext
) -> TransitionResult:
    """Evaluate post-commit rollback or compensation without minting authority."""

    if proposal.material_failure_confirmed is False:
        return TransitionResult(
            TransitionDecision.REJECT, ("RECOVERY_TRIGGER_NOT_ESTABLISHED",)
        )
    if proposal.material_failure_confirmed is not True:
        return TransitionResult(
            TransitionDecision.ESCALATE, ("RECOVERY_TRIGGER_UNKNOWN",)
        )

    if proposal.design_epoch != context.current_design_epoch:
        return TransitionResult(
            TransitionDecision.REJECT, ("RECOVERY_STALE_DESIGN_EPOCH",)
        )

    assurance_binding = _assurance_binding_result(
        purpose="RECOVERY",
        transition_id=proposal.transition_id,
        effect_scope=proposal.effect_scope,
        current_stage=proposal.current_stage,
        target_stage=proposal.target_stage,
        design_epoch=proposal.design_epoch,
        context=context,
    )
    if assurance_binding is not None:
        return assurance_binding

    if context.authority_validated is False:
        return TransitionResult(
            TransitionDecision.REJECT, ("RECOVERY_AUTHORITY_INVALID",)
        )
    if context.authority_validated is not True:
        return TransitionResult(
            TransitionDecision.ESCALATE, ("RECOVERY_AUTHORITY_UNKNOWN",)
        )

    required_hard_gates = BASE_TRANSITION_HARD_GATES | context.required_hard_gates
    failed_gates = sorted(
        gate for gate in required_hard_gates if context.hard_gates.get(gate) is False
    )
    if failed_gates:
        return TransitionResult(
            TransitionDecision.REJECT,
            tuple(f"RECOVERY_HARD_GATE_FAILED:{gate}" for gate in failed_gates),
        )
    unknown_gates = sorted(
        gate
        for gate in required_hard_gates
        if context.hard_gates.get(gate) is not True
        and context.hard_gates.get(gate) is not False
    )
    if unknown_gates:
        return TransitionResult(
            TransitionDecision.ESCALATE,
            tuple(f"RECOVERY_HARD_GATE_UNKNOWN:{gate}" for gate in unknown_gates),
        )

    if context.independent_verification is False:
        return TransitionResult(
            TransitionDecision.HOLD, ("RECOVERY_INDEPENDENT_VERIFICATION_FAILED",)
        )
    if context.independent_verification is not True:
        return TransitionResult(
            TransitionDecision.ESCALATE,
            ("RECOVERY_INDEPENDENT_VERIFICATION_UNKNOWN",),
        )

    if context.capture_conflict_clear is False:
        return TransitionResult(
            TransitionDecision.HOLD, ("RECOVERY_CAPTURE_OR_CONFLICT_CHECK_FAILED",)
        )
    if context.capture_conflict_clear is not True:
        return TransitionResult(
            TransitionDecision.ESCALATE,
            ("RECOVERY_CAPTURE_OR_CONFLICT_CHECK_UNKNOWN",),
        )

    if proposal.reversible_effect:
        try:
            current_index = STANDARD_TRANSITION_PLAN.index(proposal.current_stage)
            target_index = STANDARD_TRANSITION_PLAN.index(proposal.target_stage)
        except ValueError:
            return TransitionResult(
                TransitionDecision.REJECT, ("RECOVERY_STAGE_UNKNOWN",)
            )
        if target_index >= current_index:
            return TransitionResult(
                TransitionDecision.REJECT, ("ROLLBACK_TARGET_NOT_EARLIER",)
            )
        if context.last_qualified_stage is None:
            return TransitionResult(
                TransitionDecision.ESCALATE, ("LAST_QUALIFIED_STAGE_UNKNOWN",)
            )
        if proposal.target_stage is not context.last_qualified_stage:
            return TransitionResult(
                TransitionDecision.REJECT, ("ROLLBACK_TARGET_NOT_LAST_QUALIFIED",)
            )
        if context.rollback_ready is False:
            return TransitionResult(
                TransitionDecision.HOLD, ("ROLLBACK_NOT_READY",)
            )
        if context.rollback_ready is not True:
            return TransitionResult(
                TransitionDecision.ESCALATE, ("ROLLBACK_READINESS_UNKNOWN",)
            )
        return TransitionResult(
            TransitionDecision.ROLLBACK,
            (
                "MATERIAL_FAILURE_CONFIRMED",
                "FRESH_RECOVERY_ADMISSION_PASS",
                "ROLLBACK_TO_EARLIER_STAGE",
                "NO_AUTHORITY_CREATED_BY_RECOVERY",
            ),
        )

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
        TransitionDecision.COMPENSATE,
        (
            "MATERIAL_FAILURE_CONFIRMED",
            "FRESH_RECOVERY_ADMISSION_PASS",
            "IRREVERSIBLE_EFFECT_USES_COMPENSATION_OR_RECOVERY",
            "NO_AUTHORITY_CREATED_BY_RECOVERY",
        ),
    )
