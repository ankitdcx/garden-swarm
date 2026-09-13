from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable


class ConstitutionalCheck(str, Enum):
    PASS = "PASS"
    VETO = "VETO"
    UNKNOWN = "UNKNOWN"


class HardeningDecision(str, Enum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    ESCALATE = "ESCALATE"


@dataclass(frozen=True)
class ConstitutionalEvent:
    event_id: str
    action_ref: str
    check_result: ConstitutionalCheck
    design_epoch: str
    rights: tuple[str, ...] = ()


@dataclass(frozen=True)
class AuthorityLease:
    lease_id: str
    subject: str
    actions: frozenset[str]
    resources: frozenset[str]
    design_epoch: str
    valid_from: int
    expires_at: int
    invalidators: frozenset[str] = frozenset()


@dataclass(frozen=True)
class HardeningResult:
    decision: HardeningDecision
    reasons: tuple[str, ...]


EventWriter = Callable[[ConstitutionalEvent], bool]


def enforce_constitutional_event(event: ConstitutionalEvent, writer: EventWriter) -> HardeningResult:
    """Non-certified fail-closed fixture for a consequential constitutional gate.

    A VETO never becomes ALLOW because event persistence/routing failed. Unknown gate
    state escalates. PASS still requires durable event recording in this fixture.
    """
    try:
        persisted = bool(writer(event))
    except Exception:
        persisted = False

    if event.check_result is ConstitutionalCheck.VETO:
        if not persisted:
            return HardeningResult(HardeningDecision.BLOCK, ("CONSTITUTIONAL_VETO", "EVENT_PERSISTENCE_FAILED"))
        return HardeningResult(HardeningDecision.BLOCK, ("CONSTITUTIONAL_VETO",))

    if event.check_result is ConstitutionalCheck.UNKNOWN:
        return HardeningResult(HardeningDecision.ESCALATE, ("CONSTITUTIONAL_CHECK_UNKNOWN",))

    if not persisted:
        return HardeningResult(HardeningDecision.ESCALATE, ("EVENT_PERSISTENCE_FAILED",))

    return HardeningResult(HardeningDecision.ALLOW, ("CONSTITUTIONAL_CHECK_PASS_RECORDED",))


def validate_authority_lease(
    lease: AuthorityLease,
    *,
    now: int,
    current_design_epoch: str,
    action: str,
    resource: str,
    active_invalidators: frozenset[str] = frozenset(),
) -> HardeningResult:
    """Validate a bounded pre-authorized lease without a universal fixed TTL.

    Expiry, scope, epoch and invalidators are all explicit. Any stale or ambiguous
    condition fails closed; the caller must re-enter deeper assurance before action.
    """
    reasons: list[str] = []
    if now < lease.valid_from:
        reasons.append("LEASE_NOT_YET_VALID")
    if now >= lease.expires_at:
        reasons.append("LEASE_EXPIRED")
    if lease.design_epoch != current_design_epoch:
        reasons.append("LEASE_STALE_DESIGN_EPOCH")
    triggered = sorted(lease.invalidators & active_invalidators)
    reasons.extend(f"LEASE_INVALIDATED:{name}" for name in triggered)
    if action not in lease.actions:
        reasons.append("ACTION_OUTSIDE_LEASE_SCOPE")
    if resource not in lease.resources:
        reasons.append("RESOURCE_OUTSIDE_LEASE_SCOPE")

    if reasons:
        return HardeningResult(HardeningDecision.BLOCK, tuple(reasons))
    return HardeningResult(HardeningDecision.ALLOW, ("LEASE_CURRENT_AND_IN_SCOPE",))
