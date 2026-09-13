#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = "63561ce9fcd4a72f44af333662b342fd18c4e99930209c30c5f801bcc5c74598"
DESIGN_EPOCH_REF = f"Garden-v15.5@{SOURCE_ROOT}"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: str) -> dict[str, Any]:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def public_functions(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    }


def decorator_name(node: ast.AST) -> str:
    if isinstance(node, ast.Call):
        return decorator_name(node.func)
    if isinstance(node, ast.Attribute):
        left = decorator_name(node.value)
        return f"{left}.{node.attr}" if left else node.attr
    if isinstance(node, ast.Name):
        return node.id
    return ""


def mcp_tools(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    tools: set[str] = set()
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if any(decorator_name(d) == "mcp.tool" for d in node.decorator_list):
            tools.add(node.name)
    return tools


def stage(name: str, passed: bool, evidence: Any) -> dict[str, Any]:
    return {
        "stage": name,
        "result": "PASS" if passed else "FAIL",
        "evidence": evidence,
    }


def validate_source_identity() -> dict[str, Any]:
    manifest = load("SOURCE_MANIFEST.json")
    epoch = load("gsl/DESIGN_EPOCH.json")
    observed = {row["path"]: row["sha256"] for row in manifest["canonical_files"]}
    expected = epoch["source_document_roots"]
    errors = []
    for name, expected_hash in expected.items():
        if observed.get(name) != expected_hash:
            errors.append(f"{name}: expected {expected_hash}, observed {observed.get(name)}")
    if epoch.get("design_epoch_ref") != DESIGN_EPOCH_REF:
        errors.append("DesignEpoch ref does not equal current v15.5 source root")
    if epoch.get("accepted") is not False or epoch.get("status") != "SPECIFIED_DESIGNEPOCH_CANDIDATE":
        errors.append("public repository must not self-issue an accepted DesignEpoch")
    return stage("DESIGN_EPOCH_SOURCE_IDENTITY", not errors, {"errors": errors})


def validate_skill_manifest() -> dict[str, Any]:
    skills = load("SKILLS.json")
    required = {
        "schema", "manifest_id", "manifest_version", "design_epoch_ref",
        "source_document_roots", "rule_and_invariant_refs", "test_and_proof_refs",
        "role_semantics", "tool_and_policy_constraints", "required_outputs_and_checks",
        "manifest_hash", "effective_from", "provenance",
    }
    missing = sorted(required - set(skills))
    unhashed = dict(skills)
    claimed = str(unhashed.pop("manifest_hash", ""))
    actual = hashlib.sha256(
        json.dumps(unhashed, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    errors = []
    if missing:
        errors.append("missing fields: " + ",".join(missing))
    if skills.get("schema") != "GardenSkillManifest/v1":
        errors.append("unsupported skill manifest schema")
    if skills.get("design_epoch_ref") != DESIGN_EPOCH_REF:
        errors.append("skill manifest is not bound to current DesignEpoch")
    if claimed != actual:
        errors.append(f"manifest_hash mismatch: claimed={claimed} actual={actual}")
    return stage("GARDEN_SKILL_MANIFEST", not errors, {"errors": errors, "computed_hash": actual})


def validate_function_contracts() -> dict[str, Any]:
    registry = load("gsl/FUNCTION_CONTRACTS.json")
    contracts = registry.get("contracts") or []
    by_name = {str(c.get("owner_qualified_name")): c for c in contracts}
    errors: list[str] = []
    bindings: list[dict[str, str]] = []
    seen: set[str] = set()
    for path in sorted((ROOT / "prototype").glob("*.py")):
        if path.name == "__init__.py":
            continue
        module = f"prototype.{path.stem}"
        for fn in sorted(public_functions(path)):
            qname = f"{module}.{fn}"
            seen.add(qname)
            contract = by_name.get(qname)
            if contract is None:
                errors.append(f"unregistered callable: {qname}")
                continue
            if contract.get("implementation_source") != path.relative_to(ROOT).as_posix():
                errors.append(f"source binding mismatch: {qname}")
            bindings.append({
                "contract_id": str(contract.get("contract_id")),
                "owner_qualified_name": qname,
                "implementation_source": path.relative_to(ROOT).as_posix(),
                "implementation_sha256": digest(path),
            })
    extras = sorted(set(by_name) - seen)
    if extras:
        errors.extend(f"contract has no public prototype callable: {name}" for name in extras)
    if registry.get("design_epoch_ref") != DESIGN_EPOCH_REF:
        errors.append("FunctionContract registry is stale for current DesignEpoch")
    return stage("FUNCTION_CONTRACT_COVERAGE", not errors, {"errors": errors, "bindings": bindings})


def validate_mcp_envelope() -> dict[str, Any]:
    payload = load("gsl/AGENT_ENVELOPES.json")
    envelopes = payload.get("envelopes") or []
    errors = []
    if payload.get("design_epoch_ref") != DESIGN_EPOCH_REF:
        errors.append("AgentEnvelope registry is stale for current DesignEpoch")
    target = next((x for x in envelopes if x.get("envelope_id") == "AGENT-ENVELOPE-GARDEN-PUBLIC-MCP-v1"), None)
    if target is None:
        errors.append("public MCP envelope missing")
        allowlist: set[str] = set()
    else:
        allowlist = set(target.get("tool_allowlist") or [])
        authority = target.get("authority") or {}
        if any(bool(authority.get(k)) for k in ("github_write", "deployment", "canonical_promotion", "real_world_actuation")):
            errors.append("public MCP envelope grants prohibited authority")
        if target.get("delegation", {}).get("allowed") is not False:
            errors.append("public MCP envelope must forbid delegation")
    observed = mcp_tools(ROOT / "server" / "mcp_service.py")
    if observed != allowlist:
        errors.append(f"MCP tool/envelope mismatch: observed={sorted(observed)} allowlist={sorted(allowlist)}")
    return stage("MCP_AGENT_ENVELOPE", not errors, {"errors": errors, "observed_tools": sorted(observed)})


def validate_typed_receipt_result() -> dict[str, Any]:
    path = ROOT / "prototype" / "tokens.py"
    names = public_functions(path)
    errors = []
    if "validate_receipt" not in names:
        errors.append("typed validate_receipt result surface missing")
    text = path.read_text(encoding="utf-8")
    if "class ReceiptValidationStatus" not in text or "class ReceiptValidationResult" not in text:
        errors.append("typed receipt result algebra missing")
    return stage("RESULT_ALGEBRA_RECEIPT_VALIDATION", not errors, {"errors": errors})


def validate_declared_references() -> dict[str, Any]:
    paths: set[str] = {
        "SOURCE_MANIFEST.json", "SKILLS.json", "AGENTS.md", "ATTACK_SURFACE.md",
        "QUICKSTART.md", "gsl/DESIGN_EPOCH.json", "gsl/FUNCTION_CONTRACTS.json",
        "gsl/AGENT_ENVELOPES.json",
    }
    skills = load("SKILLS.json")
    paths.update(str(v) for v in skills.get("source_document_roots", {}).values())
    paths.update(str(v) for v in skills.get("test_and_proof_refs", []) if not str(v).endswith("/"))
    missing = sorted(p for p in paths if not (ROOT / p).exists())
    return stage(
        "REFERENCE_CLOSURE_DECLARED_SURFACE",
        not missing,
        {
            "coverage": "DECLARED_MACHINE_REFERENCES_ONLY",
            "checked": sorted(paths),
            "unresolved": missing,
            "semantic_reference_closure_proved": False,
        },
    )


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--output", default="/tmp/garden-gsl-conformance-receipt.json")
    args = p.parse_args()

    stages = [
        validate_source_identity(),
        validate_skill_manifest(),
        validate_function_contracts(),
        validate_mcp_envelope(),
        validate_typed_receipt_result(),
        validate_declared_references(),
    ]
    overall = "PASS" if all(x["result"] == "PASS" for x in stages) else "FAIL"
    receipt = {
        "schema": "CIConformancePipelineReceipt/v1",
        "repository": "ankitdcx/garden-swarm",
        "design_epoch_ref": DESIGN_EPOCH_REF,
        "stages": stages,
        "overall": overall,
        "certification_boundary": "PASS establishes only these executable repository checks; it is not Garden semantic certification, empirical validation, canonical promotion or deployment permission.",
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"overall": overall, "output": str(out)}, sort_keys=True))
    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
