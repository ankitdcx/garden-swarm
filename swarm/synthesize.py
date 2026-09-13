#!/usr/bin/env python3
"""Deterministically normalize Garden swarm outputs into candidate findings.

This module does not decide truth, severity, or admission. It preserves provenance
and converts model outputs into a cross-reference queue for later whole-corpus
verification.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def _parse_output(text: str) -> tuple[dict[str, Any] | None, str | None]:
    text = (text or "").strip()
    if not text:
        return None, "EMPTY_OUTPUT"
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        return None, f"INVALID_JSON:{exc.msg}"
    if not isinstance(value, dict):
        return None, "OUTPUT_NOT_OBJECT"
    return value, None


def _fingerprint(finding: dict[str, Any]) -> str:
    payload = {
        "kind": str(finding.get("kind", "")).strip().lower(),
        "current_claim": str(finding.get("current_claim", "")).strip(),
        "anchors": sorted(str(x).strip() for x in (finding.get("affected_anchors_or_terms") or [])),
        "problem": str(finding.get("problem_or_opportunity", "")).strip(),
    }
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def synthesize(receipt: dict[str, Any]) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    rejected_outputs: list[dict[str, Any]] = []

    for result in receipt.get("results", []):
        provenance = {
            "role_id": result.get("role_id"),
            "role_name": result.get("role_name"),
            "requested_model": result.get("requested_model"),
            "returned_model": result.get("returned_model"),
            "work_item": result.get("work_item"),
            "usage": result.get("usage"),
        }
        if result.get("status") != "OK":
            rejected_outputs.append({**provenance, "reason": result.get("error") or "CALL_NOT_OK"})
            continue

        parsed, error = _parse_output(result.get("output") or "")
        if error:
            rejected_outputs.append({**provenance, "reason": error})
            continue

        verdict = str(parsed.get("verdict", "NEEDS_CROSS_REFERENCE"))
        for finding in parsed.get("findings") or []:
            if not isinstance(finding, dict):
                continue
            anchors = [str(x) for x in (finding.get("affected_anchors_or_terms") or [])]
            evidence = [str(x) for x in (finding.get("evidence_needed") or [])]
            candidate = {
                "candidate_id": _fingerprint(finding),
                "status": "NEEDS_CROSS_REFERENCE",
                "source_verdict": verdict,
                "title": finding.get("title"),
                "kind": finding.get("kind"),
                "severity_claimed_by_agent": finding.get("severity"),
                "current_claim": finding.get("current_claim"),
                "problem_or_opportunity": finding.get("problem_or_opportunity"),
                "proposed_change": finding.get("proposed_change"),
                "alternatives_considered": finding.get("alternatives_considered") or [],
                "affected_anchors_or_terms": anchors,
                "evidence_needed": evidence,
                "regression_test": finding.get("regression_test"),
                "uncertainty": finding.get("uncertainty"),
                "what_would_overturn": finding.get("what_would_overturn"),
                "cross_reference_queries": sorted(set(anchors + evidence)),
                "provenance": provenance,
            }
            candidates.append(candidate)

    # Exact duplicates only. Semantic similarity is intentionally not used here:
    # a later verifier may discover that superficially similar findings differ.
    unique: dict[str, dict[str, Any]] = {}
    duplicate_sources: dict[str, list[dict[str, Any]]] = {}
    for c in candidates:
        cid = c["candidate_id"]
        if cid not in unique:
            unique[cid] = c
        else:
            duplicate_sources.setdefault(cid, []).append(c["provenance"])

    for cid, sources in duplicate_sources.items():
        unique[cid]["exact_duplicate_provenance"] = sources

    return {
        "schema": "GardenSwarmCandidateSynthesis/v0.1",
        "garden_release": receipt.get("garden_release"),
        "source_run_schema": receipt.get("schema"),
        "source_identity": receipt.get("source_identity", []),
        "admission_status": "CANDIDATES_ONLY_NOT_ADMITTED",
        "decision_rule": "No majority vote. Every candidate requires whole-corpus cross-reference and applicable tests/evidence before admission.",
        "candidate_count": len(unique),
        "candidates": list(unique.values()),
        "rejected_outputs": rejected_outputs,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("receipt")
    p.add_argument("--output", default="swarm/runs/latest-synthesis.json")
    args = p.parse_args()
    receipt = json.loads(Path(args.receipt).read_text(encoding="utf-8"))
    result = synthesize(receipt)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"candidates={result['candidate_count']}")
    print(f"rejected_outputs={len(result['rejected_outputs'])}")
    print(f"output={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
