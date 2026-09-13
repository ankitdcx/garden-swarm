from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping, Optional

from prototype.authority import AuthorityEnvelope, can_execute


class Decision(str, Enum):
    ALLOW = "ALLOW"
    REJECT = "REJECT"
    ESCALATE = "ESCALATE"


class GateConditionStatus(str, Enum):
    """Status of the facts/preconditions feeding the Decision Algebra.

    Keeping this separate prevents STALE/UNKNOWN from being laundered into an
    ordinary denial while preserving ALLOW/REJECT/ESCALATE as decisions.
    """

    CURRENT = "CURRENT"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class GateResult:
    decision: Decision
    condition_status: GateConditionStatus
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class ActionProposal:
    principal: str
    action: str
    target: str
    capability: str
    delegation_chain: tuple[str, ...]
    policy_epoch: str
    context_trust: str = "trusted"  # trusted | untrusted
    independent_review: bool = False


@dataclass
class GateContext:
    current_policy_epoch: str
    capabilities_by_principal: Mapping[str, frozenset[str]]
    authority_by_subject: Mapping[str, AuthorityEnvelope] = field(default_factory=dict)
    revoked_delegations: set[tuple[str, str]] = field(default_factory=set)
    hard_gates: Mapping[str, Optional[bool]] = field(default_factory=dict)
    high_impact_actions: frozenset[str] = frozenset()


def evaluate_action(proposal: ActionProposal, context: GateContext) -> GateResult:
    """Small deterministic reference gate.

    This is intentionally not a complete Garden runtime. It demonstrates that
    capability, authority, resource scope, delegation depth, hard-gate state,
    and freshness/knowledge state remain distinct. Missing/stale/unknown
    authority never becomes ALLOW and need not be recovered by parsing reasons.
    """

    reasons: list[str] = []

    if proposal.policy_epoch != context.current_policy_epoch:
        return GateResult(Decision.REJECT, GateConditionStatus.STALE, ("STALE_POLICY_EPOCH",))

    if not proposal.delegation_chain or proposal.delegation_chain[0] != proposal.principal:
        return GateResult(Decision.REJECT, GateConditionStatus.CURRENT, ("INVALID_DELEGATION_ROOT",))

    granted = context.capabilities_by_principal.get(proposal.principal, frozenset())
    if proposal.capability not in granted:
        return GateResult(Decision.REJECT, GateConditionStatus.CURRENT, ("CAPABILITY_NOT_GRANTED",))

    for parent, child in zip(proposal.delegation_chain, proposal.delegation_chain[1:]):
        if (parent, child) in context.revoked_delegations:
            return GateResult(Decision.REJECT, GateConditionStatus.CURRENT, ("DELEGATION_REVOKED",))

    authority_chain: list[AuthorityEnvelope] = []
    for subject in proposal.delegation_chain:
        envelope = context.authority_by_subject.get(subject)
        if envelope is None:
            return GateResult(
                Decision.ESCALATE,
                GateConditionStatus.UNKNOWN,
                (f"AUTHORITY_ENVELOPE_UNKNOWN:{subject}",),
            )
        if envelope.subject != subject:
            return GateResult(
                Decision.REJECT,
                GateConditionStatus.CURRENT,
                (f"AUTHORITY_SUBJECT_MISMATCH:{subject}",),
            )
        authority_chain.append(envelope)

    depth = max(0, len(proposal.delegation_chain) - 1)
    if not can_execute(
        authority_chain,
        action=proposal.action,
        resource=proposal.target,
        depth=depth,
    ):
        return GateResult(Decision.REJECT, GateConditionStatus.CURRENT, ("AUTHORITY_SCOPE_DENIED",))

    unknown_gates = [name for name, state in context.hard_gates.items() if state is None]
    failed_gates = [name for name, state in context.hard_gates.items() if state is False]

    if failed_gates:
        return GateResult(
            Decision.REJECT,
            GateConditionStatus.CURRENT,
            tuple(f"HARD_GATE_FAILED:{name}" for name in sorted(failed_gates)),
        )

    if unknown_gates:
        return GateResult(
            Decision.ESCALATE,
            GateConditionStatus.UNKNOWN,
            tuple(f"HARD_GATE_UNKNOWN:{name}" for name in sorted(unknown_gates)),
        )

    if (
        proposal.context_trust == "untrusted"
        and proposal.action in context.high_impact_actions
        and not proposal.independent_review
    ):
        return GateResult(
            Decision.ESCALATE,
            GateConditionStatus.CURRENT,
            ("UNTRUSTED_CONTEXT_REQUIRES_FRESH_REVIEW",),
        )

    reasons.append("ALL_REQUIRED_CHECKS_PASS")
    return GateResult(Decision.ALLOW, GateConditionStatus.CURRENT, tuple(reasons))


def _demo() -> None:
    context = GateContext(
        current_policy_epoch="E1",
        capabilities_by_principal={"human:alice": frozenset({"notify"})},
        authority_by_subject={
            "human:alice": AuthorityEnvelope(
                subject="human:alice",
                actions=frozenset({"notify"}),
                resources=frozenset({"demo-channel"}),
                max_depth=1,
            ),
            "agent:A": AuthorityEnvelope(
                subject="agent:A",
                actions=frozenset({"notify"}),
                resources=frozenset({"demo-channel"}),
                max_depth=1,
            ),
        },
        hard_gates={"rights": True, "policy": True, "safety": True},
    )
    proposal = ActionProposal(
        principal="human:alice",
        action="notify",
        target="demo-channel",
        capability="notify",
        delegation_chain=("human:alice", "agent:A"),
        policy_epoch="E1",
    )
    result = evaluate_action(proposal, context)
    print({
        "decision": result.decision.value,
        "condition_status": result.condition_status.value,
        "reasons": list(result.reasons),
    })


if __name__ == "__main__":
    _demo()
