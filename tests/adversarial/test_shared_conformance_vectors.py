import json
from pathlib import Path

from prototype.actiongate import ActionProposal, Decision, GateContext, evaluate_action
from prototype.authority import (
    ActionEligibleArtifact,
    AuthorityEnvelope,
    AuthorityProvenanceChain,
    AuthorityScope,
    authorize_artifact_trigger,
    can_execute,
    compose_authority,
)
from prototype.design_epoch import ArtifactBinding, BindingStatus, validate_binding
from prototype.tokens import ReceiptValidationStatus

ROOT = Path(__file__).resolve().parents[2]
VECTORS = json.loads((ROOT / "gsl" / "CONFORMANCE_VECTORS.json").read_text(encoding="utf-8"))["vectors"]
BY_ID = {row["vector_id"]: row for row in VECTORS}


def test_authority_intersection_vector():
    v = BY_ID["AUTHORITY-INTERSECTION-001"]
    scopes = tuple(
        AuthorityEnvelope(
            subject=row["subject"],
            actions=frozenset(row["actions"]),
            resources=frozenset(row["resources"]),
            max_depth=row["max_depth"],
        )
        for row in v["input"]["scopes"]
    )
    effective = compose_authority(scopes)
    q = v["input"]["query"]
    assert can_execute(scopes, action=q["action"], resource=q["resource"], depth=q["depth"]) is v["expected"]["allowed"]
    assert sorted(effective.actions) == v["expected"]["effective_actions"]
    assert sorted(effective.resources) == v["expected"]["effective_resources"]
    assert effective.max_depth == v["expected"]["max_depth"]


def test_design_epoch_stale_vector():
    v = BY_ID["DESIGN-EPOCH-STALE-001"]
    i = v["input"]
    result = validate_binding(
        ArtifactBinding(
            artifact_id="vector-binding",
            design_epoch=i["binding_epoch"],
            dependencies=i["bound_dependencies"],
            required_dependencies=frozenset(i["required_dependencies"]),
        ),
        current_design_epoch=i["current_epoch"],
        current_dependencies=i["current_dependencies"],
    )
    assert result.status.value == v["expected"]["status"]
    for prefix in v["expected"]["reason_prefixes"]:
        assert any(reason.startswith(prefix) for reason in result.reasons)


def test_missing_authority_gate_vector():
    v = BY_ID["ACTION-GATE-MISSING-AUTHORITY-001"]
    i = v["input"]
    proposal = ActionProposal(
        principal=i["principal"], action=i["action"], target=i["target"], capability=i["capability"],
        delegation_chain=(i["principal"],), policy_epoch=i["policy_epoch"],
    )
    result = evaluate_action(
        proposal,
        GateContext(
            current_policy_epoch=i["current_policy_epoch"],
            capabilities_by_principal={i["principal"]: frozenset({i["capability"]})},
            hard_gates={"rights": True, "policy": True, "safety": True},
        ),
    )
    assert result.decision.value == v["expected"]["decision"]
    assert result.reasons == (v["expected"]["reason"],)


def test_shared_state_authority_vector():
    v = BY_ID["SHARED-STATE-AUTHORITY-001"]
    i = v["input"]
    writer = i["writer_scope"]
    reader = i["reader_scope"]
    artifact = ActionEligibleArtifact(
        artifact_id="claim:1",
        target_action=i["artifact"]["target_action"],
        target_resource=i["artifact"]["target_resource"],
        authority_chain=AuthorityProvenanceChain(
            chain_id="chain:1",
            controlling_scopes=(AuthorityScope(
                subject=writer["subject"], actions=frozenset(writer["actions"]),
                resources=frozenset(writer["resources"]), source_ref=writer["source_ref"],
            ),),
            provenance_refs=("vector",),
        ),
    )
    acting = AuthorityScope(
        subject=reader["subject"], actions=frozenset(reader["actions"]),
        resources=frozenset(reader["resources"]), source_ref=reader["source_ref"],
    )
    assert authorize_artifact_trigger(acting_scope=acting, artifact=artifact) is v["expected"]["allowed"]


def test_receipt_vector_preserves_typed_terminal():
    v = BY_ID["RESULT-ALGEBRA-RECEIPT-001"]
    assert ReceiptValidationStatus(v["expected"]["status"]) is ReceiptValidationStatus.EXPIRED
    assert v["expected"]["boolean_collapse_forbidden"] is True
