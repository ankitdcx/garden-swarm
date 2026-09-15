#!/usr/bin/env python3
"""Hardened GardenReviewPacket builder wrapper.

The conservative closure builder is preserved in build_review_packet_legacy.py.
This layer makes its HEAD^1 diff semantics explicit and mechanically relates the
tip-commit context to the selected target/closure before recomputing packet_hash.
It does NOT pretend tip context is a prior-cycle or selected-target delta.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tools import build_review_packet_legacy as legacy
from tools.validate_review_packet import canonical_hash, DIFF_SCOPE_POLICY

OUT = Path("agents/runtime/review-packet.json")
RECEIPT = Path("agents/runtime/packet-completeness-receipt.json")


def classify_diff_relation(packet: dict[str, Any]) -> str:
    changed = {str(x) for x in packet.get("changed_files") or []}
    if not changed:
        return "NO_CHANGE"
    target_path = str((packet.get("target") or {}).get("source_file") or "")
    if target_path and target_path in changed:
        return "TOUCHES_TARGET_SOURCE"
    closure_paths = {
        str(row.get("path"))
        for row in ((packet.get("closure") or {}).get("objects") or [])
        if isinstance(row, dict) and row.get("path")
    }
    if changed & closure_paths:
        return "TOUCHES_TARGET_CLOSURE"
    return "UNRELATED_TO_SELECTED_TARGET"


def main() -> int:
    legacy.main()
    packet = json.loads(OUT.read_text(encoding="utf-8"))
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))

    relation = classify_diff_relation(packet)
    packet["diff_scope_policy"] = DIFF_SCOPE_POLICY
    packet["changed_files_semantics"] = "TIP_COMMIT_CONTEXT_ONLY"
    packet["changed_symbols_semantics"] = "TIP_COMMIT_CONTEXT_ONLY"
    for row in packet.get("diffs") or []:
        row["semantic_role"] = "REPOSITORY_TIP_COMMIT_CONTEXT"
        row["selected_target_relation"] = relation
        row["claims_selected_target_delta"] = False
        row["claims_prior_cycle_delta"] = False
    packet["packet_construction_version"] = "GardenReviewPacketBuilder/v1.1"
    limitations = list(packet.get("construction_limitations") or [])
    if "tip-context-is-not-prior-cycle-delta" not in limitations:
        limitations.append("tip-context-is-not-prior-cycle-delta")
    packet["construction_limitations"] = limitations

    payload = {k: v for k, v in packet.items() if k != "packet_hash"}
    packet["packet_hash"] = canonical_hash(payload)
    receipt["packet_hash"] = packet["packet_hash"]
    receipt["diff_scope_policy"] = DIFF_SCOPE_POLICY
    receipt["selected_target_relation"] = relation

    OUT.write_text(json.dumps(packet, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    RECEIPT.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "cycle_id": packet["cycle_id"],
        "packet_hash": packet["packet_hash"],
        "diff_scope_policy": DIFF_SCOPE_POLICY,
        "selected_target_relation": relation,
        "completeness": receipt.get("status"),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
