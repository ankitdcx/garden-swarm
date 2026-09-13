from prototype.hardening import (
    AuthorityLease,
    ConstitutionalCheck,
    ConstitutionalEvent,
    HardeningDecision,
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
