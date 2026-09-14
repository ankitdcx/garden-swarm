from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable


class ConstitutionalCheck(str, Enum):
    PASS = "PASS"
    VETO = "VETO"
    INCONCLUSIVE = "INCONCLUSIVE"
    UNKNOWN = "UNKNOWN"


class ConstitutionalEventKind(str, Enum):
    CHECK = "CHECK"
    VIOLATION = "VIOLATION"


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
    kind: ConstitutionalEventKind | None = None


@dataclass(frozen=True)
class VerifiedContainmentAdmission:
    """Positive containment admission produced by a separate trusted authority path.

    This reference object does not mint or verify authority by itself. Callers may
    supply it only after the applicable authority/admission mechanism has verified
    the containment decision. Its purpose here is to make the separation between a
    ConstitutionalEvent and a later containment execution mechanically visible.
    """

    admission_id: str
    constitutional_event_id: str
    decision_ref: str
    design_epoch: str


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


def effective_event_kind(event: ConstitutionalEvent) -> ConstitutionalEventKind:
    """Return a conservative default kind without hiding an explicit producer value.

    PASS is an ordinary CHECK. VETO defaults to VIOLATION for this reference fixture.
    UNKNOWN/INCONCLUSIVE remain CHECK unless a producer explicitly classifies a
    provisional event otherwise. Stronger mappings must be declared by the owner
    contract rather than inferred here.
    """

    if event.kind is not None:
        return event.kind
    if event.check_result is ConstitutionalCheck.VETO:
        return ConstitutionalEventKind.VIOLATION
    return ConstitutionalEventKind.CHECK


def validate_constitutional_event(event: ConstitutionalEvent) -> tuple[str, ...]:
    """Validate the cross-field coherence already implied by v15.5 conformance tests.

    The canonical test surface says PASS emits kind=CHECK and a detected violation
    emits kind=VIOLATION. We reject the directly contradictory VIOLATION+PASS state,
    but do not invent stronger equivalences for VETO, INCONCLUSIVE or UNKNOWN.
    """

    errors: list[str] = []
    kind = effective_event_kind(event)
    if event.check_result is ConstitutionalCheck.PASS and kind is not ConstitutionalEventKind.CHECK:
        errors.append("PASS_REQUIRES_CHECK_KIND")
    if kind is ConstitutionalEventKind.VIOLATION and event.check_result is ConstitutionalCheck.PASS:
        errors.append("VIOLATION_CANNOT_HAVE_PASS_RESULT")
    return tuple(errors)


def enforce_constitutional_event(event: ConstitutionalEvent, writer: EventWriter) -> HardeningResult:
    """Non-certified fail-closed fixture for a consequential constitutional gate.

    A VETO never becomes ALLOW because event persistence/routing failed. UNKNOWN or
    INCONCLUSIVE never authorizes consequential continuation. PASS still requires a
    durable event record. Contradictory typed states fail closed for review.
    """

    coherence_errors = validate_constitutional_event(event)
    if coherence_errors:
        return HardeningResult(
            HardeningDecision.ESCALATE,
            tuple(f"CONSTITUTIONAL_EVENT_INVALID:{reason}" for reason in coherence_errors),
        )

    try:
        persisted = bool(writer(event))
    except Exception:
        persisted = False

    if event.check_result is ConstitutionalCheck.VETO:
        reasons = ["CONSTITUTIONAL_VETO"]
        if not persisted:
            reasons.append("EVENT_PERSISTENCE_FAILED")
        return HardeningResult(HardeningDecision.BLOCK, tuple(reasons))

    if event.check_result in {ConstitutionalCheck.UNKNOWN, ConstitutionalCheck.INCONCLUSIVE}:
        reason = (
            "CONSTITUTIONAL_CHECK_UNKNOWN"
            if event.check_result is ConstitutionalCheck.UNKNOWN
            else "CONSTITUTIONAL_CHECK_INCONCLUSIVE"
        )
        reasons = [reason]
        if not persisted:
            reasons.append("EVENT_PERSISTENCE_FAILED")
        return HardeningResult(HardeningDecision.ESCALATE, tuple(reasons))

    if not persisted:
        return HardeningResult(HardeningDecision.ESCALATE, ("EVENT_PERSISTENCE_FAILED",))

    return HardeningResult(HardeningDecision.ALLOW, ("CONSTITUTIONAL_CHECK_PASS_RECORDED",))


def validate_containment_admission(
    event: ConstitutionalEvent,
    admission: VerifiedContainmentAdmission | None,
    *,
    current_design_epoch: str,
) -> HardeningResult:
    """Require a separately verified admission before a containment effect executes.

    The ConstitutionalEvent, its VETO, and any violation classification are never
    sufficient containment authority. This helper validates only the binding of an
    already-verified external admission to the immutable event and current epoch;
    it does not create or independently verify authority.
    """

    reasons: list[str] = []
    if admission is None:
        reasons.append("SEPARATE_CONTAINMENT_ADMISSION_REQUIRED")
    else:
        if admission.constitutional_event_id != event.event_id:
            reasons.append("CONTAINMENT_ADMISSION_EVENT_MISMATCH")
        if admission.design_epoch != event.design_epoch:
            reasons.append("CONTAINMENT_ADMISSION_EVENT_EPOCH_MISMATCH")
        if admission.design_epoch != current_design_epoch:
            reasons.append("CONTAINMENT_ADMISSION_STALE_DESIGN_EPOCH")
        if not admission.admission_id.strip() or not admission.decision_ref.strip():
            reasons.append("CONTAINMENT_ADMISSION_REFERENCE_INVALID")

    if reasons:
        return HardeningResult(HardeningDecision.BLOCK, tuple(reasons))
    return HardeningResult(HardeningDecision.ALLOW, ("SEPARATE_CONTAINMENT_ADMISSION_BOUND",))


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
