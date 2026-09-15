#!/usr/bin/env python3
"""Hardened ReviewPacket validation for Garden Process v2.

The base coherent-completeness validator remains in validate_review_packet_base.py.
This layer additionally requires explicit typing of repository diff context so a
HEAD^1 diff cannot be mistaken for a selected-target or prior-cycle delta.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from tools.validate_review_packet_base import canonical_bytes, canonical_hash
from tools.validate_review_packet_base import validate_packet as _validate_base

DIFF_SCOPE_POLICY = "TIP_COMMIT_CONTEXT_NOT_CYCLE_OR_TARGET_DELTA"
ALLOWED_RELATIONS = {"NO_CHANGE", "TOUCHES_TARGET_SOURCE", "TOUCHES_TARGET_CLOSURE", "UNRELATED_TO_SELECTED_TARGET"}


def validate_packet(packet: dict[str, Any], receipt: dict[str, Any] | None = None) -> dict[str, Any]:
    result = _validate_base(packet, receipt)
    if packet.get("diff_scope_policy") != DIFF_SCOPE_POLICY:
        raise ValueError("packet must explicitly type repository diff scope")
    if packet.get("changed_files_semantics") != "TIP_COMMIT_CONTEXT_ONLY":
        raise ValueError("changed_files must be explicitly typed as tip-commit context")
    if packet.get("changed_symbols_semantics") != "TIP_COMMIT_CONTEXT_ONLY":
        raise ValueError("changed_symbols must be explicitly typed as tip-commit context")
    for row in packet.get("diffs") or []:
        if row.get("semantic_role") != "REPOSITORY_TIP_COMMIT_CONTEXT":
            raise ValueError("diff semantic_role must be REPOSITORY_TIP_COMMIT_CONTEXT")
        if row.get("claims_selected_target_delta") is not False:
            raise ValueError("tip diff may not claim to be selected-target delta")
        if row.get("claims_prior_cycle_delta") is not False:
            raise ValueError("tip diff may not claim to be prior-cycle delta")
        if row.get("selected_target_relation") not in ALLOWED_RELATIONS:
            raise ValueError("invalid selected_target_relation")
    result["diff_scope_policy"] = DIFF_SCOPE_POLICY
    return result


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
