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
    hard_gates: Mapping[str, Optional[bool]] = field(default_factory=dict)
    high_impact_actions: frozenset[str] = frozenset()
    required_human_effect_gates: frozenset[str] = frozenset(
        {"rights", "consent", "privacy", "law", "safety", "human_effect"}
    )
    external_runtime_blocks: Mapping[str, frozenset[str]] = field(default_factory=dict)
    revoked_goal_ids: frozenset[str] = frozenset()


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

    if instruction.source_class is ConstraintClass.EXTERNAL_RUNTIME_CONSTRAINT:
        return RuntimeResult(
            RuntimeDecision.PROPOSAL_ONLY,
            ("EXTERNAL_RUNTIME_CONSTRAINT_CANNOT_AUTHORIZE_ACTION",),
        )

    block_sources = _external_block_sources(instruction.action, context)
    if block_sources:
        return RuntimeResult(
            RuntimeDecision.EXTERNALLY_BLOCKED,
            tuple(f"EXTERNAL_RUNTIME_BLOCK:{source}" for source in block_sources),
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
    for subject in instruction.delegation_chain:
        envelope = context.authority_by_subject.get(subject)
        if envelope is None:
            return RuntimeResult(
                RuntimeDecision.ESCALATE,
                (f"AUTHORITY_ENVELOPE_UNKNOWN:{subject}",),
            )
        if envelope.subject != subject:
            return RuntimeResult(
                RuntimeDecision.REJECT,
                (f"AUTHORITY_SUBJECT_MISMATCH:{subject}",),
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

    if instruction.action in context.high_impact_actions:
        failed = sorted(
            gate
            for gate in context.required_human_effect_gates
            if context.hard_gates.get(gate) is False
        )
        unknown = sorted(
            gate
            for gate in context.required_human_effect_gates
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

    return RuntimeResult(
        RuntimeDecision.ALLOW,
        (
            "EXISTING_AUTHORITY_AND_CAPABILITY_SUFFICIENT",
            "SOURCE_CLASS_DID_NOT_CREATE_AUTHORITY",
        ),
    )
