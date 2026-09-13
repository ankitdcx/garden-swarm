#!/usr/bin/env python3
"""Fail-closed multi-agent integration provenance guard for Garden.

This module does not merge branches or grant authority. It compares declared
AgentWorkIntent/v1 objects and validates an IntegrationReceipt/v1 when concurrent
changes overlap by path, symbol, semantic domain, invariant, or contract.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Iterable, Mapping

WORK_INTENT_SCHEMA = "AgentWorkIntent/v1"
INTEGRATION_RECEIPT_SCHEMA = "IntegrationReceipt/v1"
GUARD_RECEIPT_SCHEMA = "IntegrationGuardReceipt/v1"
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_ALLOWED_PARALLEL_MODES = {"SERIAL", "INDEPENDENT_COMPARISON", "COORDINATED"}
_ALLOWED_COMPARE_RESULTS = {"COMPATIBLE", "INTENTIONAL_ALTERNATIVES", "BLOCKED"}


def _nonempty_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _string_set(value: Any, field: str, *, required: bool = False) -> frozenset[str]:
    if value is None:
        value = []
    if not isinstance(value, list) or any(not isinstance(v, str) or not v.strip() for v in value):
        raise ValueError(f"{field} must be a list of non-empty strings")
    result = frozenset(v.strip() for v in value)
    if required and not result:
        raise ValueError(f"{field} must not be empty")
    return result


def normalize_path(path: str) -> str:
    raw = _nonempty_text(path, "target_paths[]").replace("\\", "/")
    while raw.startswith("./"):
        raw = raw[2:]
    p = PurePosixPath(raw)
    if p.is_absolute() or ".." in p.parts:
        raise ValueError(f"unsafe repository path: {path!r}")
    normalized = str(p)
    if normalized in {"", "."}:
        raise ValueError("repository path must identify a file or directory")
    return normalized.rstrip("/")


@dataclass(frozen=True)
class AgentWorkIntent:
    intent_id: str
    agent_id: str
    task_id: str
    base_sha: str
    target_paths: frozenset[str]
    target_symbols: frozenset[str]
    semantic_domains: frozenset[str]
    affected_invariants: frozenset[str]
    affected_contracts: frozenset[str]
    intended_effect: str
    parallel_mode: str

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "AgentWorkIntent":
        if data.get("schema") != WORK_INTENT_SCHEMA:
            raise ValueError(f"schema must be {WORK_INTENT_SCHEMA}")
        base_sha = _nonempty_text(data.get("base_sha"), "base_sha").lower()
        if not _SHA_RE.fullmatch(base_sha):
            raise ValueError("base_sha must be a full 40-character lowercase Git SHA")
        mode = _nonempty_text(data.get("parallel_mode"), "parallel_mode").upper()
        if mode not in _ALLOWED_PARALLEL_MODES:
            raise ValueError(f"parallel_mode must be one of {sorted(_ALLOWED_PARALLEL_MODES)}")
        paths = frozenset(normalize_path(v) for v in _string_set(data.get("target_paths"), "target_paths", required=True))
        return cls(
            intent_id=_nonempty_text(data.get("intent_id"), "intent_id"),
            agent_id=_nonempty_text(data.get("agent_id"), "agent_id"),
            task_id=_nonempty_text(data.get("task_id"), "task_id"),
            base_sha=base_sha,
            target_paths=paths,
            target_symbols=_string_set(data.get("target_symbols"), "target_symbols"),
            semantic_domains=_string_set(data.get("semantic_domains"), "semantic_domains", required=True),
            affected_invariants=_string_set(data.get("affected_invariants"), "affected_invariants"),
            affected_contracts=_string_set(data.get("affected_contracts"), "affected_contracts"),
            intended_effect=_nonempty_text(data.get("intended_effect"), "intended_effect"),
            parallel_mode=mode,
        )

    def evidence_hash(self) -> str:
        canonical = json.dumps(
            {
                "intent_id": self.intent_id,
                "agent_id": self.agent_id,
                "task_id": self.task_id,
                "base_sha": self.base_sha,
                "target_paths": sorted(self.target_paths),
                "target_symbols": sorted(self.target_symbols),
                "semantic_domains": sorted(self.semantic_domains),
                "affected_invariants": sorted(self.affected_invariants),
                "affected_contracts": sorted(self.affected_contracts),
                "intended_effect": self.intended_effect,
                "parallel_mode": self.parallel_mode,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()


def _path_pairs(a: Iterable[str], b: Iterable[str]) -> list[list[str]]:
    overlaps: list[list[str]] = []
    for left in sorted(a):
        for right in sorted(b):
            if left == right or left.startswith(right + "/") or right.startswith(left + "/"):
                overlaps.append([left, right])
    return overlaps


def compare_intents(current: AgentWorkIntent, other: AgentWorkIntent) -> dict[str, Any]:
    path_pairs = _path_pairs(current.target_paths, other.target_paths)
    shared_symbols = sorted(current.target_symbols & other.target_symbols)
    shared_domains = sorted(current.semantic_domains & other.semantic_domains)
    shared_invariants = sorted(current.affected_invariants & other.affected_invariants)
    shared_contracts = sorted(current.affected_contracts & other.affected_contracts)
    reasons: list[str] = []
    if path_pairs:
        reasons.append("PATH_OVERLAP")
    if shared_symbols:
        reasons.append("SYMBOL_OVERLAP")
    if shared_domains:
        reasons.append("SEMANTIC_DOMAIN_OVERLAP")
    if shared_invariants:
        reasons.append("INVARIANT_OVERLAP")
    if shared_contracts:
        reasons.append("CONTRACT_OVERLAP")
    if current.base_sha != other.base_sha:
        reasons.append("DIVERGENT_BASE_SHA")

    collision = any(r != "DIVERGENT_BASE_SHA" for r in reasons)
    return {
        "other_intent_id": other.intent_id,
        "other_intent_hash": other.evidence_hash(),
        "classification": "POTENTIAL_COLLISION" if collision else "NO_OVERLAP",
        "reasons": reasons,
        "path_overlaps": path_pairs,
        "shared_symbols": shared_symbols,
        "shared_semantic_domains": shared_domains,
        "shared_invariants": shared_invariants,
        "shared_contracts": shared_contracts,
        "requires_integration_receipt": collision,
    }


def _validate_receipt(receipt: Mapping[str, Any], current: AgentWorkIntent, required_ids: set[str]) -> tuple[bool, list[str], str | None]:
    errors: list[str] = []
    if receipt.get("schema") != INTEGRATION_RECEIPT_SCHEMA:
        errors.append(f"schema must be {INTEGRATION_RECEIPT_SCHEMA}")
    if receipt.get("current_intent_id") != current.intent_id:
        errors.append("current_intent_id does not bind the current work intent")
    if receipt.get("base_sha") != current.base_sha:
        errors.append("base_sha does not bind the current work intent base")
    participants = set(receipt.get("concurrent_intent_ids") or [])
    missing = sorted(required_ids - participants)
    if missing:
        errors.append("receipt omits colliding intents: " + ", ".join(missing))
    result = receipt.get("semantic_compare")
    if result not in _ALLOWED_COMPARE_RESULTS:
        errors.append(f"semantic_compare must be one of {sorted(_ALLOWED_COMPARE_RESULTS)}")
    if result == "COMPATIBLE" and not receipt.get("tests_after_integration"):
        errors.append("COMPATIBLE requires tests_after_integration evidence")
    if result in {"COMPATIBLE", "INTENTIONAL_ALTERNATIVES"} and not receipt.get("composition_evidence"):
        errors.append("non-blocking semantic_compare requires composition_evidence")
    return not errors, errors, result if isinstance(result, str) else None


def assess_intents(current: AgentWorkIntent, others: Iterable[AgentWorkIntent], receipt: Mapping[str, Any] | None = None) -> dict[str, Any]:
    comparisons = [compare_intents(current, other) for other in others if other.intent_id != current.intent_id]
    collisions = [c for c in comparisons if c["requires_integration_receipt"]]
    required_ids = {c["other_intent_id"] for c in collisions}
    disposition = "PASS"
    receipt_status: dict[str, Any] | None = None

    if collisions:
        if receipt is None:
            disposition = "REQUIRES_INTEGRATION_RECEIPT"
        else:
            valid, errors, result = _validate_receipt(receipt, current, required_ids)
            receipt_status = {"valid": valid, "errors": errors, "semantic_compare": result}
            if not valid or result == "BLOCKED":
                disposition = "BLOCKED"
            else:
                disposition = "PASS"

    return {
        "schema": GUARD_RECEIPT_SCHEMA,
        "current_intent_id": current.intent_id,
        "current_intent_hash": current.evidence_hash(),
        "base_sha": current.base_sha,
        "comparisons": comparisons,
        "required_concurrent_intent_ids": sorted(required_ids),
        "integration_receipt_status": receipt_status,
        "disposition": disposition,
        "authority_effect": "NONE_PROPOSAL_ONLY",
        "uncertainty": "Undeclared or stale work intents cannot be inferred by this guard; absence outside the supplied intent set is not proof of no collision.",
    }


def _load_json(path: str) -> Mapping[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("current", help="current AgentWorkIntent/v1 JSON")
    parser.add_argument("others", nargs="*", help="concurrent AgentWorkIntent/v1 JSON files")
    parser.add_argument("--receipt", help="optional IntegrationReceipt/v1 JSON")
    args = parser.parse_args()

    current = AgentWorkIntent.from_mapping(_load_json(args.current))
    others = [AgentWorkIntent.from_mapping(_load_json(p)) for p in args.others]
    receipt = _load_json(args.receipt) if args.receipt else None
    result = assess_intents(current, others, receipt)
    print(json.dumps(result, indent=2, sort_keys=True))
    return {"PASS": 0, "REQUIRES_INTEGRATION_RECEIPT": 2, "BLOCKED": 3}[result["disposition"]]


if __name__ == "__main__":
    raise SystemExit(main())
