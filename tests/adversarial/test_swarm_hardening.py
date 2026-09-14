from prototype.hardening import (
    AuthorityLease,
    ConstitutionalCheck,
    ConstitutionalEvent,
    ConstitutionalEventKind,
    HardeningDecision,
    VerifiedContainmentAdmission,
    _validate_constitutional_event,
    _validate_containment_admission,
    enforce_constitutional_event,
    validate_authority_lease,
)


def test_veto_remains_blocked_when_event_store_fails():
    event = ConstitutionalEvent("evt-1", "action:1", ConstitutionalCheck.VETO, "E1", ("RIGHT-001",))
    result = enforce_constitutional_event(event, lambda _: False)
    assert result.decision is HardeningDecision.BLOCK
    assert "CONSTITUTIONAL_VETO" in result.reasons
    assert "EVENT_PERSISTENCE_FAILED" in result.reasons


def test_veto_remains_blocked_when_event_writer_raises():
    def broken(_):
        raise RuntimeError("synthetic store outage")

    event = ConstitutionalEvent("evt-2", "action:2", ConstitutionalCheck.VETO, "E1")
    result = enforce_constitutional_event(event, broken)
    assert result.decision is HardeningDecision.BLOCK


def test_pass_does_not_allow_if_required_event_record_is_missing():
    event = ConstitutionalEvent("evt-3", "action:3", ConstitutionalCheck.PASS, "E1")
    result = enforce_constitutional_event(event, lambda _: False)
    assert result.decision is HardeningDecision.ESCALATE


def test_pass_requires_check_kind():
    event = ConstitutionalEvent(
        "evt-coherence", "action:coherence", ConstitutionalCheck.PASS, "E1",
        kind=ConstitutionalEventKind.VIOLATION,
    )
    errors = _validate_constitutional_event(event)
    assert "PASS_REQUIRES_CHECK_KIND" in errors
    result = enforce_constitutional_event(event, lambda _: True)
    assert result.decision is HardeningDecision.ESCALATE
    assert not any(reason.startswith("CONSTITUTIONAL_CHECK_PASS_RECORDED") for reason in result.reasons)


def test_pass_with_check_kind_remains_valid():
    event = ConstitutionalEvent(
        "evt-pass", "action:pass", ConstitutionalCheck.PASS, "E1",
        kind=ConstitutionalEventKind.CHECK,
    )
    assert _validate_constitutional_event(event) == ()
    result = enforce_constitutional_event(event, lambda _: True)
    assert result.decision is HardeningDecision.ALLOW


def test_unknown_and_inconclusive_never_allow_consequential_continuation():
    for check in (ConstitutionalCheck.UNKNOWN, ConstitutionalCheck.INCONCLUSIVE):
        event = ConstitutionalEvent(f"evt-{check.value}", "action:x", check, "E1")
        result = enforce_constitutional_event(event, lambda _: True)
        assert result.decision is HardeningDecision.ESCALATE


def test_constitutional_event_alone_never_authorizes_containment():
    event = ConstitutionalEvent(
        "evt-contain", "action:contain", ConstitutionalCheck.VETO, "E1",
        kind=ConstitutionalEventKind.VIOLATION,
    )
    containment = _validate_containment_admission(event, None, current_design_epoch="E1")
    assert containment.decision is HardeningDecision.BLOCK
    assert "SEPARATE_CONTAINMENT_ADMISSION_REQUIRED" in containment.reasons
    assert enforce_constitutional_event(event, lambda _: True).decision is HardeningDecision.BLOCK


def test_verified_containment_admission_must_bind_event_and_epoch():
    event = ConstitutionalEvent(
        "evt-contain-2", "action:contain", ConstitutionalCheck.VETO, "E1",
        kind=ConstitutionalEventKind.VIOLATION,
    )
    wrong_event = VerifiedContainmentAdmission("admit-1", "evt-other", "decision:1", "E1")
    assert _validate_containment_admission(
        event, wrong_event, current_design_epoch="E1"
    ).decision is HardeningDecision.BLOCK

    stale = VerifiedContainmentAdmission("admit-2", event.event_id, "decision:2", "E0")
    assert _validate_containment_admission(
        event, stale, current_design_epoch="E1"
    ).decision is HardeningDecision.BLOCK

    current = VerifiedContainmentAdmission("admit-3", event.event_id, "decision:3", "E1")
    containment = _validate_containment_admission(event, current, current_design_epoch="E1")
    assert containment.decision is HardeningDecision.ALLOW
    # A separately admitted containment action does not mutate/release the vetoed transition.
    assert enforce_constitutional_event(event, lambda _: True).decision is HardeningDecision.BLOCK


def test_stale_design_epoch_blocks_pre_authorized_lease():
    lease = AuthorityLease(
        "lease-1", "agent:A", frozenset({"notify"}), frozenset({"channel:x"}),
        "E1", valid_from=100, expires_at=1000,
    )
    result = validate_authority_lease(
        lease, now=500, current_design_epoch="E2", action="notify", resource="channel:x"
    )
    assert result.decision is HardeningDecision.BLOCK
    assert "LEASE_STALE_DESIGN_EPOCH" in result.reasons


def test_expiry_is_profile_bound_not_fixed_500ms():
    lease = AuthorityLease(
        "lease-2", "agent:A", frozenset({"notify"}), frozenset({"channel:x"}),
        "E1", valid_from=100, expires_at=10000,
    )
    current = validate_authority_lease(
        lease, now=5000, current_design_epoch="E1", action="notify", resource="channel:x"
    )
    expired = validate_authority_lease(
        lease, now=10000, current_design_epoch="E1", action="notify", resource="channel:x"
    )
    assert current.decision is HardeningDecision.ALLOW
    assert expired.decision is HardeningDecision.BLOCK
    assert "LEASE_EXPIRED" in expired.reasons


def test_active_invalidator_blocks_even_before_expiry():
    lease = AuthorityLease(
        "lease-3", "agent:A", frozenset({"notify"}), frozenset({"channel:x"}),
        "E1", valid_from=100, expires_at=10000, invalidators=frozenset({"consent_changed"}),
    )
    result = validate_authority_lease(
        lease, now=500, current_design_epoch="E1", action="notify", resource="channel:x",
        active_invalidators=frozenset({"consent_changed"}),
    )
    assert result.decision is HardeningDecision.BLOCK
    assert "LEASE_INVALIDATED:consent_changed" in result.reasons


def test_scope_change_cannot_get_one_extra_transition():
    lease = AuthorityLease(
        "lease-4", "agent:A", frozenset({"notify"}), frozenset({"channel:x"}),
        "E1", valid_from=100, expires_at=10000,
    )
    result = validate_authority_lease(
        lease, now=500, current_design_epoch="E1", action="transfer", resource="account:y"
    )
    assert result.decision is HardeningDecision.BLOCK
    assert "ACTION_OUTSIDE_LEASE_SCOPE" in result.reasons
    assert "RESOURCE_OUTSIDE_LEASE_SCOPE" in result.reasons
