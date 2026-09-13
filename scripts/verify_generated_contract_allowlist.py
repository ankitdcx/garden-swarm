#!/usr/bin/env python3
from __future__ import annotations

import ast
import fnmatch
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESIGN_EPOCH_REF = "Garden-v15.5@63561ce9fcd4a72f44af333662b342fd18c4e99930209c30c5f801bcc5c74598"
EXECUTABLE_DIRS = ("prototype", "server", "swarm", "tools", "scripts")


def main() -> int:
    failures: list[str] = []
    direct: set[str] = set()
    for path in sorted((ROOT / "gsl" / "contracts").glob("FUNCTION_CONTRACTS*.json")):
        if path.name.startswith("FUNCTION_CONTRACT_GENERATION"):
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("schema") != "GardenFunctionContractRegistry/v1":
            continue
        for contract in payload.get("contracts") or []:
            qname = str(contract.get("owner_qualified_name", ""))
            if qname:
                direct.add(qname)

    generated = json.loads((ROOT / "gsl/contracts/FUNCTION_CONTRACT_GENERATION.json").read_text(encoding="utf-8"))
    if generated.get("design_epoch_ref") != DESIGN_EPOCH_REF:
        failures.append("GENERATED_CONTRACT_REGISTRY_STALE")
    rules = generated.get("generation_rules") or []

    allowlists: dict[str, set[str]] = {}
    allowlist_paths = sorted((ROOT / "gsl/contracts").glob("FUNCTION_CONTRACT_GENERATION_ALLOWLIST*.json"))
    if not allowlist_paths:
        failures.append("GENERATED_CONTRACT_ALLOWLIST_MISSING")
    for path in allowlist_paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("schema") != "GardenGeneratedFunctionContractAllowlist/v1":
            failures.append(f"ALLOWLIST_SCHEMA_INVALID:{path.name}")
            continue
        if payload.get("design_epoch_ref") != DESIGN_EPOCH_REF:
            failures.append(f"ALLOWLIST_STALE:{path.name}")
        for rule_id, names in (payload.get("allowlists") or {}).items():
            bucket = allowlists.setdefault(str(rule_id), set())
            for qname in names or []:
                if qname in bucket:
                    failures.append(f"DUPLICATE_GENERATED_ALLOWLIST:{rule_id}:{qname}")
                bucket.add(str(qname))

    observed_generated: set[str] = set()
    for dirname in EXECUTABLE_DIRS:
        for path in sorted((ROOT / dirname).glob("*.py")):
            if path.name == "__init__.py":
                continue
            rel = path.relative_to(ROOT).as_posix()
            module = rel[:-3].replace("/", ".")
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
            for node in tree.body:
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                qname = f"{module}.{node.name}"
                if qname in direct:
                    continue
                matched = []
                for rule in rules:
                    if not fnmatch.fnmatchcase(rel, str(rule.get("pattern", ""))):
                        continue
                    visibility = str(rule.get("visibility", "ALL"))
                    visible = visibility == "ALL" or (visibility == "PRIVATE_ONLY" and node.name.startswith("_")) or (visibility == "PUBLIC_ONLY" and not node.name.startswith("_"))
                    if visible:
                        matched.append(rule)
                if len(matched) != 1:
                    failures.append(f"{qname}:EXPECTED_ONE_GENERATION_RULE_FOUND_{len(matched)}")
                    continue
                rule_id = str(matched[0].get("rule_id", ""))
                if qname not in allowlists.get(rule_id, set()):
                    failures.append(f"{qname}:NOT_EXPLICITLY_ALLOWLISTED_FOR_{rule_id}")
                else:
                    observed_generated.add(qname)

    declared_generated = set().union(*allowlists.values()) if allowlists else set()
    orphaned = sorted(declared_generated - observed_generated)
    failures.extend(f"ORPHAN_GENERATED_ALLOWLIST:{qname}" for qname in orphaned)

    result = {
        "schema": "GeneratedFunctionContractAllowlistReceipt/v1",
        "design_epoch_ref": DESIGN_EPOCH_REF,
        "direct_contract_count": len(direct),
        "allowlist_shard_count": len(allowlist_paths),
        "explicit_generated_binding_count": len(observed_generated),
        "failures": failures,
        "result": "PASS" if not failures else "FAIL",
        "boundary": "PASS proves that path-pattern generation cannot silently admit a new callable; it does not by itself prove each inherited semantic contract is correct."
    }
    print(json.dumps(result, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
