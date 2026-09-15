#!/usr/bin/env python3
"""Deterministically validate producer-assigned Garden evidence classes."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

CLASSES = {"E0", "E1", "E2", "E3", "E4"}


def validate_evidence(value: dict[str, Any]) -> dict[str, Any]:
    claimed = value.get("claimed_evidence_class")
    if claimed not in CLASSES:
        raise ValueError("claimed_evidence_class must be one of E0..E4")
    evidence = value.get("evidence")
    if not isinstance(evidence, dict):
        raise ValueError("evidence object is required")

    kind = str(evidence.get("kind", "")).strip()
    if claimed == "E0":
        pass
    elif claimed == "E1":
        if not str(evidence.get("argument", "")).strip():
            raise ValueError("E1 requires reasoned argument")
        if not evidence.get("ancestry"):
            raise ValueError("E1 requires evidence ancestry")
    elif claimed == "E2":
        if kind not in {"authoritative_source", "exact_code", "exact_schema", "exact_contract"}:
            raise ValueError("E2 requires authoritative exact source/code/schema/contract evidence")
        if not evidence.get("source_ref") or not evidence.get("source_hash"):
            raise ValueError("E2 requires source_ref and source_hash")
    elif claimed == "E3":
        if kind not in {"formal_proof", "machine_checkable_contradiction"}:
            raise ValueError("E3 requires formal proof or machine-checkable contradiction")
        premises = evidence.get("premises")
        bindings = evidence.get("premise_bindings")
        if not isinstance(premises, list) or not premises:
            raise ValueError("E3 requires premises")
        if not isinstance(bindings, list) or len(bindings) != len(premises):
            raise ValueError("E3 requires one current binding per premise")
        if any(not isinstance(row, dict) or not row.get("ref") or not row.get("hash") for row in bindings):
            raise ValueError("E3 premise bindings require ref and hash")
    elif claimed == "E4":
        if kind != "executable_trace":
            raise ValueError("E4 requires executable_trace")
        required = ["repo_commit", "design_epoch", "environment", "command", "exit_code", "output_hash"]
        missing = [key for key in required if evidence.get(key) in (None, "")]
        if missing:
            raise ValueError(f"E4 missing required bindings: {missing}")

    result = dict(value)
    result["validated_evidence_class"] = claimed
    result["evidence_class_validation"] = "PASS"
    result["validated_class_immutable"] = True
    return result


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        raise SystemExit("usage: validate_evidence_class.py <finding.json>")
    path = Path(args[0])
    payload = json.loads(path.read_text(encoding="utf-8"))
    validated = validate_evidence(payload)
    print(json.dumps(validated, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
