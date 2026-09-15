#!/usr/bin/env python3
"""Budget-correct multi-family OpenRouter review for Garden public IP-origin data.

The base inventory may be extended by IP_ORIGIN_SUPPLEMENT.json. Every batch
receives all four specialist dimensions across the approved family set, followed
by one independent cross-examination per family. Role-to-family assignment
rotates by batch. Proposal evidence only: no filing, grant, ownership,
infringement, enforceability, or semantic admission is created here.
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
    ("novelty_prior_art", "Find the genuinely new Garden-origin technical delta versus known prior ideas. A new name or old ingredient is not novelty. State closest known basis."),
    ("patent_scope", "Screen candidate patent relevance only: technical character, concrete mechanism, novelty/non-obviousness risk, and claim narrowing. Never invent filing/grant status."),
    ("copyright_other_rights", "Separate idea from expression and classify plausible patent/copyright/trade-secret/trademark/design-right/contract routes or abstract-idea/no-automatic-exclusivity."),
    ("duplicate_lineage", "Find aliases, renamed descendants, decompositions, merged families, and historical renumbering. Reject double-counting and prefer canonical provenance lineage."),
]
ALLOWED_ORIGIN = {"GARDEN_ORIGIN_SUPPORTED","GARDEN_ORIGIN_PLAUSIBLE","ORIGIN_UNCERTAIN","LIKELY_PREEXISTING","DUPLICATE_OR_ALIAS"}


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
    return f"""You are one independent reviewer in a Garden IP-origin audit.
ROLE={role}
{instruction}
Boundaries: Garden-origin is provenance, not automatic legal exclusivity. Known science, equations, standards, generic algorithms, and third-party technology are not Garden inventions merely because Garden uses them. A concrete new combination may still be a candidate when ingredients are old. No model may create patent/copyright filing, grant, ownership, infringement, enforceability, or legal-opinion status. Be adversarial and concise.
Return ONLY JSON {{"items":[...]}} with exactly one item per ID. Each item contains only id, origin_status, protection_candidates, prior_art_basis, confidence, note. origin_status in {sorted(ALLOWED_ORIGIN)}; confidence LOW/MEDIUM/HIGH. protection_candidates array values only from PATENT_CANDIDATE, COPYRIGHT_EXPRESSION, TRADE_SECRET_CANDIDATE, TRADEMARK_CANDIDATE, DESIGN_RIGHT_CANDIDATE, CONTRACT_LICENSE, ABSTRACT_IDEA_NO_AUTOMATIC_EXCLUSIVITY. Keep prior_art_basis and note under 12 words each.
Candidates:\n{json.dumps(batch, ensure_ascii=False, separators=(',', ':'))}
"""


def _validate(raw: dict[str, Any], expected: set[str]) -> list[dict[str, Any]]:
    items = raw.get("items")
    if not isinstance(items, list): raise ValueError("missing items")
    seen: set[str] = set()
    for row in items:
        if not isinstance(row, dict): raise ValueError("item not object")
        rid = str(row.get("id", ""))
        if rid not in expected or rid in seen: raise ValueError(f"bad id {rid}")
        if row.get("origin_status") not in ALLOWED_ORIGIN: raise ValueError(f"bad origin_status {rid}")
        if row.get("confidence") not in {"LOW","MEDIUM","HIGH"}: raise ValueError(f"bad confidence {rid}")
        if not isinstance(row.get("protection_candidates"), list): raise ValueError(f"bad protection_candidates {rid}")
        seen.add(rid)
    if seen != expected: raise ValueError(f"missing ids {sorted(expected-seen)}")
    return items


def main() -> int:
    if not os.environ.get("OPENROUTER_API_KEY"): raise SystemExit("OPENROUTER_API_KEY unavailable")
    records, supplement = load_records()
    selection = json.loads(SELECTION.read_text(encoding="utf-8"))
    selected_rows = [x for x in selection.get("selected", []) if isinstance(x, dict) and x.get("family")]
    selected = {str(x["family"]):x for x in selected_rows}
    approved = [str(x) for x in (selection.get("approved_families") or list(selected)) if str(x) in selected]
    if "deepseek" not in approved or "qwen" not in approved or len(approved) < 4:
        raise SystemExit("IP-origin backfill requires DeepSeek, Qwen and at least four approved families")
    if selection.get("provider_policy",{}).get("data_collection") != "deny": raise SystemExit("data_collection must be deny")

    per_call = float(selection["routine_model_call_cost_ceiling_usd"])
    cumulative=0.0; calls=[]; findings=[]; complete=True
    batches=[records[i:i+BATCH_SIZE] for i in range(0,len(records),BATCH_SIZE)]
    if len(batches)*len(approved)*2 > 64:
        raise SystemExit("combined IP inventory exceeds 64-call backfill envelope; split lineage rather than weaken budget guard")

    halted = False
    for batch_index,batch in enumerate(batches):
        expected={str(x["id"]) for x in batch}; batch_reviews={}
        for family_index,family in enumerate(approved):
            role,instruction=ROLE_PROMPTS[(family_index+batch_index)%len(ROLE_PROMPTS)]
            if WORKFLOW_COST_CEILING_USD-cumulative < per_call:
                complete=False; calls.append({"batch":batch_index,"family":family,"role":role,"status":"WORKFLOW_BUDGET_GUARD"}); continue
            raw,attempt=_call(model=selected[family],prompt=_prompt(role,instruction,batch),selection=selection,reasoning={"effort":"none"})
            if isinstance(attempt.get("cost"),(int,float)) and float(attempt["cost"])>=0: cumulative+=float(attempt["cost"])
            attempt.update({"batch":batch_index,"role":role}); calls.append(attempt)
            if raw is None:
                complete=False; halted=True; break
            try: items=_validate(raw,expected)
            except Exception as exc:
                complete=False; calls.append({"batch":batch_index,"family":family,"role":role,"status":"INVALID_OUTPUT","detail":str(exc),"cost":0.0}); continue
            batch_reviews[f"{family}:{role}"]=items
            findings.extend({"batch":batch_index,"family":family,"role":role,**item} for item in items)
        if batch_reviews and not halted:
            digest=json.dumps(batch_reviews,ensure_ascii=False,separators=(",",":"))
            for family in approved:
                if WORKFLOW_COST_CEILING_USD-cumulative < per_call:
                    complete=False; calls.append({"batch":batch_index,"family":family,"role":"cross_exam","status":"WORKFLOW_BUDGET_GUARD"}); continue
                prompt=f"""You are the {family} cross-examiner for one Garden IP-origin batch. Challenge overclaim, prior-art blindness, duplicate/alias counting, protection-category mistakes, and unsupported confidence. Do not create legal rights. Return ONLY JSON with keys batch, disputed_ids, corrections, unresolved_ids, confidence. Keep concise.\n{digest}"""
                raw,attempt=_call(model=selected[family],prompt=prompt,selection=selection,reasoning={"effort":"none"})
                if isinstance(attempt.get("cost"),(int,float)) and float(attempt["cost"])>=0: cumulative+=float(attempt["cost"])
                attempt.update({"batch":batch_index,"role":"cross_exam"}); calls.append(attempt)
                if raw is None:
                    complete=False; halted=True; break
                findings.append({"batch":batch_index,"family":family,"role":"cross_exam","review":raw})

        if halted:
            break

    receipt={"schema":"GardenIPOriginMultiAgentReview/v4","inventory_commit":os.environ.get("GITHUB_SHA"),"base_record_count":len(records)-(len((supplement or {}).get("additional_records") or [])),"supplement_record_count":len((supplement or {}).get("additional_records") or []),"combined_record_count":len(records),"families":approved,"specialist_calls_per_batch":len(approved),"cross_examiners_per_batch":len(approved),"batch_size":BATCH_SIZE,"batch_count":len(batches),"maximum_planned_calls":len(batches)*len(approved)*2,"workflow_cost_ceiling_usd":WORKFLOW_COST_CEILING_USD,"actual_cost_usd":round(cumulative,8),"provider_policy":{"data_collection":"deny"},"complete":complete,"calls":calls,"findings":findings,"semantic_delta_admitted":False,"patent_status_admitted":False,"legal_opinion":False}
    OUT.write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({k:receipt[k] for k in ["combined_record_count","families","batch_count","maximum_planned_calls","actual_cost_usd","complete"]},sort_keys=True))
    if not complete: raise SystemExit("IP-origin review incomplete; receipt retained for exact resume/repair")
    return 0

if __name__=="__main__": raise SystemExit(main())
