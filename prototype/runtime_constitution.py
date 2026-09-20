from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
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


class ExternalEnforcementStatus(str, Enum):
    NONE = "NONE"
    BLOCKED = "BLOCKED"
    REQUIRED = "REQUIRED"
    BLOCKED_AND_REQUIRED = "BLOCKED_AND_REQUIRED"


@dataclass(frozen=True)
class RuntimeResult:
    decision: RuntimeDecision
    reasons: tuple[str, ...]
    authority_created: bool = False
    garden_decision: RuntimeDecision | None = None
    external_status: ExternalEnforcementStatus = ExternalEnforcementStatus.NONE


@dataclass(frozen=True)
class AuthorityValidationReceipt:
    subject: str
    claim_digest: str
    parent_subject: str | None
    policy_epoch: str
    jurisdiction: str
    context_scope: str
    validation_pass: Optional[bool]
    identity_authenticated: Optional[bool]
    revoked: Optional[bool]
    verifier_id: str
    verifier_control_lineage: str
    verifier_independent: Optional[bool]
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True)
class GoalProposal:
    goal_id: str
    proposer: str
    source_class: ConstraintClass
    summary: str


@dataclass(frozen=True)
class GoalLease:
    goal_id: str
    design_epoch: str
    policy_epoch: str
    delegated_by: str
    authority_claim_digests: tuple[str, ...]
    dependency_digest: str
    resource_bound: str
    termination_condition: str
    invalidators: tuple[str, ...]
    evidence_refs: tuple[str, ...]

    def digest(self) -> str:
        return _sha256_payload(
            {
                "goal_id": self.goal_id,
                "design_epoch": self.design_epoch,
                "policy_epoch": self.policy_epoch,
                "delegated_by": self.delegated_by,
                "authority_claim_digests": list(self.authority_claim_digests),
                "dependency_digest": self.dependency_digest,
                "resource_bound": self.resource_bound,
                "termination_condition": self.termination_condition,
                "invalidators": list(self.invalidators),
                "evidence_refs": list(self.evidence_refs),
            }
        )


@dataclass(frozen=True)
class GoalValidationReceipt:
    goal_id: str
    lease_digest: str
    policy_epoch: str
    validation_pass: Optional[bool]
    verifier_id: str
    verifier_control_lineage: str
    verifier_independent: Optional[bool]
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True)
class GoalValidity:
    design_epoch_current: Optional[bool]
    delegation_current: Optional[bool]
    expiry_current: Optional[bool]
    dependencies_current: Optional[bool]
    resource_bounds_present: Optional[bool]
    termination_conditions_present: Optional[bool]


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
    jurisdiction: str = "default"
    context_scope: str = "default"


@dataclass
class RuntimeConstitutionContext:
    current_policy_epoch: str
    assurance_policy_epoch: str | None
    current_design_epoch: str
    capabilities_by_subject: Mapping[str, frozenset[str]]
    authority_by_subject: Mapping[str, AuthorityEnvelope] = field(default_factory=dict)
    authority_validation_by_subject: Mapping[str, Optional[bool]] = field(default_factory=dict)
    authority_provenance_by_subject: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    authority_parent_by_subject: Mapping[str, str] = field(default_factory=dict)
    authority_claim_digest_by_subject: Mapping[str, str] = field(default_factory=dict)
    authority_validation_receipt_by_subject: Mapping[str, AuthorityValidationReceipt] = field(default_factory=dict)
    revoked_authority_subjects: frozenset[str] = frozenset()
    hard_gates: Mapping[str, Optional[bool]] = field(default_factory=dict)
    human_effect_materiality_by_effect: Mapping[tuple[str, str], Optional[bool]] = field(default_factory=dict)
    human_effect_materiality_validation_by_effect: Mapping[tuple[str, str], Optional[bool]] = field(default_factory=dict)
    human_effect_materiality_digest_by_effect: Mapping[tuple[str, str], str] = field(default_factory=dict)
    required_human_effect_gates: frozenset[str] = frozenset()
    external_runtime_blocks: Mapping[str, frozenset[tuple[str, str]]] = field(default_factory=dict)
    external_runtime_requirements: Mapping[str, frozenset[tuple[str, str]]] = field(default_factory=dict)
    revoked_goal_ids: frozenset[str] = frozenset()
    goal_validity_by_id: Mapping[str, GoalValidity] = field(default_factory=dict)
    goal_lease_by_id: Mapping[str, GoalLease] = field(default_factory=dict)
    goal_validation_receipt_by_id: Mapping[str, GoalValidationReceipt] = field(default_factory=dict)




def _sha256_payload(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _authority_claim_digest(
    *,
    subject: str,
    envelope: AuthorityEnvelope,
    parent: str | None,
    provenance: tuple[str, ...],
) -> str:
    return _sha256_payload(
        {
            "subject": subject,
            "actions": sorted(envelope.actions),
            "resources": sorted(envelope.resources),
            "max_depth": envelope.max_depth,
            "parent": parent,
            "provenance": list(provenance),
        }
    )


def _materiality_claim_digest(
    *,
    action: str,
    target: str,
    material: bool,
    policy_epoch: str,
) -> str:
    return _sha256_payload(
        {
            "action": action,
            "target": target,
            "material": material,
            "policy_epoch": policy_epoch,
        }
    )


def _authority_validation_result(
    *,
    instruction: RuntimeInstruction,
    subject: str,
    claim_digest: str,
    parent: str | None,
    context: RuntimeConstitutionContext,
) -> RuntimeResult | None:
    receipt = context.authority_validation_receipt_by_subject.get(subject)
    if receipt is None:
        return RuntimeResult(
            RuntimeDecision.ESCALATE,
            (f"AUTHORITY_VALIDATION_RECEIPT_UNKNOWN:{subject}",),
        )
    if (
        receipt.subject != subject
        or receipt.claim_digest != claim_digest
        or receipt.parent_subject != parent
        or receipt.policy_epoch != context.current_policy_epoch
        or receipt.jurisdiction != instruction.jurisdiction
        or receipt.context_scope != instruction.context_scope
    ):
        return RuntimeResult(
            RuntimeDecision.REJECT,
            (f"AUTHORITY_VALIDATION_RECEIPT_MISMATCH:{subject}",),
        )
    if receipt.validation_pass is False or receipt.identity_authenticated is False:
        return RuntimeResult(
            RuntimeDecision.REJECT,
            (f"AUTHORITY_VALIDATION_RECEIPT_INVALID:{subject}",),
        )
    if receipt.validation_pass is not True or receipt.identity_authenticated is not True:
        return RuntimeResult(
            RuntimeDecision.ESCALATE,
            (f"AUTHORITY_VALIDATION_RECEIPT_UNVALIDATED:{subject}",),
        )
    if receipt.revoked is True:
        return RuntimeResult(
            RuntimeDecision.REJECT,
            (f"AUTHORITY_VALIDATION_RECEIPT_REVOKED:{subject}",),
        )
    if receipt.revoked is not False:
        return RuntimeResult(
            RuntimeDecision.ESCALATE,
            (f"AUTHORITY_VALIDATION_RECEIPT_REVOCATION_UNKNOWN:{subject}",),
        )
    if (
        not receipt.verifier_id.strip()
        or not receipt.verifier_control_lineage.strip()
        or not receipt.evidence_refs
    ):
        return RuntimeResult(
            RuntimeDecision.ESCALATE,
            (f"AUTHORITY_VALIDATION_EVIDENCE_INCOMPLETE:{subject}",),
        )
    if receipt.verifier_independent is False:
        return RuntimeResult(
            RuntimeDecision.REJECT,
            (f"AUTHORITY_VALIDATION_NOT_INDEPENDENT:{subject}",),
        )
    if receipt.verifier_independent is not True:
        return RuntimeResult(
            RuntimeDecision.ESCALATE,
            (f"AUTHORITY_VALIDATION_INDEPENDENCE_UNKNOWN:{subject}",),
        )
    return None


def _goal_lease_result(
    goal_id: str, context: RuntimeConstitutionContext
) -> RuntimeResult | None:
    lease = context.goal_lease_by_id.get(goal_id)
    if lease is None:
        return RuntimeResult(RuntimeDecision.ESCALATE, ("GOAL_LEASE_UNKNOWN",))
    if (
        lease.goal_id != goal_id
        or lease.design_epoch != context.current_design_epoch
        or lease.policy_epoch != context.current_policy_epoch
    ):
        return RuntimeResult(RuntimeDecision.REJECT, ("GOAL_LEASE_STALE",))
    current_authority_digests = set(context.authority_claim_digest_by_subject.values())
    if not set(lease.authority_claim_digests).issubset(current_authority_digests):
        return RuntimeResult(
            RuntimeDecision.REJECT, ("GOAL_LEASE_AUTHORITY_STALE",)
        )

    if (
        not lease.delegated_by.strip()
        or not lease.authority_claim_digests
        or not lease.dependency_digest.strip()
        or not lease.resource_bound.strip()
        or not lease.termination_condition.strip()
        or not lease.invalidators
        or not lease.evidence_refs
    ):
        return RuntimeResult(
            RuntimeDecision.ESCALATE, ("GOAL_LEASE_BINDING_INCOMPLETE",)
        )

    receipt = context.goal_validation_receipt_by_id.get(goal_id)
    if receipt is None:
        return RuntimeResult(
            RuntimeDecision.ESCALATE, ("GOAL_VALIDATION_RECEIPT_UNKNOWN",)
        )
    if (
        receipt.goal_id != goal_id
        or receipt.lease_digest != lease.digest()
        or receipt.policy_epoch != context.current_policy_epoch
    ):
        return RuntimeResult(
            RuntimeDecision.REJECT, ("GOAL_VALIDATION_RECEIPT_MISMATCH",)
        )
    if receipt.validation_pass is False:
        return RuntimeResult(
            RuntimeDecision.REJECT, ("GOAL_VALIDATION_RECEIPT_INVALID",)
        )
    if receipt.validation_pass is not True:
        return RuntimeResult(
            RuntimeDecision.ESCALATE, ("GOAL_VALIDATION_RECEIPT_UNVALIDATED",)
        )
    if (
        not receipt.verifier_id.strip()
        or not receipt.verifier_control_lineage.strip()
        or not receipt.evidence_refs
    ):
        return RuntimeResult(
            RuntimeDecision.ESCALATE, ("GOAL_VALIDATION_EVIDENCE_INCOMPLETE",)
        )
    if receipt.verifier_independent is False:
        return RuntimeResult(
            RuntimeDecision.REJECT, ("GOAL_VALIDATION_NOT_INDEPENDENT",)
        )
    if receipt.verifier_independent is not True:
        return RuntimeResult(
            RuntimeDecision.ESCALATE, ("GOAL_VALIDATION_INDEPENDENCE_UNKNOWN",)
        )
    return None


def classify_instruction_authority(source_class: ConstraintClass) -> InstructionAuthority:
    """Classify what an instruction source can contribute before action checks."""
    if source_class is ConstraintClass.GARDEN_CONSTITUTION:
        return InstructionAuthority.GARDEN_CONSTRAINT_ONLY
    if source_class is ConstraintClass.AUTHORIZED_HUMAN_INSTRUCTION:
        return InstructionAuthority.DELEGATED_AUTHORITY_REQUIRED
    if source_class is ConstraintClass.EXTERNAL_RUNTIME_CONSTRAINT:
        return InstructionAuthority.EXTERNAL_ENFORCEMENT_ONLY
    return InstructionAuthority.PROPOSAL_ONLY


def _goal_validity_result(
    goal_id: str, context: RuntimeConstitutionContext
) -> RuntimeResult | None:
    if goal_id in context.revoked_goal_ids:
        return RuntimeResult(RuntimeDecision.REJECT, ("GOAL_REVOKED",))

    lease_result = _goal_lease_result(goal_id, context)
    if lease_result is not None:
        return lease_result

    validity = context.goal_validity_by_id.get(goal_id)
    if validity is None:
        return RuntimeResult(RuntimeDecision.ESCALATE, ("GOAL_VALIDITY_UNKNOWN",))

    checks = {
        "design_epoch": validity.design_epoch_current,
        "delegation": validity.delegation_current,
        "expiry": validity.expiry_current,
        "dependencies": validity.dependencies_current,
        "resource_bounds": validity.resource_bounds_present,
        "termination_conditions": validity.termination_conditions_present,
    }
    failed = sorted(name for name, value in checks.items() if value is False)
    if failed:
        return RuntimeResult(
            RuntimeDecision.REJECT,
            tuple(f"GOAL_BINDING_INVALID:{name}" for name in failed),
        )
    unknown = sorted(name for name, value in checks.items() if value is not True)
    if unknown:
        return RuntimeResult(
            RuntimeDecision.ESCALATE,
            tuple(f"GOAL_BINDING_UNKNOWN:{name}" for name in unknown),
        )
    return None


def evaluate_goal(goal: GoalProposal, context: RuntimeConstitutionContext) -> RuntimeResult:
    """Admit a goal as planning state without minting execution authority.

    Garden allows humans or agents to propose/retain goals. Goal admission is not
    action admission. Every consequential effect still needs fresh authority and
    hard-gate checks at point of use.
    """

    validity_result = _goal_validity_result(goal.goal_id, context)
    if validity_result is not None:
        return validity_result

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


def _external_block_sources(
    action: str, target: str, context: RuntimeConstitutionContext
) -> tuple[str, ...]:
    effect = (action, target)
    return tuple(
        sorted(
            source
            for source, blocked_effects in context.external_runtime_blocks.items()
            if effect in blocked_effects
            or (action, "*") in blocked_effects
            or ("*", "*") in blocked_effects
        )
    )


def _evaluate_garden_instruction(
    instruction: RuntimeInstruction, context: RuntimeConstitutionContext
) -> RuntimeResult:
    """Evaluate one proposed external effect under the runtime constitution.

    Source status never mints authority. Host/provider constraints may block the
    reachable action set, but cannot authorize an action or become semantic truth.
    """

    if instruction.policy_epoch != context.current_policy_epoch:
        return RuntimeResult(RuntimeDecision.REJECT, ("STALE_POLICY_EPOCH",))

    if context.assurance_policy_epoch is None:
        return RuntimeResult(
            RuntimeDecision.ESCALATE, ("RUNTIME_ASSURANCE_EPOCH_UNKNOWN",)
        )
    if context.assurance_policy_epoch != context.current_policy_epoch:
        return RuntimeResult(
            RuntimeDecision.REJECT, ("RUNTIME_ASSURANCE_EPOCH_STALE",)
        )

    if instruction.goal_id:
        validity_result = _goal_validity_result(instruction.goal_id, context)
        if validity_result is not None:
            return validity_result

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
        parent = instruction.delegation_chain[index - 1] if index > 0 else None
        expected_claim_digest = context.authority_claim_digest_by_subject.get(subject)
        if expected_claim_digest is None:
            return RuntimeResult(
                RuntimeDecision.ESCALATE,
                (f"AUTHORITY_CLAIM_DIGEST_UNKNOWN:{subject}",),
            )
        actual_claim_digest = _authority_claim_digest(
            subject=subject,
            envelope=envelope,
            parent=parent,
            provenance=provenance,
        )
        if expected_claim_digest != actual_claim_digest:
            return RuntimeResult(
                RuntimeDecision.REJECT,
                (f"AUTHORITY_CLAIM_DIGEST_MISMATCH:{subject}",),
            )

        receipt_result = _authority_validation_result(
            instruction=instruction,
            subject=subject,
            claim_digest=actual_claim_digest,
            parent=parent,
            context=context,
        )
        if receipt_result is not None:
            return receipt_result

        authority_chain.append(envelope)

    depth = max(0, len(instruction.delegation_chain) - 1)
    if not can_execute(
        authority_chain,
        action=instruction.action,
        resource=instruction.target,
        depth=depth,
    ):
        return RuntimeResult(RuntimeDecision.REJECT, ("AUTHORITY_SCOPE_DENIED",))

    effect_key = (instruction.action, instruction.target)
    material_human_effect = context.human_effect_materiality_by_effect.get(effect_key)
    if material_human_effect is None:
        return RuntimeResult(
            RuntimeDecision.ESCALATE,
            ("HUMAN_EFFECT_MATERIALITY_UNKNOWN",),
        )

    materiality_validation = (
        context.human_effect_materiality_validation_by_effect.get(effect_key)
    )
    if materiality_validation is False:
        return RuntimeResult(
            RuntimeDecision.REJECT,
            ("HUMAN_EFFECT_MATERIALITY_INVALID",),
        )
    if materiality_validation is not True:
        return RuntimeResult(
            RuntimeDecision.ESCALATE,
            ("HUMAN_EFFECT_MATERIALITY_UNVALIDATED",),
        )

    expected_materiality_digest = (
        context.human_effect_materiality_digest_by_effect.get(effect_key)
    )
    if expected_materiality_digest is None:
        return RuntimeResult(
            RuntimeDecision.ESCALATE,
            ("HUMAN_EFFECT_MATERIALITY_DIGEST_UNKNOWN",),
        )
    actual_materiality_digest = _materiality_claim_digest(
        action=instruction.action,
        target=instruction.target,
        material=material_human_effect,
        policy_epoch=context.current_policy_epoch,
    )
    if expected_materiality_digest != actual_materiality_digest:
        return RuntimeResult(
            RuntimeDecision.REJECT,
            ("HUMAN_EFFECT_MATERIALITY_DIGEST_MISMATCH",),
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

    return RuntimeResult(
        RuntimeDecision.ALLOW,
        (
            "EXISTING_AUTHORITY_AND_CAPABILITY_SUFFICIENT",
            "SOURCE_CLASS_DID_NOT_CREATE_AUTHORITY",
        ),
    )



def _external_requirement_sources(
    action: str, target: str, context: RuntimeConstitutionContext
) -> tuple[str, ...]:
    effect = (action, target)
    return tuple(
        sorted(
            source
            for source, required_effects in context.external_runtime_requirements.items()
            if effect in required_effects
            or (action, "*") in required_effects
            or ("*", "*") in required_effects
        )
    )


def evaluate_instruction(
    instruction: RuntimeInstruction, context: RuntimeConstitutionContext
) -> RuntimeResult:
    """Return Garden admission and external enforcement as distinct dimensions."""

    garden = _evaluate_garden_instruction(instruction, context)
    block_sources = _external_block_sources(
        instruction.action, instruction.target, context
    )
    requirement_sources = _external_requirement_sources(
        instruction.action, instruction.target, context
    )

    if block_sources and requirement_sources:
        external_status = ExternalEnforcementStatus.BLOCKED_AND_REQUIRED
    elif block_sources:
        external_status = ExternalEnforcementStatus.BLOCKED
    elif requirement_sources:
        external_status = ExternalEnforcementStatus.REQUIRED
    else:
        external_status = ExternalEnforcementStatus.NONE

    reasons = list(garden.reasons)
    if requirement_sources and garden.decision is not RuntimeDecision.ALLOW:
        reasons.extend(
            f"EXTERNAL_RUNTIME_REQUIREMENT_CONFLICT:{source}"
            for source in requirement_sources
        )
    if block_sources and garden.decision is not RuntimeDecision.ALLOW:
        reasons.extend(
            f"EXTERNAL_RUNTIME_BLOCK:{source}" for source in block_sources
        )

    if block_sources and garden.decision is RuntimeDecision.ALLOW:
        return RuntimeResult(
            RuntimeDecision.EXTERNALLY_BLOCKED,
            tuple(f"EXTERNAL_RUNTIME_BLOCK:{source}" for source in block_sources),
            authority_created=False,
            garden_decision=RuntimeDecision.ALLOW,
            external_status=external_status,
        )

    return RuntimeResult(
        garden.decision,
        tuple(reasons),
        authority_created=garden.authority_created,
        garden_decision=garden.decision,
        external_status=external_status,
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
