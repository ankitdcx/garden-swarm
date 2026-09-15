#!/usr/bin/env python3
"""Budget-correct multi-family OpenRouter review for Garden public IP-origin data.

The base inventory may be extended by IP_ORIGIN_SUPPLEMENT.json. Each batch gets
one rotated specialist role from every approved family, followed by one compact
cross-examination from every family. The wire format is deliberately coded and
bounded so a 25-record batch cannot consume the entire final-answer token budget
before returning parseable JSON.

Proposal evidence only: no filing, grant, ownership, infringement,
enforceability, legal opinion, or semantic admission is created here.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from tools.run_paid_matrix_review import _call

INVENTORY = Path("IP_ORIGIN_INVENTORY.json")
SUPPLEMENT = Path("IP_ORIGIN_SUPPLEMENT.json")
SELECTION = Path("agents/runtime/paid-selection.json")
OUT = Path("ip-origin-multi-agent-review.json")
BATCH_SIZE = 25
WORKFLOW_COST_CEILING_USD = 0.80

ROLE_PROMPTS = [
    ("novelty_prior_art", "Judge whether the specific Garden delta is genuinely new versus known prior ideas; old ingredients or a new name are not novelty."),
    ("patent_scope", "Screen technical/patent-candidate relevance and narrowness only; never invent filing or grant status."),
    ("copyright_other_rights", "Separate idea from expression and classify plausible protection routes."),
    ("duplicate_lineage", "Detect aliases, renames, splits, merges and historical renumbering; reject double counting."),
]

ORIGIN_BY_CODE = {
    "S": "GARDEN_ORIGIN_SUPPORTED",
    "P": "GARDEN_ORIGIN_PLAUSIBLE",
    "U": "ORIGIN_UNCERTAIN",
    "E": "LIKELY_PREEXISTING",
    "D": "DUPLICATE_OR_ALIAS",
}
CODE_BY_ORIGIN = {v: k for k, v in ORIGIN_BY_CODE.items()}
PROTECTION_BY_CODE = {
    "P": "PATENT_CANDIDATE",
    "C": "COPYRIGHT_EXPRESSION",
    "S": "TRADE_SECRET_CANDIDATE",
    "T": "TRADEMARK_CANDIDATE",
    "D": "DESIGN_RIGHT_CANDIDATE",
    "L": "CONTRACT_LICENSE",
    "A": "ABSTRACT_IDEA_NO_AUTOMATIC_EXCLUSIVITY",
}
CONFIDENCE_BY_CODE = {"L": "LOW", "M": "MEDIUM", "H": "HIGH"}


def load_records() -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    inv = json.loads(INVENTORY.read_text(encoding="utf-8"))
    if inv.get("schema") != "GardenIPOriginInventory/v1":
        raise SystemExit("unsupported inventory schema")
    records = list(inv.get("records") or [])
    supplement = None
    if SUPPLEMENT.exists():
        supplement = json.loads(SUPPLEMENT.read_text(encoding="utf-8"))
        if supplement.get("schema") != "GardenIPOriginSupplement/v1":
            raise SystemExit("unsupported IP origin supplement schema")
        records.extend(list(supplement.get("additional_records") or []))
    if not records:
        raise SystemExit("inventory empty")
    ids = [str(x.get("id", "")) for x in records]
    if any(not x for x in ids) or len(ids) != len(set(ids)):
        raise SystemExit("combined inventory ids invalid or duplicated")
    return records, supplement


def _prompt(role: str, instruction: str, batch: list[dict[str, Any]]) -> str:
    compact_candidates = [[str(row["id"]), str(row.get("name", "")), str(row.get("group", ""))] for row in batch]
    return f"""You are one independent reviewer in a Garden IP-origin audit.
ROLE={role}
{instruction}

Boundaries: Garden-origin means provenance for a specific mechanism/combination/expression, not automatic legal exclusivity. Known science, equations, standards, generic algorithms and third-party technology are not Garden inventions merely because Garden uses them. A concrete new combination can still be a candidate. No model may create filing, grant, ownership, infringement, enforceability or legal-opinion status.

Return ONLY compact JSON with exactly one row per candidate, in the same ID set:
{{"r":[[id,origin,protections,confidence],...]}}
origin code: S=supported Garden origin, P=plausible Garden origin, U=uncertain, E=likely pre-existing, D=duplicate/alias.
protections: a string containing zero or more unique codes from P=patent candidate, C=copyright expression, S=trade-secret candidate, T=trademark candidate, D=design-right candidate, L=contract/licence, A=abstract idea/no automatic exclusivity. Use "" if none.
confidence: L/M/H.
No explanations, markdown, extra keys, or prose.

Candidates:\n{json.dumps(compact_candidates, ensure_ascii=False, separators=(',', ':'))}
"""


def _validate_specialist(raw: dict[str, Any], expected: set[str]) -> list[dict[str, Any]]:
    rows = raw.get("r")
    if not isinstance(rows, list):
        raise ValueError("missing compact r array")
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, list) or len(row) != 4:
            raise ValueError("specialist row must be [id,origin,protections,confidence]")
        rid, origin_code, protection_codes, confidence_code = map(str, row)
        if rid not in expected or rid in seen:
            raise ValueError(f"bad id {rid}")
        if origin_code not in ORIGIN_BY_CODE:
            raise ValueError(f"bad origin code {origin_code} for {rid}")
        if confidence_code not in CONFIDENCE_BY_CODE:
            raise ValueError(f"bad confidence code {confidence_code} for {rid}")
        if len(set(protection_codes)) != len(protection_codes) or any(c not in PROTECTION_BY_CODE for c in protection_codes):
            raise ValueError(f"bad protection codes {protection_codes} for {rid}")
        seen.add(rid)
        out.append({
            "id": rid,
            "origin_status": ORIGIN_BY_CODE[origin_code],
            "protection_candidates": [PROTECTION_BY_CODE[c] for c in protection_codes],
            "confidence": CONFIDENCE_BY_CODE[confidence_code],
        })
    if seen != expected:
        raise ValueError(f"missing ids {sorted(expected-seen)}")
    return out


def _cross_prompt(family: str, batch: list[dict[str, Any]], batch_reviews: dict[str, Any]) -> str:
    ids = [str(x["id"]) for x in batch]
    return f"""You are the {family} cross-examiner for one Garden IP-origin batch.
Challenge overclaim, prior-art blindness, duplicate/alias counting, protection-category mistakes and unsupported confidence. Do not create legal rights.

Return ONLY compact JSON:
{{"d":[[id,reason,origin,protections,confidence],...],"u":[id,...]}}
Only include disputed/corrected candidates in d. reason <= 6 words. origin/protections/confidence use the same codes as the specialist protocol. u lists materially unresolved IDs. Empty arrays are valid. No extra keys or prose.
Allowed IDs: {json.dumps(ids,separators=(',',':'))}
Specialist judgments: {json.dumps(batch_reviews,ensure_ascii=False,separators=(',',':'))}
"""


def _validate_cross(raw: dict[str, Any], expected: set[str]) -> dict[str, Any]:
    disputes = raw.get("d")
    unresolved = raw.get("u")
    if not isinstance(disputes, list) or not isinstance(unresolved, list):
        raise ValueError("cross-exam requires d and u arrays")
    clean_d = []
    seen = set()
    for row in disputes:
        if not isinstance(row, list) or len(row) != 5:
            raise ValueError("cross row must be [id,reason,origin,protections,confidence]")
        rid, reason, origin_code, protection_codes, confidence_code = map(str, row)
        if rid not in expected or rid in seen:
            raise ValueError(f"bad cross id {rid}")
        if origin_code not in ORIGIN_BY_CODE or confidence_code not in CONFIDENCE_BY_CODE:
            raise ValueError(f"bad cross codes {rid}")
        if len(set(protection_codes)) != len(protection_codes) or any(c not in PROTECTION_BY_CODE for c in protection_codes):
            raise ValueError(f"bad cross protections {rid}")
        seen.add(rid)
        clean_d.append({
            "id": rid,
            "reason": reason[:120],
            "origin_status": ORIGIN_BY_CODE[origin_code],
            "protection_candidates": [PROTECTION_BY_CODE[c] for c in protection_codes],
            "confidence": CONFIDENCE_BY_CODE[confidence_code],
        })
    clean_u = []
    for rid in unresolved:
        rid = str(rid)
        if rid not in expected:
            raise ValueError(f"bad unresolved id {rid}")
        if rid not in clean_u:
            clean_u.append(rid)
    return {"disputes": clean_d, "unresolved_ids": clean_u}


def main() -> int:
    if not os.environ.get("OPENROUTER_API_KEY"):
        raise SystemExit("OPENROUTER_API_KEY unavailable")
    records, supplement = load_records()
    selection = json.loads(SELECTION.read_text(encoding="utf-8"))
    selected_rows = [x for x in selection.get("selected", []) if isinstance(x, dict) and x.get("family")]
    selected = {str(x["family"]): x for x in selected_rows}
    approved = [str(x) for x in (selection.get("approved_families") or list(selected)) if str(x) in selected]
    if "deepseek" not in approved or "qwen" not in approved or len(approved) < 4:
        raise SystemExit("IP-origin backfill requires DeepSeek, Qwen and at least four approved families")
    if selection.get("provider_policy", {}).get("data_collection") != "deny":
        raise SystemExit("data_collection must be deny")

    per_call = float(selection["routine_model_call_cost_ceiling_usd"])
    cumulative = 0.0
    calls: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    complete = True
    batches = [records[i:i+BATCH_SIZE] for i in range(0, len(records), BATCH_SIZE)]
    if len(batches) * len(approved) * 2 > 64:
        raise SystemExit("combined IP inventory exceeds 64-call backfill envelope; split lineage rather than weaken budget guard")

    halted = False
    for batch_index, batch in enumerate(batches):
        expected = {str(x["id"]) for x in batch}
        batch_reviews: dict[str, Any] = {}
        for family_index, family in enumerate(approved):
            role, instruction = ROLE_PROMPTS[(family_index + batch_index) % len(ROLE_PROMPTS)]
            if WORKFLOW_COST_CEILING_USD - cumulative < per_call:
                complete = False
                calls.append({"batch": batch_index, "family": family, "role": role, "status": "WORKFLOW_BUDGET_GUARD"})
                halted = True
                break
            raw, attempt = _call(
                model=selected[family],
                prompt=_prompt(role, instruction, batch),
                selection=selection,
                reasoning={"effort": "none"},
            )
            if isinstance(attempt.get("cost"), (int, float)) and float(attempt["cost"]) >= 0:
                cumulative += float(attempt["cost"])
            attempt.update({"batch": batch_index, "role": role})
            calls.append(attempt)
            if raw is None:
                complete = False
                halted = True
                break
            try:
                items = _validate_specialist(raw, expected)
            except Exception as exc:
                complete = False
                calls.append({"batch": batch_index, "family": family, "role": role, "status": "INVALID_OUTPUT", "detail": str(exc), "cost": 0.0})
                halted = True
                break
            compact = [[item["id"], CODE_BY_ORIGIN[item["origin_status"]], "".join(c for c, label in PROTECTION_BY_CODE.items() if label in item["protection_candidates"]), item["confidence"][0]] for item in items]
            batch_reviews[f"{family}:{role}"] = compact
            findings.extend({"batch": batch_index, "family": family, "role": role, **item} for item in items)

        if batch_reviews and not halted:
            for family in approved:
                if WORKFLOW_COST_CEILING_USD - cumulative < per_call:
                    complete = False
                    calls.append({"batch": batch_index, "family": family, "role": "cross_exam", "status": "WORKFLOW_BUDGET_GUARD"})
                    halted = True
                    break
                raw, attempt = _call(
                    model=selected[family],
                    prompt=_cross_prompt(family, batch, batch_reviews),
                    selection=selection,
                    reasoning={"effort": "none"},
                )
                if isinstance(attempt.get("cost"), (int, float)) and float(attempt["cost"]) >= 0:
                    cumulative += float(attempt["cost"])
                attempt.update({"batch": batch_index, "role": "cross_exam"})
                calls.append(attempt)
                if raw is None:
                    complete = False
                    halted = True
                    break
                try:
                    cross = _validate_cross(raw, expected)
                except Exception as exc:
                    complete = False
                    calls.append({"batch": batch_index, "family": family, "role": "cross_exam", "status": "INVALID_OUTPUT", "detail": str(exc), "cost": 0.0})
                    halted = True
                    break
                findings.append({"batch": batch_index, "family": family, "role": "cross_exam", **cross})

        if halted:
            break

    supplement_count = len((supplement or {}).get("additional_records") or [])
    receipt = {
        "schema": "GardenIPOriginMultiAgentReview/v5",
        "inventory_commit": os.environ.get("GITHUB_SHA"),
        "base_record_count": len(records) - supplement_count,
        "supplement_record_count": supplement_count,
        "combined_record_count": len(records),
        "families": approved,
        "specialist_calls_per_batch": len(approved),
        "cross_examiners_per_batch": len(approved),
        "batch_size": BATCH_SIZE,
        "batch_count": len(batches),
        "maximum_planned_calls": len(batches) * len(approved) * 2,
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
    print(json.dumps({k: receipt[k] for k in ["combined_record_count", "families", "batch_count", "maximum_planned_calls", "actual_cost_usd", "complete"]}, sort_keys=True))
    if not complete:
        raise SystemExit("IP-origin review incomplete; receipt retained for exact resume/repair")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
