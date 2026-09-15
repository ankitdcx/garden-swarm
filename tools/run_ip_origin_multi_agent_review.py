#!/usr/bin/env python3
"""Multi-family OpenRouter review of the public Garden IP origin inventory.

Proposal evidence only. This evaluates provenance/origin plausibility, duplicate
lineage, and candidate protection routes. It never files patents, grants rights,
or turns an abstract idea into exclusive property.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from tools.run_paid_matrix_review import _call

INVENTORY = Path("IP_ORIGIN_INVENTORY.json")
SELECTION = Path("agents/runtime/paid-selection.json")
OUT = Path("ip-origin-multi-agent-review.json")
BATCH_SIZE = 15
WORKFLOW_COST_CEILING_USD = 1.00

ROLE_PROMPTS = {
    "novelty_prior_art": (
        "Evaluate whether each candidate looks genuinely new versus known pre-existing ideas. "
        "Do not equate a new name or combination with novelty. Identify likely prior-art building blocks "
        "and distinguish a potentially new technical combination from an old principle."
    ),
    "patent_scope": (
        "Evaluate candidate patent relevance only: technical character, concrete mechanism, likely novelty/non-obviousness risk, "
        "and whether the record needs a narrower claim. Do not say a patent exists unless the inventory says FILED or GRANTED."
    ),
    "copyright_other_rights": (
        "Classify likely protection routes: copyright in expression/code/schema text, patent candidate, trade-secret candidate, "
        "trademark/design-right candidate, contract/licence only, or abstract concept with no automatic exclusivity. "
        "Separate the underlying idea from its written/code expression."
    ),
    "duplicate_lineage": (
        "Look for aliases, renamed descendants, decompositions, and overlapping families. Prefer one canonical origin family with "
        "lineage links instead of double-counting the same mechanism. Flag historical portfolio inflation or duplicate IDs."
    ),
}

ALLOWED_ORIGIN = {
    "GARDEN_ORIGIN_SUPPORTED",
    "GARDEN_ORIGIN_PLAUSIBLE",
    "ORIGIN_UNCERTAIN",
    "LIKELY_PREEXISTING",
    "DUPLICATE_OR_ALIAS",
}


def _review_prompt(role: str, batch: list[dict[str, Any]]) -> str:
    return f"""You are one independent reviewer in a Garden IP-origin audit.
Role: {role}
Task: {ROLE_PROMPTS[role]}

Important boundaries:
- 'Garden-origin' means the supplied historical provenance supports Garden as the source of this specific candidate mechanism or expression. It is NOT a legal conclusion that every abstract idea is exclusively owned.
- Existing scientific laws, equations, standard algorithms, public standards, and known third-party technologies are not Garden inventions merely because Garden uses them.
- A new technical combination or implementation may still be a candidate even when its ingredients are old.
- Patent/copyright status is never upgraded by this review. No filing, grant, infringement, or enforceability is established.
- Be adversarial. Reject duplicate counting and renamed prior art.

Return ONLY JSON with top-level key 'items'. 'items' must contain one object per candidate ID with:
id, origin_status, protection_candidates, closest_known_preexisting_basis, duplicate_or_lineage_notes, confidence, decisive_next_check.
origin_status must be one of {sorted(ALLOWED_ORIGIN)}.
confidence must be LOW, MEDIUM, or HIGH.
protection_candidates must be an array drawn from PATENT_CANDIDATE, COPYRIGHT_EXPRESSION, TRADE_SECRET_CANDIDATE, TRADEMARK_CANDIDATE, DESIGN_RIGHT_CANDIDATE, CONTRACT_LICENSE, ABSTRACT_IDEA_NO_AUTOMATIC_EXCLUSIVITY.

Candidates:\n{json.dumps(batch, ensure_ascii=False, separators=(',', ':'))}
"""


def _validate(raw: dict[str, Any], expected_ids: set[str]) -> list[dict[str, Any]]:
    items = raw.get("items")
    if not isinstance(items, list):
        raise ValueError("missing items array")
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for row in items:
        if not isinstance(row, dict):
            raise ValueError("item is not object")
        rid = str(row.get("id", ""))
        if rid not in expected_ids or rid in seen:
            raise ValueError(f"invalid/duplicate id: {rid}")
        if row.get("origin_status") not in ALLOWED_ORIGIN:
            raise ValueError(f"invalid origin status for {rid}")
        if row.get("confidence") not in {"LOW", "MEDIUM", "HIGH"}:
            raise ValueError(f"invalid confidence for {rid}")
        if not isinstance(row.get("protection_candidates"), list):
            raise ValueError(f"invalid protection candidates for {rid}")
        seen.add(rid)
        out.append(row)
    if seen != expected_ids:
        raise ValueError(f"missing ids: {sorted(expected_ids - seen)}")
    return out


def main() -> int:
    if not os.environ.get("OPENROUTER_API_KEY"):
        raise SystemExit("OPENROUTER_API_KEY unavailable")

    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    if inventory.get("schema") != "GardenIPOriginInventory/v1":
        raise SystemExit("unsupported inventory schema")
    records = inventory.get("records")
    if not isinstance(records, list) or not records:
        raise SystemExit("inventory has no records")
    ids = [str(r.get("id", "")) for r in records]
    if len(ids) != len(set(ids)) or any(not i for i in ids):
        raise SystemExit("inventory IDs must be unique/non-empty")

    selection = json.loads(SELECTION.read_text(encoding="utf-8"))
    selected_rows = [row for row in selection.get("selected", []) if isinstance(row, dict) and row.get("family")]
    selected = {str(row["family"]): row for row in selected_rows}
    approved_source = selection.get("approved_families") or list(selected)
    approved = {str(x) for x in approved_source if x}
    families = [family for family in selected if family in approved]
    if len(families) < 2:
        raise SystemExit("IP origin review requires at least two approved independent reviewer families")
    if "deepseek" not in families or "qwen" not in families:
        raise SystemExit("IP origin review requires DeepSeek and Qwen as anchor families")
    if selection.get("provider_policy", {}).get("data_collection") != "deny":
        raise SystemExit("provider data_collection must be deny")

    calls: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    cumulative = 0.0
    complete = True
    per_call = float(selection["routine_model_call_cost_ceiling_usd"])

    batches = [records[i:i + BATCH_SIZE] for i in range(0, len(records), BATCH_SIZE)]
    for batch_index, batch in enumerate(batches):
        expected = {str(r["id"]) for r in batch}
        batch_reviews: dict[str, list[dict[str, Any]]] = {}

        for role in ROLE_PROMPTS:
            for family in families:
                if WORKFLOW_COST_CEILING_USD - cumulative < per_call:
                    complete = False
                    calls.append({
                        "batch": batch_index,
                        "role": role,
                        "family": family,
                        "status": "WORKFLOW_BUDGET_GUARD",
                    })
                    continue
                raw, attempt = _call(
                    model=selected[family],
                    prompt=_review_prompt(role, batch),
                    selection=selection,
                    reasoning={"effort": "none"},
                )
                cost = attempt.get("cost")
                if isinstance(cost, (int, float)) and cost >= 0:
                    cumulative += float(cost)
                attempt.update({"batch": batch_index, "role": role})
                calls.append(attempt)
                if raw is None:
                    complete = False
                    continue
                try:
                    validated = _validate(raw, expected)
                except Exception as exc:
                    complete = False
                    calls.append({
                        "batch": batch_index,
                        "role": role,
                        "family": family,
                        "status": "INVALID_OUTPUT",
                        "detail": str(exc),
                        "cost": 0.0,
                    })
                    continue
                key = f"{family}:{role}"
                batch_reviews[key] = validated
                for item in validated:
                    findings.append({"batch": batch_index, "family": family, "role": role, **item})

        # Every approved family independently cross-examines the complete role-review digest.
        if batch_reviews:
            digest = json.dumps(batch_reviews, ensure_ascii=False, separators=(",", ":"))
            for family in families:
                if WORKFLOW_COST_CEILING_USD - cumulative < per_call:
                    complete = False
                    calls.append({
                        "batch": batch_index,
                        "role": "cross_exam",
                        "family": family,
                        "status": "WORKFLOW_BUDGET_GUARD",
                    })
                    continue
                other_families = [f for f in families if f != family]
                prompt = f"""You are the {family} cross-examiner in a Garden IP-origin audit.
Review the independent role outputs below, especially disagreements with the other approved families {other_families}.
Do not create ownership or patent rights. Identify overclaim, duplicate counting, prior-art blindness, correlated reasoning, and unsupported confidence.
Return ONLY JSON with keys: batch, disagreements, corrections, unresolved, confidence.

{digest}"""
                raw, attempt = _call(
                    model=selected[family],
                    prompt=prompt,
                    selection=selection,
                    reasoning={"effort": "none"},
                )
                cost = attempt.get("cost")
                if isinstance(cost, (int, float)) and cost >= 0:
                    cumulative += float(cost)
                attempt.update({"batch": batch_index, "role": "cross_exam"})
                calls.append(attempt)
                if raw is None:
                    complete = False
                    continue
                findings.append({"batch": batch_index, "family": family, "role": "cross_exam", "review": raw})

    receipt = {
        "schema": "GardenIPOriginMultiAgentReview/v2",
        "inventory_commit": os.environ.get("GITHUB_SHA"),
        "inventory_record_count": len(records),
        "families": families,
        "role_agents_per_batch": len(ROLE_PROMPTS) * len(families),
        "cross_examiners_per_batch": len(families),
        "batch_size": BATCH_SIZE,
        "workflow_cost_ceiling_usd": WORKFLOW_COST_CEILING_USD,
        "actual_cost_usd": round(cumulative, 8),
        "provider_policy": {"data_collection": "deny"},
        "complete": complete,
        "calls": calls,
        "findings": findings,
        "semantic_delta_admitted": False,
        "patent_status_admitted": False,
        "legal_opinion": False,
    }
    OUT.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "records": len(records),
        "families": families,
        "role_agents_per_batch": receipt["role_agents_per_batch"],
        "cross_examiners_per_batch": receipt["cross_examiners_per_batch"],
        "calls": len(calls),
        "actual_cost_usd": receipt["actual_cost_usd"],
        "complete": complete,
    }, sort_keys=True))
    if not complete:
        raise SystemExit("multi-agent IP origin review incomplete; receipt uploaded for inspection")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
