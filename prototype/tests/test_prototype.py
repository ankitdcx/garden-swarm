import base64
import json

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from prototype.actiongate import ActionProposal, Decision, GateContext, evaluate_action
from prototype.authority import AuthorityEnvelope, can_execute, compose_authority
from prototype.design_epoch import ArtifactBinding, BindingStatus, validate_binding
from prototype.tokens import DelegationReceipt, sign_receipt, verify_receipt


def test_actiongate_allows_current_authorized_action():
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
        delegation_chain=("human:alice", "agent:A"),
        policy_epoch="E1",
    )
    assert evaluate_action(proposal, ctx).decision is Decision.ALLOW


def test_actiongate_rejects_stale_policy_epoch():
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
    )
    result = validate_binding(
        binding,
        current_design_epoch="E1",
        current_dependencies={},
    )
    assert result.status is BindingStatus.UNKNOWN


def test_signed_delegation_receipt_rejects_mutation_and_expiry():
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

    ok, reason, decoded = verify_receipt(
        public,
        signed,
        now=1_900_000_000,
        required_capability="notify",
        expected_subject="agent:A",
    )
    assert ok is True
    assert decoded is not None
    assert reason == "VALID_FOR_DECLARED_SCOPE"

    payload = json.loads(base64.urlsafe_b64decode(signed["payload"]).decode("utf-8"))
    payload["capabilities"].append("execute_high")
    tampered = dict(signed)
    tampered["payload"] = base64.urlsafe_b64encode(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).decode("ascii")
    ok, reason, _ = verify_receipt(public, tampered, now=1_900_000_000)
    assert ok is False
    assert reason == "INVALID_SIGNATURE_OR_PAYLOAD"

    ok, reason, _ = verify_receipt(public, signed, now=2_100_000_000)
    assert ok is False
    assert reason == "EXPIRED"
