import base64
import json

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from prototype.actiongate import ActionProposal, Decision, GateContext, evaluate_action
from prototype.authority import AuthorityEnvelope, can_execute, compose_authority
from prototype.design_epoch import ArtifactBinding, BindingStatus, validate_binding
from prototype.tokens import (
    DelegationReceipt,
    ReceiptValidationStatus,
    receipt_digest,
    sign_receipt,
    validate_receipt,
)


def _authority(subject: str, actions: set[str], resources: set[str], depth: int = 2) -> AuthorityEnvelope:
    return AuthorityEnvelope(
        subject=subject,
        actions=frozenset(actions),
        resources=frozenset(resources),
        max_depth=depth,
    )


def test_actiongate_allows_current_authorized_action():
    ctx = GateContext(
        current_policy_epoch="E1",
        capabilities_by_principal={"human:alice": frozenset({"notify"})},
        authority_by_subject={
            "human:alice": _authority("human:alice", {"notify"}, {"demo"}),
            "agent:A": _authority("agent:A", {"notify"}, {"demo"}),
        },
        hard_gates={"rights": True, "policy": True, "safety": True},
    )
    proposal = ActionProposal(
        principal="human:alice",
        action="notify",
        target="demo",
        capability="notify",
        delegation_chain=("human:alice", "agent:A"),
        policy_epoch="E1",
    )
    assert evaluate_action(proposal, ctx).decision is Decision.ALLOW


def test_actiongate_rejects_stale_policy_epoch_without_laundering_reason():
    ctx = GateContext(
        current_policy_epoch="E2",
        capabilities_by_principal={"human:alice": frozenset({"notify"})},
        hard_gates={"rights": True, "policy": True},
    )
    proposal = ActionProposal(
        principal="human:alice",
        action="notify",
        target="demo",
        capability="notify",
        delegation_chain=("human:alice", "agent:A"),
        policy_epoch="E1",
    )
    result = evaluate_action(proposal, ctx)
    assert result.decision is Decision.REJECT
    assert "STALE_POLICY_EPOCH" in result.reasons


def test_actiongate_escalates_untrusted_high_impact_context():
    ctx = GateContext(
        current_policy_epoch="E1",
        capabilities_by_principal={"human:alice": frozenset({"transfer"})},
        authority_by_subject={
            "human:alice": _authority("human:alice", {"transfer"}, {"account:X"}),
            "agent:A": _authority("agent:A", {"transfer"}, {"account:X"}),
        },
        hard_gates={"rights": True, "policy": True},
        high_impact_actions=frozenset({"transfer"}),
    )
    proposal = ActionProposal(
        principal="human:alice",
        action="transfer",
        target="account:X",
        capability="transfer",
        delegation_chain=("human:alice", "agent:A"),
        policy_epoch="E1",
        context_trust="untrusted",
        independent_review=False,
    )
    result = evaluate_action(proposal, ctx)
    assert result.decision is Decision.ESCALATE
    assert "UNTRUSTED_CONTEXT_REQUIRES_FRESH_REVIEW" in result.reasons


def test_gate_rejects_capability_present_but_resource_out_of_scope():
    ctx = GateContext(
        current_policy_epoch="E1",
        capabilities_by_principal={"human:alice": frozenset({"transfer"})},
        authority_by_subject={
            "human:alice": _authority("human:alice", {"transfer"}, {"public"}),
        },
        hard_gates={"rights": True, "policy": True, "safety": True},
    )
    proposal = ActionProposal(
        principal="human:alice",
        action="transfer",
        target="account:X",
        capability="transfer",
        delegation_chain=("human:alice",),
        policy_epoch="E1",
    )
    result = evaluate_action(proposal, ctx)
    assert result.decision is Decision.REJECT
    assert result.reasons == ("AUTHORITY_SCOPE_DENIED",)


def test_gate_missing_authority_is_unknown_not_allow():
    ctx = GateContext(
        current_policy_epoch="E1",
        capabilities_by_principal={"human:alice": frozenset({"notify"})},
        hard_gates={"rights": True, "policy": True, "safety": True},
    )
    proposal = ActionProposal(
        principal="human:alice",
        action="notify",
        target="demo",
        capability="notify",
        delegation_chain=("human:alice",),
        policy_epoch="E1",
    )
    result = evaluate_action(proposal, ctx)
    assert result.decision is Decision.ESCALATE
    assert result.reasons == ("AUTHORITY_ENVELOPE_UNKNOWN:human:alice",)


def test_three_agent_chain_cannot_amplify_authority():
    a = AuthorityEnvelope(
        "A",
        actions=frozenset({"suggest"}),
        resources=frozenset({"public"}),
        max_depth=3,
    )
    b = AuthorityEnvelope(
        "B",
        actions=frozenset({"suggest", "low_tool"}),
        resources=frozenset({"public", "internal"}),
        max_depth=2,
    )
    c = AuthorityEnvelope(
        "C",
        actions=frozenset({"execute_high"}),
        resources=frozenset({"financial"}),
        max_depth=1,
    )
    effective = compose_authority((a, b, c))
    assert "execute_high" not in effective.actions
    assert not can_execute((a, b, c), action="execute_high", resource="financial", depth=1)


def test_design_epoch_change_marks_binding_stale():
    binding = ArtifactBinding(
        artifact_id="policy-x",
        design_epoch="E1",
        dependencies={"consent-definition": "v1", "policy": "p1"},
        required_dependencies=frozenset({"consent-definition", "policy"}),
    )
    result = validate_binding(
        binding,
        current_design_epoch="E2",
        current_dependencies={"consent-definition": "v2", "policy": "p1"},
    )
    assert result.status is BindingStatus.STALE
    assert any(reason.startswith("DESIGN_EPOCH_CHANGED") for reason in result.reasons)
    assert any(reason.startswith("DEPENDENCY_CHANGED:consent-definition") for reason in result.reasons)


def test_unknown_dependency_state_never_becomes_current():
    binding = ArtifactBinding(
        artifact_id="cache-x",
        design_epoch="E1",
        dependencies={"source": "s1"},
        required_dependencies=frozenset({"source"}),
    )
    result = validate_binding(
        binding,
        current_design_epoch="E1",
        current_dependencies={},
    )
    assert result.status is BindingStatus.UNKNOWN


def test_incomplete_dependency_closure_is_unknown_not_current():
    binding = ArtifactBinding(
        artifact_id="policy",
        design_epoch="E1",
        dependencies={},
        required_dependencies=frozenset({"consent"}),
    )
    result = validate_binding(
        binding,
        current_design_epoch="E1",
        current_dependencies={"consent": "v2"},
    )
    assert result.status is BindingStatus.UNKNOWN
    assert result.reasons == ("DEPENDENCY_CLOSURE_INCOMPLETE:consent",)


def test_undeclared_dependency_closure_is_unknown():
    binding = ArtifactBinding(
        artifact_id="legacy",
        design_epoch="E1",
        dependencies={},
    )
    result = validate_binding(
        binding,
        current_design_epoch="E1",
        current_dependencies={},
    )
    assert result.status is BindingStatus.UNKNOWN
    assert result.reasons == ("DEPENDENCY_CLOSURE_NOT_DECLARED",)


def test_signed_delegation_receipt_rejects_mutation_and_expiry_with_typed_states():
    private = Ed25519PrivateKey.generate()
    public = private.public_key()
    receipt = DelegationReceipt(
        issuer="human:alice",
        subject="agent:A",
        capabilities=("notify",),
        expires_at=2_000_000_000,
        nonce="n-1",
    )
    signed = sign_receipt(private, receipt)

    result = validate_receipt(
        public,
        signed,
        now=1_900_000_000,
        required_capability="notify",
        expected_subject="agent:A",
        expected_issuer="human:alice",
    )
    assert result.status is ReceiptValidationStatus.VALID
    assert result.receipt is not None

    payload = json.loads(base64.urlsafe_b64decode(signed["payload"]).decode("utf-8"))
    payload["capabilities"].append("execute_high")
    tampered = dict(signed)
    tampered["payload"] = base64.urlsafe_b64encode(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).decode("ascii")
    result = validate_receipt(public, tampered, now=1_900_000_000)
    assert result.status is ReceiptValidationStatus.INVALID_SIGNATURE_OR_PAYLOAD

    result = validate_receipt(public, signed, now=2_100_000_000)
    assert result.status is ReceiptValidationStatus.EXPIRED


def test_receipt_rejects_wrong_expected_issuer_with_typed_state():
    private = Ed25519PrivateKey.generate()
    receipt = DelegationReceipt(
        issuer="agent:mallory",
        subject="agent:A",
        capabilities=("notify",),
        expires_at=2_000_000_000,
        nonce="n-x",
    )
    signed = sign_receipt(private, receipt)
    result = validate_receipt(
        private.public_key(), signed, now=1_900_000_000, expected_issuer="human:alice"
    )
    assert result.status is ReceiptValidationStatus.ISSUER_MISMATCH


def test_chained_receipt_requires_verified_parent_and_rejects_substitution():
    parent = DelegationReceipt(
        issuer="human:alice",
        subject="agent:A",
        capabilities=("notify", "summarize"),
        expires_at=2_000_000_000,
        nonce="parent-1",
    )
    child = DelegationReceipt(
        issuer="agent:A",
        subject="agent:B",
        capabilities=("notify",),
        expires_at=1_990_000_000,
        nonce="child-1",
        parent_digest=receipt_digest(parent),
    )
    child_key = Ed25519PrivateKey.generate()
    signed_child = sign_receipt(child_key, child)

    result = validate_receipt(
        child_key.public_key(), signed_child, now=1_900_000_000,
        expected_issuer="agent:A", expected_subject="agent:B",
    )
    assert result.status is ReceiptValidationStatus.PARENT_RECEIPT_REQUIRED

    substitute_parent = DelegationReceipt(
        issuer="human:alice",
        subject="agent:A",
        capabilities=("notify", "summarize"),
        expires_at=2_000_000_000,
        nonce="different-parent",
    )
    result = validate_receipt(
        child_key.public_key(), signed_child, now=1_900_000_000,
        expected_issuer="agent:A", expected_subject="agent:B",
        expected_parent=substitute_parent,
    )
    assert result.status is ReceiptValidationStatus.PARENT_DIGEST_MISMATCH

    result = validate_receipt(
        child_key.public_key(), signed_child, now=1_900_000_000,
        required_capability="notify", expected_issuer="agent:A",
        expected_subject="agent:B", expected_parent=parent,
    )
    assert result.status is ReceiptValidationStatus.VALID
