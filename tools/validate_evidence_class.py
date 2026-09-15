#!/usr/bin/env python3
"""Packet-aware evidence validation for Garden Process v2.

The legacy structural validator is preserved in validate_evidence_class_structural.py.
`validate_evidence` remains the structural syntax check for compatibility. Runtime
blind-review admission MUST use `validate_evidence_bound`, which resolves E2/E3/E4
claims against the exact current GardenReviewPacket.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from tools.validate_evidence_class_structural import CLASSES, validate_evidence as _validate_structural


def validate_evidence(value: dict[str, Any]) -> dict[str, Any]:
    """Compatibility syntax validation only; does not grant packet-bound evidence weight."""
    return _validate_structural(value)


def _binding_index(packet: dict[str, Any]) -> dict[str, str]:
    index: dict[str, str] = {}
    target = packet.get("target") or {}
    source_file = str(target.get("source_file") or "")
    source_hash = str(target.get("source_hash") or "")
    target_id = str(target.get("target_id") or "")
    if source_file and source_hash:
        index[source_file] = source_hash
        index[f"file:{source_file}"] = source_hash
    if target_id and source_hash:
        index[f"target:{target_id}"] = source_hash

    closure = packet.get("closure") or {}
    for row in closure.get("objects") or []:
        if not isinstance(row, dict):
            continue
        digest = str(row.get("sha256") or "")
        if not digest:
            continue
        for key in (row.get("object_id"), row.get("path")):
            if key:
                index[str(key)] = digest
    return index


def _trace_candidates(packet: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in packet.get("ci_test_evidence") or []:
        if not isinstance(row, dict):
            continue
        out.append(row)
        for nested in row.get("traces") or []:
            if isinstance(nested, dict):
                out.append(nested)
    return out


def validate_evidence_bound(value: dict[str, Any], packet: dict[str, Any]) -> dict[str, Any]:
    """Validate the claimed evidence class against the exact packet bindings."""
    result = _validate_structural(value)
    claimed = result["validated_evidence_class"]
    evidence = value["evidence"]
    index = _binding_index(packet)

    if claimed == "E2":
        ref = str(evidence.get("source_ref") or "")
        digest = str(evidence.get("source_hash") or "")
        if ref not in index:
            raise ValueError(f"E2 source_ref is not bound by current packet: {ref}")
        if index[ref] != digest:
            raise ValueError("E2 source_hash does not match current packet binding")

    elif claimed == "E3":
        for binding in evidence.get("premise_bindings") or []:
            ref = str(binding.get("ref") or "")
            digest = str(binding.get("hash") or "")
            if ref not in index:
                raise ValueError(f"E3 premise ref is not bound by current packet: {ref}")
            if index[ref] != digest:
                raise ValueError(f"E3 premise hash mismatch for {ref}")

    elif claimed == "E4":
        required = ["repo_commit", "design_epoch", "environment", "command", "exit_code", "output_hash"]
        wanted = {key: evidence.get(key) for key in required}
        matches = []
        for trace in _trace_candidates(packet):
            if all(trace.get(key) == wanted[key] for key in required):
                matches.append(trace)
        if not matches:
            raise ValueError("E4 executable trace is not exactly bound in current packet ci_test_evidence")
        if evidence.get("repo_commit") != (packet.get("public_repo") or {}).get("commit"):
            raise ValueError("E4 repo_commit is not the current packet commit")
        if evidence.get("design_epoch") != packet.get("design_epoch"):
            raise ValueError("E4 DesignEpoch does not match current packet")

    result["evidence_binding_validation"] = "PASS_PACKET_BOUND"
    result["binding_packet_hash"] = packet.get("packet_hash")
    return result


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) not in {1, 2}:
        raise SystemExit("usage: validate_evidence_class.py <finding.json> [review-packet.json]")
    finding = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    if len(args) == 2:
        packet = json.loads(Path(args[1]).read_text(encoding="utf-8"))
        validated = validate_evidence_bound(finding, packet)
    else:
        validated = validate_evidence(finding)
        validated["authority_note"] = "STRUCTURAL_ONLY_NOT_PACKET_BOUND"
    print(json.dumps(validated, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
