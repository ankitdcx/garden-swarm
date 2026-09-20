from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping, Optional

from prototype.authority import AuthorityEnvelope, can_execute


class ConstraintClass(str, Enum):
    GARDEN_CONSTITUTION = "GARDEN_CONSTITUTION"
    AUTHORIZED_HUMAN_INSTRUCTION = "AUTHORIZED_HUMAN_INSTRUCTION"
    OPERATOR_INSTRUCTION = "OPERATOR_INSTRUCTION"
    MODEL_SUBGOAL = "MODEL_SUBGOAL"
    EXTERNAL_RUNTIME_CONSTRAINT = "EXTERNAL_RUNTIME_CONSTRAINT"


RUNTIME_CONSTITUTION_SCHEMA = "GardenRuntimeConstitutionEnvelope/v1"

BASE_HUMAN_EFFECT_GATES = frozenset(
    {"rights", "consent", "privacy", "law", "safety", "human_effect"}
)


class InstructionAuthority(str, Enum):
    GARDEN_CONSTRAINT_ONLY = "GARDEN_CONSTRAINT_ONLY"
    DELEGATED_AUTHORITY_REQUIRED = "DELEGATED_AUTHORITY_REQUIRED"
    PROPOSAL_ONLY = "PROPOSAL_ONLY"
    EXTERNAL_ENFORCEMENT_ONLY = "EXTERNAL_ENFORCEMENT_ONLY"


class RuntimeDecision(str, Enum):
    ALLOW = "ALLOW"
    REJECT = "REJECT"
    ESCALATE = "ESCALATE"
    PROPOSAL_ONLY = "PROPOSAL_ONLY"
    EXTERNALLY_BLOCKED = "EXTERNALLY_BLOCKED"


@dataclass(frozen=True)
class RuntimeResult:
    decision: RuntimeDecision
    reasons: tuple[str, ...]
    authority_created: bool = False


@dataclass(frozen=True)
class GoalProposal:
    goal_id: str
    proposer: str
    source_class: ConstraintClass
    summary: str


@dataclass(frozen=True)
class RuntimeInstruction:
    principal: str
    actor: str
    source_class: ConstraintClass
    action: str
    target: str
    capability: str
    delegation_chain: tuple[str, ...]
    policy_epoch: str
    goal_id: str | None = None


@dataclass
class RuntimeConstitutionContext:
    current_policy_epoch: str
    capabilities_by_subject: Mapping[str, frozenset[str]]
    authority_by_subject: Mapping[str, AuthorityEnvelope] = field(default_factory=dict)
    authority_validation_by_subject: Mapping[str, Optional[bool]] = field(default_factory=dict)
    authority_provenance_by_subject: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    authority_parent_by_subject: Mapping[str, str] = field(default_factory=dict)
    revoked_authority_subjects: frozenset[str] = frozenset()
    hard_gates: Mapping[str, Optional[bool]] = field(default_factory=dict)
    high_impact_actions: frozenset[str] = frozenset()
    human_effect_materiality_by_action: Mapping[str, Optional[bool]] = field(default_factory=dict)
    required_human_effect_gates: frozenset[str] = frozenset()
    external_runtime_blocks: Mapping[str, frozenset[str]] = field(default_factory=dict)
    revoked_goal_ids: frozenset[str] = frozenset()


def classify_instruction_authority(source_class: ConstraintClass) -> InstructionAuthority:
    """Classify what an instruction source can contribute before action checks."""
    if source_class is ConstraintClass.GARDEN_CONSTITUTION:
        return InstructionAuthority.GARDEN_CONSTRAINT_ONLY
    if source_class is ConstraintClass.AUTHORIZED_HUMAN_INSTRUCTION:
        return InstructionAuthority.DELEGATED_AUTHORITY_REQUIRED
    if source_class is ConstraintClass.EXTERNAL_RUNTIME_CONSTRAINT:
        return InstructionAuthority.EXTERNAL_ENFORCEMENT_ONLY
    return InstructionAuthority.PROPOSAL_ONLY


def evaluate_goal(goal: GoalProposal, context: RuntimeConstitutionContext) -> RuntimeResult:
    """Admit a goal as planning state without minting execution authority.

    Garden allows humans or agents to propose/retain goals. Goal admission is not
    action admission. Every consequential effect still needs fresh authority and
    hard-gate checks at point of use.
    """

    if goal.goal_id in context.revoked_goal_ids:
        return RuntimeResult(RuntimeDecision.REJECT, ("GOAL_REVOKED",))

    if goal.source_class is ConstraintClass.EXTERNAL_RUNTIME_CONSTRAINT:
        return RuntimeResult(
            RuntimeDecision.PROPOSAL_ONLY,
            ("EXTERNAL_CONSTRAINT_IS_NOT_A_GOAL_AUTHORITY_SOURCE",),
        )

    return RuntimeResult(
        RuntimeDecision.PROPOSAL_ONLY,
        (
            "GOAL_MAY_PERSIST_WITHOUT_AUTHORITY_AMPLIFICATION",
            "EACH_EFFECT_REQUIRES_FRESH_AUTHORIZATION",
        ),
    )


def _external_block_sources(action: str, context: RuntimeConstitutionContext) -> tuple[str, ...]:
    return tuple(
        sorted(
            source
            for source, blocked_actions in context.external_runtime_blocks.items()
            if action in blocked_actions or "*" in blocked_actions
        )
    )


def evaluate_instruction(
    instruction: RuntimeInstruction, context: RuntimeConstitutionContext
) -> RuntimeResult:
    """Evaluate one proposed external effect under the runtime constitution.

    Source status never mints authority. Host/provider constraints may block the
    reachable action set, but cannot authorize an action or become semantic truth.
    """

    if instruction.policy_epoch != context.current_policy_epoch:
        return RuntimeResult(RuntimeDecision.REJECT, ("STALE_POLICY_EPOCH",))

    if instruction.goal_id and instruction.goal_id in context.revoked_goal_ids:
        return RuntimeResult(RuntimeDecision.REJECT, ("GOAL_REVOKED",))

    if instruction.source_class is ConstraintClass.GARDEN_CONSTITUTION:
        return RuntimeResult(
            RuntimeDecision.PROPOSAL_ONLY,
            ("GARDEN_CONSTITUTION_CONSTRAINS_BUT_DOES_NOT_AUTHORIZE_ACTION",),
        )

    if instruction.source_class is ConstraintClass.EXTERNAL_RUNTIME_CONSTRAINT:
        return RuntimeResult(
            RuntimeDecision.PROPOSAL_ONLY,
            ("EXTERNAL_RUNTIME_CONSTRAINT_CANNOT_AUTHORIZE_ACTION",),
        )

    if not instruction.delegation_chain:
        return RuntimeResult(RuntimeDecision.ESCALATE, ("AUTHORITY_CHAIN_MISSING",))

    if instruction.delegation_chain[0] != instruction.principal:
        return RuntimeResult(RuntimeDecision.REJECT, ("INVALID_DELEGATION_ROOT",))

    if instruction.delegation_chain[-1] != instruction.actor:
        return RuntimeResult(RuntimeDecision.REJECT, ("INVALID_ACTOR_BINDING",))

    actor_capabilities = context.capabilities_by_subject.get(
        instruction.actor, frozenset()
    )
    if instruction.capability not in actor_capabilities:
        return RuntimeResult(RuntimeDecision.REJECT, ("CAPABILITY_NOT_PRESENT",))

    authority_chain: list[AuthorityEnvelope] = []
    for index, subject in enumerate(instruction.delegation_chain):
        if subject in context.revoked_authority_subjects:
            return RuntimeResult(
                RuntimeDecision.REJECT,
                (f"AUTHORITY_REVOKED:{subject}",),
            )

        envelope = context.authority_by_subject.get(subject)
        if envelope is None:
            return RuntimeResult(
                RuntimeDecision.ESCALATE,
                (f"AUTHORITY_ENVELOPE_UNKNOWN:{subject}",),
            )

        validation = context.authority_validation_by_subject.get(subject)
        if validation is False:
            return RuntimeResult(
                RuntimeDecision.REJECT,
                (f"AUTHORITY_CLAIM_INVALID:{subject}",),
            )
        if validation is not True:
            return RuntimeResult(
                RuntimeDecision.ESCALATE,
                (f"AUTHORITY_CLAIM_UNVALIDATED:{subject}",),
            )

        provenance = context.authority_provenance_by_subject.get(subject, ())
        if not provenance:
            return RuntimeResult(
                RuntimeDecision.ESCALATE,
                (f"AUTHORITY_PROVENANCE_MISSING:{subject}",),
            )

        if envelope.subject != subject:
            return RuntimeResult(
                RuntimeDecision.REJECT,
                (f"AUTHORITY_SUBJECT_MISMATCH:{subject}",),
            )

        if index > 0:
            expected_parent = instruction.delegation_chain[index - 1]
            actual_parent = context.authority_parent_by_subject.get(subject)
            if actual_parent is None:
                return RuntimeResult(
                    RuntimeDecision.ESCALATE,
                    (f"AUTHORITY_PARENT_UNKNOWN:{subject}",),
                )
            if actual_parent != expected_parent:
                return RuntimeResult(
                    RuntimeDecision.REJECT,
                    (f"AUTHORITY_PARENT_MISMATCH:{subject}",),
                )
        authority_chain.append(envelope)

    depth = max(0, len(instruction.delegation_chain) - 1)
    if not can_execute(
        authority_chain,
        action=instruction.action,
        resource=instruction.target,
        depth=depth,
    ):
        return RuntimeResult(RuntimeDecision.REJECT, ("AUTHORITY_SCOPE_DENIED",))

    material_human_effect = context.human_effect_materiality_by_action.get(
        instruction.action
    )
    if material_human_effect is None:
        if instruction.action in context.high_impact_actions:
            material_human_effect = True
        else:
            return RuntimeResult(
                RuntimeDecision.ESCALATE,
                ("HUMAN_EFFECT_MATERIALITY_UNKNOWN",),
            )

    if material_human_effect:
        required_human_effect_gates = (
            BASE_HUMAN_EFFECT_GATES | context.required_human_effect_gates
        )
        failed = sorted(
            gate
            for gate in required_human_effect_gates
            if context.hard_gates.get(gate) is False
        )
        unknown = sorted(
            gate
            for gate in required_human_effect_gates
            if context.hard_gates.get(gate) is not True
            and context.hard_gates.get(gate) is not False
        )
        if failed:
            return RuntimeResult(
                RuntimeDecision.REJECT,
                tuple(f"HUMAN_EFFECT_GATE_FAILED:{gate}" for gate in failed),
            )
        if unknown:
            return RuntimeResult(
                RuntimeDecision.ESCALATE,
                tuple(f"HUMAN_EFFECT_GATE_UNKNOWN:{gate}" for gate in unknown),
            )

    block_sources = _external_block_sources(instruction.action, context)
    if block_sources:
        return RuntimeResult(
            RuntimeDecision.EXTERNALLY_BLOCKED,
            tuple(f"EXTERNAL_RUNTIME_BLOCK:{source}" for source in block_sources),
        )

    return RuntimeResult(
        RuntimeDecision.ALLOW,
        (
            "EXISTING_AUTHORITY_AND_CAPABILITY_SUFFICIENT",
            "SOURCE_CLASS_DID_NOT_CREATE_AUTHORITY",
        ),
    )


def evaluate_answer_integrity(
    *,
    direct_judgment_permitted: bool,
    response_claims_model_judgment: bool,
    substitutes_external_judgment: bool,
    constraint_disclosed: bool,
) -> RuntimeResult:
    """Prevent constraint-induced substitution from masquerading as a direct answer."""

    if direct_judgment_permitted:
        return RuntimeResult(
            RuntimeDecision.ALLOW,
            ("DIRECT_JUDGMENT_PATH_AVAILABLE",),
        )

    if response_claims_model_judgment:
        return RuntimeResult(
            RuntimeDecision.REJECT,
            ("FALSE_MODEL_JUDGMENT_CLAIM",),
        )

    if substitutes_external_judgment:
        return RuntimeResult(
            RuntimeDecision.REJECT,
            ("CONSTRAINT_BLOCKED_JUDGMENT_SUBSTITUTED_BY_EXTERNAL_JUDGMENT",),
        )

    if not constraint_disclosed:
        return RuntimeResult(
            RuntimeDecision.REJECT,
            ("CONSTRAINT_BOUNDARY_NOT_DISCLOSED",),
        )

    return RuntimeResult(
        RuntimeDecision.ALLOW,
        (
            "CONSTRAINT_BOUNDARY_DISCLOSED",
            "EXTERNAL_ATTRIBUTION_REMAINS_DISTINCT_FROM_MODEL_JUDGMENT",
        ),
    )
