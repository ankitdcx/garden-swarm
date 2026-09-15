#!/usr/bin/env python3
"""Fail-closed validator for coherent-complete GardenReviewPacket/v1."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REQUIRED_PACKET_FIELDS = [
    "schema", "cycle_id", "public_repo", "private_repo", "canonical_version",
    "design_epoch", "canonical_source_root_sha256", "process_version", "target",
    "diffs", "changed_files", "changed_symbols", "closure", "affected_objects",
    "ci_test_evidence", "linked_findings", "active_freezes", "exclusions",
    "closure_frontier", "packet_construction_version"
]


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _validate_repo_binding(name: str, value: Any) -> None:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be object")
    status = value.get("status", "BOUND")
    if status == "BOUND":
        if not value.get("commit"):
            raise ValueError(f"{name} BOUND requires commit")
    elif name == "private_repo" and status == "PRIVATE_REPO_INACCESSIBLE":
        if not value.get("reason"):
            raise ValueError("private inaccessible status requires reason")
    else:
        raise ValueError(f"unsupported {name} status: {status}")


def validate_packet(packet: dict[str, Any], receipt: dict[str, Any] | None = None) -> dict[str, Any]:
    missing = [key for key in REQUIRED_PACKET_FIELDS if key not in packet]
    if missing:
        raise ValueError(f"missing packet fields: {missing}")
    if packet.get("schema") != "GardenReviewPacket/v1":
        raise ValueError("unsupported packet schema")
    if not str(packet.get("cycle_id", "")).strip():
        raise ValueError("cycle_id required")
    _validate_repo_binding("public_repo", packet["public_repo"])
    _validate_repo_binding("private_repo", packet["private_repo"])
    if not packet.get("canonical_version") or not packet.get("design_epoch"):
        raise ValueError("canonical version and DesignEpoch required")
    if not packet.get("canonical_source_root_sha256") or not packet.get("process_version"):
        raise ValueError("source root and ProcessVersion required")

    target = packet.get("target")
    if not isinstance(target, dict) or not target.get("target_id") or not target.get("source_hash"):
        raise ValueError("target_id and source_hash required")

    diffs = packet.get("diffs")
    if not isinstance(diffs, list) or not diffs:
        raise ValueError("at least one diff/NO_CHANGE proof required")
    for row in diffs:
        if not isinstance(row, dict) or row.get("mode") not in {"DIFF", "NO_CHANGE"}:
            raise ValueError("each diff requires mode DIFF or NO_CHANGE")
        if not row.get("repo") or not row.get("base") or not row.get("head") or not row.get("digest"):
            raise ValueError("diff binding requires repo/base/head/digest")

    for key in ["changed_files", "changed_symbols", "ci_test_evidence", "linked_findings", "active_freezes", "exclusions"]:
        if not isinstance(packet.get(key), list):
            raise ValueError(f"{key} must be list")

    closure = packet.get("closure")
    if not isinstance(closure, dict):
        raise ValueError("closure must be object")
    included = closure.get("included_objects")
    declared = closure.get("declared_objects")
    if not isinstance(included, list) or not isinstance(declared, list):
        raise ValueError("closure requires declared_objects and included_objects lists")

    exclusions = packet.get("exclusions")
    excluded_ids = set()
    for row in exclusions:
        if not isinstance(row, dict) or not row.get("object_id") or not row.get("reason_code") or not row.get("reason"):
            raise ValueError("every exclusion requires object_id, reason_code and reason")
        excluded_ids.add(str(row["object_id"]))

    included_ids = {str(x) for x in included}
    declared_ids = {str(x) for x in declared}
    if included_ids & excluded_ids:
        raise ValueError("object cannot be both included and excluded")
    unresolved = declared_ids - included_ids - excluded_ids
    if unresolved:
        raise ValueError(f"declared closure objects unresolved: {sorted(unresolved)}")

    frontier = packet.get("closure_frontier")
    if not isinstance(frontier, dict) or frontier.get("status") != "CLOSED_UNDER_DECLARED_ALGORITHM":
        raise ValueError("closure frontier must prove closure under declared algorithm")
    if frontier.get("unresolved_candidates") not in ([], None):
        raise ValueError("closure frontier has unresolved candidates")

    affected = packet.get("affected_objects")
    if not isinstance(affected, dict):
        raise ValueError("affected_objects must be object")
    for key in ["schemas", "function_contracts", "invariants", "tests", "registries", "implementation_bindings"]:
        if not isinstance(affected.get(key), list):
            raise ValueError(f"affected_objects.{key} must be list")

    payload_without_hash = {k: v for k, v in packet.items() if k != "packet_hash"}
    computed = canonical_hash(payload_without_hash)
    if packet.get("packet_hash") != computed:
        raise ValueError("packet_hash mismatch")

    if receipt is not None:
        if receipt.get("schema") != "PacketCompletenessReceipt/v1":
            raise ValueError("unsupported completeness receipt schema")
        if receipt.get("criterion") != "COHERENT_COMPLETE":
            raise ValueError("criterion must be COHERENT_COMPLETE")
        if receipt.get("cycle_id") != packet.get("cycle_id") or receipt.get("packet_hash") != computed:
            raise ValueError("receipt cycle/hash mismatch")
        if receipt.get("status") != "PASS":
            raise ValueError("completeness receipt is not PASS")
        if receipt.get("manual_unexplained_exclusions") not in (0, None):
            raise ValueError("unexplained manual exclusions present")

    return {
        "schema": "PacketValidationReceipt/v1",
        "cycle_id": packet["cycle_id"],
        "packet_hash": computed,
        "criterion": "COHERENT_COMPLETE",
        "status": "PASS"
    }


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not 1 <= len(args) <= 2:
        raise SystemExit("usage: validate_review_packet.py <packet.json> [completeness-receipt.json]")
    packet = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    receipt = json.loads(Path(args[1]).read_text(encoding="utf-8")) if len(args) == 2 else None
    print(json.dumps(validate_packet(packet, receipt), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
